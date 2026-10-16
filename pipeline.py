"""
Módulo Orquestador del Pipeline Agrometeorológico y Financiero (RF-02).
Ejecuta de forma secuencial y trazable todo el flujo: descarga, preprocesamiento,
física de suelos, entrenamiento, calibración, inferencia, geometría y finanzas.
Incorpora caché en memoria para inferencia de latencia ultrabaja,
soporte para parcelas irregulares y extracción de series reales de lluvia (RF-04).
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd

from config.settings import (
    GeoConfig,
    AgroConfig,
    SoilConfig,
    MacroClimateConfig,
    MagaPriceConfig,
    PathConfig,
    SemaforoConfig,
    GEO_CONFIG,
    AGRO_CONFIG,
    SOIL_CONFIG,
    MACRO_CONFIG,
    MAGA_CONFIG,
    SEMAFORO_CONFIG,
    PATH_CONFIG,
)
from core.data_fetcher import fetch_weather, fetch_macro
from core.maga_scraper import fetch_maga_white_corn_price
from core.soil_balance import SoilProfile, build_dataset
from core.models import (
    make_xgb,
    make_logit,
    cross_validate,
    train_calibrated_model,
    enso_phase,
    semaforo,
    proyectar_futuro,
)
from core.agronomy_economics import (
    TerrainModel,
    calculate_sowing_density,
    calculate_financial_projection,
    calcular_analisis_pluviometrico,
)
from core.input_validator import (
    validate_and_sanitize,
    ValidationError,
    get_validation_summary,
)
from core.rain_streak_analyzer import (
    analyze_rain_streaks,
    generate_streak_pdf_section,
    RainStreakReport,
)
from reporting.visualizer import (
    plot_water_balance_window,
    plot_terrain_layout,
    plot_calibration,
)
from reporting.pdf_exporter import export_pdf_report


@dataclass
class PipelineResult:
    """Contenedor de resultados integrales del pipeline."""
    success: bool
    sowing_date: str
    lat: float
    lon: float
    probabilidad: float
    semaforo_estado: str
    semaforo_color: str
    semaforo_accion: str
    fase_enso: str
    terreno: TerrainModel
    densidad: Dict[str, Any]
    financiero: Dict[str, Any]
    proyecciones_futuras: list
    cv_results: Dict[str, Any]
    mejor_modelo: str
    chart_paths: Dict[str, Any]
    timeline: Dict[str, Any]
    criterios_algoritmo: Dict[str, Any] = field(default_factory=dict)
    evaluacion_historica: Dict[str, Any] = field(default_factory=dict)
    report_pdf_path: Optional[str] = None
    capital_warnings: List[str] = field(default_factory=list)
    validation_summary: Dict[str, Any] = field(default_factory=dict)
    rain_streak_report: Optional[Dict[str, Any]] = None


class AgroViabilityPipeline:
    """
    Orquestador principal que ejecuta el análisis agrometeorológico y financiero
    ante cada petición del usuario (RF-02).
    """
    _cache_store = {}

    def __init__(
        self,
        geo_cfg: GeoConfig = GEO_CONFIG,
        agro_cfg: AgroConfig = AGRO_CONFIG,
        soil_cfg: SoilConfig = SOIL_CONFIG,
        macro_cfg: MacroClimateConfig = MACRO_CONFIG,
        maga_cfg: MagaPriceConfig = MAGA_CONFIG,
        semaforo_cfg: SemaforoConfig = SEMAFORO_CONFIG,
        path_cfg: PathConfig = PATH_CONFIG,
    ):
        self.geo_cfg = geo_cfg
        self.agro_cfg = agro_cfg
        self.soil_cfg = soil_cfg
        self.macro_cfg = macro_cfg
        self.maga_cfg = maga_cfg
        self.semaforo_cfg = semaforo_cfg
        self.path_cfg = path_cfg
        self.soil = SoilProfile(self.soil_cfg)

    def extract_timeline(self, ds: pd.DataFrame, sowing_date_str: str) -> Dict[str, Any]:
        """
        Extrae la serie agrometeorológica real de 60 días para la gráfica web (RF-04).
        Si la fecha es observada, extrae los días reales; si es futura,
        calcula la mediana climatológica histórica diaria para cada uno de los 60 días.
        """
        s_ts = pd.to_datetime(sowing_date_str)
        w_days = self.agro_cfg.window_days # 60 días
        kc_curve = self.agro_cfg.kc_curve

        sub = ds[(ds["time"] >= s_ts) & (ds["time"] < s_ts + pd.Timedelta(days=w_days))].copy()
        
        if len(sub) >= w_days:
            # Serie histórica real observada
            p_daily = sub["precip_mm"].round(1).tolist()
            p_acc = sub["precip_mm"].cumsum().round(1).tolist()
            etc = kc_curve[:len(sub)] * sub["et0_mm"].values
            etc_acc = np.cumsum(etc).round(1).tolist()
            soil_frac = sub["humedad_suelo_frac"].round(2).tolist()
        else:
            # Proyección climatológica de alta precisión día por día a partir de 45 años de reanálisis ERA5
            p_daily = []
            p_acc = []
            etc_acc = []
            soil_frac = []
            acc_p = 0.0
            acc_etc = 0.0

            start_doy = s_ts.dayofyear
            for i in range(w_days):
                cur_doy = ((start_doy - 1 + i) % 365) + 1
                # Filtrar todos los años históricos en este día del año
                day_history = ds[ds["time"].dt.dayofyear == cur_doy]
                
                rain = float(day_history["precip_mm"].median()) if not day_history.empty else 2.5
                et0 = float(day_history["et0_mm"].median()) if not day_history.empty else 4.2
                soil = float(day_history["humedad_suelo_frac"].median()) if not day_history.empty else 0.65
                
                acc_p += rain
                etc = kc_curve[i] * et0
                acc_etc += etc

                p_daily.append(round(rain, 1))
                p_acc.append(round(acc_p, 1))
                etc_acc.append(round(acc_etc, 1))
                soil_frac.append(round(soil, 2))

        return {
            "days": list(range(1, w_days + 1)),
            "precipDaily": p_daily,
            "precipAcc": p_acc,
            "etcAcc": etc_acc,
            "soilFrac": soil_frac
        }

    def run(
        self,
        sowing_date_str: str = "2026-06-01",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        shape_type: str = "rectangulo",
        terrain_sides: Optional[List[float]] = None,
        terrain_width_m: float = 100.0,
        terrain_length_m: float = 70.0,
        capital_disponible_q: float = 6500.0,
        tipo_maiz: str = "blanco",
        use_cache: bool = True,
        force_refresh: bool = False,
        generate_pdf: bool = True,
    ) -> PipelineResult:
        """
        Ejecuta el ciclo de cómputo completo para una fecha y parcela dada.
        """
        # 0. Validación y sanitización estricta de entradas (RF-01 / Anti-inyección / Límites)
        validated = validate_and_sanitize(
            sowing_date=sowing_date_str,
            lat=lat if lat is not None else self.geo_cfg.lat,
            lon=lon if lon is not None else self.geo_cfg.lon,
            shape_type=shape_type,
            sides=terrain_sides,
            width=terrain_width_m,
            length=terrain_length_m,
            capital=capital_disponible_q,
            corn_type=tipo_maiz,
        )
        sowing_date_str = validated.sowing_date
        active_lat = validated.lat
        active_lon = validated.lon
        shape_type = validated.shape_type
        terrain_sides = validated.sides
        terrain_width_m = validated.width
        terrain_length_m = validated.length
        capital_disponible_q = validated.capital
        tipo_maiz = validated.corn_type
        capital_warnings = validated.capital_warnings
        validation_summary = get_validation_summary(validated)

        geo_active = GeoConfig(
            lat=active_lat,
            lon=active_lon,
            start_year=self.geo_cfg.start_year,
            timezone=self.geo_cfg.timezone,
            municipality=self.geo_cfg.municipality,
        )

        print("\n" + "=" * 70)
        print("  SISTEMA ABIERTO DE VIABILIDAD AGRÍCOLA - JUTIAPA (GUATEMALA)")
        print(f"  Coordenadas: ({geo_active.lat}, {geo_active.lon}) | Fecha: {sowing_date_str}")
        print("=" * 70)

        cache_key = (round(active_lat, 3), round(active_lon, 3))

        # Verificar si el modelo y dataset ya están calibrados en memoria
        if use_cache and not force_refresh and cache_key in self._cache_store:
            print("  [Caché en Memoria] Reutilizando modelo calibrado y dataset procesado...")
            ds, calibrated_model, feats_best, best_model_name, cv_res, train_df = self._cache_store[cache_key]
        else:
            # 1. Descarga y Adquisición de Clima ERA5
            print("\n[Paso 1/5] Adquisición de series meteorológicas ERA5...")
            df_weather = fetch_weather(
                geo=geo_active,
                cache_dir=self.path_cfg.cache_dir,
                use_cache=use_cache,
                force_refresh=force_refresh
            )

            # 2. Descarga de Índices ENSO de NOAA PSL
            print("\n[Paso 2/5] Descarga y alineación de índices macroclimáticos ENSO...")
            df_macro = fetch_macro(
                macro_cfg=self.macro_cfg,
                cache_dir=self.path_cfg.cache_dir,
                use_cache=use_cache,
                force_refresh=force_refresh
            )

            # 3. Modelado Hidrológico y Balance de Suelos (FAO-56)
            print("\n[Paso 3/5] Construcción del balance hídrico y perfil edáfico Saxton & Rawls...")
            ds = build_dataset(df_weather, df_macro, self.soil, self.agro_cfg)
            train_df = ds.dropna(subset=self.macro_cfg.features_full + ["target"]).reset_index(drop=True)

            print(f"  [OK] Muestras válidas: {len(train_df)} | Años evaluados: {train_df['year'].nunique()}")
            print(f"  [OK] Tasa histórica de éxito: {train_df['target'].mean()*100:.1f}%")
            print(f"  [OK] Fallos por déficit/sequía: {train_df['fallo_sequia'].mean()*100:.1f}% | Exceso/anegamiento: {train_df['fallo_exceso'].mean()*100:.1f}%")

            # 4. Validación Cruzada Temporal (GroupKFold por años) y Calibración
            print("\n[Paso 4/5] Validación cruzada temporal out-of-fold y selección de modelo...")
            configs = {
                "Logística local": (list(self.macro_cfg.features_local), make_logit),
                "Logística local+ENSO": (self.macro_cfg.features_full, make_logit),
                "XGBoost local": (list(self.macro_cfg.features_local), make_xgb),
                "XGBoost local+ENSO": (self.macro_cfg.features_full, make_xgb),
            }
            cv_res = {}
            for name, (feats, mk_fn) in configs.items():
                cv_res[name] = cross_validate(train_df, feats, mk_fn)
                print(f"    - {name:<22} AUC={cv_res[name]['auc']:.3f} | BSS={cv_res[name]['bss']:+.3f}")

            best_model_name = max(cv_res, key=lambda k: cv_res[k]["bss"])
            print(f"\n  [OK] Mejor configuración predictiva: {best_model_name} (BSS: {cv_res[best_model_name]['bss']:+.3f})")

            feats_best, mk_best = configs[best_model_name]
            calibrated_model = train_calibrated_model(train_df, feats_best, mk_best)

            # Almacenar en caché de memoria para consultas instantáneas subsiguientes
            self._cache_store[cache_key] = (ds, calibrated_model, feats_best, best_model_name, cv_res, train_df)

        # Proyección futura de los próximos meses
        proyecciones = proyectar_futuro(
            ds,
            calibrated_model,
            feats_best,
            horizon_months=5,
            sem_cfg=self.semaforo_cfg
        )

        # 5. Inferencia para la Fecha de Siembra Seleccionada
        sowing_ts = pd.to_datetime(sowing_date_str)
        report_row = ds[ds["time"] == sowing_ts]

        if report_row.empty or report_row.dropna(subset=feats_best).empty:
            print(f"  [Aviso] La fecha {sowing_date_str} es futura o no tiene registro directo. Usando climatología histórica de {sowing_ts.strftime('%B')} y señal ENSO...")
            m_sow = sowing_ts.month
            clima_mes = ds[ds["month"] == m_sow]
            last_valid = ds.dropna(subset=["mei_lag1", "mei_trend"]).iloc[-1]
            vector_estacional = pd.Series({
                "precip_acc_15d": clima_mes["precip_acc_15d"].median() if not clima_mes.empty else ds["precip_acc_15d"].median(),
                "precip_acc_30d": clima_mes["precip_acc_30d"].median() if not clima_mes.empty else ds["precip_acc_30d"].median(),
                "balance_hidrico_30d": clima_mes["balance_hidrico_30d"].median() if not clima_mes.empty else ds["balance_hidrico_30d"].median(),
                "humedad_suelo_frac": clima_mes["humedad_suelo_frac"].median() if not clima_mes.empty else ds["humedad_suelo_frac"].median(),
                "dry_spell_len": clima_mes["dry_spell_len"].median() if not clima_mes.empty else ds["dry_spell_len"].median(),
                "doy_sin": np.sin(2 * np.pi * sowing_ts.dayofyear / 365.25),
                "doy_cos": np.cos(2 * np.pi * sowing_ts.dayofyear / 365.25),
                "mei_lag1": last_valid["mei_lag1"],
                "mei_trend": last_valid["mei_trend"]
            })
            x_in = vector_estacional[feats_best].astype(float).values.reshape(1, -1)
            prob = float(calibrated_model.predict_proba(x_in)[0, 1])
            fase = enso_phase(vector_estacional.get("mei_lag1", np.nan))
        else:
            report_row = report_row.iloc[0]
            prob = float(calibrated_model.predict_proba(report_row[feats_best].astype(float).values.reshape(1, -1))[0, 1])
            fase = enso_phase(report_row.get("mei_lag1", np.nan))

        estado, color, accion = semaforo(prob, fase, sem_cfg=self.semaforo_cfg)

        # 6. Modelado del Terreno (RF-05) y Densidad (RF-06)
        print("\n[Paso 5/5] Cálculos agronómicos y financieros...")
        terrain = TerrainModel(
            shape_type=shape_type,
            ancho_m=terrain_width_m,
            largo_m=terrain_length_m,
            sides=terrain_sides or [terrain_width_m, terrain_length_m, terrain_width_m, terrain_length_m]
        )
        densidad = calculate_sowing_density(terrain, prob, color)

        # 7. Proyección Financiera con Precios Oficiales MAGA (RF-07)
        # Actualización automática mediante scraper oficial del MAGA (La Terminal)
        try:
            live_maga = fetch_maga_white_corn_price(timeout_sec=3)
            if live_maga and live_maga.get("precio"):
                self.maga_cfg.precio_qq_maiz_blanco = float(live_maga["precio"])
                self.maga_cfg.fecha_actualizacion = str(live_maga.get("fecha", "09/10/2026"))
                self.maga_cfg.fuente_oficial = f"MAGA DIPLAN - Precios Diarios ({live_maga.get('mercado', 'La Terminal')})"
        except Exception:
            pass

        financiero = calculate_financial_projection(
            terrain=terrain,
            viability_prob=prob,
            capital_inversion=capital_disponible_q,
            maga_cfg=self.maga_cfg,
            tipo_maiz="blanco",
        )

        # Criterios agrometeorológicos aplicados (exactos del algoritmo principal)
        criterios_algoritmo = {
            "eta_etc_min": self.agro_cfg.eta_etc_min,
            "excess_mm_day": self.agro_cfg.excess_mm_day,
            "waterlog_max_days": self.agro_cfg.waterlog_max_days,
            "ventana_dias": self.agro_cfg.window_days,
            "fallow_kc": self.agro_cfg.fallow_kc,
            "suelo_textura": f"{self.soil_cfg.clay_pct}% Arcilla, {self.soil_cfg.sand_pct}% Arena, {self.soil_cfg.om_pct}% MO",
            "prob_optimo_min": self.semaforo_cfg.prob_optimo_min,
            "prob_alerta_min": self.semaforo_cfg.prob_alerta_min,
        }

        # Comprobación de resultado histórico real (si ya transcurrieron 60 días para la fecha en la serie observada)
        evaluacion_historica = {
            "disponible": False,
            "eta_etc_real": None,
            "dias_anegamiento_real": None,
            "fallo_sequia": None,
            "fallo_exceso": None,
            "resultado_real": "Fecha futura o periodo sin cierre de 60 días",
            "motivo_fallo": None,
            "nota_discrepancia": None,
        }

        row_eval = ds[ds["time"] == sowing_ts]
        if not row_eval.empty and pd.notna(row_eval.iloc[0].get("eta_etc")):
            r_obs = row_eval.iloc[0]
            eta_val = float(r_obs["eta_etc"])
            wl_val = int(r_obs["dias_anegamiento"])
            f_seq = bool(r_obs["fallo_sequia"])
            f_exc = bool(r_obs["fallo_exceso"])
            es_viable = bool(r_obs["target"] == 1.0)

            res_str = "VIABLE" if es_viable else "FRACASO"
            if f_seq:
                motivo = f"Déficit hídrico: relación hídrica alcanzó {eta_val:.2f}, menor al umbral estricto de {self.agro_cfg.eta_etc_min:.2f}"
            elif f_exc:
                motivo = f"Exceso hídrico: {wl_val} días de saturación, mayor al umbral máximo de {self.agro_cfg.waterlog_max_days} días"
            else:
                motivo = "Satisfactorio: Demanda hídrica cumplida sin anegamiento crítico"

            nota = (
                f"El modelo evaluó las condiciones previas a la siembra con una probabilidad pronosticada de {prob*100:.1f}% con dictamen {estado}. "
                f"En la realidad observada durante los 60 días subsiguientes, la cobertura de demanda hídrica fue de {eta_val:.2f} "
                f"con {wl_val} días de anegamiento, resultando en {res_str} respecto al umbral mínimo de {self.agro_cfg.eta_etc_min:.2f}."
            )

            evaluacion_historica = {
                "disponible": True,
                "eta_etc_real": round(eta_val, 3),
                "dias_anegamiento_real": wl_val,
                "fallo_sequia": f_seq,
                "fallo_exceso": f_exc,
                "resultado_real": res_str,
                "motivo_fallo": motivo,
                "nota_discrepancia": nota,
            }

        # 8. Extraer Serie de Lluvias Real de 60 Días (RF-04) y Ciclo Fenológico Completo de 120 Días
        timeline_data = self.extract_timeline(ds, sowing_date_str)

        # Extracción de la serie diaria de 120 días del ciclo del maíz para análisis de rachas
        s_ts = pd.to_datetime(sowing_date_str)
        cycle_days = 120
        sub_120 = ds[(ds["time"] >= s_ts) & (ds["time"] < s_ts + pd.Timedelta(days=cycle_days))].copy()

        if len(sub_120) >= cycle_days:
            p_120 = sub_120["precip_mm"].round(2).tolist()
        else:
            # Reanálisis diario histórico de 45 años día por día para cada uno de los 120 días
            p_120 = []
            start_doy = s_ts.dayofyear
            for i in range(cycle_days):
                cur_doy = ((start_doy - 1 + i) % 365) + 1
                day_history = ds[ds["time"].dt.dayofyear == cur_doy]
                r_val = float(day_history["precip_mm"].median()) if not day_history.empty else 2.5
                p_120.append(round(r_val, 2))

        # Ejecutar análisis especializado de rachas pluviométricas y distribución fenológica
        streak_report = analyze_rain_streaks(p_120, sowing_date_str)
        streak_section = generate_streak_pdf_section(streak_report)

        # CALIBRACIÓN RIGUROSA CONTRA FALSOS POSITIVOS Y FALSOS NEGATIVOS (Calderas / Corredor Seco):
        # El maíz no tolera ni sequía extrema ni exceso anegante.
        # Si el análisis fenológico detecta fallas críticas en germinación (días 1-15) o floración R1 (días 56-75):
        if streak_report.overall_verdict == "NO APTO PARA SIEMBRA" or len(streak_report.critical_alerts) > 0:
            prob = min(prob, 0.35)  # Castigo de probabilidad para evitar falso positivo
            estado = "NO SEMBRAR"
            color = "Rojo"
            alerta_msg = streak_report.critical_alerts[0] if streak_report.critical_alerts else "Falla crítica por rachas hídricas en fases fenológicas cardinales."
            accion = f"DICTAMEN ADVERSO (Fallo Fenológico): {alerta_msg}. No se recomienda siembra a temporal."
        elif streak_report.overall_verdict == "SIEMBRA CON PRECAUCIÓN":
            if color == "Verde":
                color = "Amarillo"
                estado = "CONDICIONADO O EN ALERTA"
                prob = min(prob, 0.74)
                issue_msg = streak_report.stages[0].issues[0] if (streak_report.stages and streak_report.stages[0].issues) else "Riesgo moderado de canícula o déficit."
                accion = f"CONDICIONADO: {issue_msg}. Adoptar variedades precoces y técnicas de retención de humedad."

        # 9. Generación de Gráficos (RF-03, RF-04, RF-05)
        chart_paths = {}
        chart_paths["water_balance"] = plot_water_balance_window(
            df=ds,
            sowing_date_str=sowing_date_str,
            agro_cfg=self.agro_cfg,
            output_path=self.path_cfg.output_dir / "balance_hidrico_siembra.png"
        )
        chart_paths["terrain"] = plot_terrain_layout(
            terrain=terrain,
            output_path=self.path_cfg.output_dir / "plano_terreno.png"
        )
        chart_paths["calibration"] = plot_calibration(
            y_true=train_df["target"].values,
            y_prob=cv_res[best_model_name]["oof"],
            model_name=best_model_name,
            output_path=self.path_cfg.output_dir / "calibracion_modelo.png"
        )

        # 10. Exportación del Informe en PDF (RF-08)
        report_data = {
            "municipio": geo_active.municipality,
            "lat": geo_active.lat,
            "lon": geo_active.lon,
            "fecha_siembra": sowing_date_str,
            "probabilidad": prob,
            "semaforo_estado": estado,
            "semaforo_color": color,
            "semaforo_accion": accion,
            "fase_enso": fase,
            "criterios_algoritmo": criterios_algoritmo,
            "evaluacion_historica": evaluacion_historica,
            "terreno": {
                "forma": terrain.descripcion_forma,
                "shape_type": terrain.shape_type,
                "lados": terrain.sides,
                "ancho_m": terrain.ancho_m,
                "largo_m": terrain.largo_m,
                "area_m2": terrain.area_m2,
                "manzanas": terrain.manzanas,
                "hectareas": terrain.hectareas,
                "perimetro_m": terrain.perimetro_m,
            },
            "densidad": densidad,
            "financiero": financiero,
            "analisis_pluviometrico": calcular_analisis_pluviometrico(sowing_date_str, fase),
            "capital_warnings": capital_warnings,
            "validation_summary": validation_summary,
            "analisis_rachas": streak_section,
        }

        pdf_path = None
        if generate_pdf:
            pdf_path = export_pdf_report(report_data, chart_paths, self.path_cfg.output_dir / "Informe_Viabilidad_Maiz_Jutiapa.pdf")

        return PipelineResult(
            success=True,
            sowing_date=sowing_date_str,
            lat=geo_active.lat,
            lon=geo_active.lon,
            probabilidad=prob,
            semaforo_estado=estado,
            semaforo_color=color,
            semaforo_accion=accion,
            fase_enso=fase,
            terreno=terrain,
            densidad=densidad,
            financiero=financiero,
            proyecciones_futuras=proyecciones,
            cv_results=cv_res,
            mejor_modelo=best_model_name,
            chart_paths=chart_paths,
            timeline=timeline_data,
            criterios_algoritmo=criterios_algoritmo,
            evaluacion_historica=evaluacion_historica,
            report_pdf_path=str(pdf_path) if pdf_path else None,
            capital_warnings=capital_warnings,
            validation_summary=validation_summary,
            rain_streak_report=streak_section,
        )
