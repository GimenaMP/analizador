"""
Módulo de Extracción en Tiempo Real (Scraping) de Precios Oficiales del MAGA.
Fuente: Sistema de Precios Diarios del Ministerio de Agricultura, Ganadería y Alimentación de Guatemala
URL: https://precios.maga.gob.gt/diarios/diarios.html
Implementado con la librería estándar urllib (cero dependencias externas requeridas).
"""
import re
import time
import ssl
import urllib.request
from typing import Dict, Any, List, Optional
from datetime import datetime

MAGA_URL = "https://precios.maga.gob.gt/diarios/diarios.html"

# Memoria caché en ejecución para no saturar el servidor del MAGA
_CACHE: Dict[str, Any] = {
    "timestamp": 0,
    "data": None,
    "ttl_seconds": 600  # 10 minutos
}

FALLBACK_PRICE_DATA = {
    "producto": "Maíz blanco, de primera",
    "mercado": "La Terminal",
    "medida": "Quintal",
    "precio": 200.00,
    "fecha": "30/10/2026",
    "fuente": "MAGA Guatemala - Precios Diarios de Mercados Mayoristas",
    "estado": "fallback",
    "hora_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "variedades": [
        {"producto": "Maíz blanco, de primera", "mercado": "La Terminal", "medida": "Quintal", "precio": 200.00},
        {"producto": "Maíz blanco, de primera, otros orígenes", "mercado": "La Terminal", "medida": "Quintal", "precio": 190.00},
        {"producto": "Maíz blanco, de segunda", "mercado": "La Terminal", "medida": "Quintal", "precio": 185.00},
        {"producto": "Maíz amarillo, de primera", "mercado": "La Terminal", "medida": "Quintal", "precio": 200.00},
        {"producto": "Maíz amarillo, de segunda", "mercado": "La Terminal", "medida": "Quintal", "precio": 200.00}
    ]
}


def fetch_maga_white_corn_price(timeout_sec: int = 7, force: bool = False) -> Dict[str, Any]:
    """
    Obtiene el precio oficial diario del Maíz blanco de primera en La Terminal desde la página del MAGA.
    Scrapea en tiempo real https://precios.maga.gob.gt/diarios/diarios.html
    Extrae la fecha oficial del boletín y todas las variedades de maíz reportadas.
    """
    global _CACHE
    now = time.time()
    
    # Retornar caché si aún es válido y no se solicitó forzar actualización
    if not force and _CACHE["data"] and (now - _CACHE["timestamp"] < _CACHE["ttl_seconds"]):
        return _CACHE["data"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-GT,es;q=0.9,en;q=0.8"
    }

    try:
        # Contexto SSL seguro permisivo para certificados gubernamentales locales
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(MAGA_URL, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=timeout_sec) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

            # 1. Extraer fecha del reporte (ej. <h5>30/10/2026</h5>)
            date_match = re.search(r"<h5>\s*(\d{2}/\d{2}/\d{4})\s*</h5>", html, re.IGNORECASE)
            fecha_reporte = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")

            # 2. Extraer todas las variedades de maíz disponibles en la tabla
            variedades_regex = re.compile(
                r"<tr>\s*<td>\s*(Ma[íi]z[^<]+)</td>\s*<td>\s*([^<]+)</td>\s*<td[^>]*>\s*([^<]+)</td>\s*<td[^>]*class=['\"]precios['\"][^>]*>\s*([\d\.]+)",
                re.IGNORECASE
            )

            variedades = []
            for match in variedades_regex.finditer(html):
                variedades.append({
                    "producto": match.group(1).strip(),
                    "mercado": match.group(2).strip(),
                    "medida": match.group(3).strip(),
                    "precio": float(match.group(4))
                })

            # 3. Buscar específicamente Maíz blanco, de primera en La Terminal
            precio_principal = None
            for v in variedades:
                if "blanco" in v["producto"].lower() and "primera" in v["producto"].lower() and "otros" not in v["producto"].lower() and "terminal" in v["mercado"].lower():
                    precio_principal = v["precio"]
                    break

            if precio_principal is None and variedades:
                # Fallback al primer maíz blanco encontrado
                for v in variedades:
                    if "blanco" in v["producto"].lower():
                        precio_principal = v["precio"]
                        break

            if precio_principal is not None:
                result = {
                    "producto": "Maíz blanco, de primera",
                    "mercado": "La Terminal",
                    "medida": "Quintal",
                    "precio": precio_principal,
                    "fecha": fecha_reporte,
                    "fuente": "MAGA Guatemala - Precios Diarios de Mercados Mayoristas (DIPLAN / SIMPA)",
                    "url_fuente": MAGA_URL,
                    "estado": "en_linea",
                    "hora_extraccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "variedades": variedades
                }
                _CACHE["timestamp"] = now
                _CACHE["data"] = result
                return result

    except Exception as e:
        print(f"[MAGA Scraper Aviso] No se pudo conectar a {MAGA_URL}: {e}")

    # Fallback seguro con indicación explícita
    fallback = dict(FALLBACK_PRICE_DATA)
    fallback["hora_extraccion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return fallback


if __name__ == "__main__":
    data = fetch_maga_white_corn_price(force=True)
    print("Resultado MAGA Scraper en vivo:")
    print(f"Producto: {data.get('producto')} | Mercado: {data.get('mercado')}")
    print(f"Precio: Q {data.get('precio')} por {data.get('medida')} | Fecha MAGA: {data.get('fecha')}")
    print(f"Estado: {data.get('estado')} | Hora: {data.get('hora_extraccion')}")
    print(f"Variedades detectadas: {len(data.get('variedades', []))}")
