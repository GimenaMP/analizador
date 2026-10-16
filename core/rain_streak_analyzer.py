"""
Módulo de Análisis de Rachas Hídricas y Distribución Fenológica del Maíz Blanco.
Diseñado específicamente para el municipio de Calderas, San José Acatempa (Jutiapa),
ubicado en la franja crítica del Corredor Seco de Guatemala.

Este módulo implementa el análisis de rachas consecutivas de precipitación y sequía
a lo largo de las 4 etapas fenológicas del maíz (120 días). Evalúa la distribución
temporal del agua, detecta la canícula intra-estival (julio-agosto), calcula riesgos
de asfixia radicular, desecación de polen y pudrición de mazorca, y genera resúmenes
históricos multianuales a partir de series climáticas ERA5.
"""
from dataclasses import dataclass, field
import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable
import numpy as np
import pandas as pd


@dataclass
class StageAnalysis:
    """Análisis agroclimático detallado de una etapa fenológica específica."""
    stage_name: str
    stage_days: str  # e.g. "Días 1-15"
    total_rain_mm: float
    avg_daily_rain_mm: float
    max_consecutive_dry_days: int  # días con < 1.5 mm
    max_consecutive_wet_days: int  # días con > 15.0 mm
    longest_dry_streak_start_day: int
    longest_wet_streak_start_day: int
    rain_adequacy: str  # "Déficit Severo", "Déficit Moderado", "Adecuado", "Exceso Moderado", "Exceso Severo"
    risk_level: str  # "Bajo", "Moderado", "Alto", "Crítico"
    issues: List[str]  # Problemas agrometeorológicos identificados
    recommendations: List[str]  # Directivas de manejo agronómico


@dataclass
class RainStreakReport:
    """Informe integral de rachas pluviométricas y fenología a 120 días."""
    overall_verdict: str  # "APTO PARA SIEMBRA", "SIEMBRA CON PRECAUCIÓN", "NO APTO PARA SIEMBRA"
    overall_risk_score: float  # 0.0 (peor) a 1.0 (óptimo)
    stages: List[StageAnalysis]
    critical_alerts: List[str]  # Alertas bloqueantes o letales para el cultivo
    canicula_detected: bool
    canicula_severity: str  # "Ninguna", "Leve", "Moderada", "Severa"
    canicula_days: int
    total_cycle_rain_mm: float
    rain_distribution_quality: str  # "Buena", "Irregular", "Deficiente"


@dataclass
class HistoricalStreakSummary:
    """Resumen estadístico de patrones históricos de rachas en múltiples años ERA5."""
    years_analyzed: int
    pct_years_canicula: float
    avg_canicula_duration_days: float
    pct_years_excess_rain: float
    avg_longest_dry_streak: float
    avg_longest_wet_streak: float
    pct_years_viable: float
    worst_year: int
    best_year: int


def _find_longest_streak(series: List[float], condition_fn: Callable[[float], bool]) -> Tuple[int, int]:
    """
    Identifica la racha continua más larga en una serie numérica que satisface una condición dada.

    Args:
        series: Lista de valores diarios (e.g. precipitación en mm).
        condition_fn: Función booleana evaluada en cada día (e.g. lambda x: x < 1.5).

    Returns:
        Tuple[int, int]: (duración_máxima_en_días, índice_inicial_0_based).
                         Si no se registra ningún día coincidente, retorna (0, 0).
    """
    max_len = 0
    start_idx = 0
    curr_len = 0
    curr_start = 0

    for i, val in enumerate(series):
        if condition_fn(val):
            if curr_len == 0:
                curr_start = i
            curr_len += 1
            if curr_len > max_len:
                max_len = curr_len
                start_idx = curr_start
        else:
            curr_len = 0

    return max_len, start_idx


def _classify_rain_adequacy(total_mm: float, min_req_mm: float, max_req_mm: float) -> str:
    """
    Clasifica la suficiencia pluviométrica comparando la lámina recibida
    contra el rango hídrico óptimo de la etapa fenológica.

    Args:
        total_mm: Precipitación total acumulada en la etapa (mm).
        min_req_mm: Requerimiento hídrico mínimo para desarrollo normal (mm).
        max_req_mm: Límite superior sin comprometer la oxigenación edáfica (mm).

    Returns:
        str: "Déficit Severo", "Déficit Moderado", "Adecuado", "Exceso Moderado" o "Exceso Severo".
    """
    if total_mm < 0.60 * min_req_mm:
        return "Déficit Severo"
    elif total_mm < min_req_mm:
        return "Déficit Moderado"
    elif total_mm <= max_req_mm:
        return "Adecuado"
    elif total_mm <= 1.40 * max_req_mm:
        return "Exceso Moderado"
    else:
        return "Exceso Severo"


