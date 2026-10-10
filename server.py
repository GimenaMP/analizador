"""
Servidor Web Multihilo para el Sistema Abierto de Viabilidad Agrícola.
Sirve los archivos estáticos de front/ y proporciona la API REST /api/analyze
conectada directamente con el pipeline agrometeorológico y financiero de Python.
Soporta parcelas irregulares, inversión directa del productor y series reales de lluvia.
"""
import json
import mimetypes
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path

# Directorios base
BASE_DIR = Path(__file__).resolve().parent
FRONT_DIR = BASE_DIR / "front"
OUTPUT_DIR = BASE_DIR / "output"

# Asegurar importación de pipeline
sys.path.insert(0, str(BASE_DIR))

try:
    from pipeline import AgroViabilityPipeline
    PIPELINE_INSTANCE = AgroViabilityPipeline()
except Exception as e:
    print(f"[Aviso] No se pudo inicializar AgroViabilityPipeline al inicio: {e}")
    PIPELINE_INSTANCE = None


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP multihilo para atender solicitudes concurrentes sin bloqueos."""
    daemon_threads = True


class AgroServerHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        """Mapea rutas URL a archivos locales de front/ o output/."""
        clean_path = path.split("?")[0].split("#")[0]
        
        if clean_path.startswith("/output/"):
            rel_path = clean_path.replace("/output/", "", 1)
            return str(OUTPUT_DIR / rel_path)
            
        rel_path = clean_path.lstrip("/")
        if not rel_path or rel_path == "":
            return str(FRONT_DIR / "index.html")
            
        target = FRONT_DIR / rel_path
        if target.exists():
            return str(target)
            
        return str(FRONT_DIR / rel_path)

    def do_GET(self):
        """Maneja peticiones GET a la API y archivos estáticos."""
        if self.path.startswith("/api/maga-price"):
            try:
                from core.maga_scraper import fetch_maga_white_corn_price
                data = fetch_maga_white_corn_price()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        """Maneja llamadas a la API agrometeorológica y financiera."""
        if self.path == "/api/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            
            try:
                params = json.loads(body)
                sowing_date = params.get("date", "2026-06-01")
                lat = float(params.get("lat", 14.267))
                lon = float(params.get("lon", -90.133))
                
                # Geometría del terreno (regular o irregular)
                shape_type = params.get("shape_type", "rectangulo")
                sides = params.get("sides")
                if sides and isinstance(sides, list):
                    sides = [float(s) for s in sides]
                width = float(params.get("width", 100))
                length = float(params.get("length", 70))
                
                # Inversión aportada directamente por el usuario
                capital = float(params.get("capital", 6500))
                corn_type = params.get("corn_type", "blanco")

                print(f"[API] Ejecutando análisis para {sowing_date} en ({lat}, {lon}) | Forma: {shape_type} | Capital: Q{capital:,.2f}...")

                global PIPELINE_INSTANCE
                if PIPELINE_INSTANCE is None:
                    PIPELINE_INSTANCE = AgroViabilityPipeline()

                res = PIPELINE_INSTANCE.run(
                    sowing_date_str=sowing_date,
                    lat=lat,
                    lon=lon,
                    shape_type=shape_type,
                    terrain_sides=sides,
                    terrain_width_m=width,
                    terrain_length_m=length,
                    capital_disponible_q=capital,
                    tipo_maiz=corn_type,
                    use_cache=True,
                    generate_pdf=True
                )

                t = res.terreno
                response_data = {
                    "success": True,
                    "sowing_date": res.sowing_date,
                    "lat": res.lat,
                    "lon": res.lon,
                    "probabilidad": res.probabilidad,
                    "semaforo_estado": res.semaforo_estado,
                    "semaforo_color": res.semaforo_color,
                    "semaforo_accion": res.semaforo_accion,
                    "fase_enso": res.fase_enso,
                    "terreno": {
                        "forma": t.descripcion_forma,
                        "shape_type": t.shape_type,
                        "sides": t.sides,
                        "vertices": t.get_polygon_vertices(),
                        "ancho_m": t.ancho_m,
                        "largo_m": t.largo_m,
                        "area_m2": t.area_m2,
                        "manzanas": t.manzanas,
                        "hectareas": t.hectareas,
                        "perimetro_m": t.perimetro_m,
                    },
                    "densidad": res.densidad,
                    "financiero": res.financiero,
                    "timeline": res.timeline,
                    "proyecciones_futuras": res.proyecciones_futuras,
                    "criterios_algoritmo": res.criterios_algoritmo,
                    "evaluacion_historica": res.evaluacion_historica,
                    "report_pdf_path": os.path.basename(res.report_pdf_path) if res.report_pdf_path else None
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response_data, default=str).encode("utf-8"))

            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[API Error] {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}, default=str).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        """Soporte para preflight CORS."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# Exportaciones de nivel superior para compatibilidad con Vercel Serverless
handler = AgroServerHandler
app = AgroServerHandler


def run_server(port=8000):
    server_address = ("", port)
    httpd = ThreadedHTTPServer(server_address, AgroServerHandler)
    print(f"\n==================================================================")
    print(f"  SERVIDOR AGRO-JUTIAPA ACTIVO (Multihilo)")
    print(f"  Accede en tu navegador a: http://localhost:{port}")
    print(f"==================================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
