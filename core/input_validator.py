"""
Módulo de Validación Integral de Entradas y Seguridad (RF-01 / Hardening).
Proporciona validación estricta de dominios agronómicos, límites geográficos
de Jutiapa (Guatemala), consistencia geométrica de parcelas, análisis financiero
de capital por manzana y protección activa contra inyecciones (SQL, XSS, Path Traversal).
"""
from dataclasses import dataclass, field
from datetime import datetime, date
import math
import re
from typing import Dict, Any, List, Optional, Union

try:
    from config.settings import VALIDATION_CONFIG, ValidationConfig
except ImportError:
    # Respaldo con las mismas constantes históricas si se ejecuta en modo desacoplado
    @dataclass(frozen=True)
    class ValidationConfig:
        lat_min: float = 14.240
        lat_max: float = 14.290
        lon_min: float = -90.160
        lon_max: float = -90.110
        localidad_exclusiva: str = "Calderas, San José Acatempa, Jutiapa"
        date_min_year: int = 1981
        date_max_year: int = 2030
        capital_min_q: float = 500.0
        capital_max_q: float = 150_000.0
        capital_per_mz_min_q: float = 2_000.0
        capital_per_mz_max_q: float = 25_000.0
        side_min_m: float = 1.0
        side_max_m: float = 2_000.0
        max_area_m2: float = 700_000.0
        max_string_length: int = 100

    VALIDATION_CONFIG = ValidationConfig()


class ValidationError(ValueError):
    """
    Excepción personalizada para fallos de validación agronómica,
    geográfica o de seguridad en las entradas del usuario.
    """
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.field = field

    def __str__(self) -> str:
        if self.field:
            return f"[{self.field}] {self.message}"
        return self.message


