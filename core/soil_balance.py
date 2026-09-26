"""
Módulo de Física de Suelos y Balance Hídrico Agrometeorológico.
Implementa el modelo pedotransfer de Saxton & Rawls (2006) y la simulación
hidrológica de suelo por capas/bucket bajo lineamientos FAO-56.
"""
from typing import Tuple
import numpy as np
import pandas as pd

from config.settings import AgroConfig, SoilConfig, AGRO_CONFIG, SOIL_CONFIG


class SoilProfile:
    """
    Perfil edáfico basado en funciones de pedotransferencia de Saxton & Rawls (2006).
    Calcula capacidad de campo (FC), punto de marchitez permanente (WP),
    agua total disponible (TAW) y agua fácilmente aprovechable (RAW).
    """
    def __init__(self, cfg: SoilConfig = SOIL_CONFIG):
        s = cfg.sand_pct / 100.0
        c = cfg.clay_pct / 100.0
        om = cfg.om_pct

        # Estimación de humedad volumétrica a capacidad de campo (θFC)
        fc_first = (
            -0.251 * s + 0.195 * c + 0.011 * om + 0.006 * s * om
            - 0.027 * c * om + 0.452 * s * c + 0.299
        )
        self.theta_fc = fc_first + (1.283 * fc_first**2 - 0.374 * fc_first - 0.015)

        # Estimación de humedad volumétrica a punto de marchitez permanente (θWP)
        wp_first = (
            -0.024 * s + 0.487 * c + 0.006 * om + 0.005 * s * om
            - 0.013 * c * om + 0.068 * s * c + 0.031
        )
        self.theta_wp = wp_first + (0.14 * wp_first - 0.02)
        self.p_depletion = cfg.p_depletion

    def taw(self, root_depth_mm: float) -> float:
        """Total Available Water (Agua Total Disponible en mm)."""
        return max(0.0, (self.theta_fc - self.theta_wp) * root_depth_mm)

    def raw(self, root_depth_mm: float) -> float:
        """Readily Available Water (Agua Fácilmente Aprovechable sin estrés en mm)."""
        return self.p_depletion * self.taw(root_depth_mm)


def bucket_series(
    p_arr: np.ndarray,
    et0_arr: np.ndarray,
    taw: float,
    raw: float,
    kc: float,
    s0_frac: float = 0.5
) -> np.ndarray:
    """
    Simulación continua tipo cubo (bucket) para humedad del suelo en descanso/antecedente.
    Retorna la fracción de llenado s / TAW.
    """
    s = taw * s0_frac
    out = np.empty(len(p_arr), dtype=float)
    for i in range(len(p_arr)):
        # Factor de estrés hídrico Ks (FAO-56)
        ks = 1.0 if (taw - s) <= raw else min(1.0, max(0.0, s / max(taw - raw, 1e-6)))
        s = min(taw, max(0.0, s + p_arr[i] - kc * et0_arr[i] * ks))
        out[i] = s / max(taw, 1e-6)
    return out


def simulate_window(
    p_window: np.ndarray,
    et0_window: np.ndarray,
    f0: float,
    soil: SoilProfile,
    agro_cfg: AgroConfig = AGRO_CONFIG
) -> Tuple[float, int]:
    """
    Simula el balance hídrico del cultivo durante la ventana crítica fenológica (60 días).
    Retorna:
      - ratio: Relación de evapotranspiración real a evapotranspiración del cultivo (ETa / ETc).
      - waterlog_days: Número de días con exceso severo de agua en el perfil (anegamiento).
    """
    taw = soil.taw(agro_cfg.crop_root_mm)
    raw = soil.raw(agro_cfg.crop_root_mm)
    s = f0 * taw
    eta_sum = 0.0
    etc_sum = 0.0
    waterlog_count = 0
    kc_curve = agro_cfg.kc_curve

    for i in range(agro_cfg.window_days):
        etc = kc_curve[i] * et0_window[i]
        ks = 1.0 if (taw - s) <= raw else min(1.0, max(0.0, s / max(taw - raw, 1e-6)))
        eta = etc * ks
        s += p_window[i] - eta

        if s > taw:
            if (s - taw) >= agro_cfg.excess_mm_day:
                waterlog_count += 1
            s = taw
        elif s < 0.0:
            s = 0.0

        eta_sum += eta
        etc_sum += etc

    ratio = eta_sum / max(etc_sum, 1e-6)
    return ratio, waterlog_count


def build_dataset(
    df_weather: pd.DataFrame,
    df_macro: pd.DataFrame,
    soil: SoilProfile,
    agro_cfg: AgroConfig = AGRO_CONFIG
) -> pd.DataFrame:
    """
    Construye el dataset con variables hidrológicas, climatológicas y etiquetas de viabilidad.
    """
    df = df_weather.copy()

    # 1. Humedad del suelo antecedente (fallow)
    df["humedad_suelo_frac"] = bucket_series(
        df["precip_mm"].values,
        df["et0_mm"].values,
        soil.taw(agro_cfg.fallow_root_mm),
        soil.raw(agro_cfg.fallow_root_mm),
        agro_cfg.fallow_kc
    )

    # 2. Rachas secas (dry spells < 1.5 mm/día)
    dry = (df["precip_mm"] < 1.5).astype(int)
    df["dry_spell_len"] = dry.groupby((dry == 0).cumsum()).cumsum()

    # 3. Lluvia acumulada y balance hídrico móvil
    df["precip_acc_15d"] = df["precip_mm"].rolling(15, min_periods=15).sum()
    df["precip_acc_30d"] = df["precip_mm"].rolling(30, min_periods=30).sum()
    df["balance_hidrico_30d"] = df["precip_acc_30d"] - df["et0_mm"].rolling(30, min_periods=30).sum()

    # 4. Características de estacionalidad continua (seno / coseno del día del año)
    df["month"] = df["time"].dt.month
    df["year"] = df["time"].dt.year
    doy = df["time"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)

    # 5. Cruce con índices ENSO mensuales (rezago temporal exacto)
    df["month_key"] = df["time"].dt.to_period("M").dt.to_timestamp()
    df = df.merge(df_macro, left_on="month_key", right_index=True, how="left")

    # 6. Simulación de la ventana de siembra hacia el futuro para generar etiquetas de entrenamiento
    n = len(df)
    p_vals = df["precip_mm"].values
    et0_vals = df["et0_mm"].values
    frac_vals = df["humedad_suelo_frac"].values
    months = df["month"].values

    ratio_arr = np.full(n, np.nan)
    wl_arr = np.full(n, np.nan)

    for t in range(agro_cfg.spinup_days, n - agro_cfg.window_days):
        if months[t] in agro_cfg.sowing_months:
            ratio_arr[t], wl_arr[t] = simulate_window(
                p_vals[t + 1 : t + 1 + agro_cfg.window_days],
                et0_vals[t + 1 : t + 1 + agro_cfg.window_days],
                frac_vals[t],
                soil,
                agro_cfg
            )

    df["eta_etc"] = ratio_arr
    df["dias_anegamiento"] = wl_arr
    df["fallo_sequia"] = df["eta_etc"] < agro_cfg.eta_etc_min
    df["fallo_exceso"] = df["dias_anegamiento"] > agro_cfg.waterlog_max_days

    # Target de viabilidad global: 1 = viable, 0 = fracaso por estrés o exceso hídrico
    df["target"] = np.where(
        df["eta_etc"].notna(),
        (~df["fallo_sequia"] & ~df["fallo_exceso"]).astype(float),
        np.nan
    )

    return df