def analyze_rain_streaks(daily_rain_mm: List[float], sowing_date: str) -> RainStreakReport:
    """
    Analiza una serie diaria de precipitación de 120 días a partir de la fecha de siembra
    y determina el impacto fisiológico de rachas secas y de anegamiento en maíz blanco.

    Considera las 4 etapas fenológicas para Calderas, San José Acatempa (Jutiapa):
      1. Germinación y Emergencia (Días 1-15): 20-40 mm req.
         Falla si >5 días consecutivos >15 mm/día o >7 días consecutivos <1 mm/día.
      2. Desarrollo Vegetativo (Días 16-55): 150-250 mm req.
         Falla si >8 días consecutivos >20 mm/día o >10 días consecutivos <1.5 mm/día.
         Alerta si se detecta racha seca de canícula >5 días <1.5 mm/día.
      3. Floración y Polinización - CRÍTICA (Días 56-75): 80-120 mm req.
         Falla si >4 días consecutivos <2 mm/día (desecación de polen, caída de rendimiento 6-10%/día)
         o >6 días consecutivos >25 mm/día (lavado de polen y daño floral).
      4. Llenado de Grano (Días 76-120): 150-250 mm req.
         Falla si >6 días consecutivos <1.5 mm/día en días 76-95 (aborto de grano).
         Alerta si >10 días consecutivos >15 mm/día (riesgo de pudrición de mazorca en días 76-120).

    Args:
        daily_rain_mm: Lista o vector con al menos 120 valores de lluvia diaria (mm).
        sowing_date: Fecha de siembra en formato 'AAAA-MM-DD'.

    Returns:
        RainStreakReport: Diagnóstico integral por etapa y dictamen general.
    """
    if daily_rain_mm is None or len(daily_rain_mm) < 120:
        recibidos = len(daily_rain_mm) if daily_rain_mm is not None else 0
        raise ValueError(
            f"La serie diaria de precipitación debe contener al menos 120 días para "
            f"evaluar el ciclo de cultivo completo (se recibieron {recibidos} días)."
        )

    # Sanitización de datos numéricos (garantizar floats no negativos)
    clean_series: List[float] = []
    for idx, v in enumerate(daily_rain_mm[:120]):
        try:
            val = float(v)
            clean_series.append(max(0.0, val) if not np.isnan(val) else 0.0)
        except (ValueError, TypeError):
            clean_series.append(0.0)

    # Parseo de fecha de siembra
    try:
        sowing_dt = pd.to_datetime(str(sowing_date).split("T")[0]).normalize()
    except Exception:
        sowing_dt = pd.Timestamp("2026-06-01")

    total_cycle_rain_mm = round(float(sum(clean_series)), 2)
    critical_alerts: List[str] = []

    # -------------------------------------------------------------------------
    # ETAPA 1: Germinación y Emergencia (Días 1-15, índices 0 a 14)
    # -------------------------------------------------------------------------
    s1_rain = clean_series[0:15]
    s1_total = round(float(sum(s1_rain)), 2)
    s1_avg = round(s1_total / 15.0, 2)
    s1_dry_streak, s1_dry_start = _find_longest_streak(s1_rain, lambda x: x < 1.5)
    s1_wet_streak, s1_wet_start = _find_longest_streak(s1_rain, lambda x: x > 15.0)
    s1_dry_start_day = (1 + s1_dry_start) if s1_dry_streak > 0 else 0
    s1_wet_start_day = (1 + s1_wet_start) if s1_wet_streak > 0 else 0
    s1_adequacy = _classify_rain_adequacy(s1_total, min_req_mm=20.0, max_req_mm=40.0)

    s1_issues: List[str] = []
    s1_recommendations: List[str] = []
    s1_failed = False

    # Chequeo estricto de fallo: >5 días >15mm (pudrición) o >7 días <1mm (falla germinación)
    s1_wet_fail_len, s1_wet_fail_start = _find_longest_streak(s1_rain, lambda x: x > 15.0)
    s1_dry_fail_len, s1_dry_fail_start = _find_longest_streak(s1_rain, lambda x: x < 1.0)

    if s1_wet_fail_len > 5:
        s1_failed = True
        msg = (
            f"Pudrición de semilla y asfixia en germinación: Racha excesiva de {s1_wet_fail_len} "
            f"días consecutivos con lluvia > 15.0 mm/día (iniciando el día {1 + s1_wet_fail_start}). "
            f"Suelo saturado con anoxia radicular e infestación por Pythium/Fusarium."
        )
        s1_issues.append(msg)
        s1_recommendations.append(
            "Implementar zanjas perimetrales de drenaje superficial y efectuar siembra en camellones "
            "o lomos sobreelevados para permitir escurrimiento en los primeros 15 cm de suelo."
        )
        critical_alerts.append(
            f"Falla crítica en Germinación (Etapa 1): {s1_wet_fail_len} días continuos con lluvia >15 mm/día. "
            f"Peligro inminente de pudrición de semilla."
        )

    if s1_dry_fail_len > 7:
        s1_failed = True
        msg = (
            f"Falla total de germinación y emergencia: Racha seca severa de {s1_dry_fail_len} "
            f"días consecutivos con precipitación < 1.0 mm/día (iniciando el día {1 + s1_dry_fail_start}). "
            f"Desecación total del embrión seminal en suelo seco."
        )
        s1_issues.append(msg)
        s1_recommendations.append(
            "Suspender siembra a temporal seco; aplicar riego de asiento de 20-25 mm o sembrar únicamente "
            "tras acumularse al menos 35-40 mm de humedad efectiva en el perfil con labranza conservacionista."
        )
        critical_alerts.append(
            f"Falla crítica en Germinación (Etapa 1): {s1_dry_fail_len} días continuos con lluvia <1 mm/día. "
            f"Emergencia de plántulas nula sin riego suplementario."
        )

    # Evaluación de suficiencia si no hubo fallo estricto
    if not s1_failed:
        if s1_adequacy == "Déficit Severo":
            s1_issues.append(f"Déficit hídrico severo en emergencia: Lluvia acumulada ({s1_total:.1f} mm) muy inferior al mínimo requerido (20 mm).")
            s1_recommendations.append("Suministrar micro-riego de emergencia para evitar retraso y desuniformidad en el nacimiento de la milpa.")
        elif s1_adequacy == "Déficit Moderado":
            s1_issues.append(f"Déficit hídrico moderado en emergencia ({s1_total:.1f} mm vs 20-40 mm esperados).")
            s1_recommendations.append("Retener humedad cubriendo los surcos con rastrojo previo de maíz o frijol.")
        elif s1_adequacy == "Exceso Severo":
            s1_issues.append(f"Exceso pluviométrico severo en emergencia ({s1_total:.1f} mm acumulados vs 40 mm máximo).")
            s1_recommendations.append("Supervisar desagües en parcelas de pendiente baja en Calderas para evitar láminas estancadas.")
        elif s1_adequacy == "Exceso Moderado":
            s1_issues.append(f"Lluvias por encima del rango óptimo en emergencia ({s1_total:.1f} mm).")
            s1_recommendations.append("Monitorear posibles brotes de damping-off en plántulas recién nacidas.")
        else:
            s1_recommendations.append("Humedad adecuada para emergencia homogénea; aplicar insecticida granulado preventivo al fondo del surco contra gallina ciega.")

    if s1_failed:
        s1_risk = "Crítico"
    elif s1_adequacy in ("Déficit Severo", "Exceso Severo"):
        s1_risk = "Alto"
    elif s1_adequacy in ("Déficit Moderado", "Exceso Moderado") or s1_dry_streak >= 5 or s1_wet_streak >= 4:
        s1_risk = "Moderado"
    else:
        s1_risk = "Bajo"

    stage1 = StageAnalysis(
        stage_name="Germinación y Emergencia",
        stage_days="Días 1-15",
        total_rain_mm=s1_total,
        avg_daily_rain_mm=s1_avg,
        max_consecutive_dry_days=s1_dry_streak,
        max_consecutive_wet_days=s1_wet_streak,
        longest_dry_streak_start_day=s1_dry_start_day,
        longest_wet_streak_start_day=s1_wet_start_day,
        rain_adequacy=s1_adequacy,
        risk_level=s1_risk,
        issues=s1_issues,
        recommendations=s1_recommendations,
    )

    # -------------------------------------------------------------------------
    # ETAPA 2: Desarrollo Vegetativo (Días 16-55, índices 15 a 54)
    # -------------------------------------------------------------------------
    s2_rain = clean_series[15:55]
    s2_total = round(float(sum(s2_rain)), 2)
    s2_avg = round(s2_total / 40.0, 2)
    s2_dry_streak, s2_dry_start = _find_longest_streak(s2_rain, lambda x: x < 1.5)
    s2_wet_streak, s2_wet_start = _find_longest_streak(s2_rain, lambda x: x > 15.0)
    s2_dry_start_day = (16 + s2_dry_start) if s2_dry_streak > 0 else 0
    s2_wet_start_day = (16 + s2_wet_start) if s2_wet_streak > 0 else 0
    s2_adequacy = _classify_rain_adequacy(s2_total, min_req_mm=150.0, max_req_mm=250.0)

    s2_issues: List[str] = []
    s2_recommendations: List[str] = []
    s2_failed = False

    # Chequeo estricto de fallo: >8 días >20mm (asfixia) o >10 días <1.5mm (enanismo)
    s2_wet_fail_len, s2_wet_fail_start = _find_longest_streak(s2_rain, lambda x: x > 20.0)
    s2_dry_fail_len, s2_dry_fail_start = _find_longest_streak(s2_rain, lambda x: x < 1.5)

    if s2_wet_fail_len > 8:
        s2_failed = True
        msg = (
            f"Asfixia radicular irreversible y clorosis por saturación continua: Racha de {s2_wet_fail_len} "
            f"días consecutivos con lluvia > 20.0 mm/día (iniciando el día {16 + s2_wet_fail_start}). "
            f"Pérdida de raíces absorbentes y bloqueo de asimilación de nitrógeno y fósforo."
        )
        s2_issues.append(msg)
        s2_recommendations.append(
            "Abrir sangrías transversales de drenaje con azadón para desfogar excesos freáticos; aplicar "
            "aspersiones foliares con nitrógeno amínico y zinc para sostener el dosel durante la anoxia."
        )
        critical_alerts.append(
            f"Falla crítica en Desarrollo Vegetativo (Etapa 2): {s2_wet_fail_len} días continuos con lluvia >20 mm/día. "
            f"Asfixia radicular extendida."
        )

    if s2_dry_fail_len > 10:
        s2_failed = True
        msg = (
            f"Detención severa del crecimiento vegetativo y enanismo: Racha seca de {s2_dry_fail_len} "
            f"días consecutivos con lluvia < 1.5 mm/día (iniciando el día {16 + s2_dry_fail_start}). "
            f"Reducción permanente de altura, área foliar fotosintética y número potencial de hileras de mazorca."
        )
        s2_issues.append(msg)
        s2_recommendations.append(
            "Aplicar riego de auxilio inmediato (mínimo 30 mm); incorporar cobertura vegetal muerta (mulch) "
            "en las hileras y aplicar bioestimulantes antiestrés a base de aminoácidos y silicio."
        )
        critical_alerts.append(
            f"Falla crítica en Desarrollo Vegetativo (Etapa 2): {s2_dry_fail_len} días continuos con lluvia <1.5 mm/día. "
            f"Enanismo y pérdida de potencial biológico."
        )

    # Alerta de patrón de Canícula en fase vegetativa (>5 días secos)
    s2_canicula_warning = False
    if not s2_failed and s2_dry_streak > 5:
        s2_canicula_warning = True
        msg = (
            f"Alerta de Canícula intra-estival en fase vegetativa: Racha seca de {s2_dry_streak} días "
            f"consecutivos con lluvia < 1.5 mm/día (iniciando el día {s2_dry_start_day}). "
            f"Genera estrés hídrico y térmico en pleno ensanchamiento de caña."
        )
        s2_issues.append(msg)
        s2_recommendations.append(
            "Realizar aporque alto para proteger el sistema radicular de la radiación solar; no deshierbar "
            "con machete a ras de suelo para evitar evaporación acelerada de la humedad edáfica residual."
        )

    if not s2_failed:
        if s2_adequacy == "Déficit Severo":
            s2_issues.append(f"Déficit hídrico severo en vegetativo: Lluvia ({s2_total:.1f} mm) bajo el 60% del umbral óptimo (150 mm).")
            s2_recommendations.append("Optimizar fertilización nitrogenada aplicándola en horas frescas o fraccionada en fertirriego.")
        elif s2_adequacy == "Déficit Moderado":
            s2_issues.append(f"Déficit hídrico moderado en vegetativo ({s2_total:.1f} mm vs 150-250 mm esperados).")
            s2_recommendations.append("Aplicar fertilizante soluble foliar con potasio para favorecer el cierre estomático y ahorro hídrico.")
        elif s2_adequacy == "Exceso Severo":
            s2_issues.append(f"Exceso hídrico severo en vegetativo ({s2_total:.1f} mm acumulados vs 250 mm).")
            s2_recommendations.append("Monitorear mancha de asfalto (Phyllachora maydis) y mancha por Cercospora provocadas por alta humedad relativa.")
        elif s2_adequacy == "Exceso Moderado":
            s2_issues.append(f"Exceso moderado de lluvia en vegetativo ({s2_total:.1f} mm).")
            s2_recommendations.append("Asegurar drenajes limpios de maleza para canalizar escurrimientos fuera del predio.")
        elif not s2_canicula_warning:
            s2_recommendations.append("Crecimiento vegetativo vigoroso; realizar segunda fertilización al aporque (día 30-35) con Urea + 15-15-15.")

    if s2_failed:
        s2_risk = "Crítico"
    elif s2_canicula_warning or s2_adequacy in ("Déficit Severo", "Exceso Severo"):
        s2_risk = "Alto"
    elif s2_adequacy in ("Déficit Moderado", "Exceso Moderado") or s2_dry_streak >= 5 or s2_wet_streak >= 6:
        s2_risk = "Moderado"
    else:
        s2_risk = "Bajo"

    stage2 = StageAnalysis(
        stage_name="Desarrollo Vegetativo",
        stage_days="Días 16-55",
        total_rain_mm=s2_total,
        avg_daily_rain_mm=s2_avg,
        max_consecutive_dry_days=s2_dry_streak,
        max_consecutive_wet_days=s2_wet_streak,
        longest_dry_streak_start_day=s2_dry_start_day,
        longest_wet_streak_start_day=s2_wet_start_day,
        rain_adequacy=s2_adequacy,
        risk_level=s2_risk,
        issues=s2_issues,
        recommendations=s2_recommendations,
    )

    # -------------------------------------------------------------------------
    # ETAPA 3: Floración y Polinización - CRÍTICA (Días 56-75, índices 55 a 74)
    # -------------------------------------------------------------------------
    s3_rain = clean_series[55:75]
    s3_total = round(float(sum(s3_rain)), 2)
    s3_avg = round(s3_total / 20.0, 2)
    s3_dry_streak, s3_dry_start = _find_longest_streak(s3_rain, lambda x: x < 1.5)
    s3_wet_streak, s3_wet_start = _find_longest_streak(s3_rain, lambda x: x > 15.0)
    s3_dry_start_day = (56 + s3_dry_start) if s3_dry_streak > 0 else 0
    s3_wet_start_day = (56 + s3_wet_start) if s3_wet_streak > 0 else 0
    s3_adequacy = _classify_rain_adequacy(s3_total, min_req_mm=80.0, max_req_mm=120.0)

    s3_issues: List[str] = []
    s3_recommendations: List[str] = []
    s3_failed = False

    # Chequeo estricto de fallo: >4 días <2mm (desecación polen) o >6 días >25mm (lavado polen)
    s3_dry_fail_len, s3_dry_fail_start = _find_longest_streak(s3_rain, lambda x: x < 2.0)
    s3_wet_fail_len, s3_wet_fail_start = _find_longest_streak(s3_rain, lambda x: x > 25.0)

    if s3_dry_fail_len > 4:
        s3_failed = True
        perdida_min = s3_dry_fail_len * 6
        perdida_max = min(100, s3_dry_fail_len * 10)
        msg = (
            f"Desecación letal de polen y asincronía floral (fallo de jiloteo): Racha seca crítica de {s3_dry_fail_len} "
            f"días consecutivos con precipitación < 2.0 mm/día (iniciando el día {56 + s3_dry_fail_start}). "
            f"Los estigmas pierden receptividad hídrica. Pérdida irreversible proyectada: {perdida_min}% a {perdida_max}% "
            f"del rendimiento total (6-10% por día de estrés en etapa crítica)."
        )
        s3_issues.append(msg)
        s3_recommendations.append(
            "Intervención de emergencia obligatoria: Aplicar riego de auxilio por gravedad o aspersión ligera "
            "(mínimo 35 mm en la ventana). No realizar aplicaciones químicas matutinas (8:00 a 11:00 am) para no afectar la viabilidad del polen."
        )
        critical_alerts.append(
            f"Falla letal en Floración (Etapa 3 - CRÍTICA): {s3_dry_fail_len} días continuos con lluvia <2 mm/día. "
            f"Desecación de polen y estigmas; merma de rendimiento estimada entre {perdida_min}% y {perdida_max}%."
        )

    if s3_wet_fail_len > 6:
        s3_failed = True
        msg = (
            f"Lavado mecánico de polen y daño floral: Racha torrencial de {s3_wet_fail_len} "
            f"días consecutivos con precipitación > 25.0 mm/día (iniciando el día {56 + s3_wet_fail_start}). "
            f"El agua continua lava el grano de polen de la espiga antes de fecundar los estigmas del jilote."
        )
        s3_issues.append(msg)
        s3_recommendations.append(
            "Inspeccionar el cuajado de grano 10 días tras el temporal; planificar aplicación preventiva de fungicida "
            "contra pudrición de espiga y tizón foliar que prosperan con exceso de humedad ambiental."
        )
        critical_alerts.append(
            f"Falla crítica en Floración (Etapa 3 - CRÍTICA): {s3_wet_fail_len} días continuos con lluvia >25 mm/día. "
            f"Lavado de polen y fallo general de fecundación."
        )

    if not s3_failed:
        if s3_adequacy == "Déficit Severo":
            s3_issues.append(f"Déficit hídrico severo en floración: Lluvia ({s3_total:.1f} mm) insuficiente para cubrir demanda de transpiración (80-120 mm).")
            s3_recommendations.append("Concentrar todos los recursos hídricos disponibles en esta etapa, decisiva para la formación de mazorcas.")
        elif s3_adequacy == "Déficit Moderado":
            s3_issues.append(f"Déficit hídrico moderado en floración ({s3_total:.1f} mm acumulados).")
            s3_recommendations.append("Proteger la milpa de vientos desecantes mediante barreras vivas temporales y evitar labores que remuevan el suelo.")
        elif s3_adequacy == "Exceso Severo":
            s3_issues.append(f"Exceso pluviométrico severo en floración ({s3_total:.1f} mm).")
            s3_recommendations.append("Vigilar la aireación del lote para reducir riesgo de pudrición bacteriana en el cogollo y la espiga.")
        elif s3_adequacy == "Exceso Moderado":
            s3_issues.append(f"Lluvias abundantes en floración ({s3_total:.1f} mm).")
            s3_recommendations.append("Monitorear fecundación uniforme en jilotes centrales.")
        else:
            s3_recommendations.append("Condiciones óptimas de polinización; mantener el monitoreo fitosanitario y evitar maquinaria pesada en surcos.")

    if s3_failed or s3_adequacy == "Déficit Severo":
        s3_risk = "Crítico"
    elif s3_adequacy in ("Déficit Moderado", "Exceso Severo") or s3_dry_streak >= 3 or s3_wet_streak >= 5:
        s3_risk = "Alto"
    elif s3_adequacy == "Exceso Moderado" or s3_dry_streak >= 2:
        s3_risk = "Moderado"
    else:
        s3_risk = "Bajo"

    stage3 = StageAnalysis(
        stage_name="Floración y Polinización",
        stage_days="Días 56-75",
        total_rain_mm=s3_total,
        avg_daily_rain_mm=s3_avg,
        max_consecutive_dry_days=s3_dry_streak,
        max_consecutive_wet_days=s3_wet_streak,
        longest_dry_streak_start_day=s3_dry_start_day,
        longest_wet_streak_start_day=s3_wet_start_day,
        rain_adequacy=s3_adequacy,
        risk_level=s3_risk,
        issues=s3_issues,
        recommendations=s3_recommendations,
    )

    # -------------------------------------------------------------------------
    # ETAPA 4: Llenado de Grano (Días 76-120, índices 75 a 119)
    # -------------------------------------------------------------------------
    s4_rain = clean_series[75:120]
    s4_total = round(float(sum(s4_rain)), 2)
    s4_avg = round(s4_total / 45.0, 2)
    s4_dry_streak, s4_dry_start = _find_longest_streak(s4_rain, lambda x: x < 1.5)
    s4_wet_streak, s4_wet_start = _find_longest_streak(s4_rain, lambda x: x > 15.0)
    s4_dry_start_day = (76 + s4_dry_start) if s4_dry_streak > 0 else 0
    s4_wet_start_day = (76 + s4_wet_start) if s4_wet_streak > 0 else 0
    s4_adequacy = _classify_rain_adequacy(s4_total, min_req_mm=150.0, max_req_mm=250.0)

    s4_issues: List[str] = []
    s4_recommendations: List[str] = []
    s4_failed = False

    # Chequeo estricto de fallo: >6 días <1.5mm en días 76-95 (índices 75 a 94 en la serie general)
    s4_early_rain = clean_series[75:95]
    s4_early_dry_len, s4_early_dry_start = _find_longest_streak(s4_early_rain, lambda x: x < 1.5)

    if s4_early_dry_len > 6:
        s4_failed = True
        msg = (
            f"Aborto de granos y deficiente peso específico en llenado temprano: Racha seca de {s4_early_dry_len} "
            f"días consecutivos con lluvia < 1.5 mm/día en días 76-95 (iniciando el día {76 + s4_early_dry_start}). "
            f"Ocasiona puntas de mazorca vanas, grano arrugado y bajo peso hectolítrico."
        )
        s4_issues.append(msg)
        s4_recommendations.append(
            "Mantener el lote estrictamente limpio de malezas competitivas; aplicar riego suplementario de auxilio "
            "de 25-30 mm si se cuenta con pozo o derivación comunitaria."
        )
        critical_alerts.append(
            f"Falla crítica en Llenado Temprano (Etapa 4): {s4_early_dry_len} días continuos con lluvia <1.5 mm/día "
            f"entre días 76 y 95. Aborto masivo de granos."
        )

    # Chequeo de alerta: >10 días >15mm en días 76-120 (riesgo pudrición de mazorca)
    s4_wet_warn_len, s4_wet_warn_start = _find_longest_streak(s4_rain, lambda x: x > 15.0)
    s4_wet_warning = False
    if s4_wet_warn_len > 10:
        s4_wet_warning = True
        msg = (
            f"Riesgo fitosanitario severo de pudrición de mazorca: Racha de exceso húmedo de {s4_wet_warn_len} "
            f"días consecutivos con precipitación > 15.0 mm/día (iniciando el día {76 + s4_wet_warn_start}). "
            f"Favorece pudriciones por Fusarium, Stenocarpella (Diplodia) y brotado prematuro del grano en la espiga."
        )
        s4_issues.append(msg)
        s4_recommendations.append(
            "Realizar la doblada de la caña (tapeque tradicional) inmediatamente al alcanzar la madurez fisiológica "
            "(capa negra en el grano, aprox. día 95-100) para inclinar la mazorca e impedir la entrada de lluvia en las brácteas."
        )

    # Nota sobre tolerancia aumentada en días 96-120 (madurez y secado en pie)
    if not s4_failed:
        if s4_adequacy == "Déficit Severo":
            s4_issues.append(f"Déficit pluviométrico severo en llenado de grano ({s4_total:.1f} mm acumulados vs 150 mm).")
            s4_recommendations.append("Priorizar la cosecha anticipada para forraje o silo si el grano no completa la masa harinosa.")
        elif s4_adequacy == "Déficit Moderado":
            s4_issues.append(f"Déficit moderado en llenado ({s4_total:.1f} mm).")
            s4_recommendations.append("La tolerancia de la planta aumenta hacia los días 96-120; las rachas secas finales favorecen el secado natural en campo.")
        elif s4_adequacy == "Exceso Severo":
            s4_issues.append(f"Exceso pluviométrico severo en maduración ({s4_total:.1f} mm).")
            s4_recommendations.append("Agilizar la cosecha tan pronto como el grano alcance 18-20% de humedad y secar artificialmente o en carpas solares.")
        elif s4_adequacy == "Exceso Moderado":
            s4_issues.append(f"Exceso moderado de humedad en llenado ({s4_total:.1f} mm).")
            s4_recommendations.append("Inspeccionar muestras de mazorcas para descartar mohos en el grano.")
        else:
            s4_recommendations.append("Llenado óptimo; en días 96-120 la planta tolera periodos secos que facilitan el secado en campo para cosecha a 14% de humedad.")

    if s4_failed:
        s4_risk = "Crítico"
    elif s4_wet_warning or s4_adequacy in ("Déficit Severo", "Exceso Severo"):
        s4_risk = "Alto"
    elif s4_adequacy in ("Déficit Moderado", "Exceso Moderado") or s4_dry_streak >= 8 or s4_wet_streak >= 7:
        s4_risk = "Moderado"
    else:
        s4_risk = "Bajo"

    stage4 = StageAnalysis(
        stage_name="Llenado de Grano",
        stage_days="Días 76-120",
        total_rain_mm=s4_total,
        avg_daily_rain_mm=s4_avg,
        max_consecutive_dry_days=s4_dry_streak,
        max_consecutive_wet_days=s4_wet_streak,
        longest_dry_streak_start_day=s4_dry_start_day,
        longest_wet_streak_start_day=s4_wet_start_day,
        rain_adequacy=s4_adequacy,
        risk_level=s4_risk,
        issues=s4_issues,
        recommendations=s4_recommendations,
    )

    stages_list = [stage1, stage2, stage3, stage4]

    # -------------------------------------------------------------------------
    # ANÁLISIS DE LA CANÍCULA (Período estival Julio-Agosto en Guatemala)
    # -------------------------------------------------------------------------
    # Extraer días del ciclo de 120 días que coinciden con los meses 7 y 8 (Julio y Agosto)
    canicula_indices = []
    for day_i in range(120):
        current_date = sowing_dt + pd.Timedelta(days=day_i)
        if current_date.month in (7, 8):
            canicula_indices.append(day_i)

    if canicula_indices:
        canicula_rain = [clean_series[idx] for idx in canicula_indices]
        can_streak, _ = _find_longest_streak(canicula_rain, lambda x: x < 1.5)
    else:
        # Si la ventana no coincide con julio-agosto (e.g. siembra en fecha no estival),
        # evaluar ventana de sequía intermedia (días 30 a 70 del ciclo)
        mid_cycle_rain = clean_series[30:71]
        can_streak, _ = _find_longest_streak(mid_cycle_rain, lambda x: x < 1.5)

    if can_streak >= 15:
        canicula_detected = True
        canicula_severity = "Severa"
        canicula_days = can_streak
        critical_alerts.append(
            f"Alerta de Canícula Severa: Racha seca prolongada de {canicula_days} días consecutivos "
            f"con precipitación < 1.5 mm/día en pleno régimen estival de Jutiapa."
        )
    elif can_streak >= 9:
        canicula_detected = True
        canicula_severity = "Moderada"
        canicula_days = can_streak
    elif can_streak >= 5:
        canicula_detected = True
        canicula_severity = "Leve"
        canicula_days = can_streak
    else:
        canicula_detected = False
        canicula_severity = "Ninguna"
        canicula_days = 0

    # -------------------------------------------------------------------------
    # CALIDAD DE DISTRIBUCIÓN DE LA LLUVIA
    # -------------------------------------------------------------------------
    severos = sum(1 for s in stages_list if s.rain_adequacy in ("Déficit Severo", "Exceso Severo"))
    moderados = sum(1 for s in stages_list if s.rain_adequacy in ("Déficit Moderado", "Exceso Moderado"))

    if (
        severos >= 2
        or stage3.rain_adequacy in ("Déficit Severo", "Exceso Severo")
        or total_cycle_rain_mm < 350.0
        or total_cycle_rain_mm > 850.0
        or len(critical_alerts) > 0
    ):
        rain_distribution_quality = "Deficiente"
    elif severos == 0 and moderados == 0 and all(s.risk_level in ("Bajo", "Moderado") for s in stages_list):
        rain_distribution_quality = "Buena"
    else:
        rain_distribution_quality = "Irregular"

    if total_cycle_rain_mm < 300.0:
        critical_alerts.append(
            f"Precipitación total del ciclo críticamente insuficiente: {total_cycle_rain_mm:.1f} mm acumulados "
            f"frente al mínimo requerido de 400 mm para sostener maíz blanco comercial en el Corredor Seco."
        )

    # -------------------------------------------------------------------------
    # PUNTUACIÓN DE RIESGO Y VEREDICTO GENERAL
    # -------------------------------------------------------------------------
    risk_weights = {
        "Germinación y Emergencia": 0.15,
        "Desarrollo Vegetativo": 0.25,
        "Floración y Polinización": 0.40,  # Etapa más crítica
        "Llenado de Grano": 0.20,
    }
    score_by_level = {
        "Bajo": 1.00,
        "Moderado": 0.70,
        "Alto": 0.35,
        "Crítico": 0.05,
    }

    base_score = 0.0
    for stg in stages_list:
        w = risk_weights.get(stg.stage_name, 0.25)
        lvl_score = score_by_level.get(stg.risk_level, 0.50)
        base_score += w * lvl_score

    # Penalizaciones adicionales por canícula, calidad de distribución y alertas
    penalizacion = 0.0
    if canicula_severity == "Severa":
        penalizacion += 0.20
    elif canicula_severity == "Moderada":
        penalizacion += 0.10
    elif canicula_severity == "Leve":
        penalizacion += 0.05

    if rain_distribution_quality == "Deficiente":
        penalizacion += 0.15
    elif rain_distribution_quality == "Irregular":
        penalizacion += 0.05

    if critical_alerts:
        penalizacion += min(0.35, len(critical_alerts) * 0.12)

    overall_risk_score = round(max(0.0, min(1.0, base_score - penalizacion)), 3)

    # Determinación del Veredicto Final
    if len(critical_alerts) > 0 or any(s.risk_level == "Crítico" for s in stages_list) or overall_risk_score < 0.50:
        overall_verdict = "NO APTO PARA SIEMBRA"
    elif any(s.risk_level == "Alto" for s in stages_list) or canicula_severity in ("Moderada", "Severa") or overall_risk_score < 0.75:
        overall_verdict = "SIEMBRA CON PRECAUCIÓN"
    else:
        overall_verdict = "APTO PARA SIEMBRA"

    return RainStreakReport(
        overall_verdict=overall_verdict,
        overall_risk_score=overall_risk_score,
        stages=stages_list,
        critical_alerts=critical_alerts,
        canicula_detected=canicula_detected,
        canicula_severity=canicula_severity,
        canicula_days=canicula_days,
        total_cycle_rain_mm=total_cycle_rain_mm,
        rain_distribution_quality=rain_distribution_quality,
    )