def sanitize_string(value: str, field_name: str, max_length: int = 100) -> str:
    """
    Sanitiza una entrada de tipo cadena contra ataques de inyección.
    
    Aplica las siguientes protecciones:
      1. Verificación de tipo de dato estricto (rechaza objetos no textuales).
      2. Límite de longitud máxima (por defecto 100 caracteres) para prevenir DoS.
      3. Eliminación iterativa de etiquetas <script> y su contenido interior.
      4. Eliminación de etiquetas HTML generales (<...>).
      5. Eliminación de secuencias de evasión de directorios / path traversal (.., /, \\).
      6. Eliminación de secuencias SQL peligrosas: palabras clave completas
         (SELECT, DROP, INSERT, DELETE, UPDATE, UNION), terminadores (;) y comentarios (--).
      7. Limpieza de espacios redundantes en extremos.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"El campo '{field_name}' debe ser una cadena de texto, recibido: {type(value).__name__}.",
            field=field_name
        )

    if len(value) > max_length:
        raise ValidationError(
            f"El campo '{field_name}' excede la longitud máxima permitida de {max_length} caracteres (longitud actual: {len(value)}).",
            field=field_name
        )

    sanitized = value

    # Ciclo iterativo (hasta 5 pasadas) para desarmar inyecciones recursivas o anidadas (e.g. <scr<script>ipt> o ....//)
    for _ in range(5):
        prev = sanitized

        # 1. Eliminar etiquetas <script>...</script> y su contenido (insensible a mayúsculas/minúsculas y multilínea)
        sanitized = re.sub(r"(?is)<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", sanitized)

        # 2. Eliminar cualquier etiqueta HTML remanente o malformada
        sanitized = re.sub(r"<[^>]+>", "", sanitized)

        # 3. Eliminar secuencias de salto de directorio (Path Traversal)
        sanitized = sanitized.replace("..", "").replace("/", "").replace("\\", "")

        # 4. Eliminar comentarios SQL y terminadores de sentencia
        sanitized = sanitized.replace("--", "").replace(";", "")

        # 5. Eliminar palabras clave SQL destructivas o de exfiltración como palabras completas
        sanitized = re.sub(
            r"(?i)\b(SELECT|DROP|INSERT|DELETE|UPDATE|UNION)\b",
            "",
            sanitized
        )

        if sanitized == prev:
            break

    return sanitized.strip()


def _parse_and_validate_number(val: Any, field_name: str, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """
    Valida y convierte un valor a float asegurando que sea un número real genuino
    y no una cadena que contenga código malicioso ejecutable.
    """
    if isinstance(val, bool):
        raise ValidationError(
            f"El campo '{field_name}' debe ser un valor numérico real, no un booleano.",
            field=field_name
        )

    if isinstance(val, (int, float)):
        num = float(val)
    elif isinstance(val, str):
        # Verificar que la cadena no sea código inyectado
        val_str = val.strip()
        # Rechazar inmediatamente si contiene identificadores de código, llamadas a funciones o sintaxis sospechosa
        if re.search(r"[a-zA-Z_()\[\]{}\'\"`$!=#&|]", val_str):
            raise ValidationError(
                f"El valor numérico para '{field_name}' contiene caracteres o fragmentos de código inválidos: '{val}'.",
                field=field_name
            )
        try:
            num = float(val_str)
        except ValueError:
            raise ValidationError(
                f"El campo '{field_name}' no contiene un número decimal válido: '{val}'.",
                field=field_name
            )
    else:
        raise ValidationError(
            f"El campo '{field_name}' debe ser de tipo numérico (int o float), recibido: {type(val).__name__}.",
            field=field_name
        )

    if math.isnan(num) or math.isinf(num):
        raise ValidationError(
            f"El campo '{field_name}' no puede ser NaN ni Infinito.",
            field=field_name
        )

    if min_val is not None and num < min_val:
        raise ValidationError(
            f"El campo '{field_name}' ({num}) es menor al valor mínimo permitido de {min_val}.",
            field=field_name
        )

    if max_val is not None and num > max_val:
        raise ValidationError(
            f"El campo '{field_name}' ({num}) excede el valor máximo permitido de {max_val}.",
            field=field_name
        )

    return num


def _calculate_terrain_area(shape_type: str, sides: List[float], width: float, length: float) -> float:
    """
    Calcula el área en metros cuadrados según la geometría validada.
    Utiliza las fórmulas oficiales agronómicas aplicadas en el Corredor Seco.
    """
    if shape_type == "triangulo":
        # Fórmula de Herón para 3 lados
        a, b, c = sides[0], sides[1], sides[2]
        s = (a + b + c) / 2.0
        radicando = s * (s - a) * (s - b) * (s - c)
        return math.sqrt(max(0.0, radicando))
    elif shape_type == "cuadrilatero":
        # Técnica MAGA de lados opuestos promediados para parcelas irregulares de 4 lados
        a, b, c, d = sides[0], sides[1], sides[2], sides[3]
        return ((a + c) / 2.0) * ((b + d) / 2.0)
    else:
        # Rectángulo regular
        return width * length


@dataclass
class ValidatedInput:
    """
    Contenedor de parámetros de entrada previamente validados, tipados
    y sanitizados contra inyecciones para el análisis agroclimático y financiero.
    """
    sowing_date: str
    lat: float
    lon: float
    shape_type: str
    sides: List[float]
    width: float
    length: float
    capital: float
    corn_type: str
    capital_warnings: List[str]  # Advertencias no bloqueantes sobre idoneidad del capital
    capital_per_manzana: float   # Inversión calculada por manzana (Q/mz)

    @property
    def area_m2(self) -> float:
        """Área de la parcela en metros cuadrados."""
        return _calculate_terrain_area(self.shape_type, self.sides, self.width, self.length)

    @property
    def manzanas(self) -> float:
        """Área en manzanas guatemaltecas tradicionales (1 mz = 7,000 m²)."""
        return self.area_m2 / 7000.0

    @property
    def hectareas(self) -> float:
        """Área en hectáreas internacionales (1 ha = 10,000 m²)."""
        return self.area_m2 / 10000.0

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la estructura validada a un diccionario serializable."""
        return {
            "sowing_date": self.sowing_date,
            "lat": self.lat,
            "lon": self.lon,
            "shape_type": self.shape_type,
            "sides": list(self.sides),
            "width": self.width,
            "length": self.length,
            "capital": self.capital,
            "corn_type": self.corn_type,
            "capital_warnings": list(self.capital_warnings),
            "capital_per_manzana": round(self.capital_per_manzana, 2),
            "area_m2": round(self.area_m2, 2),
            "manzanas": round(self.manzanas, 3),
            "hectareas": round(self.hectareas, 3),
        }


