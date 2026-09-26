"""
Módulo de Exportación de Informes en Formato PDF (RF-08, RNF-04).
Genera un informe ejecutivo integral y profesional con márgenes estándar,
tablas de pérdidas y ganancias, gráficos de soporte y recomendaciones técnicas.
Cumple con la evaluación de inversión directa del productor y terrenos irregulares.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import datetime

from config.settings import PATH_CONFIG


def export_pdf_report(
    report_data: Dict[str, Any],
    chart_paths: Optional[Dict[str, Path]] = None,
    output_path: Optional[Path] = None
) -> Path:
    """
    Genera el informe final en formato PDF (RF-08).
    Si fpdf2 está disponible lo compila a PDF vectorial estructurado;
    adicionalmente siempre genera una versión Markdown de alta fidelidad.
    """
    out_dir = PATH_CONFIG.output_dir
    pdf_file = output_path or (out_dir / "Informe_Viabilidad_Maiz_Jutiapa.pdf")
    md_file = out_dir / "Informe_Viabilidad_Maiz_Jutiapa.md"

    # 1. Generar contenido estructurado en Markdown como respaldo
    md_content = _build_markdown_summary(report_data, chart_paths)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 2. Compilar a PDF mediante fpdf2 si la librería está disponible
    try:
        from fpdf import FPDF

        class AgriculturalReportPDF(FPDF):
            def header(self):
                self.set_font("Helvetica", "B", 13)
                self.set_text_color(22, 101, 52) # Verde bosque
                self.cell(0, 7, "SISTEMA ABIERTO DE VIABILIDAD AGRÍCOLA - JUTIAPA", ln=True, align="C")
                self.set_font("Helvetica", "I", 8.5)
                self.set_text_color(100, 100, 100)
                self.cell(0, 5, "Dictamen Agrometeorológico, Modelado de Parcela y Proyección Financiera MAGA", ln=True, align="C")
                self.line(15, 23, 195, 23)
                self.ln(5)

            def footer(self):
                self.set_y(-15)
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(130, 130, 130)
                self.cell(0, 10, f"Página {self.page_no()} | Plataforma Abierta de Apoyo al Productor - Jutiapa", align="C")

        pdf = AgriculturalReportPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(15, 15, 15)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # 1. INFORMACIÓN GENERAL Y LOCALIZACIÓN
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, "1. INFORMACIÓN GENERAL Y LOCALIZACIÓN", ln=True)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(95, 5, f"Municipio: {report_data['municipio']}", ln=False)
        pdf.cell(85, 5, f"Coordenadas: {report_data['lat']:.4f}, {report_data['lon']:.4f}", ln=True)
        pdf.cell(95, 5, f"Fecha Tentativa de Siembra: {report_data['fecha_siembra']}", ln=False)
        pdf.cell(85, 5, f"Fecha de Emisión: {datetime.date.today().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(2)

        # 2. DICTAMEN AGROMETEOROLÓGICO Y FASE ENSO (RF-03)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(0, 6, "2. DICTAMEN AGROMETEOROLÓGICO Y FASE ENSO (RF-03)", ln=True)
        
        sem_color = report_data.get("semaforo_color", "Amarillo")
        if sem_color == "Verde":
            pdf.set_fill_color(220, 252, 231)
            pdf.set_text_color(22, 101, 52)
        elif sem_color == "Amarillo":
            pdf.set_fill_color(254, 243, 199)
            pdf.set_text_color(180, 83, 9)
        else:
            pdf.set_fill_color(254, 226, 226)
            pdf.set_text_color(185, 28, 28)

        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(60, 7.5, f" ESTADO: {report_data['semaforo_estado']}", border=1, fill=True)
        pdf.cell(65, 7.5, f" Probabilidad: {report_data['probabilidad']*100:.1f}%", border=1, fill=True)
        pdf.cell(55, 7.5, f" Fase ENSO: {report_data['fase_enso']}", border=1, fill=True, ln=True)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.ln(1.5)
        pdf.multi_cell(0, 4.2, f"Recomendación Operativa: {report_data['semaforo_accion']}")
        pdf.ln(1.5)

        # Criterios del algoritmo agrometeorológico (ETA_ETC_MIN = 0.90)
        crit = report_data.get("criterios_algoritmo", {})
        eta_min = crit.get("eta_etc_min", 0.90)
        wl_max = crit.get("waterlog_max_days", 8)
        pdf.set_font("Helvetica", "I", 7.8)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 3.8, f"Criterios de Viabilidad: Demanda hídrica mínima ETa/ETc >= {eta_min:.2f} (90%) | Anegamiento <= {wl_max} días | Ventana: 60 días", ln=True)

        # Validación histórica ex-post si ya transcurrió la ventana de 60 días
        ev_hist = report_data.get("evaluacion_historica", {})
        if ev_hist.get("disponible"):
            eta_obs = ev_hist.get("eta_etc_real")
            wl_obs = ev_hist.get("dias_anegamiento_real")
            res_obs = ev_hist.get("resultado_real")
            motivo_obs = ev_hist.get("motivo_fallo")
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(0, 4, f"Validación Histórica Ex-Post (a 60 días): ETa/ETc Observado = {eta_obs:.2f} | Anegamiento = {wl_obs} días -> {res_obs}", ln=True)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 3.5, f"Diagnóstico: {motivo_obs}. El pronóstico evalúa condiciones antecedentes al día de siembra; ex-post, la lluvia acumulada determinó el resultado.")

        pdf.ln(2.5)

        # 3. GEOMETRÍA DEL TERRENO Y DENSIDAD DE SIEMBRA (RF-05, RF-06)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(0, 6, "3. PARCELA Y RECOMENDACIÓN DE DENSIDAD (RF-05, RF-06)", ln=True)
        pdf.set_font("Helvetica", "", 8.5)
        
        d = report_data["densidad"]
        t = report_data["terreno"]
        forma_desc = t.get("forma", "Parcela")
        pdf.cell(0, 4.8, f"Forma Geométrica del Terreno: {forma_desc}", ln=True)
        pdf.cell(95, 4.8, f"Superficie: {t['area_m2']:,.1f} m² ({t['manzanas']:.3f} mz / {t['hectareas']:.3f} ha)", ln=False)
        pdf.cell(85, 4.8, f"Perímetro Total: {t.get('perimetro_m', 0):,.1f} m", ln=True)
        pdf.cell(95, 4.8, f"Densidad Óptima: {d['densidad_plantas_m2']} pl/m² ({d['densidad_plantas_mz']:,} pl/mz)", ln=False)
        pdf.cell(85, 4.8, f"Población Total Estimada: {d['plantas_totales_predio']:,} plantas", ln=True)
        pdf.cell(95, 4.8, f"Semilla Requerida: {d['semillas_totales_requeridas']:,} semillas ({d['libras_semilla']} lbs)", ln=False)
        pdf.cell(85, 4.8, f"Distanciamiento: {d['distancia_surcos_cm']} cm surco | {d['distancia_posturas_cm']} cm postura", ln=True)
        pdf.ln(2.5)

        # 4. PROYECCIÓN FINANCIERA Y PÉRDIDAS & GANANCIAS (RF-07)
        fin = report_data["financiero"]
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(0, 6, "4. PROYECCIÓN FINANCIERA Y ESTADO DE PÉRDIDAS Y GANANCIAS (RF-07)", ln=True)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 4, f"Precios oficiales de referencia: {fin['fuente_oficial_maga']} | Actualizado al: {fin['fecha_actualizacion_maga']}", ln=True)
        
        pdf.ln(1.5)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(115, 5.5, "Indicador Financiero / Rubro Evaluado", border=1, fill=True)
        pdf.cell(65, 5.5, "Valor Proyectado", border=1, fill=True, ln=True, align="R")

        pdf.set_font("Helvetica", "", 8.5)
        pdf.cell(115, 5, "  Capital de Inversión Aportado por el Productor", border=1)
        pdf.cell(65, 5, f"Q {fin['capital_inversion_q']:,.2f}", border=1, ln=True, align="R")

        pdf.cell(115, 5, f"  Rendimiento Estimado (ajustado por modelo agrometeorológico)", border=1)
        pdf.cell(65, 5, f"{fin['rendimiento_estimado_qq_mz']} qq/manzana", border=1, ln=True, align="R")

        pdf.cell(115, 5, f"  Producción Total Estimada de Maíz {fin.get('tipo_maiz', '')}", border=1)
        pdf.cell(65, 5, f"{fin['produccion_total_estimada_qq']} quintales (qq)", border=1, ln=True, align="R")

        pdf.cell(115, 5, f"  Precio Oficial MAGA al Productor (Actualizado al {fin['fecha_actualizacion_maga']})", border=1)
        pdf.cell(65, 5, f"Q {fin['precio_maga_qq']:.2f} / quintal", border=1, ln=True, align="R")

        pdf.cell(115, 5.5, "  Ingreso Bruto Proyectado por Venta de Cosecha", border=1)
        pdf.cell(65, 5.5, f"Q {fin['ingreso_bruto_q']:,.2f}", border=1, ln=True, align="R")

        # Color de utilidad neta
        if fin["utilidad_neta_q"] >= 0:
            pdf.set_text_color(22, 101, 52)
        else:
            pdf.set_text_color(185, 28, 28)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(115, 6, f"  UTILIDAD NETA ESPERADA (ROI: {fin['roi_pct']}%)", border=1)
        pdf.cell(65, 6, f"Q {fin['utilidad_neta_q']:,.2f}", border=1, ln=True, align="R")

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.ln(1.5)
        pdf.cell(95, 4.5, f"Punto de Equilibrio: {fin['punto_equilibrio_qq']} quintales", ln=False)
        pdf.cell(85, 4.5, f"Inversión por Quintal: Q {fin['inversion_por_quintal_q']:,.2f} / qq", ln=True)

        # Tabla de Análisis de Sensibilidad
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, "Análisis de Sensibilidad de Escenarios:", ln=True)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(65, 5, "Escenario", border=1, fill=True)
        pdf.cell(25, 5, "Rend. (qq/mz)", border=1, fill=True, align="C")
        pdf.cell(25, 5, "Prod. (qq)", border=1, fill=True, align="C")
        pdf.cell(35, 5, "Ingreso Bruto (Q)", border=1, fill=True, align="R")
        pdf.cell(30, 5, "Utilidad Neta (Q)", border=1, fill=True, align="R", ln=True)

        pdf.set_font("Helvetica", "", 7.5)
        for esc in fin["escenarios_sensibilidad"]:
            pdf.cell(65, 4.5, esc["Escenario"][:36], border=1)
            pdf.cell(25, 4.5, str(esc["Rendimiento (qq/mz)"]), border=1, align="C")
            pdf.cell(25, 4.5, str(esc["Producción Total (qq)"]), border=1, align="C")
            pdf.cell(35, 4.5, f"Q {esc['Ingreso Bruto (Q)']:,.2f}", border=1, align="R")
            u_color = (22, 101, 52) if esc["Utilidad Neta (Q)"] >= 0 else (185, 28, 28)
            pdf.set_text_color(*u_color)
            pdf.cell(30, 4.5, f"Q {esc['Utilidad Neta (Q)']:,.2f}", border=1, align="R", ln=True)
            pdf.set_text_color(0, 0, 0)

        # Página 2: Anexos Gráficos
        if chart_paths:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 6, "5. ANEXOS GRÁFICOS: BALANCE HÍDRICO Y PLANO A ESCALA", ln=True)
            pdf.ln(3)

            y_pos = 28
            if "water_balance" in chart_paths and Path(chart_paths["water_balance"]).exists():
                pdf.image(str(chart_paths["water_balance"]), x=15, y=y_pos, w=180)
                y_pos += 115

            if "terrain" in chart_paths and Path(chart_paths["terrain"]).exists() and y_pos < 185:
                pdf.image(str(chart_paths["terrain"]), x=25, y=y_pos, w=160)

        pdf.output(str(pdf_file))
        print(f"  [PDF] Informe generado exitosamente en: {pdf_file.name}")
        return pdf_file

    except ImportError:
        print("  [PDF Info] fpdf2 no está instalado en el entorno. Se generó versión completa en Markdown.")
        return md_file


def _build_markdown_summary(
    data: Dict[str, Any],
    chart_paths: Optional[Dict[str, Path]] = None
) -> str:
    """Construye un reporte en formato Markdown legible y limpio."""
    t = data["terreno"]
    d = data["densidad"]
    fin = data["financiero"]
    forma_desc = t.get("forma", "Parcela")
    
    md = [
        "# INFORME DE VIABILIDAD AGRÍCOLA Y PROYECCIÓN FINANCIERA",
        "**Cultivo:** Maíz (*Zea mays*)  ",
        f"**Ubicación:** {data['municipio']} ({data['lat']:.4f}, {data['lon']:.4f})  ",
        f"**Fecha Tentativa de Siembra:** {data['fecha_siembra']}  ",
        f"**Fase ENSO Observada:** {data['fase_enso']}  ",
        "",
        "---",
        "",
        "## 1. Dictamen Agrometeorológico",
        f"- **Estado Semáforo:** `{data['semaforo_estado']}` ({data.get('semaforo_color', '')})",
        f"- **Probabilidad Calibrada de Éxito:** **{data['probabilidad']*100:.1f}%**",
        f"- **Recomendación Operativa:** {data['semaforo_accion']}",
        f"- **Criterio de Viabilidad Agrometeorológica:** Demanda hídrica mínima $ET_a/ET_c \\ge {data.get('criterios_algoritmo', {}).get('eta_etc_min', 0.90):.2f}$ (90%) | Límite anegamiento: $\\le {data.get('criterios_algoritmo', {}).get('waterlog_max_days', 8)}$ días | Ventana crítica: 60 días",
        *(
            [
                f"- **Validación Histórica Ex-Post (a 60 días):** $ET_a/ET_c = {data['evaluacion_historica'].get('eta_etc_real'):.2f}$ | Anegamiento = {data['evaluacion_historica'].get('dias_anegamiento_real')} días -> **{data['evaluacion_historica'].get('resultado_real')}** ({data['evaluacion_historica'].get('motivo_fallo')})",
                f"- **Nota:** {data['evaluacion_historica'].get('nota_discrepancia')}",
            ]
            if data.get("evaluacion_historica", {}).get("disponible")
            else []
        ),
        "",
        "---",
        "",
        "## 2. Modelado del Terreno y Densidad de Siembra (RF-05, RF-06)",
        f"- **Forma del Terreno:** {forma_desc}",
        f"- **Superficie Total:** {t['area_m2']:,.1f} m² ({t['manzanas']:.3f} manzanas | {t['hectareas']:.3f} hectáreas)",
        f"- **Perímetro Total:** {t.get('perimetro_m', 0):,.1f} m",
        f"- **Densidad Recomendada:** **{d['densidad_plantas_m2']} plantas/m²** ({d['densidad_plantas_mz']:,} plantas/manzana)",
        f"- **Población Total Estimada:** {d['plantas_totales_predio']:,} plantas",
        f"- **Semilla Comercial Requerida:** {d['semillas_totales_requeridas']:,} semillas ({d['libras_semilla']} libras / {d['bolsas_comerciales']} bolsas)",
        f"- **Marco de Plantación:** {d['distancia_surcos_cm']} cm entre surcos × {d['distancia_posturas_cm']} cm entre posturas ({d['semillas_por_postura']} semilla por postura)",
        f"- **Criterio Técnico:** {d['diagnostico_densidad']}",
        "",
        "---",
        "",
        "## 3. Estado de Pérdidas y Ganancias (P&L) y Proyección Financiera (RF-07)",
        f"> **Fuente Oficial de Precios:** {fin['fuente_oficial_maga']}  ",
        f"> **Última Fecha de Actualización de Precios:** `{fin['fecha_actualizacion_maga']}`  ",
        f"> **Precio de Referencia MAGA:** Q {fin['precio_maga_qq']:.2f} por quintal (qq)",
        "",
        "### Resumen de Pérdidas y Ganancias",
        f"- **Capital de Inversión Aportado por el Productor:** Q {fin['capital_inversion_q']:,.2f}",
        f"- **Rendimiento Estimado:** {fin['rendimiento_estimado_qq_mz']} qq/manzana",
        f"- **Producción Total Estimada:** {fin['produccion_total_estimada_qq']} quintales",
        f"- **Ingreso Bruto Proyectado:** Q {fin['ingreso_bruto_q']:,.2f}",
        f"- **Utilidad Neta Proyectada:** **Q {fin['utilidad_neta_q']:,.2f}**",
        f"- **Retorno sobre la Inversión (ROI):** {fin['roi_pct']}%",
        f"- **Punto de Equilibrio:** {fin['punto_equilibrio_qq']} quintales",
        f"- **Inversión por Quintal:** Q {fin['inversion_por_quintal_q']:,.2f} / qq",
        "",
        "---",
        "",
        "## 4. Análisis de Sensibilidad de Escenarios",
        "| Escenario | Rendimiento (qq/mz) | Producción (qq) | Ingreso Bruto (Q) | Utilidad Neta (Q) | ROI (%) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for esc in fin["escenarios_sensibilidad"]:
        md.append(f"| {esc['Escenario']} | {esc['Rendimiento (qq/mz)']} | {esc['Producción Total (qq)']} | Q {esc['Ingreso Bruto (Q)']:,.2f} | Q {esc['Utilidad Neta (Q)']:,.2f} | {esc['ROI (%)']}% |")

    return "\n".join(md)
