"""
Módulo de Visualización Gráfica para el Sistema Agrícola (RF-03, RF-04, RF-05).
Genera gráficas de balance hídrico, planos del terreno a escala (rectangulares, triangulares o cuadriláteros irregulares),
curvas de calibración y tableros integrados para toma de decisiones agronómicas.
"""
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from config.settings import AgroConfig, AGRO_CONFIG, PATH_CONFIG
from core.agronomy_economics import TerrainModel


def plot_water_balance_window(
    df: pd.DataFrame,
    sowing_date_str: str,
    agro_cfg: AgroConfig = AGRO_CONFIG,
    output_path: Optional[Path] = None
) -> Path:
    """
    Gráfica del comportamiento de lluvias y balance hídrico durante el ciclo del cultivo (RF-04).
    Muestra precipitación diaria, lluvia acumulada, demanda hídrica ETc y humedad del suelo.
    """
    s_ts = pd.to_datetime(sowing_date_str)
    
    # Extraer ventana exactamente de longitud agro_cfg.window_days
    sub = df[(df["time"] >= s_ts) & (df["time"] < s_ts + pd.Timedelta(days=agro_cfg.window_days))].copy()
    if sub.empty or len(sub) < 15:
        # Fallback a ventana climatológica si la fecha es futura
        m = s_ts.month
        month_subset = df[df["month"] == m]
        if not month_subset.empty:
            last_year_in_month = month_subset["year"].max()
            ref_start = pd.Timestamp(year=last_year_in_month, month=m, day=min(s_ts.day, 28))
            sub = df[(df["time"] >= ref_start) & (df["time"] < ref_start + pd.Timedelta(days=agro_cfg.window_days))].copy()

        if sub.empty or len(sub) < agro_cfg.window_days:
            sub = df.tail(agro_cfg.window_days).copy()

        sub["time"] = pd.date_range(s_ts, periods=len(sub), freq="D")

    # Garantizar exactamente window_days
    sub = sub.iloc[:agro_cfg.window_days].reset_index(drop=True)
    n_days = len(sub)
    dias = np.arange(1, n_days + 1)
    precip_acc = sub["precip_mm"].cumsum()

    # Interpolar Kc exactamente para los n_days
    kc = np.interp(dias, list(agro_cfg.kc_days_points), list(agro_cfg.kc_values_points))
    etc = kc * sub["et0_mm"].values
    etc_acc = np.cumsum(etc)
    e_ts = sub["time"].iloc[-1]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
    
    # Panel 1: Lluvia vs Demanda Hídrica ETc
    ax1.bar(dias, sub["precip_mm"], color="#3B82F6", alpha=0.6, width=0.8, label="Lluvia diaria (mm)")
    ax1.plot(dias, etc, color="#EF4444", linewidth=2.0, linestyle="--", label="Demanda ETc (mm/día)")
    ax1.plot(dias, precip_acc, color="#1D4ED8", linewidth=2.2, label="Lluvia acumulada (mm)")
    ax1.plot(dias, etc_acc, color="#B91C1C", linewidth=2.0, label="ETc acumulada (mm)")
    
    ax1.set_ylabel("Milímetros (mm)", fontsize=11, fontweight="bold")
    ax1.set_title(f"Balance Hídrico del Cultivo • Ventana de 60 Días: {sowing_date_str} a {e_ts.strftime('%Y-%m-%d')}", fontsize=11, fontweight="bold", pad=12)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Panel 2: Fracción de Humedad del Suelo
    s_frac = sub["humedad_suelo_frac"].values
    ax2.plot(dias, s_frac * 100, color="#10B981", linewidth=2.2, label="% Agua útil disponible")
    ax2.axhline(50, color="#F59E0B", linestyle=":", linewidth=1.8, label="Umbral de inicio de estrés (RAW 50%)")
    ax2.axhline(20, color="#EF4444", linestyle="--", linewidth=1.5, label="Estrés severo (20%)")
    ax2.fill_between(dias, 0, 50, color="#F59E0B", alpha=0.12)
    ax2.fill_between(dias, 0, 20, color="#EF4444", alpha=0.2)
    
    ax2.set_xlabel("Días desde la siembra (DDS)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Humedad Suelo (%)", fontsize=11, fontweight="bold")
    ax2.set_ylim(0, 105)
    ax2.legend(loc="lower left", frameon=True, facecolor="white", framealpha=0.9)
    ax2.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    save_path = output_path or (PATH_CONFIG.output_dir / "balance_hidrico_siembra.png")
    plt.savefig(save_path, dpi=200)
    plt.close()
    return save_path