def validate_and_sanitize(raw_inputs: Optional[Dict[str, Any]] = None, **kwargs) -> ValidatedInput:
    """
    Valida y sanitiza exhaustivamente todas las entradas del usuario antes
    de procesarlas en el pipeline agrometeorológico y financiero.

    Acepta un diccionario o argumentos por nombre (kwargs). Soporta nombres de parámetros
    tanto en español como en inglés para interoperabilidad CLI y Web.

    Lanza ValidationError con mensajes claros y descriptivos si cualquier regla es violada.
    """
    # 1. Consolidar entradas de diccionario y kwargs
    inputs: Dict[str, Any] = {}
    if raw_inputs and isinstance(raw_inputs, dict):
        inputs.update(raw_inputs)
    inputs.update(kwargs)

    # -------------------------------------------------------------------------
    # A. Extracción y Normalización de Claves (Soporte de Aliases)
    # -------------------------------------------------------------------------
    raw_date = inputs.get("sowing_date") or inputs.get("sowing_date_str") or inputs.get("date") or inputs.get("fecha_siembra")
    raw_lat = inputs.get("lat") if "lat" in inputs else (inputs.get("latitude") if "latitude" in inputs else 14.267)
    raw_lon = inputs.get("lon") if "lon" in inputs else (inputs.get("longitude") if "longitude" in inputs else -90.133)
    raw_shape = inputs.get("shape_type") or inputs.get("shape") or inputs.get("forma") or "rectangulo"
    raw_sides = inputs.get("sides") if "sides" in inputs else (inputs.get("terrain_sides") if "terrain_sides" in inputs else inputs.get("lados"))
    raw_width = inputs.get("width") if "width" in inputs else (inputs.get("terrain_width_m") if "terrain_width_m" in inputs else inputs.get("ancho_m"))
    raw_length = inputs.get("length") if "length" in inputs else (inputs.get("terrain_length_m") if "terrain_length_m" in inputs else inputs.get("largo_m"))
    raw_capital = inputs.get("capital") if "capital" in inputs else (inputs.get("capital_disponible_q") if "capital_disponible_q" in inputs else inputs.get("capital_inversion"))
    raw_corn_type = inputs.get("corn_type") or inputs.get("tipo_maiz") or "blanco"

    # Si la fecha no fue provista, lanzar error explícito
    if raw_date is None:
        raise ValidationError(
            "La fecha de siembra ('sowing_date') es obligatoria y debe tener formato YYYY-MM-DD.",
            field="sowing_date"
        )

    # Si el capital no fue provisto, lanzar error explícito
    if raw_capital is None:
        raise ValidationError(
            "El capital de inversión ('capital') es obligatorio.",
            field="capital"
        )

    # -------------------------------------------------------------------------
    # B. Validación de Fecha de Siembra (Anti-inyección y Rango 1981 - 2030)
    # -------------------------------------------------------------------------
    if isinstance(raw_date, (datetime, date)):
        date_str = raw_date.strftime("%Y-%m-%d")
    elif isinstance(raw_date, str):
        sanitized_date = sanitize_string(raw_date, "sowing_date", max_length=VALIDATION_CONFIG.max_string_length)
        date_str = sanitized_date
    else:
        raise ValidationError(
            f"El formato de la fecha de siembra debe ser una cadena YYYY-MM-DD, recibido: {type(raw_date).__name__}.",
            field="sowing_date"
        )

    # Comprobación de formato estricto YYYY-MM-DD mediante expresión regular
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValidationError(
            f"La fecha de siembra '{date_str}' no cumple con el formato obligatorio YYYY-MM-DD (ejemplo: 2026-06-01).",
            field="sowing_date"
        )

    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValidationError(
            f"La fecha de siembra '{date_str}' no es una fecha válida en el calendario gregoriano: {e}.",
            field="sowing_date"
        )

    min_date = date(VALIDATION_CONFIG.date_min_year, 1, 1)
    max_date = date(VALIDATION_CONFIG.date_max_year, 12, 31)

    if parsed_date < min_date or parsed_date > max_date:
        raise ValidationError(
            f"La fecha de siembra '{date_str}' debe estar comprendida dentro del registro histórico y horizonte de proyección (entre {min_date.isoformat()} y {max_date.isoformat()}).",
            field="sowing_date"
        )

    # -------------------------------------------------------------------------
    # C. Validación Geográfica Exclusiva (Calderas, San José Acatempa, Jutiapa)
    # -------------------------------------------------------------------------
    try:
        lat = _parse_and_validate_number(
            raw_lat,
            field_name="lat",
            min_val=VALIDATION_CONFIG.lat_min,
            max_val=VALIDATION_CONFIG.lat_max
        )
        lon = _parse_and_validate_number(
            raw_lon,
            field_name="lon",
            min_val=VALIDATION_CONFIG.lon_min,
            max_val=VALIDATION_CONFIG.lon_max
        )
    except ValidationError:
        raise ValidationError(
            f"UBICACIÓN NO PERMITIDA: Este sistema está diseñado, calibrado y habilitado ÚNICAMENTE para Calderas, San José Acatempa, Jutiapa (Guatemala). Coordenadas recibidas: ({raw_lat}, {raw_lon}). Límite permitido para Calderas: Lat [{VALIDATION_CONFIG.lat_min}, {VALIDATION_CONFIG.lat_max}], Lon [{VALIDATION_CONFIG.lon_min}, {VALIDATION_CONFIG.lon_max}].",
            field="lat/lon"
        )

    # -------------------------------------------------------------------------
    # D. Validación de Forma y Geometría del Terreno
    # -------------------------------------------------------------------------
    if not isinstance(raw_shape, str):
        raise ValidationError(
            f"El tipo de forma del terreno ('shape_type') debe ser una cadena de texto, recibido: {type(raw_shape).__name__}.",
            field="shape_type"
        )

    shape_type = sanitize_string(raw_shape, "shape_type", max_length=30).lower()
    allowed_shapes = ["rectangulo", "cuadrilatero", "triangulo"]
    if shape_type not in allowed_shapes:
        raise ValidationError(
            f"Forma de terreno '{shape_type}' no permitida. Debe ser una de: {allowed_shapes}.",
            field="shape_type"
        )

    # Normalización y validación de lados (sides), ancho (width) y largo (length)
    sides: List[float] = []

    if raw_sides is not None:
        if not isinstance(raw_sides, (list, tuple)):
            raise ValidationError(
                f"El parámetro 'sides' debe ser una lista o tupla de números, recibido: {type(raw_sides).__name__}.",
                field="sides"
            )

        # Validar longitud de lados según la forma
        expected_sides_count = 3 if shape_type == "triangulo" else 4
        if len(raw_sides) != expected_sides_count:
            raise ValidationError(
                f"Para la forma '{shape_type}', la lista de lados ('sides') debe contener exactamente {expected_sides_count} medidas (recibidas: {len(raw_sides)}).",
                field="sides"
            )

        for i, s_val in enumerate(raw_sides):
            val_f = _parse_and_validate_number(
                s_val,
                field_name=f"sides[{i}]",
                min_val=VALIDATION_CONFIG.side_min_m,
                max_val=VALIDATION_CONFIG.side_max_m
            )
            sides.append(val_f)
    else:
        # Si no se pasó sides explícito, intentar derivar de width y length
        if shape_type == "rectangulo":
            w_candidate = raw_width if raw_width is not None else 100.0
            l_candidate = raw_length if raw_length is not None else 70.0
            w_val = _parse_and_validate_number(w_candidate, "width", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)
            l_val = _parse_and_validate_number(l_candidate, "length", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)
            sides = [w_val, l_val, w_val, l_val]
        elif shape_type == "cuadrilatero":
            w_candidate = raw_width if raw_width is not None else 100.0
            l_candidate = raw_length if raw_length is not None else 70.0
            w_val = _parse_and_validate_number(w_candidate, "width", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)
            l_val = _parse_and_validate_number(l_candidate, "length", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)
            sides = [w_val, l_val, w_val, l_val]
        else: # triangulo
            raise ValidationError(
                "Para parcelas triangulares ('triangulo'), es obligatorio proporcionar la lista 'sides' con los 3 lados.",
                field="sides"
            )

    # Determinar y validar width y length
    if raw_width is not None:
        width = _parse_and_validate_number(raw_width, "width", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)
    else:
        if shape_type == "rectangulo":
            width = sides[0]
        elif shape_type == "cuadrilatero":
            width = (sides[0] + sides[2]) / 2.0
        else:
            width = sides[0]
        width = _parse_and_validate_number(width, "width", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)

    if raw_length is not None:
        length = _parse_and_validate_number(raw_length, "length", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)
    else:
        if shape_type == "rectangulo":
            length = sides[1]
        elif shape_type == "cuadrilatero":
            length = (sides[1] + sides[3]) / 2.0
        else:
            length = sides[1]
        length = _parse_and_validate_number(length, "length", VALIDATION_CONFIG.side_min_m, VALIDATION_CONFIG.side_max_m)

    # Validar Desigualdad Triangular para triángulos
    if shape_type == "triangulo":
        a, b, c = sides[0], sides[1], sides[2]
        if (a + b <= c) or (a + c <= b) or (b + c <= a):
            raise ValidationError(
                f"Las longitudes de los lados {sides} no satisfacen el teorema de la desigualdad triangular (la suma de cualquier par de lados debe ser estrictamente mayor que el tercer lado: a={a}, b={b}, c={c}).",
                field="sides"
            )

    # -------------------------------------------------------------------------
    # E. Validación de Tipo de Maíz
    # -------------------------------------------------------------------------
    if not isinstance(raw_corn_type, str):
        raise ValidationError(
            f"El campo 'corn_type' debe ser una cadena de texto, recibido: {type(raw_corn_type).__name__}.",
            field="corn_type"
        )

    corn_type = sanitize_string(raw_corn_type, "corn_type", max_length=VALIDATION_CONFIG.max_string_length).lower()
    if corn_type != "blanco":
        raise ValidationError(
            f"Tipo de cultivo de maíz '{corn_type}' no soportado. El sistema está calibrado exclusivamente para 'blanco' (maíz blanco de primera en Jutiapa).",
            field="corn_type"
        )

    # -------------------------------------------------------------------------
    # F. Validación Financiera / Capital y Cálculo de Adecuación
    # -------------------------------------------------------------------------
    capital = _parse_and_validate_number(
        raw_capital,
        field_name="capital",
        min_val=VALIDATION_CONFIG.capital_min_q,
        max_val=VALIDATION_CONFIG.capital_max_q
    )

    # Calcular área y manzanas
    area_m2 = _calculate_terrain_area(shape_type, sides, width, length)
    if area_m2 <= 0.0:
        raise ValidationError(
            f"El área resultante del terreno ({area_m2} m²) no es válida para cultivo.",
            field="sides"
        )

    manzanas = area_m2 / 7000.0
    capital_per_manzana = capital / max(manzanas, 1e-4)

    # Evaluar advertencias no bloqueantes sobre la razonabilidad del capital por manzana
    capital_warnings: List[str] = []
    if capital_per_manzana < VALIDATION_CONFIG.capital_per_mz_min_q:
        capital_warnings.append(
            f"Advertencia de Capital: El capital ingresado (Q {capital:,.2f}) equivale a Q {capital_per_manzana:,.2f}/manzana "
            f"para una parcela de {manzanas:.2f} mz ({area_m2:,.1f} m²). Este monto se ubica por debajo del rango histórico "
            f"mínimo de subsistencia (Q {VALIDATION_CONFIG.capital_per_mz_min_q:,.2f}/mz) en Jutiapa, lo que podría implicar "
            f"insuficiencia de recursos para fertilización o labores culturales completas."
        )
    elif capital_per_manzana > VALIDATION_CONFIG.capital_per_mz_max_q:
        capital_warnings.append(
            f"Advertencia de Capital: El capital ingresado (Q {capital:,.2f}) equivale a Q {capital_per_manzana:,.2f}/manzana "
            f"para una parcela de {manzanas:.2f} mz ({area_m2:,.1f} m²). Este monto supera el costo promedio de producción "
            f"altamente tecnificada con riego (Q {VALIDATION_CONFIG.capital_per_mz_max_q:,.2f}/mz) para maíz en el departamento. "
            f"Verifique que la inversión no incluya activos fijos o rubros ajenos al ciclo operativo agrícola."
        )

    return ValidatedInput(
        sowing_date=date_str,
        lat=lat,
        lon=lon,
        shape_type=shape_type,
        sides=sides,
        width=width,
        length=length,
        capital=capital,
        corn_type=corn_type,
        capital_warnings=capital_warnings,
        capital_per_manzana=capital_per_manzana
    )