def analyze_historical_streaks(weather_df: pd.DataFrame, month: int, day: int = 1) -> HistoricalStreakSummary:
    """
    Analiza patrones climáticos históricos para un mes y día de siembra determinado
    a través de todos los años disponibles en el conjunto de datos agrometeorológicos ERA5.

    Evalúa la recurrencia de canícula, la incidencia de lluvias excesivas, la duración
    promedio de rachas secas y húmedas, y la tasa de viabilidad agronómica del maíz blanco.

    Args:
        weather_df: DataFrame con series diarias de tiempo y precipitación (e.g. ERA5).
        month: Mes objetivo de siembra (1 = Enero, ..., 12 = Diciembre).
        day: Día del mes para iniciar la siembra simulada (por defecto 1).

    Returns:
        HistoricalStreakSummary: Métricas agregadas y estadísticas extremas multianuales.
    """
    if weather_df is None or weather_df.empty:
        return HistoricalStreakSummary(
            years_analyzed=0,
            pct_years_canicula=0.0,
            avg_canicula_duration_days=0.0,
            pct_years_excess_rain=0.0,
            avg_longest_dry_streak=0.0,
            avg_longest_wet_streak=0.0,
            pct_years_viable=0.0,
            worst_year=0,
            best_year=0,
        )

    # Identificación flexible de columnas de fecha y lluvia
    df = weather_df.copy()
    date_col = None
    for c in ["time", "date", "fecha"]:
        if c in df.columns:
            date_col = c
            break

    if date_col is None:
        if isinstance(df.index, pd.DatetimeIndex):
            df["time"] = df.index
            date_col = "time"
        else:
            raise ValueError(
                f"No se identificó una columna de fecha en el DataFrame. "
                f"Columnas disponibles: {list(df.columns)}"
            )

    rain_col = None
    for c in ["precip_mm", "precipitation_sum", "precip", "rain", "lluvia"]:
        if c in df.columns:
            rain_col = c
            break

    if rain_col is None:
        raise ValueError(
            f"No se identificó una columna de precipitación en el DataFrame. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).reset_index(drop=True)

    years = sorted(df[date_col].dt.year.unique())
    year_records: List[Dict[str, Any]] = []

    for y in years:
        try:
            s_date = pd.Timestamp(year=int(y), month=int(month), day=int(day))
        except ValueError:
            # En caso de fecha inválida (e.g. 29 de febrero en año no bisiesto), ajustar al último día
            s_date = pd.Timestamp(year=int(y), month=int(month), day=28)

        e_date = s_date + pd.Timedelta(days=119)
        sub = df[(df[date_col] >= s_date) & (df[date_col] <= e_date)]

        if len(sub) < 120:
            # Año incompleto en el dataset (e.g. año actual o año límite)
            continue

        daily_rain = sub[rain_col].astype(float).fillna(0.0).tolist()[:120]
        s_date_str = s_date.strftime("%Y-%m-%d")

        try:
            rep = analyze_rain_streaks(daily_rain, s_date_str)
        except Exception:
            continue

        has_canicula = rep.canicula_detected
        can_days = rep.canicula_days

        # Exceso de lluvia considerado si el total supera 700 mm o hay rachas excesivas
        has_excess = (
            rep.total_cycle_rain_mm > 700.0
            or any("Exceso" in s.rain_adequacy for s in rep.stages)
            or any(s.max_consecutive_wet_days > 7 for s in rep.stages)
        )

        longest_dry, _ = _find_longest_streak(daily_rain, lambda x: x < 1.5)
        longest_wet, _ = _find_longest_streak(daily_rain, lambda x: x > 15.0)

        is_viable = (rep.overall_verdict != "NO APTO PARA SIEMBRA")

        year_records.append({
            "year": int(y),
            "score": rep.overall_risk_score,
            "has_canicula": has_canicula,
            "canicula_days": can_days,
            "has_excess": has_excess,
            "longest_dry": longest_dry,
            "longest_wet": longest_wet,
            "is_viable": is_viable,
            "total_rain": rep.total_cycle_rain_mm,
        })

    if not year_records:
        return HistoricalStreakSummary(
            years_analyzed=0,
            pct_years_canicula=0.0,
            avg_canicula_duration_days=0.0,
            pct_years_excess_rain=0.0,
            avg_longest_dry_streak=0.0,
            avg_longest_wet_streak=0.0,
            pct_years_viable=0.0,
            worst_year=0,
            best_year=0,
        )

    n_years = len(year_records)
    pct_canicula = round((sum(1 for r in year_records if r["has_canicula"]) / n_years) * 100.0, 1)

    can_days_list = [r["canicula_days"] for r in year_records if r["has_canicula"]]
    avg_can_duration = round(float(np.mean(can_days_list)), 1) if can_days_list else 0.0

    pct_excess = round((sum(1 for r in year_records if r["has_excess"]) / n_years) * 100.0, 1)
    avg_dry = round(float(np.mean([r["longest_dry"] for r in year_records])), 1)
    avg_wet = round(float(np.mean([r["longest_wet"] for r in year_records])), 1)
    pct_viable = round((sum(1 for r in year_records if r["is_viable"]) / n_years) * 100.0, 1)

    # Identificación del mejor y peor año con criterios estables
    best_record = max(year_records, key=lambda r: (r["score"], -r["longest_dry"], r["total_rain"]))
    worst_record = min(year_records, key=lambda r: (r["score"], -r["longest_dry"], r["total_rain"]))

    return HistoricalStreakSummary(
        years_analyzed=n_years,
        pct_years_canicula=pct_canicula,
        avg_canicula_duration_days=avg_can_duration,
        pct_years_excess_rain=pct_excess,
        avg_longest_dry_streak=avg_dry,
        avg_longest_wet_streak=avg_wet,
        pct_years_viable=pct_viable,
        worst_year=worst_record["year"],
        best_year=best_record["year"],
    )


def generate_streak_pdf_section(report: RainStreakReport) -> Dict[str, Any]:
    """
    Formatea y estructura todos los resultados del análisis de rachas para su
    inclusión directa y armónica en el dictamen técnico en formato PDF y Markdown.

    Args:
        report: Instancia de RainStreakReport generada por analyze_rain_streaks.

    Returns:
        Dict[str, Any]: Estructura jerárquica con tablas, métricas destacadas y directivas.
    """
    tabla_etapas: List[Dict[str, Any]] = []
    for stg in report.stages:
        dry_str = f"{stg.max_consecutive_dry_days} días (Día {stg.longest_dry_streak_start_day})" if stg.max_consecutive_dry_days > 0 else "0 días"
        wet_str = f"{stg.max_consecutive_wet_days} días (Día {stg.longest_wet_streak_start_day})" if stg.max_consecutive_wet_days > 0 else "0 días"

        tabla_etapas.append({
            "etapa": stg.stage_name,
            "dias": stg.stage_days,
            "lluvia_total": f"{stg.total_rain_mm:.1f} mm",
            "promedio_diario": f"{stg.avg_daily_rain_mm:.2f} mm/día",
            "racha_seca_max": dry_str,
            "racha_humeda_max": wet_str,
            "adecuacion": stg.rain_adequacy,
            "nivel_riesgo": stg.risk_level,
            "problemas": stg.issues,
            "recomendaciones": stg.recommendations,
        })

    # Construcción de síntesis ejecutiva adaptada al Corredor Seco
    if report.overall_verdict == "APTO PARA SIEMBRA":
        resumen_ejecutivo = (
            f"El régimen de lluvias proyectado para el ciclo de 120 días presenta una acumulación favorable "
            f"de {report.total_cycle_rain_mm:.1f} mm con calidad de distribución '{report.rain_distribution_quality}'. "
            f"No se detectaron rachas críticas que comprometan la floración ni la emergencia. Las fases de mayor "
            f"sensibilidad cuentan con respaldo de humedad edáfica suficiente para sostener rendimientos comerciales."
        )
        directiva = (
            "Proceder con la preparación del terreno y siembra bajo el marco de densidad recomendado. "
            "Mantener el programa planificado de fertilización balanceada y monitoreo integrado de plagas."
        )
    elif report.overall_verdict == "SIEMBRA CON PRECAUCIÓN":
        resumen_ejecutivo = (
            f"Se identifican factores de vulnerabilidad pluviométrica en el ciclo (acumulado: {report.total_cycle_rain_mm:.1f} mm, "
            f"distribución: '{report.rain_distribution_quality}', severidad de canícula: '{report.canicula_severity}'). "
            f"Existen etapas con riesgo moderado a alto por rachas secas o excesos puntuales que exigen labores agronómicas mitigadoras."
        )
        directiva = (
            "Condicionar la siembra a la disponibilidad de riego complementario de auxilio o implementar técnicas de "
            "conservación de humedad (mulch de rastrojo, cero labranza, surcos en contorno y bioestimulantes antiestrés)."
        )
    else:
        resumen_ejecutivo = (
            f"DICTAMEN ADVERSO: Se proyectan fallas agrometeorológicas severas durante el ciclo (lluvia acumulada: {report.total_cycle_rain_mm:.1f} mm, "
            f"distribución: '{report.rain_distribution_quality}'). Se detectaron {len(report.critical_alerts)} alertas críticas bloqueantes, "
            f"incluyendo estrés hídrico letal o asfixia en etapas fenológicas cardinales de la milpa."
        )
        directiva = (
            "NO SE RECOMIENDA la siembra a temporal en la fecha propuesta. Posponer la fecha de siembra hacia una ventana "
            "más favorable o sustituir el cultivo por especies tolerantes a sequía extrema (sorgo o pastos forrajeros)."
        )

    canicula_msg = (
        f"Canícula {report.canicula_severity} identificada con {report.canicula_days} días consecutivos sin lluvia efectiva (<1.5 mm/día)."
        if report.canicula_detected else
        "No se detectó un patrón severo de canícula durante la ventana crítica analizada."
    )

    return {
        "titulo": "ANÁLISIS DE RACHAS HÍDRICAS Y DISTRIBUCIÓN FENOLÓGICA",
        "subtitulo": "Evaluación de Rachas Secas y de Exceso en Calderas, San José Acatempa (Jutiapa)",
        "veredicto_general": report.overall_verdict,
        "puntaje_riesgo": report.overall_risk_score,
        "puntaje_riesgo_pct": f"{report.overall_risk_score * 100:.1f}%",
        "calidad_distribucion": report.rain_distribution_quality,
        "total_precipitacion_ciclo_mm": f"{report.total_cycle_rain_mm:.1f} mm",
        "total_precipitacion_num": report.total_cycle_rain_mm,
        "alertas_criticas": report.critical_alerts,
        "tiene_alertas_criticas": len(report.critical_alerts) > 0,
        "canicula": {
            "detectada": report.canicula_detected,
            "severidad": report.canicula_severity,
            "dias_duracion": report.canicula_days,
            "diagnostico": canicula_msg,
        },
        "tabla_etapas": tabla_etapas,
        "resumen_ejecutivo": resumen_ejecutivo,
        "directiva_agronomica": directiva,
    }
