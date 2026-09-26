"""
Módulo de Descarga y Adquisición de Datos Agrometeorológicos.
Descarga datos de reanálisis ERA5 vía Open-Meteo y series ENSO de NOAA PSL con soporte de caché local.
"""
import time
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
import requests

from config.settings import GeoConfig, MacroClimateConfig, GEO_CONFIG, MACRO_CONFIG, PATH_CONFIG


def _get_json_with_retry(url: str, params: dict, retries: int = 5, initial_backoff: float = 5.0) -> dict:
    """Realiza peticiones HTTP GET con reintentos exponenciales para mitigar códigos 429."""
    backoff = initial_backoff
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, params=params, timeout=90)
            if response.status_code == 429:
                wait_time = backoff * attempt
                print(f"  [Open-Meteo] Límite de tasa (429). Esperando {wait_time:.1f}s antes de reintentar...")
                time.sleep(wait_time)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt == retries:
                raise RuntimeError(f"Error persistente en Open-Meteo tras {retries} intentos: {e}")
            time.sleep(backoff)
    raise RuntimeError("Open-Meteo: Se superó el límite de intentos (HTTP 429).")


def fetch_weather(
    geo: GeoConfig = GEO_CONFIG,
    cache_dir: Optional[Path] = None,
    use_cache: bool = True,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Descarga la serie diaria histórica ERA5 para las coordenadas dadas.
    Implementa caché local para acelerar reejecuciones y proteger la cuota de la API.
    """
    cache_path = (cache_dir or PATH_CONFIG.cache_dir) / f"weather_{geo.lat:.3f}_{geo.lon:.3f}_{geo.start_year}.csv"
    
    if use_cache and not force_refresh and cache_path.exists():
        print(f"  [Caché] Cargando clima ERA5 desde {cache_path.name}")
        df = pd.read_csv(cache_path)
        df["time"] = pd.to_datetime(df["time"])
        return df

    print(f"  [API] Descargando serie diaria ERA5 desde {geo.start_year} para ({geo.lat}, {geo.lon})...")
    end = pd.Timestamp.today().normalize() - pd.Timedelta(days=6)
    frames, elev = [], None

    for y0 in range(geo.start_year, end.year + 1, 10):
        s = pd.Timestamp(y0, 1, 1)
        e = min(pd.Timestamp(y0 + 9, 12, 31), end)
        js = _get_json_with_retry(
            geo.archive_url,
            dict(
                latitude=geo.lat,
                longitude=geo.lon,
                start_date=s.date().isoformat(),
                end_date=e.date().isoformat(),
                daily=",".join(geo.daily_vars),
                timezone=geo.timezone,
            )
        )
        elev = js.get("elevation", elev)
        frames.append(pd.DataFrame(js["daily"]))
        print(f"    [OK] ERA5 tramo {s.year}-{e.year} completado")

    df = pd.concat(frames, ignore_index=True).rename(
        columns={
            "precipitation_sum": "precip_mm",
            "et0_fao_evapotranspiration": "et0_mm",
            "temperature_2m_mean": "t_mean_c",
        }
    )
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)

    core = ["precip_mm", "et0_mm", "t_mean_c"]
    ok = df[core].notna().all(axis=1)
    df = df.loc[:ok[ok].index.max()].copy()

    # Validaciones de integridad física y temporal
    assert df[core].notna().all().all(), "Huecos internos en la serie meteorológica descargada."
    assert (df["time"].diff().dropna() == pd.Timedelta(days=1)).all(), "Serie con días faltantes en secuencia."
    assert df["precip_mm"].between(0, 600).all() and df["et0_mm"].between(0, 20).all(), "Valores físicos fuera de rango."

    print(f"    Punto ERA5: elevación = {elev} m | Cobertura: {df['time'].iloc[0].date()} a {df['time'].iloc[-1].date()} ({len(df)} días)")

    if use_cache:
        df.to_csv(cache_path, index=False)
        print(f"    Guardado en caché local: {cache_path.name}")

    return df


def parse_psl_series(url: str, col_name: str) -> pd.Series:
    """Parsea el formato tabular de texto de series históricas de NOAA PSL."""
    resp = requests.get(url, timeout=40)
    resp.raise_for_status()
    rows = []
    for line in resp.text.splitlines():
        tok = line.strip().split()
        if len(tok) == 13 and tok[0].isdigit() and len(tok[0]) == 4:
            rows.append(tok)

    if not rows:
        raise ValueError(f"Formato no reconocido o archivo vacío en {url}")

    raw = pd.DataFrame(rows, columns=["year"] + list(range(1, 13))).astype(float)
    long_df = raw.melt(id_vars="year", var_name="month", value_name=col_name)
    long_df["date"] = pd.to_datetime(
        dict(year=long_df["year"].astype(int), month=long_df["month"].astype(int), day=1)
    )
    long_df.loc[long_df[col_name] <= -90.0, col_name] = np.nan
    return long_df.set_index("date")[col_name].sort_index()


def fetch_macro(
    macro_cfg: MacroClimateConfig = MACRO_CONFIG,
    cache_dir: Optional[Path] = None,
    use_cache: bool = True,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Descarga y calcula los índices climáticos ENSO rezagados (sin filtrado de futuro).
    """
    cache_path = (cache_dir or PATH_CONFIG.cache_dir) / "macro_enso_indices.csv"

    if use_cache and not force_refresh and cache_path.exists():
        print(f"  [Caché] Cargando índices ENSO desde {cache_path.name}")
        df = pd.read_csv(cache_path, index_col=0)
        df.index = pd.to_datetime(df.index)
        return df

    print("  [API] Descargando índices ENSO desde NOAA PSL...")
    series_list = []
    for name, url in macro_cfg.urls.items():
        s = parse_psl_series(url, name)
        series_list.append(s)
        print(f"    [OK] Índice {name} descargado exitosamente")

    df = pd.concat(series_list, axis=1).sort_index().asfreq("MS")
    # Construcción rigurosa de lags para evitar 'lookahead bias'
    df["mei_lag1"] = df["mei_v2"].shift(1)
    df["mei_trend"] = df["mei_lag1"] - df["mei_v2"].shift(2)
    df["nino34_lag1"] = df["nino34_anom"].shift(1)

    result = df[["mei_lag1", "mei_trend", "nino34_lag1"]].copy()

    if use_cache:
        result.to_csv(cache_path)
        print(f"    Guardado en caché local: {cache_path.name}")

    return result
