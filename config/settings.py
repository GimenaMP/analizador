"""
Módulo de Configuración Centralizada para el Sistema de Viabilidad Agrícola.
Define parámetros geográficos, agronómicos, de física de suelos, económicos (MAGA) y de modelos.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
import numpy as np


@dataclass(frozen=True)
class GeoConfig:
    """Configuración geográfica de la parcela."""
    lat: float = 14.267
    lon: float = -90.133
    start_year: int = 1981
    timezone: str = "America/Guatemala"
    municipality: str = "Calderas, San José Acatempa, Jutiapa (Guatemala)"
    archive_url: str = "https://archive-api.open-meteo.com/v1/archive"
    daily_vars: Tuple[str, ...] = (
        "precipitation_sum",
        "et0_fao_evapotranspiration",
        "temperature_2m_mean",
    )


@dataclass(frozen=True)
class AgroConfig:
    """Parámetros fenológicos y agronómicos del cultivo de maíz."""
    sowing_months: List[int] = field(default_factory=lambda: [1,2,3,4,5, 6, 7, 8, 9, 10, 11, 12])
    window_days: int = 60
    total_cycle_days: int = 120
    spinup_days: int = 365
    eta_etc_min: float = 0.90
    excess_mm_day: float = 15.0
    waterlog_max_days: int = 8

    # Coeficientes de cultivo Kc para la ventana inicial/crítica (60 días)
    # y coeficientes para suelo en descanso
    kc_days_points: Tuple[int, int, int] = (0, 20, 60)
    kc_values_points: Tuple[float, float, float] = (0.30, 0.30, 1.15)
    fallow_kc: float = 0.5
    fallow_root_mm: float = 400.0
    crop_root_mm: float = 600.0

    @property
    def kc_curve(self) -> np.ndarray:
        return np.interp(
            np.arange(1, self.window_days + 1),
            list(self.kc_days_points),
            list(self.kc_values_points)
        )


@dataclass(frozen=True)
class SoilConfig:
    """Parámetros de textura de suelo según Saxton & Rawls (2006)."""
    clay_pct: float = 26.0      # % Arcilla (Franco-arcillo-arenoso por defecto)
    sand_pct: float = 52.0      # % Arena
    om_pct: float = 1.8         # % Materia orgánica
    p_depletion: float = 0.55   # Factor de agotamiento de agua fácilmente aprovechable (RAW)


@dataclass(frozen=True)
class MacroClimateConfig:
    """URLs oficiales para índices climáticos ENSO de NOAA PSL."""
    urls: dict = field(default_factory=lambda: {
        "mei_v2": "https://psl.noaa.gov/data/correlation/meiv2.data",
        "nino34_anom": "https://psl.noaa.gov/data/timeseries/month/data/nino34.long.anom.data",
    })
    features_local: Tuple[str, ...] = (
        "precip_acc_15d",
        "precip_acc_30d",
        "balance_hidrico_30d",
        "humedad_suelo_frac",
        "dry_spell_len",
        "doy_sin",
        "doy_cos",
    )
    features_enso: Tuple[str, ...] = ("mei_lag1", "mei_trend")

    @property
    def features_full(self) -> List[str]:
        return list(self.features_local + self.features_enso)


@dataclass(frozen=True)
class MagaPriceConfig:
    """
    Precios oficiales de mercado de granos básicos en Guatemala.
    Fuente: Ministerio de Agricultura, Ganadería y Alimentación (MAGA) - DIPLAN / SIMPA.
    """
    fuente_oficial: str = "MAGA - DIPLAN / SIMPA (Mercado Mayorista La Terminal)"
    fecha_actualizacion: str = "2026-10-09"
    
    # Precios de referencia por quintal (qq) en Quetzales (Q)
    precio_qq_maiz_blanco: float = 235.0
    
    # Costos promedio de producción de maíz tradicional/tecnificado por manzana (Q/mz)
    costo_preparacion_suelo_mz: float = 650.0
    costo_semilla_mz: float = 850.0
    costo_fertilizacion_mz: float = 1800.0
    costo_control_plagas_malezas_mz: float = 600.0
    costo_mano_obra_labores_mz: float = 1200.0
    costo_cosecha_desgrane_mz: float = 800.0

    # Rendimiento esperado base en quintales por manzana en la región
    rendimiento_base_qq_mz: float = 65.0


@dataclass(frozen=True)
class SemaforoConfig:
    """
    Umbrales de probabilidad calibrada para el semáforo agrometeorológico (RF-03).
    Ajustados empíricamente según tasa real de éxito en 45 años de ERA5:
      - prob >= prob_optimo_min (0.70): ÓPTIMO (Verde, tasa real > 76%)
      - prob_alerta_min (0.40) <= prob < 0.70: CONDICIONADO / ALERTA (Amarillo)
      - prob < prob_alerta_min (0.40): NO SEMBRAR (Rojo, tasa de fracaso > 89%)
    """
    prob_optimo_min: float = 0.80
    prob_alerta_min: float = 0.40


@dataclass(frozen=True)
class ValidationConfig:
    """
    Límites de validación de entradas basados en datos históricos del sector agrícola
    de Jutiapa, Guatemala (Corredor Seco).
    Fuentes: ICTA, MAGA-DIPLAN, FAO Guatemala, datos de campo extensionistas.
    """
    # Límites geográficos exclusivos de la micro-región de Calderas, San José Acatempa, Jutiapa
    lat_min: float = 14.240
    lat_max: float = 14.290
    lon_min: float = -90.160
    lon_max: float = -90.110
    localidad_exclusiva: str = "Calderas, San José Acatempa, Jutiapa"

    # Límites de fecha de análisis
    date_min_year: int = 1981
    date_max_year: int = 2030

    # Límites financieros históricos para el Corredor Seco (Q por manzana)
    capital_min_q: float = 500.0          # Mínimo absoluto (ni semilla se compra)
    capital_max_q: float = 150_000.0      # Máximo razonable para agricultura familiar
    capital_per_mz_min_q: float = 2_000.0 # Mínimo histórico por manzana (subsistencia extrema)
    capital_per_mz_max_q: float = 25_000.0 # Máximo histórico por manzana (tecnificado con riego)

    # Límites de terreno
    side_min_m: float = 1.0
    side_max_m: float = 2_000.0
    max_area_m2: float = 700_000.0  # 100 manzanas (límite razonable)

    # Límites de strings anti-inyección
    max_string_length: int = 100


@dataclass(frozen=True)
class PathConfig:
    """Rutas de directorios del proyecto."""
    root_dir: Path = Path(__file__).resolve().parent.parent
    cache_dir: Path = field(init=False)
    output_dir: Path = field(init=False)

    def __post_init__(self):
        cache = self.root_dir / ".cache"
        output = self.root_dir / "output"
        cache.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "cache_dir", cache)
        object.__setattr__(self, "output_dir", output)


# Instancias globales de configuración por defecto
GEO_CONFIG = GeoConfig()
AGRO_CONFIG = AgroConfig()
SOIL_CONFIG = SoilConfig()
MACRO_CONFIG = MacroClimateConfig()
MAGA_CONFIG = MagaPriceConfig()
SEMAFORO_CONFIG = SemaforoConfig()
VALIDATION_CONFIG = ValidationConfig()
PATH_CONFIG = PathConfig()
