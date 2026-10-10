"""
Módulo de Modelado de Terreno (RF-05), Densidad de Siembra (RF-06)
y Proyección Financiera con Precios Oficiales MAGA (RF-07).
Permite terrenos regulares e irregulares (3 lados, 4 lados desiguales o polígonos)
y evalúa la inversión del productor sin presupuestos desglosados no solicitados.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import math
import numpy as np

from config.settings import MagaPriceConfig, MAGA_CONFIG


@dataclass
class TerrainModel:
    """
    Representación geométrica de la parcela o lote agrícola (RF-05).
    Soporta:
      - Cuadriláteros irregulares (4 lados desiguales: e.g. Norte, Este, Sur, Oeste)
      - Triángulos (3 lados desiguales: fórmula de Herón)
      - Rectángulos / Formatos estándar (Ancho x Largo)
      - Polígonos de N vértices
    Convierte automáticamente dimensiones métricas a unidades agrarias locales (manzanas y hectáreas).
    """
    shape_type: str = "rectangulo" # "cuadrilatero", "triangulo", "rectangulo", "poligono"
    ancho_m: float = 100.0
    largo_m: float = 70.0
    sides: List[float] = field(default_factory=lambda: [100.0, 70.0, 100.0, 70.0])
    custom_coords: Optional[List[Tuple[float, float]]] = None

    def __post_init__(self):
        # Normalizar dimensiones y lados
        if self.shape_type == "rectangulo":
            if not self.sides or len(self.sides) != 4:
                self.sides = [float(self.ancho_m), float(self.largo_m), float(self.ancho_m), float(self.largo_m)]
            else:
                self.ancho_m = float(self.sides[0])
                self.largo_m = float(self.sides[1]) if len(self.sides) > 1 else float(self.sides[0])
        elif self.shape_type == "cuadrilatero":
            # 4 lados diferentes [lado1, lado2, lado3, lado4]
            if not self.sides or len(self.sides) < 4:
                self.sides = [float(self.ancho_m), float(self.largo_m), float(self.ancho_m), float(self.largo_m)]
            else:
                self.sides = [float(s) for s in self.sides[:4]]
                # Ancho y largo promedio para resúmenes
                self.ancho_m = (self.sides[0] + self.sides[2]) / 2.0
                self.largo_m = (self.sides[1] + self.sides[3]) / 2.0
        elif self.shape_type == "triangulo":
            # 3 lados diferentes [lado_a, lado_b, lado_c]
            if not self.sides or len(self.sides) < 3:
                self.sides = [80.0, 75.0, 90.0]
            else:
                self.sides = [float(s) for s in self.sides[:3]]
            self.ancho_m = self.sides[0]
            self.largo_m = self.sides[1]

    @property
    def area_m2(self) -> float:
        """Calcula el área real en metros cuadrados según la forma geométrica."""
        if self.shape_type == "triangulo":
            # Fórmula de Herón para 3 lados desiguales
            a, b, c = self.sides[0], self.sides[1], self.sides[2]
            # Validar desigualdad triangular
            if a + b <= c or a + c <= b or b + c <= a:
                # Ajuste de seguridad si las medidas no cierran estrictamente
                s = (a + b + c) / 2.0
                return max(1.0, 0.5 * a * b * math.sin(math.radians(60)))
            s = (a + b + c) / 2.0
            radicando = s * (s - a) * (s - b) * (s - c)
            return math.sqrt(max(0.0, radicando))

        elif self.shape_type == "cuadrilatero":
            # Cuadrilátero irregular con 4 lados desiguales: a, b, c, d
            # En agrimensura rural guatemalteca (técnica estándar de campo de extensionistas MAGA):
            # Área = Promedio de lados opuestos: ((a + c) / 2) * ((b + d) / 2)
            a, b, c, d = self.sides[0], self.sides[1], self.sides[2], self.sides[3]
            area_promedio = ((a + c) / 2.0) * ((b + d) / 2.0)
            return max(1.0, area_promedio)

        elif self.shape_type == "poligono" and self.custom_coords:
            # Fórmula de Gauss / Shoelace para polígonos por coordenadas
            pts = self.custom_coords
            n = len(pts)
            area = 0.0
            for i in range(n):
                j = (i + 1) % n
                area += pts[i][0] * pts[j][1]
                area -= pts[j][0] * pts[i][1]
            return max(1.0, abs(area) / 2.0)

        else:
            # Rectangular estándar: Ancho x Largo
            return max(1.0, self.ancho_m * self.largo_m)

    @property
    def manzanas(self) -> float:
        # En Guatemala 1 manzana tradicional equivale exactamente a 7,000 m² (o 10,000 varas²)
        return self.area_m2 / 7000.0

    @property
    def hectareas(self) -> float:
        return self.area_m2 / 10000.0

    @property
    def perimetro_m(self) -> float:
        if self.shape_type == "triangulo":
            return sum(self.sides[:3])
        elif self.shape_type == "cuadrilatero":
            return sum(self.sides[:4])
        elif self.shape_type == "poligono" and self.custom_coords:
            pts = self.custom_coords
            return sum(math.hypot(pts[i][0] - pts[(i+1)%len(pts)][0], pts[i][1] - pts[(i+1)%len(pts)][1]) for i in range(len(pts)))
        return 2 * (self.ancho_m + self.largo_m)

    @property
    def descripcion_forma(self) -> str:
        if self.shape_type == "cuadrilatero":
            s = self.sides
            return f"Cuadrilátero Irregular - {s[0]:.0f}m, {s[1]:.0f}m, {s[2]:.0f}m, {s[3]:.0f}m"
        elif self.shape_type == "triangulo":
            s = self.sides
            return f"Triangular - {s[0]:.0f}m, {s[1]:.0f}m, {s[2]:.0f}m"
        return f"Rectangular - {self.ancho_m:.0f}m × {self.largo_m:.0f}m"

    def get_polygon_vertices(self) -> List[Tuple[float, float]]:
        """
        Retorna los vértices 2D escalados en metros para trazar en Canvas (Web)
        o Matplotlib (PDF/Reportes).
        """
        if self.shape_type == "triangulo":
            a, b, c = self.sides[0], self.sides[1], self.sides[2]
            # V0 en origen, V1 sobre eje X con longitud a
            v0 = (0.0, 0.0)
            v1 = (a, 0.0)
            # Calcular V2 usando ley de cosenos
            cos_a = (a**2 + b**2 - c**2) / (2.0 * a * b) if (2.0 * a * b) > 0 else 0.0
            cos_a = max(-1.0, min(1.0, cos_a))
            xc = b * cos_a
            yc = b * math.sqrt(max(0.0, 1.0 - cos_a**2))
            v2 = (xc, yc)
            return [v0, v1, v2]

        elif self.shape_type == "cuadrilatero":
            # 4 lados desiguales: a (Base/Sur), b (Derecha/Este), c (Superior/Norte), d (Izquierda/Oeste)
            a, b, c, d = self.sides[0], self.sides[1], self.sides[2], self.sides[3]
            v0 = (0.0, 0.0)
            v1 = (a, 0.0)
            # Altura promedio aproximada
            h_right = b * 0.95
            h_left = d * 0.95
            offset_c = max(0.0, (a - c) / 2.0)
            v2 = (a - offset_c, h_right)
            v3 = (offset_c, h_left)
            return [v0, v1, v2, v3]

        elif self.shape_type == "poligono" and self.custom_coords:
            return self.custom_coords

        else:
            # Rectángulo regular
            w, l = self.ancho_m, self.largo_m
            return [(0.0, 0.0), (w, 0.0), (w, l), (0.0, l)]


def calculate_sowing_density(
    terrain: TerrainModel,
    viability_prob: float,
    semaforo_color: str
) -> Dict[str, Any]:
    """
    Calcula la densidad agronómica óptima por m² adaptada al riesgo hídrico (RF-06).
    """
    # Calibración de plantas por metro cuadrado según disponibilidad de agua
    if semaforo_color == "Verde":
        densidad_plantas_m2 = 5.8
        distancia_surcos_cm = 80.0
        distancia_posturas_cm = 22.0
        semillas_por_postura = 1
        diagnostico = "Densidad óptima/estándar: el régimen hídrico proyectado soporta la máxima población vegetal."
    elif semaforo_color == "Amarillo":
        densidad_plantas_m2 = 4.4
        distancia_surcos_cm = 85.0
        distancia_posturas_cm = 27.0
        semillas_por_postura = 1
        diagnostico = "Densidad moderada: se reduce la población por m² para minimizar la competencia radicular por humedad."
    else:
        densidad_plantas_m2 = 3.6
        distancia_surcos_cm = 90.0
        distancia_posturas_cm = 31.0
        semillas_por_postura = 1
        diagnostico = "Densidad baja de sobrevivencia: distanciamiento amplio ante riesgo severo de estrés hídrico."

    plantas_totales = int(np.round(densidad_plantas_m2 * terrain.area_m2))

    # Consideración de 88% de poder germinativo y 92% de sobrevivencia inicial
    factor_seguridad = 1.0 / (0.88 * 0.92)
    semillas_totales = int(np.round(plantas_totales * factor_seguridad))

    # Equivalencias de comercialización: bolsa estándar (60,000 semillas) o libras (~1,400 semillas/lb)
    bolsas_comerciales = semillas_totales / 60000.0
    libras_semilla = semillas_totales / 1400.0

    return {
        "densidad_plantas_m2": round(densidad_plantas_m2, 2),
        "densidad_plantas_mz": int(np.round(densidad_plantas_m2 * 7000)),
        "plantas_totales_predio": plantas_totales,
        "semillas_totales_requeridas": semillas_totales,
        "bolsas_comerciales": round(bolsas_comerciales, 2),
        "libras_semilla": round(libras_semilla, 1),
        "distancia_surcos_cm": distancia_surcos_cm,
        "distancia_posturas_cm": distancia_posturas_cm,
        "semillas_por_postura": semillas_por_postura,
        "diagnostico_densidad": diagnostico,
    }


def calculate_financial_projection(
    terrain: TerrainModel,
    viability_prob: float,
    capital_inversion: float,
    maga_cfg: MagaPriceConfig = MAGA_CONFIG,
    tipo_maiz: str = "blanco"
) -> Dict[str, Any]:
    """
    Genera la evaluación financiera y la tabla de Pérdidas y Ganancias (RF-07).
    Toma directamente el capital de inversión ingresado por el usuario,
    sin agregar presupuestos desglosados no solicitados.
    Utiliza los precios oficiales del maíz del MAGA con fecha de actualización explícita.
    Exclusivamente para Maíz Blanco de primera.
    """
    mz = terrain.manzanas
    precio_qq = maga_cfg.precio_qq_maiz_blanco

    # 1. Proyección de Rendimiento según viabilidad climática
    # Con viabilidad óptima (prob=1.0) se alcanza el 100% del rendimiento base (65 qq/mz).
    # Con sequía extrema (prob=0.0) el rendimiento cae al 40% (26 qq/mz).
    factor_rendimiento = 0.40 + (0.60 * np.clip(viability_prob, 0.0, 1.0))
    rendimiento_qq_mz = maga_cfg.rendimiento_base_qq_mz * factor_rendimiento
    produccion_total_qq = rendimiento_qq_mz * mz

    # 2. Inversión del Usuario (Costo de Inversión)
    # Se utiliza exactamente el capital de inversión que el usuario ingresó, sin inventar rubros
    inversion_total_q = float(capital_inversion)

    # 3. Ingresos e Indicadores de Rentabilidad
    ingreso_bruto_q = produccion_total_qq * precio_qq
    utilidad_neta_q = ingreso_bruto_q - inversion_total_q
    
    roi_pct = (utilidad_neta_q / max(inversion_total_q, 1.0)) * 100.0
    margen_utilidad_pct = (utilidad_neta_q / max(ingreso_bruto_q, 1.0)) * 100.0
    relacion_beneficio_costo = ingreso_bruto_q / max(inversion_total_q, 1.0)

    # Punto de equilibrio en quintales (cuántos quintales se deben cosechar para cubrir la inversión)
    punto_equilibrio_qq = inversion_total_q / max(precio_qq, 1e-4)
    # Inversión por quintal producido
    inversion_por_qq = inversion_total_q / max(produccion_total_qq, 1e-4)

    # 4. Tabla de Pérdidas y Ganancias (P&L) Estructurada y Limpia
    pnl_items = [
        {"concepto": "Capital de Inversión Aportado: Inversión Total", "monto": -inversion_total_q, "tipo": "costo"},
        {"concepto": f"Producción Estimada: {produccion_total_qq:.1f} quintales a Q {precio_qq:.2f} por quintal", "monto": ingreso_bruto_q, "tipo": "ingreso"},
        {"concepto": "Utilidad Neta Proyectada: Ganancia o Pérdida", "monto": utilidad_neta_q, "tipo": "resultado"},
    ]

    # 5. Análisis de Sensibilidad de Escenarios
    escenarios = [
        {
            "Escenario": "Optimista: Buen régimen de lluvias",
            "Rendimiento (qq/mz)": round(maga_cfg.rendimiento_base_qq_mz * 1.15, 1),
            "Producción Total (qq)": round(maga_cfg.rendimiento_base_qq_mz * 1.15 * mz, 1),
            "Ingreso Bruto (Q)": round(maga_cfg.rendimiento_base_qq_mz * 1.15 * mz * precio_qq, 2),
            "Utilidad Neta (Q)": round((maga_cfg.rendimiento_base_qq_mz * 1.15 * mz * precio_qq) - inversion_total_q, 2),
            "ROI (%)": round((((maga_cfg.rendimiento_base_qq_mz * 1.15 * mz * precio_qq) - inversion_total_q) / max(inversion_total_q, 1.0)) * 100, 1),
        },
        {
            "Escenario": "Proyectado: Modelo agroclimático",
            "Rendimiento (qq/mz)": round(rendimiento_qq_mz, 1),
            "Producción Total (qq)": round(produccion_total_qq, 1),
            "Ingreso Bruto (Q)": round(ingreso_bruto_q, 2),
            "Utilidad Neta (Q)": round(utilidad_neta_q, 2),
            "ROI (%)": round(roi_pct, 1),
        },
        {
            "Escenario": "Pesimista: Déficit hídrico o canícula",
            "Rendimiento (qq/mz)": round(maga_cfg.rendimiento_base_qq_mz * 0.45, 1),
            "Producción Total (qq)": round(maga_cfg.rendimiento_base_qq_mz * 0.45 * mz, 1),
            "Ingreso Bruto (Q)": round(maga_cfg.rendimiento_base_qq_mz * 0.45 * mz * precio_qq, 2),
            "Utilidad Neta (Q)": round((maga_cfg.rendimiento_base_qq_mz * 0.45 * mz * precio_qq) - inversion_total_q, 2),
            "ROI (%)": round((((maga_cfg.rendimiento_base_qq_mz * 0.45 * mz * precio_qq) - inversion_total_q) / max(inversion_total_q, 1.0)) * 100, 1),
        },
    ]

    return {
        "fuente_oficial_maga": maga_cfg.fuente_oficial,
        "fecha_actualizacion_maga": maga_cfg.fecha_actualizacion,
        "tipo_maiz": tipo_maiz.capitalize(),
        "precio_maga_qq": precio_qq,
        "area_manzanas": round(mz, 3),
        "rendimiento_estimado_qq_mz": round(rendimiento_qq_mz, 1),
        "produccion_total_estimada_qq": round(produccion_total_qq, 1),
        "capital_inversion_q": round(inversion_total_q, 2),
        "inversion_por_quintal_q": round(inversion_por_qq, 2),
        "ingreso_bruto_q": round(ingreso_bruto_q, 2),
        "utilidad_neta_q": round(utilidad_neta_q, 2),
        "roi_pct": round(roi_pct, 1),
        "margen_utilidad_pct": round(margen_utilidad_pct, 1),
        "relacion_beneficio_costo": round(relacion_beneficio_costo, 2),
        "punto_equilibrio_qq": round(punto_equilibrio_qq, 1),
        "pnl_items": pnl_items,
        "escenarios_sensibilidad": escenarios,
    }


def calcular_analisis_pluviometrico(fecha_siembra: str, fase_enso: str = "Neutral") -> Dict[str, Any]:
    """
    Calcula el análisis pluviométrico del mes seleccionado y su distribución por decenas
    a partir de las estadísticas históricas de 46 años de ERA5 para Jutiapa.
    """
    import datetime
    try:
        dt = datetime.datetime.strptime(str(fecha_siembra).split("T")[0], "%Y-%m-%d")
        m = dt.month
    except Exception:
        m = 10

    CLIMA_JUTIAPA = {
        1: {"nombre": "Enero", "precip": 3.0, "tipo": "Déficit Extremo", "caract": "Época Seca Severa (Estiaje)", "d1": 1.2, "d2": 0.9, "d3": 1.0, "ultDia": 31},
        2: {"nombre": "Febrero", "precip": 5.1, "tipo": "Déficit Extremo", "caract": "Época Seca Severa (Estiaje)", "d1": 1.1, "d2": 1.9, "d3": 2.1, "ultDia": 28},
        3: {"nombre": "Marzo", "precip": 17.7, "tipo": "Déficit Extremo", "caract": "Época Seca Severa (Estiaje)", "d1": 3.3, "d2": 7.0, "d3": 7.4, "ultDia": 31},
        4: {"nombre": "Abril", "precip": 59.5, "tipo": "Déficit Moderado", "caract": "Transición hacia Época Lluviosa", "d1": 13.0, "d2": 18.5, "d3": 28.1, "ultDia": 30},
        5: {"nombre": "Mayo", "precip": 215.2, "tipo": "Aumento de Lluvias", "caract": "Establecimiento de Temporada Lluviosa", "d1": 43.7, "d2": 59.9, "d3": 111.7, "ultDia": 31},
        6: {"nombre": "Junio", "precip": 318.2, "tipo": "Aumento Significativo", "caract": "Pico Máximo de Siembra de Primera", "d1": 110.1, "d2": 112.6, "d3": 95.5, "ultDia": 30},
        7: {"nombre": "Julio", "precip": 189.7, "tipo": "Régimen Moderado", "caract": "Disminución Temporal por Canícula", "d1": 68.8, "d2": 59.0, "d3": 61.9, "ultDia": 31},
        8: {"nombre": "Agosto", "precip": 247.5, "tipo": "Aumento de Lluvias", "caract": "Temporada Lluviosa Intensa (Postrera)", "d1": 66.6, "d2": 78.0, "d3": 102.9, "ultDia": 31},
        9: {"nombre": "Septiembre", "precip": 343.3, "tipo": "Aumento Significativo", "caract": "Pico Máximo Anual de Precipitaciones", "d1": 98.0, "d2": 104.0, "d3": 141.2, "ultDia": 30},
        10: {"nombre": "Octubre", "precip": 261.2, "tipo": "Aumento de Lluvias", "caract": "Temporada Ciclónica y Retiro de Lluvias", "d1": 113.6, "d2": 88.4, "d3": 59.2, "ultDia": 31},
        11: {"nombre": "Noviembre", "precip": 58.4, "tipo": "Déficit Moderado", "caract": "Transición hacia Época Seca", "d1": 31.5, "d2": 18.2, "d3": 8.8, "ultDia": 30},
        12: {"nombre": "Diciembre", "precip": 9.0, "tipo": "Déficit Extremo", "caract": "Época Seca Severa (Estiaje)", "d1": 3.4, "d2": 2.9, "d3": 2.7, "ultDia": 31},
    }

    curr = CLIMA_JUTIAPA[m]
    prev_idx = ((m - 2 + 12) % 12) + 1
    next_idx = (m % 12) + 1
    prev = CLIMA_JUTIAPA[prev_idx]
    next_m = CLIMA_JUTIAPA[next_idx]

    fase_l = (fase_enso or "").lower()
    if "nina" in fase_l or "niña" in fase_l:
        enso_label = "La Niña / Alta Influencia Ciclónica"
        enso_desc = f"En fases de La Niña o temporales ciclónicos en el Caribe, las lluvias de {curr['nombre']} en Jutiapa se incrementan en promedio +19.7%, alcanzando aproximadamente {curr['precip'] * 1.197:.1f} mm."
    elif "nino" in fase_l or "niño" in fase_l:
        enso_label = "El Niño / Déficit Pluviométrico"
        enso_desc = f"En fases de El Niño, se presenta una reducción de lluvias de aproximadamente -22.5%, proyectando {curr['precip'] * 0.775:.1f} mm con riesgo de adelanto de canícula o retiro prematuro de humedad."
    else:
        enso_label = "Fase Climática Neutral"
        enso_desc = f"Bajo condiciones Neutrales, la precipitación en {curr['nombre']} se mantiene cercana a su media histórica de {curr['precip']:.1f} mm."

    if m == 10:
        conclusion = f"Aunque en Octubre se registra un AUMENTO de lluvias ({curr['precip']:.1f} mm) impulsado por temporales y ciclones, sembrar maíz en esta fecha conlleva un riesgo severo. El ciclo del maíz blanco requiere entre 60 y 90 días: la planta germinará con alta humedad, pero enfrentará un DÉFICIT HÍDRICO TERMINAL en noviembre y diciembre durante la floración y el llenado de grano, cuando las lluvias caen bruscamente a menos de 1 mm diario."
    elif m in (5, 6):
        conclusion = f"En {curr['nombre']} se presenta un AUMENTO SIGNIFICATIVO de precipitaciones ({curr['precip']:.1f} mm), correspondiente a la ventana óptima de Siembra de Primera. Hay garantía de humedad edáfica para la germinación y desarrollo vegetativo vigoroso."
    elif m == 7:
        conclusion = f"En Julio ocurre una reducción relativa de lluvia ({curr['precip']:.1f} mm) debido a la Canícula de medio año. Se recomienda calibrar la fecha hacia la siembra de Postrera en Agosto o emplear variedades precoces tolerantes a estrés."
    elif m in (8, 9):
        conclusion = f"En {curr['nombre']} se registra un AUMENTO ELEVADO de precipitaciones ({curr['precip']:.1f} mm) característico de la temporada de Postrera. Excelente disponibilidad hídrica, debiendo vigilar drenajes en parcelas con alta retención para evitar asfixia radicular."
    else:
        conclusion = f"En {curr['nombre']} existe un DÉFICIT SEVERO de precipitaciones ({curr['precip']:.1f} mm) correspondiente al periodo seco o de estiaje. La siembra a temporal es inviable sin suministro de riego complementario."

    return {
        "mes_nombre": curr["nombre"],
        "pregunta_titulo": f"¿Hay déficit o aumento de lluvias en {curr['nombre']}?",
        "diagnostico_badge": curr["tipo"],
        "tabla_comparativa": [
            {"mes": prev["nombre"], "precip": f"{prev['precip']:.1f} mm", "caracterizacion": prev["caract"], "es_seleccionado": False},
            {"mes": curr["nombre"], "precip": f"{curr['precip']:.1f} mm", "caracterizacion": curr["caract"], "es_seleccionado": True},
            {"mes": next_m["nombre"], "precip": f"{next_m['precip']:.1f} mm", "caracterizacion": next_m["caract"], "es_seleccionado": False},
        ],
        "distribucion_decenas": [
            {"rango": f"1 a 10 de {curr['nombre']}", "etiqueta": "Primera decena", "mm": f"{curr['d1']:.1f} mm", "porcentaje": f"{(curr['d1']/curr['precip'])*100:.1f}%", "detalle": "Pico concentrado de lluvias por ondas del este y ciclones." if m == 10 else "Lluvias regulares de inicio de mes."},
            {"rango": f"11 a 20 de {curr['nombre']}", "etiqueta": "Segunda decena", "mm": f"{curr['d2']:.1f} mm", "porcentaje": f"{(curr['d2']/curr['precip'])*100:.1f}%", "detalle": "Lluvias regulares con tendencia decreciente." if m == 10 else "Aporte hídrico sostenido."},
            {"rango": f"21 al {curr['ultDia']} de {curr['nombre']}", "etiqueta": "Tercera decena", "mm": f"{curr['d3']:.1f} mm", "porcentaje": f"{(curr['d3']/curr['precip'])*100:.1f}%", "detalle": "Desplome marcado y cese de temporada." if m == 10 else "Precipitaciones de cierre de mes."},
        ],
        "impacto_evento": {"titulo": enso_label, "descripcion": enso_desc},
        "conclusiones_modelo": conclusion,
    }
