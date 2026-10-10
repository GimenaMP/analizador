"""
Punto de Entrada Principal (CLI) del Sistema Abierto de Viabilidad Agrícola.
Permite ejecutar el pipeline con argumentos de línea de comandos o con valores predeterminados.
Soporta geometrías irregulares de parcelas (4 lados desiguales, triángulos y rectángulos)
y proyecta pérdidas y ganancias sobre la inversión directa del agricultor.
"""
import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Sistema Abierto de Viabilidad de Siembra de Maíz y Proyección Financiera - Jutiapa (Guatemala)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--date", type=str, default="2026-06-01", help="Fecha tentativa de siembra (AAAA-MM-DD)")
    parser.add_argument("--lat", type=float, default=14.267, help="Latitud decimal de la parcela")
    parser.add_argument("--lon", type=float, default=-90.133, help="Longitud decimal de la parcela")
    parser.add_argument("--shape", type=str, default="cuadrilatero", choices=["cuadrilatero", "triangulo", "rectangulo"], help="Forma geométrica del terreno")
    parser.add_argument("--sides", type=float, nargs="+", default=[100.0, 70.0, 90.0, 65.0], help="Medidas de los lados en metros (ej. 4 lados para cuadrilátero, 3 para triángulo)")
    parser.add_argument("--width", type=float, default=100.0, help="Ancho del terreno en metros (si es rectangular)")
    parser.add_argument("--length", type=float, default=70.0, help="Largo del terreno en metros (si es rectangular)")
    parser.add_argument("--capital", type=float, default=6500.0, help="Capital de inversión aportado para la siembra (Quetzales - Q)")
    parser.add_argument("--corn-type", type=str, default="blanco", choices=["blanco"], help="Tipo de maíz (Blanco, de primera)")
    parser.add_argument("--force-refresh", action="store_true", help="Forzar re-descarga de datos ignorando la caché")
    parser.add_argument("--no-pdf", action="store_true", help="Omitir la generación del archivo PDF")

    args = parser.parse_args()

    try:
        from pipeline import AgroViabilityPipeline
    except ImportError as e:
        print(f"\n[ERROR] Falta una dependencia requerida: {e}")
        print("Por favor instala las dependencias del proyecto ejecutando:")
        print("    pip install -r requirements.txt\n")
        sys.exit(1)

    pipeline = AgroViabilityPipeline()
    result = pipeline.run(
        sowing_date_str=args.date,
        lat=args.lat,
        lon=args.lon,
        shape_type=args.shape,
        terrain_sides=args.sides,
        terrain_width_m=args.width,
        terrain_length_m=args.length,
        capital_disponible_q=args.capital,
        tipo_maiz=args.corn_type,
        use_cache=not args.force_refresh,
        force_refresh=args.force_refresh,
        generate_pdf=not args.no_pdf
    )

    # Asegurar codificación utf-8 en terminales Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Impresión estructurada en consola
    print("\n" + "=" * 70)
    print("                    REPORTE AGROCLIMÁTICO Y FINANCIERO")
    print("=" * 70)
    print(f"UBICACIÓN ANALIZADA: Lat {result.lat:.4f}, Lon {result.lon:.4f} (Jutiapa, Guatemala)")
    print(f"FECHA TENTATIVA DE SIEMBRA: {result.sowing_date}")
    print(f"FASE ENSO OBSERVADA (NOAA): {result.fase_enso}")
    print(f"PROBABILIDAD CALIBRADA:     {result.probabilidad * 100:.1f}%")
    print(f"ESTADO DEL SEMÁFORO:        [{result.semaforo_color.upper()}] - {result.semaforo_estado}")
    print(f"ACCIÓN RECOMENDADA:         {result.semaforo_accion}")
    
    crit = result.criterios_algoritmo
    print(f"CRITERIOS DE VIABILIDAD:    ETa/ETc >= {crit.get('eta_etc_min', 0.90):.2f} (90%) | Anegamiento <= {crit.get('waterlog_max_days', 8)} días | Ventana: {crit.get('ventana_dias', 60)} días")

    ev = result.evaluacion_historica
    if ev.get("disponible"):
        print("\n" + "-" * 70)
        print("VALIDACIÓN HISTÓRICA REAL EX-POST (A 60 DÍAS DE LA FECHA):")
        print(f"  * Relación ETa/ETc real:     {ev['eta_etc_real']:.2f} (Umbral estricto: >= {crit.get('eta_etc_min', 0.90):.2f})")
        print(f"  * Días con anegamiento real: {ev['dias_anegamiento_real']} días (Máximo permitido: <= {crit.get('waterlog_max_days', 8)} días)")
        print(f"  * Resultado histórico real:  [{ev['resultado_real']}] - {ev['motivo_fallo']}")
        print(f"  * Diagnóstico y contexto:    {ev['nota_discrepancia']}")
    
    t = result.terreno
    d = result.densidad
    print("\n" + "-" * 70)
    print("PARCELA Y DENSIDAD DE SIEMBRA (RF-05, RF-06):")
    print(f"  * Forma del lote: {t.descripcion_forma}")
    print(f"  * Superficie calculada: {t.area_m2:,.1f} m² ({t.manzanas:.3f} mz | {t.hectareas:.3f} ha)")
    print(f"  * Perímetro total: {t.perimetro_m:,.1f} metros")
    print(f"  * Densidad recomendada: {d['densidad_plantas_m2']} plantas/m² ({d['densidad_plantas_mz']:,} pl/mz)")
    print(f"  * Población total lote: {d['plantas_totales_predio']:,} plantas")
    print(f"  * Semilla total requerida: {d['semillas_totales_requeridas']:,} semillas ({d['libras_semilla']} lbs / {d['bolsas_comerciales']} bolsas)")
    print(f"  * Marco de plantación: {d['distancia_surcos_cm']} cm entre surcos | {d['distancia_posturas_cm']} cm entre posturas")

    f = result.financiero
    print("\n" + "-" * 70)
    print("PROYECCIÓN FINANCIERA Y PÉRDIDAS & GANANCIAS (RF-07):")
    print(f"  * Fuente Oficial de Precios: {f['fuente_oficial_maga']}")
    print(f"  * Fecha Última Actualización: {f['fecha_actualizacion_maga']}")
    print(f"  * Precio Oficial Maíz {f['tipo_maiz']}: Q {f['precio_maga_qq']:.2f} / quintal")
    print(f"  * Capital de Inversión Aportado: Q {f['capital_inversion_q']:,.2f}")
    print(f"  * Rendimiento Estimado: {f['rendimiento_estimado_qq_mz']} qq/mz -> Producción Total: {f['produccion_total_estimada_qq']} qq")
    print(f"  * Ingreso Bruto Proyectado:      Q {f['ingreso_bruto_q']:,.2f}")
    print(f"  * Utilidad Neta Proyectada:      Q {f['utilidad_neta_q']:,.2f} (ROI: {f['roi_pct']}%)")
    print(f"  * Punto de Equilibrio:           {f['punto_equilibrio_qq']} quintales")
    print(f"  * Inversión por Quintal:         Q {f['inversion_por_quintal_q']:.2f} / qq")

    print("\n" + "-" * 70)
    print("PROYECCIÓN ESTACIONAL PARA PRÓXIMOS MESES:")
    print(f"{'Mes Objetivo':<16} | {'Probabilidad':<14} | {'Estado':<20} | {'Fase ENSO'}")
    print("-" * 70)
    for p in result.proyecciones_futuras:
        print(f"{p['mes_nombre']:<16} | {p['probabilidad']*100:11.1f}%   | {p['estado']:<20} | {p['fase_enso']}")

    print("\n" + "=" * 70)
    print("ARCHIVOS GENERADOS:")
    if result.report_pdf_path:
        print(f"  [OK] Reporte Ejecutivo: {result.report_pdf_path}")
    for name, path in result.chart_paths.items():
        print(f"  [OK] Gráfica ({name}): {path}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

# Exportaciones para compatibilidad de escaneo Vercel
handler = None
app = None