def get_validation_summary(validated: ValidatedInput) -> Dict[str, Any]:
    """
    Genera un diccionario exhaustivo resumiendo todas las validaciones efectuadas,
    adecuado para la pista de auditoría (audit trail) en el reporte PDF y en la UI web.
    """
    area_m2 = validated.area_m2
    mz = validated.manzanas

    return {
        "status": "VALIDATED",
        "timestamp_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_trail": [
            f"Fecha de siembra verificada: {validated.sowing_date} (dentro del rango histórico 1981-2030, sin inyecciones).",
            f"Coordenadas geográficas validadas: ({validated.lat:.4f}, {validated.lon:.4f}) en Calderas, San José Acatempa, Jutiapa.",
            f"Geometría confirmada: {validated.shape_type} con dimensiones dentro del rango agronómico [1.0 m, 2000.0 m].",
            f"Área calculada: {area_m2:,.2f} m² equivalentes a {mz:.3f} manzanas guatemaltecas (1 mz = 7,000 m²).",
            f"Cultivo verificado: Maíz {validated.corn_type.capitalize()} de primera.",
            f"Capital evaluado: Q {validated.capital:,.2f} (Q {validated.capital_per_manzana:,.2f} por manzana).",
            f"Filtros de seguridad aplicados: Anti-SQLi, Anti-XSS, Anti-Path-Traversal y tipado numérico estricto.",
        ],
        "checks": {
            "date_validation": {
                "passed": True,
                "sowing_date": validated.sowing_date,
                "min_allowed_date": f"{VALIDATION_CONFIG.date_min_year}-01-01",
                "max_allowed_date": f"{VALIDATION_CONFIG.date_max_year}-12-31",
            },
            "geographic_validation": {
                "passed": True,
                "lat": validated.lat,
                "lon": validated.lon,
                "region": "Jutiapa (Corredor Seco)",
                "lat_bounds": [VALIDATION_CONFIG.lat_min, VALIDATION_CONFIG.lat_max],
                "lon_bounds": [VALIDATION_CONFIG.lon_min, VALIDATION_CONFIG.lon_max],
            },
            "terrain_geometry": {
                "passed": True,
                "shape_type": validated.shape_type,
                "sides_m": validated.sides,
                "width_m": validated.width,
                "length_m": validated.length,
                "area_m2": round(area_m2, 2),
                "area_manzanas": round(mz, 3),
                "area_hectareas": round(validated.hectareas, 3),
                "triangle_inequality_checked": (validated.shape_type == "triangulo"),
            },
            "financial_adequacy": {
                "passed": True,
                "capital_total_q": validated.capital,
                "capital_per_manzana_q": round(validated.capital_per_manzana, 2),
                "historical_range_per_mz": [
                    VALIDATION_CONFIG.capital_per_mz_min_q,
                    VALIDATION_CONFIG.capital_per_mz_max_q
                ],
                "warnings": validated.capital_warnings,
                "warnings_count": len(validated.capital_warnings),
            },
            "crop_type": {
                "passed": True,
                "corn_type": validated.corn_type,
                "allowed_types": ["blanco"],
            },
            "security_hardening": {
                "passed": True,
                "max_string_length": VALIDATION_CONFIG.max_string_length,
                "anti_xss_stripped": True,
                "anti_sqli_stripped": True,
                "anti_path_traversal_stripped": True,
                "strict_numeric_enforced": True,
            }
        },
        "warnings": validated.capital_warnings
    }
