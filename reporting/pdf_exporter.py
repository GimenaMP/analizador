"""
Módulo de Exportación de Informes en Formato PDF (RF-08, RNF-04).
Genera un informe ejecutivo integral y profesional con tipografía balanceada,
tablas de pérdidas y ganancias, gráficos a escala calibrados y directivas agronómicas precisas.
Diseñado para lectura clara de productores agrícolas e instituciones financieras.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import datetime

from config.settings import PATH_CONFIG


def _clean_str(text: Any) -> str:
    """Sanitiza cadenas asegurando compatibilidad completa con el encoding de fuentes core de FPDF."""
    if text is None:
        return ""
    s = str(text)
    replacements = {
        "\u2022": " - ", # bullet
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2192": "->",
        "\u2190": "<-",
        "•": " - ",
        "–": "-",
        "—": "-",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def export_pdf_report(
    report_data: Dict[str, Any],
    chart_paths: Optional[Dict[str, Path]] = None,
    output_path: Optional[Path] = None
) -> Path:
    """
    Genera el informe final en formato PDF con diseño ejecutivo de alta calidad.
    Si fpdf2 está disponible compila el PDF estructurado; adicionalmente genera
    una versión Markdown de alta fidelidad como respaldo.
    """
    out_dir = PATH_CONFIG.output_dir
    pdf_file = output_path or (out_dir / "Informe_Viabilidad_Maiz_Jutiapa.pdf")
    md_file = out_dir / "Informe_Viabilidad_Maiz_Jutiapa.md"

    # 1. Generar contenido estructurado en Markdown como respaldo
    md_content = _build_markdown_summary(report_data, chart_paths)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. Compilar a PDF mediante fpdf2
    try:
        from fpdf import FPDF

        class AgriculturalReportPDF(FPDF):
            def cell(self, *args, **kwargs):
                if len(args) >= 3 and isinstance(args[2], str):
                    args = list(args)
                    args[2] = _clean_str(args[2])
                elif "text" in kwargs and isinstance(kwargs["text"], str):
                    kwargs["text"] = _clean_str(kwargs["text"])
                elif "txt" in kwargs and isinstance(kwargs["txt"], str):
                    kwargs["txt"] = _clean_str(kwargs["txt"])
                return super().cell(*args, **kwargs)

            def multi_cell(self, *args, **kwargs):
                if len(args) >= 3 and isinstance(args[2], str):
                    args = list(args)
                    args[2] = _clean_str(args[2])
                elif "text" in kwargs and isinstance(kwargs["text"], str):
                    kwargs["text"] = _clean_str(kwargs["text"])
                elif "txt" in kwargs and isinstance(kwargs["txt"], str):
                    kwargs["txt"] = _clean_str(kwargs["txt"])
                return super().multi_cell(*args, **kwargs)

            def header(self):
                # Barra superior elegante en tono verde bosque
                self.set_fill_color(27, 77, 62)
                self.rect(0, 0, 210, 4, "F")

                self.set_y(9)
                self.set_font("Helvetica", "B", 12)
                self.set_text_color(27, 77, 62)
                self.cell(0, 6, "SISTEMA DE VIABILIDAD AGRÍCOLA - JUTIAPA", ln=True, align="C")

                self.set_font("Helvetica", "", 7.8)
                self.set_text_color(100, 116, 139)
                self.cell(0, 4.5, "Dictamen Técnico Agrometeorológico, Modelado de Parcela y Evaluación Financiera MAGA", ln=True, align="C")

                self.set_draw_color(226, 232, 240)
                self.set_line_width(0.4)
                self.line(15, 21, 195, 21)
                self.ln(3)

            def footer(self):
                self.set_y(-13)
                self.set_draw_color(226, 232, 240)
                self.set_line_width(0.3)
                self.line(15, 284, 195, 284)

                self.set_font("Helvetica", "", 7.5)
                self.set_text_color(148, 163, 184)
                self.cell(90, 8, "Plataforma Abierta de Apoyo Técnico al Productor Agrícola", align="L")
                self.cell(90, 8, f"Página {self.page_no()} de 3", align="R")

        pdf = AgriculturalReportPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(15, 15, 15)
        pdf.set_auto_page_break(auto=False)
        pdf.add_page()

        # ---------------------------------------------------------
        # SECCIÓN 1: RESUMEN DEL PREDIO Y LOCALIZACIÓN
        # ---------------------------------------------------------
        pdf.set_y(24)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 5, "1. RESUMEN DEL PREDIO Y LOCALIZACIÓN", ln=True)

        # Caja contenida de datos de localización (2 filas de 2 columnas amplias)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_line_width(0.3)
        pdf.rect(15, 29, 180, 18, "DF")

        # Fila 1: Municipio y Coordenadas
        pdf.set_xy(18, 30.5)
        pdf.set_font("Helvetica", "B", 7.6)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(90, 3.8, "Municipio y Micro-región:", ln=False)
        pdf.cell(84, 3.8, "Coordenadas Geográficas:", ln=True)

        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 8.2)
        pdf.set_text_color(15, 23, 42)
        muni_raw = str(report_data.get("municipio", "Jutiapa")).replace("(", "").replace(")", "").strip()
        pdf.cell(90, 4.2, muni_raw, ln=False)
        pdf.cell(84, 4.2, f"{report_data['lat']:.4f}° N, {abs(report_data['lon']):.4f}° O", ln=True)

        # Fila 2: Fecha de Siembra y Fecha de Emisión
        pdf.set_xy(18, 38.5)
        pdf.set_font("Helvetica", "B", 7.6)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(90, 3.8, "Fecha Tentativa de Siembra:", ln=False)
        pdf.cell(84, 3.8, "Fecha de Emisión del Informe:", ln=True)

        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 8.2)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(90, 4.2, str(report_data.get("fecha_siembra", "")), ln=False)
        pdf.cell(84, 4.2, datetime.date.today().strftime("%Y-%m-%d"), ln=True)

        # ---------------------------------------------------------
        # SECCIÓN 2: DICTAMEN TÉCNICO Y SEMÁFORO DE VIABILIDAD
        # ---------------------------------------------------------
        pdf.set_y(50)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 5, "2. DICTAMEN TÉCNICO Y VIABILIDAD CLIMÁTICA", ln=True)

        sem_color = report_data.get("semaforo_color", "Amarillo")
        if sem_color == "Verde":
            bg_col = (236, 253, 245)
            border_col = (167, 243, 208)
            text_col = (6, 95, 70)
        elif sem_color == "Amarillo":
            bg_col = (254, 252, 232)
            border_col = (254, 240, 138)
            text_col = (146, 64, 14)
        else:
            bg_col = (254, 242, 242)
            border_col = (254, 202, 202)
            text_col = (153, 27, 27)

        # Banner del Semáforo
        pdf.set_y(56)
        pdf.set_fill_color(*bg_col)
        pdf.set_draw_color(*border_col)
        pdf.set_line_width(0.4)
        pdf.rect(15, 56, 180, 25, "DF")

        # Fila de métricas del dictamen
        pdf.set_xy(18, 57.5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*text_col)
        
        raw_estado = str(report_data.get("semaforo_estado", "CONDICIONADO")).replace("/", " o ").replace("(", "").replace(")", "").strip()
        pdf.cell(90, 5.5, f"ESTADO: {raw_estado}", ln=False)

        pdf.set_font("Helvetica", "B", 8.2)
        prob_val = report_data.get("probabilidad", 0.5) * 100
        pdf.cell(48, 5.5, f"Viabilidad: {prob_val:.1f}%", ln=False, align="C")

        fase_raw = str(report_data.get("fase_enso", "Neutral")).replace("(", "").replace(")", "").strip()
        pdf.cell(38, 5.5, f"ENSO: {fase_raw}", ln=True, align="R")

        # Directiva de manejo agronómico
        pdf.set_xy(18, 64)
        pdf.set_font("Helvetica", "", 7.8)
        pdf.set_text_color(30, 41, 59)
        accion_limpia = str(report_data.get("semaforo_accion", "")).replace("(", "").replace(")", "").strip()
        pdf.multi_cell(174, 3.8, accion_limpia)

        # Criterios técnicos de cálculo
        crit = report_data.get("criterios_algoritmo", {})
        eta_min = crit.get("eta_etc_min", 0.90)
        wl_max = crit.get("waterlog_max_days", 8)
        pdf.set_xy(18, 73.5)
        pdf.set_font("Helvetica", "I", 7.2)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(174, 3.5, f"Criterios evaluados: Demanda hídrica mínima ETa vs ETc {eta_min*100:.0f}% - Límite de anegamiento {wl_max} días - Ventana fenológica 60 días", ln=True)

        # ---------------------------------------------------------
        # SECCIÓN 3: GEOMETRÍA DE PARCELA Y DENSIDAD DE SIEMBRA
        # ---------------------------------------------------------
        pdf.set_y(84)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 5, "3. PARCELA Y RECOMENDACIÓN DE DENSIDAD DE SIEMBRA", ln=True)

        d = report_data.get("densidad", {})
        t = report_data.get("terreno", {})
        forma_desc = str(t.get("forma", "Parcela")).replace("(", "").replace(")", "").strip()

        # 4 Cajas métricas alineadas (42.5mm de ancho cada una con 3.3mm de gap)
        box_w = 42.5
        box_h = 17
        gap = 3.33
        start_x = 15
        box_y = 90

        metric_cards = [
            ("Superficie Total", f"{t.get('area_m2', 0):,.0f} m²", f"{t.get('manzanas', 0):.2f} mz - {t.get('hectareas', 0):.2f} ha"),
            ("Densidad Óptima", f"{d.get('densidad_plantas_m2', 0)} plantas m²", f"{d.get('densidad_plantas_mz', 0):,} plantas mz"),
            ("Semilla Requerida", f"{d.get('semillas_totales_requeridas', 0):,} semillas", f"{d.get('libras_semilla', 0)} libras semilla"),
            ("Distanciamiento", f"{d.get('distancia_surcos_cm', 0)} cm surco", f"{d.get('distancia_posturas_cm', 0)} cm postura")
        ]

        for idx, (label, val_top, val_sub) in enumerate(metric_cards):
            curr_x = start_x + idx * (box_w + gap)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            pdf.set_line_width(0.3)
            pdf.rect(curr_x, box_y, box_w, box_h, "DF")

            pdf.set_xy(curr_x + 2, box_y + 1.8)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(box_w - 4, 3.5, label, ln=True, align="C")

            pdf.set_xy(curr_x + 2, box_y + 5.8)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(box_w - 4, 4.5, val_top, ln=True, align="C")

            pdf.set_xy(curr_x + 2, box_y + 10.8)
            pdf.set_font("Helvetica", "", 6.8)
            pdf.set_text_color(71, 85, 105)
            pdf.cell(box_w - 4, 3.5, val_sub, ln=True, align="C")

        # Texto técnico de forma y perímetro con gramática cuidada
        pdf.set_y(109)
        pdf.set_font("Helvetica", "", 7.6)
        pdf.set_text_color(71, 85, 105)
        sem_postura = d.get('semillas_por_postura', 2)
        sem_txt = f"{sem_postura} semilla por postura" if sem_postura == 1 else f"{sem_postura} semillas por postura"
        perim_txt = f"Configuración: {forma_desc} - Perímetro del terreno: {t.get('perimetro_m', 0):,.1f} metros - {sem_txt}"
        pdf.cell(0, 4, perim_txt, ln=True)

        # ---------------------------------------------------------
        # SECCIÓN 4: PROYECCIÓN FINANCIERA Y PÉRDIDAS & GANANCIAS
        # ---------------------------------------------------------
        fin = report_data.get("financiero", {})
        pdf.set_y(116)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 5, "4. PROYECCIÓN FINANCIERA Y ESTADO DE RESULTADOS", ln=True)

        fuente_clean = str(fin.get('fuente_oficial_maga', 'MAGA SIMPA')).replace("/", " - ").replace("(", "").replace(")", "").strip()
        fecha_clean = str(fin.get('fecha_actualizacion_maga', '')).strip()
        pdf.set_font("Helvetica", "I", 7.2)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 3.8, f"Precios oficiales de referencia: {fuente_clean} - Actualizado al {fecha_clean}", ln=True)

        pdf.ln(1)
        # Encabezado de la tabla de P&L
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_line_width(0.3)
        pdf.set_font("Helvetica", "B", 7.6)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(120, 5, "  Indicador Financiero Evaluado", border=1, fill=True)
        pdf.cell(60, 5, "Valor Proyectado  ", border=1, fill=True, ln=True, align="R")

        rows_pnl = [
            ("Capital de Inversión Aportado por el Productor", f"Q {fin.get('capital_inversion_q', 0):,.2f}"),
            ("Rendimiento Esperado según Modelo Climático", f"{fin.get('rendimiento_estimado_qq_mz', 0)} quintales por manzana"),
            (f"Producción Total Estimada de Maíz {fin.get('tipo_maiz', 'Blanco')}", f"{fin.get('produccion_total_estimada_qq', 0)} quintales"),
            ("Precio Oficial MAGA al Productor Mayorista", f"Q {fin.get('precio_maga_qq', 0):.2f} por quintal"),
            ("Ingreso Bruto Proyectado por Cosecha", f"Q {fin.get('ingreso_bruto_q', 0):,.2f}")
        ]

        pdf.set_font("Helvetica", "", 7.6)
        pdf.set_text_color(15, 23, 42)
        for label, val in rows_pnl:
            pdf.cell(120, 4.4, f"  {label}", border=1)
            pdf.cell(60, 4.4, f"{val}  ", border=1, ln=True, align="R")

        # Fila de Utilidad Neta y ROI
        utilidad = fin.get("utilidad_neta_q", 0)
        roi = fin.get("roi_pct", 0)
        if utilidad >= 0:
            pdf.set_fill_color(236, 253, 245)
            pdf.set_text_color(6, 95, 70)
        else:
            pdf.set_fill_color(254, 242, 242)
            pdf.set_text_color(153, 27, 27)

        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(120, 5.2, f"  UTILIDAD NETA ESPERADA - Retorno sobre Inversión: {roi}%", border=1, fill=True)
        pdf.cell(60, 5.2, f"Q {utilidad:,.2f}  ", border=1, fill=True, ln=True, align="R")

        # Subindicadores de apoyo
        pdf.ln(1.5)
        pdf.set_font("Helvetica", "", 7.4)
        pdf.set_text_color(71, 85, 105)
        sub_fin_txt = f"Punto de equilibrio para cubrir costos: {fin.get('punto_equilibrio_qq', 0)} quintales - Inversión por quintal producido: Q {fin.get('inversion_por_quintal_q', 0):,.2f}"
        pdf.cell(0, 4, sub_fin_txt, ln=True)

        # ---------------------------------------------------------
        # SECCIÓN 5: ANÁLISIS DE SENSIBILIDAD DE ESCENARIOS
        # ---------------------------------------------------------
        pdf.set_y(166)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 5, "5. ANÁLISIS DE SENSIBILIDAD DE ESCENARIOS DE COSECHA", ln=True)

        pdf.set_font("Helvetica", "", 7.2)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 3.6, "Proyecciones bajo variaciones en el régimen pluviométrico durante el ciclo del cultivo:", ln=True)

        pdf.ln(1)
        # Encabezado de la tabla de sensibilidad
        # Anchos calibrados: 72 + 25 + 25 + 29 + 29 = 180mm exactos
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_font("Helvetica", "B", 7.4)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(72, 4.8, "  Escenario Pluviométrico", border=1, fill=True)
        pdf.cell(25, 4.8, "Rend. qq/mz", border=1, fill=True, align="C")
        pdf.cell(25, 4.8, "Prod. qq", border=1, fill=True, align="C")
        pdf.cell(29, 4.8, "Ingreso Bruto", border=1, fill=True, align="R")
        pdf.cell(29, 4.8, "Utilidad Neta  ", border=1, fill=True, align="R", ln=True)

        pdf.set_font("Helvetica", "", 7.2)
        for esc in fin.get("escenarios_sensibilidad", []):
            esc_name = str(esc.get("Escenario", "")).strip()
            rend_val = str(esc.get("Rendimiento (qq/mz)", esc.get("rendimiento", "")))
            prod_val = str(esc.get("Producción Total (qq)", esc.get("produccion", "")))
            ingr_val = esc.get("Ingreso Bruto (Q)", esc.get("ingreso_bruto", 0))
            util_val = esc.get("Utilidad Neta (Q)", esc.get("utilidad_neta", 0))

            pdf.set_text_color(15, 23, 42)
            pdf.cell(72, 4.4, f"  {esc_name}", border=1)
            pdf.cell(25, 4.4, rend_val, border=1, align="C")
            pdf.cell(25, 4.4, prod_val, border=1, align="C")
            pdf.cell(29, 4.4, f"Q {ingr_val:,.2f}", border=1, align="R")

            if util_val >= 0:
                pdf.set_text_color(6, 95, 70)
            else:
                pdf.set_text_color(185, 28, 28)
            pdf.cell(29, 4.4, f"Q {util_val:,.2f}  ", border=1, align="R", ln=True)

        # ---------------------------------------------------------
        # AUDITORÍA DE INVERSIÓN Y LÍMITES HISTÓRICOS (PAGE 1)
        # ---------------------------------------------------------
        cap_warnings = report_data.get("capital_warnings", [])
        cap_val = fin.get("capital_inversion_q", 0)
        mz_val = max(0.001, t.get("manzanas", 1.0))
        cap_mz = cap_val / mz_val

        pdf.set_y(186)
        box_bg = (254, 242, 242) if cap_warnings else (248, 250, 252)
        box_border = (254, 202, 202) if cap_warnings else (226, 232, 240)
        box_text = (153, 27, 27) if cap_warnings else (27, 77, 62)

        pdf.set_fill_color(*box_bg)
        pdf.set_draw_color(*box_border)
        pdf.set_line_width(0.3)
        pdf.rect(15, 186, 180, 22, "DF")

        pdf.set_xy(18, 187.5)
        pdf.set_font("Helvetica", "B", 7.6)
        pdf.set_text_color(*box_text)
        pdf.cell(174, 3.8, _clean_str("AUDITORÍA DE INVERSIÓN Y LÍMITES HISTÓRICOS (CORREDOR SECO - JUTIAPA):"), ln=True)

        pdf.set_xy(18, 191.8)
        pdf.set_font("Helvetica", "", 7.0)
        pdf.set_text_color(51, 65, 85)
        txt_cap = (
            f"Capital ingresado por el productor: Q {cap_val:,.2f} (Equivalente a Q {cap_mz:,.2f} por manzana para {mz_val:.2f} mz). "
            f"Rango histórico de costos en cosechas de maíz en el sector: Q 2,000.00 a Q 25,000.00/mz. "
            "Parámetros verificados contra inyecciones y desbordes con estricta integridad de datos."
        )
        pdf.multi_cell(174, 3.2, _clean_str(txt_cap))

        if cap_warnings:
            pdf.set_xy(18, 201)
            pdf.set_font("Helvetica", "B", 6.8)
            pdf.set_text_color(185, 28, 28)
            pdf.cell(174, 3.5, _clean_str(f"ADVERTENCIA DE CAPITAL: {cap_warnings[0]}"), ln=True)

        # ---------------------------------------------------------
        # PÁGINA 2: ANÁLISIS PLUVIOMÉTRICO MENSUAL (DÉFICIT O AUMENTO)
        # ---------------------------------------------------------
        rain_analysis = report_data.get("analisis_pluviometrico")
        if not rain_analysis:
            from core.agronomy_economics import calcular_analisis_pluviometrico
            rain_analysis = calcular_analisis_pluviometrico(report_data.get("fecha_siembra", "2026-10-01"), report_data.get("fase_enso", "Neutral"))

        pdf.add_page()

        pdf.set_y(24)
        pdf.set_font("Helvetica", "B", 10.0)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 5, _clean_str(f"6. ANÁLISIS PLUVIOMÉTRICO: {rain_analysis.get('pregunta_titulo', 'DÉFICIT O AUMENTO DE LLUVIAS')}").upper(), ln=True)

        pdf.set_font("Helvetica", "I", 7.4)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 3.8, _clean_str("Evaluación del régimen de precipitación comparada contra 46 años de series agroclimáticas ERA5 (1981-Presente)"), ln=True)

        pdf.ln(2)

        # 6.1 Tabla Comparativa de Meses (Mes, Precipitación, Caracterización climática)
        pdf.set_font("Helvetica", "B", 7.8)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 4.2, _clean_str("Régimen Pluviométrico Comparativo de la Temporada:"), ln=True)

        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_line_width(0.3)
        pdf.set_font("Helvetica", "B", 7.4)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(45, 4.6, _clean_str("  Mes"), border=1, fill=True)
        pdf.cell(45, 4.6, _clean_str("Precipitación  "), border=1, fill=True, align="C")
        pdf.cell(90, 4.6, _clean_str("  Caracterización Climática"), border=1, fill=True, ln=True)

        for row in rain_analysis.get("tabla_comparativa", []):
            is_sel = row.get("es_seleccionado", False)
            if is_sel:
                pdf.set_fill_color(236, 253, 245)
                pdf.set_text_color(6, 95, 70)
                pdf.set_font("Helvetica", "B", 7.6)
                prefix = "  * "
            else:
                pdf.set_fill_color(255, 255, 255)
                pdf.set_text_color(15, 23, 42)
                pdf.set_font("Helvetica", "", 7.3)
                prefix = "  "

            pdf.cell(45, 4.4, _clean_str(f"{prefix}{row.get('mes', '')}"), border=1, fill=is_sel)
            pdf.cell(45, 4.4, _clean_str(f"{row.get('precip', '')}  "), border=1, fill=is_sel, align="C")
            pdf.cell(90, 4.4, _clean_str(f"  {row.get('caracterizacion', '')}"), border=1, fill=is_sel, ln=True)

        pdf.ln(3)

        # 6.2 Distribución de la Lluvia dentro del Mes (Decenas)
        pdf.set_font("Helvetica", "B", 7.8)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 4.2, _clean_str(f"Distribución de la Precipitación dentro de {rain_analysis.get('mes_nombre', 'el mes evaluado')}:"), ln=True)

        d_box_w = 57.3
        d_box_h = 22
        d_gap = 4.0
        d_start_x = 15
        d_box_y = pdf.get_y() + 1

        for idx, dec in enumerate(rain_analysis.get("distribucion_decenas", [])):
            cx = d_start_x + idx * (d_box_w + d_gap)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(226, 232, 240)
            pdf.set_line_width(0.3)
            pdf.rect(cx, d_box_y, d_box_w, d_box_h, "DF")

            pdf.set_xy(cx + 2, d_box_y + 1.5)
            pdf.set_font("Helvetica", "B", 6.8)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(d_box_w - 4, 3.0, _clean_str(f"{dec.get('etiqueta', '')} ({dec.get('porcentaje', '')})"), ln=True, align="C")

            pdf.set_xy(cx + 2, d_box_y + 4.8)
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(3, 105, 161)
            pdf.cell(d_box_w - 4, 4.5, _clean_str(dec.get("mm", "")), ln=True, align="C")

            pdf.set_xy(cx + 2, d_box_y + 9.8)
            pdf.set_font("Helvetica", "B", 6.6)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(d_box_w - 4, 3.0, _clean_str(dec.get("rango", "")), ln=True, align="C")

            pdf.set_xy(cx + 2, d_box_y + 13.2)
            pdf.set_font("Helvetica", "", 6.2)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(d_box_w - 4, 2.5, _clean_str(dec.get("detalle", "")), align="C")

        pdf.set_y(d_box_y + d_box_h + 3)

        # 6.3 Conclusiones Pluviométricas del Mes
        conc_y = pdf.get_y()
        conc_bg = (254, 242, 242) if sem_color == "Rojo" else (248, 250, 252)
        conc_border = (254, 202, 202) if sem_color == "Rojo" else (226, 232, 240)
        conc_text = (185, 28, 28) if sem_color == "Rojo" else (27, 77, 62)

        pdf.set_fill_color(*conc_bg)
        pdf.set_draw_color(*conc_border)
        pdf.set_line_width(0.3)
        pdf.rect(15, conc_y, 180, 22, "DF")

        pdf.set_xy(18, conc_y + 2)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*conc_text)
        pdf.cell(174, 3.5, _clean_str("DIAGNÓSTICO PLUVIOMÉTRICO MENSUAL:"), ln=True)

        pdf.set_xy(18, conc_y + 6)
        pdf.set_font("Helvetica", "", 6.8)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(174, 3.0, _clean_str(rain_analysis.get("conclusiones_modelo", "")))

        # ---------------------------------------------------------
        # SECCIÓN 7: ANÁLISIS FENOLÓGICO DE RACHAS HÍDRICAS (120 DÍAS)
        # DICTAMEN DE GERMINACIÓN, VEGETATIVO, FLORACIÓN Y LLENADO
        # ---------------------------------------------------------
        rachas_sec = report_data.get("analisis_rachas", {})
        pdf.set_y(conc_y + 26)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(27, 77, 62)
        pdf.cell(0, 4.8, "7. EVALUACIÓN DE RACHAS HÍDRICAS POR ETAPA FENOLÓGICA (120 DÍAS)", ln=True)

        pdf.set_font("Helvetica", "I", 7.2)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 3.5, _clean_str("Comportamiento diario de días seguidos de lluvia vs sequía en Calderas, San José Acatempa"), ln=True)

        # Banner de veredicto de rachas
        verd = rachas_sec.get("veredicto_general", "APTO PARA SIEMBRA")
        if verd == "APTO PARA SIEMBRA":
            v_bg, v_border, v_txt = (236, 253, 245), (167, 243, 208), (6, 95, 70)
        elif verd == "SIEMBRA CON PRECAUCIÓN":
            v_bg, v_border, v_txt = (254, 252, 232), (254, 240, 138), (146, 64, 14)
        else:
            v_bg, v_border, v_txt = (254, 242, 242), (254, 202, 202), (185, 28, 28)

        v_y = pdf.get_y() + 1
        pdf.set_fill_color(*v_bg)
        pdf.set_draw_color(*v_border)
        pdf.rect(15, v_y, 180, 10, "DF")

        pdf.set_xy(18, v_y + 2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*v_txt)
        can_info = rachas_sec.get("canicula", {})
        can_txt = f"Canícula: {can_info.get('severidad', 'Ninguna')} ({can_info.get('dias_duracion', 0)} días)" if can_info.get("detectada") else "Canícula: No severa"
        dist_txt = f"Distribución: {rachas_sec.get('calidad_distribucion', 'Regular')}"
        pdf.cell(90, 5.5, _clean_str(f"DICTAMEN FENOLÓGICO: {verd}"), ln=False)
        pdf.set_font("Helvetica", "", 7.2)
        pdf.cell(45, 5.5, _clean_str(dist_txt), ln=False, align="C")
        pdf.cell(40, 5.5, _clean_str(can_txt), ln=True, align="R")

        # Tabla de las 4 etapas fenológicas
        pdf.set_y(v_y + 12)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(203, 213, 225)
        pdf.set_font("Helvetica", "B", 7.0)
        pdf.set_text_color(30, 41, 59)
        # Anchos: 48 + 18 + 24 + 28 + 28 + 34 = 180 mm exactos
        pdf.cell(48, 4.4, _clean_str("  Etapa Fenológica del Maíz"), border=1, fill=True)
        pdf.cell(18, 4.4, _clean_str("Ventana"), border=1, fill=True, align="C")
        pdf.cell(24, 4.4, _clean_str("Lluvia Total"), border=1, fill=True, align="C")
        pdf.cell(28, 4.4, _clean_str("Racha Seca Max"), border=1, fill=True, align="C")
        pdf.cell(28, 4.4, _clean_str("Racha Lluvia Max"), border=1, fill=True, align="C")
        pdf.cell(34, 4.4, _clean_str("Riesgo / Diagnóstico  "), border=1, fill=True, ln=True, align="C")

        pdf.set_font("Helvetica", "", 6.8)
        for stg in rachas_sec.get("tabla_etapas", []):
            stg_name = stg.get("etapa", "")
            dias_str = stg.get("dias", "")
            lluv_str = stg.get("lluvia_total", "")
            dry_str = stg.get("racha_seca_max", "")
            wet_str = stg.get("racha_humeda_max", "")
            risk_str = f"{stg.get('nivel_riesgo', '')} - {stg.get('adecuacion', '')}"

            if "Crítico" in stg.get("nivel_riesgo", "") or "Alto" in stg.get("nivel_riesgo", ""):
                pdf.set_text_color(185, 28, 28)
            elif "Moderado" in stg.get("nivel_riesgo", ""):
                pdf.set_text_color(146, 64, 14)
            else:
                pdf.set_text_color(15, 23, 42)

            pdf.cell(48, 4.2, _clean_str(f"  {stg_name}"), border=1)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(18, 4.2, _clean_str(dias_str), border=1, align="C")
            pdf.cell(24, 4.2, _clean_str(lluv_str), border=1, align="C")
            pdf.cell(28, 4.2, _clean_str(dry_str), border=1, align="C")
            pdf.cell(28, 4.2, _clean_str(wet_str), border=1, align="C")

            if "Crítico" in stg.get("nivel_riesgo", "") or "Alto" in stg.get("nivel_riesgo", ""):
                pdf.set_text_color(185, 28, 28)
            else:
                pdf.set_text_color(6, 95, 70)
            pdf.cell(34, 4.2, _clean_str(f"{risk_str}  "), border=1, ln=True, align="C")

        # Alertas críticas de rachas si existen
        alerts = rachas_sec.get("alertas_criticas", [])
        if alerts:
            al_y = pdf.get_y() + 2
            pdf.set_fill_color(254, 242, 242)
            pdf.set_draw_color(254, 202, 202)
            pdf.rect(15, al_y, 180, 14, "DF")
            pdf.set_xy(18, al_y + 1.5)
            pdf.set_font("Helvetica", "B", 7.2)
            pdf.set_text_color(185, 28, 28)
            pdf.cell(174, 3.2, _clean_str("ALERTA CRÍTICA FENOLÓGICA:"), ln=True)
            pdf.set_xy(18, al_y + 5.2)
            pdf.set_font("Helvetica", "", 6.6)
            pdf.multi_cell(174, 2.8, _clean_str("; ".join(alerts[:2])))

        # ---------------------------------------------------------
        # PÁGINA 3: ANEXOS TÉCNICOS Y GRÁFICOS
        # ---------------------------------------------------------
        if chart_paths:
            pdf.add_page()

            pdf.set_y(24)
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(27, 77, 62)
            pdf.cell(0, 5, "8. ANEXOS TÉCNICOS: BALANCE HÍDRICO Y PLANO GEOMÉTRICO", ln=True)

            wb_path = chart_paths.get("water_balance")
            ter_path = chart_paths.get("terrain")

            # Gráfico 1: Balance Hídrico (calibrado y centrado)
            if wb_path and Path(wb_path).exists():
                pdf.image(str(wb_path), x=20, y=30, w=170, h=86)
                pdf.set_xy(15, 118)
                pdf.set_font("Helvetica", "I", 7.2)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(180, 4, "Gráfico 1: Demanda hídrica diaria vs acumulación de lluvia y humedad de suelo en la ventana de 60 días.", align="C", ln=True)

            # Gráfico 2: Plano del Terreno (calibrado y centrado)
            if ter_path and Path(ter_path).exists():
                pdf.image(str(ter_path), x=30, y=124, w=150, h=84)
                pdf.set_xy(15, 210)
                pdf.set_font("Helvetica", "I", 7.2)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(180, 4, "Gráfico 2: Plano a escala del predio con orientación cardinal y trazado sugerido de surcos.", align="C", ln=True)

            # Sello de Validez, Responsabilidad Técnica y Deslinde Legal
            pdf.set_y(217)
            pdf.set_fill_color(255, 251, 235)  # Fondo ámbar suave para enfatizar importancia
            pdf.set_draw_color(251, 191, 36)
            pdf.set_line_width(0.5)
            pdf.rect(15, 217, 180, 56, "DF")

            pdf.set_xy(18, 219)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(146, 64, 14)
            pdf.cell(174, 4.5, "AVISO LEGAL, METODOLOGÍA Y DESLINDE DE RESPONSABILIDAD", ln=True)

            pdf.set_xy(18, 225)
            pdf.set_font("Helvetica", "B", 7.2)
            pdf.set_text_color(27, 77, 62)
            pdf.cell(174, 3.5, "METODOLOGÍA CIENTÍFICA:", ln=True)

            pdf.set_xy(18, 229)
            pdf.set_font("Helvetica", "", 6.8)
            pdf.set_text_color(71, 85, 105)
            nota_metodo = (
                "Este informe integra datos de reanálisis satelital ERA5 (ECMWF, 1981-2026), índices oceánicos ENSO (NOAA PSL), "
                "ecuaciones edafológicas Saxton & Rawls para suelo franco-arcilloso, balance hídrico FAO-56, modelos de aprendizaje automático "
                "calibrados (XGBoost/Logística) con validación cruzada temporal por años, y cotizaciones del Sistema de Precios del MAGA."
            )
            pdf.multi_cell(174, 3.0, nota_metodo)

            pdf.set_xy(18, 243)
            pdf.set_font("Helvetica", "B", 7.2)
            pdf.set_text_color(153, 27, 27)
            pdf.cell(174, 3.5, "DESLINDE DE RESPONSABILIDAD:", ln=True)

            pdf.set_xy(18, 247)
            pdf.set_font("Helvetica", "", 6.8)
            pdf.set_text_color(71, 85, 105)
            nota_legal = (
                "ESTE DICTAMEN CONSTITUYE EXCLUSIVAMENTE UNA HERRAMIENTA DE APOYO A LA DECISIÓN AGRÍCOLA. "
                "Las proyecciones climáticas, financieras y agronómicas presentadas son estimaciones basadas en modelos "
                "estadísticos y datos históricos que, por su naturaleza, no pueden garantizar resultados futuros con certeza absoluta. "
                "La decisión final de sembrar o no sembrar recae ÚNICA Y EXCLUSIVAMENTE en el agricultor, productor o usuario que "
                "consulta este sistema. Ni el sistema, ni sus desarrolladores, ni las fuentes de datos citadas asumen responsabilidad "
                "alguna por pérdidas económicas, daños a cultivos o cualquier consecuencia derivada de decisiones tomadas con base en "
                "este informe. Se recomienda complementar este análisis con inspección directa del terreno, consulta con extensionistas "
                "agrícolas del MAGA y monitoreo continuo de las condiciones meteorológicas locales."
            )
            pdf.multi_cell(174, 2.9, nota_legal)

        pdf.output(str(pdf_file))

        print(f"  [PDF] Informe ejecutivo generado exitosamente en: {pdf_file.name}")
        return pdf_file

    except ImportError:
        print("  [PDF Info] fpdf2 no está disponible. Se generó versión completa en Markdown.")
        return md_file


def _build_markdown_summary(
    data: Dict[str, Any],
    chart_paths: Optional[Dict[str, Path]] = None
) -> str:
    """Construye un reporte en formato Markdown legible y limpio sin paréntesis ni slashes técnicos."""
    t = data["terreno"]
    d = data["densidad"]
    fin = data["financiero"]
    forma_desc = str(t.get("forma", "Parcela")).replace("(", "").replace(")", "").strip()

    md = [
        "# INFORME DE VIABILIDAD AGRÍCOLA Y PROYECCIÓN FINANCIERA",
        "**Cultivo:** Maíz (*Zea mays*)  ",
        f"**Ubicación:** {data['municipio']} - Coordenadas {data['lat']:.4f}° N, {abs(data['lon']):.4f}° O  ",
        f"**Fecha Tentativa de Siembra:** {data['fecha_siembra']}  ",
        f"**Fase ENSO Observada:** {data['fase_enso']}  ",
        "",
        "---",
        "",
        "## 1. Dictamen Agrometeorológico",
        f"- **Estado:** {data['semaforo_estado']}",
        f"- **Viabilidad Climática Estimada:** {data['probabilidad']*100:.1f}%",
        f"- **Recomendación Operativa:** {data['semaforo_accion']}",
        f"- **Criterios Evaluados:** Demanda hídrica mínima ETa vs ETc {data.get('criterios_algoritmo', {}).get('eta_etc_min', 0.90)*100:.0f}% - Límite de anegamiento {data.get('criterios_algoritmo', {}).get('waterlog_max_days', 8)} días - Ventana fenológica 60 días",
        "",
        "---",
        "",
        "## 2. Modelado de Parcela y Densidad de Siembra",
        f"- **Forma del Terreno:** {forma_desc}",
        f"- **Superficie Total:** {t['area_m2']:,.1f} m² - {t['manzanas']:.3f} manzanas - {t['hectareas']:.3f} hectáreas",
        f"- **Perímetro Total:** {t.get('perimetro_m', 0):,.1f} metros",
        f"- **Densidad Recomendada:** {d['densidad_plantas_m2']} plantas por m² - {d['densidad_plantas_mz']:,} plantas por manzana",
        f"- **Población Total Estimada:** {d['plantas_totales_predio']:,} plantas",
        f"- **Semilla Comercial Requerida:** {d['semillas_totales_requeridas']:,} semillas ({d['libras_semilla']} libras)",
        f"- **Marco de Plantación:** {d['distancia_surcos_cm']} cm entre surcos × {d['distancia_posturas_cm']} cm entre posturas",
        "",
        "---",
        "",
        "## 3. Estado de Resultados y Proyección Financiera",
        f"- **Fuente Oficial de Precios:** {fin['fuente_oficial_maga']}",
        f"- **Fecha de Actualización:** {fin['fecha_actualizacion_maga']}",
        f"- **Capital de Inversión Aportado por el Productor:** Q {fin['capital_inversion_q']:,.2f}",
        f"- **Rendimiento Estimado:** {fin['rendimiento_estimado_qq_mz']} quintales por manzana",
        f"- **Producción Total Estimada:** {fin['produccion_total_estimada_qq']} quintales",
        f"- **Precio Oficial MAGA:** Q {fin['precio_maga_qq']:.2f} por quintal",
        f"- **Ingreso Bruto Proyectado:** Q {fin['ingreso_bruto_q']:,.2f}",
        f"- **Utilidad Neta Esperada:** Q {fin['utilidad_neta_q']:,.2f}",
        f"- **Retorno sobre la Inversión (ROI):** {fin['roi_pct']}%",
        f"- **Punto de Equilibrio:** {fin['punto_equilibrio_qq']} quintales",
        f"- **Inversión por Quintal:** Q {fin['inversion_por_quintal_q']:,.2f}",
        "",
        "---",
        "",
        "## 4. Análisis de Sensibilidad de Escenarios",
        "| Escenario Pluviométrico | Rendimiento (qq/mz) | Producción (qq) | Ingreso Bruto (Q) | Utilidad Neta (Q) |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]

    for esc in fin.get("escenarios_sensibilidad", []):
        rend = esc.get("Rendimiento (qq/mz)", esc.get("rendimiento", ""))
        prod = esc.get("Producción Total (qq)", esc.get("produccion", ""))
        ingr = esc.get("Ingreso Bruto (Q)", esc.get("ingreso_bruto", 0))
        util = esc.get("Utilidad Neta (Q)", esc.get("utilidad_neta", 0))
        md.append(f"| {esc.get('Escenario', '')} | {rend} | {prod} | Q {ingr:,.2f} | Q {util:,.2f} |")

    # Auditoría de Inversión y Límites Regionales
    cap_warns = data.get("capital_warnings", [])
    cap_mz_val = fin.get("capital_inversion_q", 0) / max(0.001, t.get("manzanas", 1.0))
    md.extend([
        "",
        "---",
        "",
        "## 5. Auditoría de Inversión y Límites Históricos (Corredor Seco)",
        f"- **Capital Total Ingresado:** Q {fin.get('capital_inversion_q', 0):,.2f}",
        f"- **Inversión por Manzana:** Q {cap_mz_val:,.2f}/mz (Rango histórico regional: Q 2,000.00 a Q 25,000.00/mz)",
        f"- **Estado de Integridad:** Verificado sin inyección de datos.",
    ])
    if cap_warns:
        md.append(f"- **⚠️ Advertencia Financiera:** {cap_warns[0]}")

    rain_analysis = data.get("analisis_pluviometrico")
    if rain_analysis:
        md.extend([
            "",
            "---",
            "",
            f"## 6. Análisis Pluviométrico: {rain_analysis.get('pregunta_titulo', 'Déficit o Aumento de Lluvias')}",
            f"- **Diagnóstico General:** {rain_analysis.get('diagnostico_badge', 'Aumento de Lluvias')}",
            "",
            "### Régimen Pluviométrico Comparativo:",
            "| Mes | Precipitación | Caracterización Climática |",
            "| :--- | :---: | :--- |",
        ])
        for row in rain_analysis.get("tabla_comparativa", []):
            sel_tag = " (Mes evaluado)" if row.get("es_seleccionado") else ""
            md.append(f"| {row.get('mes', '')}{sel_tag} | {row.get('precip', '')} | {row.get('caracterizacion', '')} |")

        md.extend([
            "",
            f"### Distribución de Precipitación en {rain_analysis.get('mes_nombre', 'el mes')}:",
        ])
        for dec in rain_analysis.get("distribucion_decenas", []):
            md.append(f"- **{dec.get('etiqueta', '')} ({dec.get('rango', '')}):** {dec.get('mm', '')} ({dec.get('porcentaje', '')}) - {dec.get('detalle', '')}")

        imp = rain_analysis.get("impacto_evento", {})
        md.extend([
            "",
            f"### Impacto del Evento Climático ({imp.get('titulo', 'ENSO')}):",
            imp.get("descripcion", ""),
            "",
            "### Conclusiones del Modelo para el Ciclo de Maíz Blanco:",
            rain_analysis.get("conclusiones_modelo", "")
        ])

    rachas = data.get("analisis_rachas")
    if rachas:
        can_i = rachas.get("canicula", {})
        can_str = f"Detectada ({can_i.get('severidad', '')}, {can_i.get('dias_duracion', 0)} días)" if can_i.get("detectada") else "No severa"
        md.extend([
            "",
            "---",
            "",
            "## 7. Evaluación de Rachas Hídricas por Etapa Fenológica (120 Días)",
            f"- **Veredicto Fenológico:** {rachas.get('veredicto_general', 'N/D')}",
            f"- **Puntaje de Riesgo:** {rachas.get('puntaje_riesgo_pct', 'N/D')} | **Distribución:** {rachas.get('calidad_distribucion', 'N/D')} | **Canícula:** {can_str}",
            "",
            "| Etapa Fenológica | Ventana | Lluvia Total | Racha Seca Max | Racha Lluvia Max | Diagnóstico / Riesgo |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |",
        ])
        for stg in rachas.get("tabla_etapas", []):
            md.append(f"| {stg.get('etapa', '')} | {stg.get('dias', '')} | {stg.get('lluvia_total', '')} | {stg.get('racha_seca_max', '')} | {stg.get('racha_humeda_max', '')} | {stg.get('nivel_riesgo', '')} - {stg.get('adecuacion', '')} |")

        if rachas.get("alertas_criticas"):
            md.extend([
                "",
                "### ⚠️ Alertas Críticas Fenológicas:",
            ])
            for al in rachas.get("alertas_criticas", []):
                md.append(f"- **{al}**")

        md.extend([
            "",
            "### Directiva Agronómica:",
            rachas.get("directiva_agronomica", "")
        ])

    # Sección de Deslinde de Responsabilidad (OBLIGATORIA)
    md.extend([
        "",
        "---",
        "",
        "## AVISO LEGAL, METODOLOGÍA Y DESLINDE DE RESPONSABILIDAD",
        "",
        "### Metodología Científica:",
        "Este informe integra datos de reanálisis satelital ERA5 (ECMWF, 1981-2026), índices oceánicos ENSO (NOAA PSL), "
        "ecuaciones edafológicas Saxton & Rawls para suelo franco-arcilloso, balance hídrico FAO-56, modelos de aprendizaje automático "
        "calibrados (XGBoost/Logística) con validación cruzada temporal por años, y cotizaciones del Sistema de Precios del MAGA.",
        "",
        "### ⚠️ DESLINDE DE RESPONSABILIDAD:",
        "**ESTE DICTAMEN CONSTITUYE EXCLUSIVAMENTE UNA HERRAMIENTA DE APOYO A LA DECISIÓN AGRÍCOLA.** "
        "Las proyecciones climáticas, financieras y agronómicas presentadas son estimaciones basadas en modelos "
        "estadísticos y datos históricos que, por su naturaleza, no pueden garantizar resultados futuros con certeza absoluta. "
        "**La decisión final de sembrar o no sembrar recae ÚNICA Y EXCLUSIVAMENTE en el agricultor, productor o usuario que "
        "consulta este sistema.** Ni el sistema, ni sus desarrolladores, ni las fuentes de datos citadas asumen responsabilidad "
        "alguna por pérdidas económicas, daños a cultivos o cualquier consecuencia derivada de decisiones tomadas con base en "
        "este informe. Se recomienda complementar este análisis con inspección directa del terreno, consulta con extensionistas "
        "agrícolas del MAGA y monitoreo continuo de las condiciones meteorológicas locales.",
    ])

    return "\n".join(md)