def plot_terrain_layout(
    terrain: TerrainModel,
    output_path: Optional[Path] = None
) -> Path:
    """
    Modelado geométrico y visual del terreno en un plano a escala interactivo (RF-05).
    Soporta terrenos rectangulares, triangulares y cuadriláteros con 4 lados desiguales.
    """
    fig, ax = plt.subplots(figsize=(8.5, 6.5))

    vertices = terrain.get_polygon_vertices()
    xs = [p[0] for p in vertices]
    ys = [p[1] for p in vertices]

    # Dibujar polígono del terreno
    poly = patches.Polygon(
        vertices, closed=True,
        linewidth=2.5, edgecolor="#166534", facecolor="#DCFCE7", alpha=0.85
    )
    ax.add_patch(poly)

    # Dibujar surcos simulados de cultivo dentro del terreno
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    step_y = max(5.0, (max_y - min_y) / 8.0)
    cur_y = min_y + step_y
    while cur_y < max_y:
        ax.plot([min_x + 5, max_x - 5], [cur_y, cur_y], color="#15803D", linestyle=":", linewidth=0.8, alpha=0.5)
        cur_y += step_y

    # Rotular cada lado con su medida exacta
    n_pts = len(vertices)
    for i in range(n_pts):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % n_pts]
        mx = (p1[0] + p2[0]) / 2.0
        my = (p1[1] + p2[1]) / 2.0
        dist = np.hypot(p2[0] - p1[0], p2[1] - p1[1])
        
        # Orientación y etiqueta
        side_label = f"Lado {i+1}: {dist:.1f} m"
        if i < len(terrain.sides):
            side_label = f"L{i+1}: {terrain.sides[i]:.1f} m"

        ax.annotate(
            side_label,
            xy=(mx, my),
            ha="center", va="center",
            fontsize=9.5, fontweight="bold", color="#14532D",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEF3C7", edgecolor="#D97706", alpha=0.9)
        )

    # Marcar vértices
    for i, (vx, vy) in enumerate(vertices):
        ax.plot(vx, vy, "o", color="#B45309", markersize=6)
        ax.text(vx, vy + 2.5, f"V{i+1}", fontsize=8.5, fontweight="bold", color="#78350F", ha="center")

    # Centro geométrico (centroide) para la caja de texto
    cx = float(np.mean(xs))
    cy = float(np.mean(ys))

    info_text = (
        f"PARCELA AGRÍCOLA MODELADA\n"
        f"Forma: {terrain.descripcion_forma}\n"
        f"-----------------------------------------\n"
        f"Superficie: {terrain.area_m2:,.1f} m²\n"
        f"Manzanas (mz): {terrain.manzanas:.3f} mz\n"
        f"Hectáreas (ha): {terrain.hectareas:.3f} ha\n"
        f"Perímetro Total: {terrain.perimetro_m:,.1f} m"
    )
    ax.text(
        cx, cy, info_text,
        ha="center", va="center", fontsize=9.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="white", edgecolor="#166534", alpha=0.94)
    )

    # Flecha de orientación Norte
    margin_x = max(10.0, (max_x - min_x) * 0.18)
    margin_y = max(10.0, (max_y - min_y) * 0.18)
    
    n_pos_x = max_x + margin_x * 0.4
    n_pos_y = max_y - margin_y * 0.2
    ax.annotate(
        "N", xy=(n_pos_x, n_pos_y),
        xytext=(n_pos_x, n_pos_y - margin_y * 0.6),
        arrowprops=dict(facecolor="#B91C1C", edgecolor="#991B1B", width=2.5, headwidth=8),
        ha="center", va="bottom", fontsize=11, fontweight="bold", color="#B91C1C"
    )

    ax.set_xlim(min_x - margin_x, max_x + margin_x)
    ax.set_ylim(min_y - margin_y, max_y + margin_y)
    ax.set_aspect("equal")
    ax.set_title(f"Plano Geométrico del Terreno • {terrain.descripcion_forma}", fontsize=12, fontweight="bold", pad=14)
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.set_xlabel("Distancia este a oeste en metros", fontsize=9, color="#4B5563")
    ax.set_ylabel("Distancia norte a sur en metros", fontsize=9, color="#4B5563")

    plt.tight_layout()
    save_path = output_path or (PATH_CONFIG.output_dir / "plano_terreno.png")
    plt.savefig(save_path, dpi=200)
    plt.close()
    return save_path


def plot_calibration(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    model_name: str,
    output_path: Optional[Path] = None
) -> Path:
    """Genera la curva de calibración de probabilidades out-of-fold."""
    from sklearn.calibration import calibration_curve
    pt, pp = calibration_curve(y_true, y_prob, n_bins=5, strategy="quantile")

    plt.figure(figsize=(6, 5))
    plt.plot(pp, pt, marker="o", color="#2563EB", linewidth=2, label=model_name)
    plt.plot([0, 1], [0, 1], "--", color="#9CA3AF", label="Calibración perfecta")
    plt.xlabel("Probabilidad Pronosticada", fontsize=10, fontweight="bold")
    plt.ylabel("Frecuencia Observada", fontsize=10, fontweight="bold")
    plt.title("Curva de Calibración Fuera de Muestra (OOF)", fontsize=11, fontweight="bold")
    plt.legend(frameon=True)
    plt.grid(alpha=0.4, linestyle=":")
    plt.tight_layout()

    save_path = output_path or (PATH_CONFIG.output_dir / "calibracion_modelo.png")
    plt.savefig(save_path, dpi=200)
    plt.close()
    return save_path
