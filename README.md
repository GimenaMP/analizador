# AGRO-JUTIAPA: Sistema Abierto de Viabilidad Agrícola y Proyección Agrometeorológica

Plataforma agrometeorológica y de proyección financiera para la evaluación probabilística de viabilidad en la siembra de **Maíz Blanco de Primera** en **Calderas, San José Acatempa, Jutiapa (Guatemala)** y regiones vulnerables del Corredor Seco oriental.

El sistema opera bajo un modelo de **acceso abierto y universal** (sin requerir autenticación, contraseñas ni roles), activando el motor predictivo y calculando dinámicamente todos los balances hídricos y estados financieros en tiempo real ante cada consulta del productor.

---

## 🌾 Características Principales

* **Ingesta Meteorológica Automatizada (1981 - Presente):**
  * Clima diario de reanálisis satelital **ERA5** vía **Open-Meteo Archive API** (Precipitación diaria acumulada, Evapotranspiración de referencia Penman-Monteith $ET_0$, Temperatura media a 2m).
  * Índices macroclimáticos globales ENSO (**MEI v2** y **Niño 3.4**) descargados directamente desde **NOAA Physical Sciences Laboratory (PSL)**.
  * Sistema de caché local (`.cache/`) y memoria en ejecución con reintentos exponenciales (*exponential backoff*).
* **Física de Suelos y Balance Hídrico Continuo (FAO-56):**
  * Estimación de capacidad de campo ($\theta_{FC}$), punto de marchitez ($\theta_{WP}$), agua total disponible ($TAW$) y agua fácilmente aprovechable ($RAW$) mediante ecuaciones de pedotransferencia de **Saxton & Rawls (2006)** calibradas para el perfil edáfico de Jutiapa (26% Arcilla, 52% Arena, 1.8% Materia Orgánica).
  * Simulación continua tipo cubo (*bucket*) con seguimiento diario de estrés hídrico ($K_s$), evapotranspiración real ($ET_a$) y detección de anegamiento radicular.
* **Análisis de Rachas y Distribución Fenológica (120 Días):**
  * Monitoreo especializado a lo largo de las 4 etapas del maíz:
    1. *Germinación y Emergencia (Días 1–15)*
    2. *Desarrollo Vegetativo (Días 16–55)*
    3. *Floración y Polinización [Fase Crítica] (Días 56–75)*
    4. *Llenado de Grano y Maduración (Días 76–120)*
  * Detección algorítmica de la **Canícula** (sequía intraestival típica de julio y agosto) y evaluación de riesgos de asfixia o desecación de polen.
* **Aprendizaje Automático y Calibración Probabilística:**
  * Modelos supervisados basados en **XGBoost 3.4** (con algoritmo `hist` y regularización L1/L2) y **Regresión Logística**.
  * Validación cruzada temporal out-of-fold agrupada por año completo (**GroupKFold**) para garantizar evaluación sin fuga de información temporal (*no temporal leakage*).
  * Métricas: Área bajo la curva ROC (**ROC-AUC**) y **Brier Skill Score (BSS)** frente a la climatología local.
  * Calibración sigmoidea de probabilidades mediante **CalibratedClassifierCV**.
* **Semáforo Agronómico Tri-Color:**
  * 🟢 **Verde (Siembra Recomendada, $\ge 60\%$):** Régimen hídrico favorable para alcanzar el potencial productivo.
  * 🟡 **Amarillo (Siembra Condicionada / Alerta, $35\% - 59\%$):** Riesgo moderado; se recomienda empleo de variedades precoces y coberturas para retención de humedad.
  * 🔴 **Rojo (No Se Recomienda Sembrar, $< 35\%$):** Alta probabilidad de estrés hídrico severo o pérdidas agronómicas.
* **Modelado Geométrico de Parcelas Agrícolas (CAD en Canvas):**
  * Soporte para parcelas rectangulares, triangulares (fórmula de Herón) y cuadriláteros irregulares de 4 lados desiguales (agrimensura de campo guatemalteca).
  * Cálculo instantáneo de superficie en metros cuadrados ($m^2$), manzanas ($mz$, donde $1\ mz = 7,000\ m^2$) y hectáreas ($ha$).
* **Densidad de Siembra Dinámica y Cálculo de Semilla:**
  * Población vegetal recomendada ajustada al riesgo hídrico ($5.8$, $4.4$ o $3.6\text{ plantas}/m^2$).
  * Requerimiento total de semilla comercial considerando 88% de poder germinativo y 92% de supervivencia en campo, desglosado en bolsas de 60,000 semillas y libras.
* **Proyección Financiera con Precios Oficiales del MAGA:**
  * Estado de Pérdidas y Ganancias (P&L) dinámico calculado sobre el capital propio aportado por el productor.
  * Scraper automatizado en tiempo real de precios mayoristas de Maíz Blanco de primera en el Mercado La Terminal (Ciudad de Guatemala), con fecha de actualización explícita.
  * Indicadores financieros clave: Ingreso Bruto, Utilidad Neta, Retorno sobre la Inversión (ROI), Punto de Equilibrio en quintales e Inversión por quintal producido.
  * Matriz de análisis de sensibilidad (Escenario Optimista +15%, Proyectado y Pesimista -55%).
* **Generación y Previsualización de Dictamen Oficial en PDF:**
  * Visor interactivo integrado en el navegador para revisar el dictamen antes de descargarlo.
  * Exportación estructurada en 3 páginas formato Carta con márgenes estandarizados y renderizado de alta resolución, evitando solapamiento de textos o cortes abruptos.
* **Seguridad y Hardening de Entradas:**
  * Módulo de sanitización contra inyecciones SQL, XSS y manipulación de rutas (*Path Traversal*).
  * Restricción geográfica estricta a la caja envolvente de Calderas, San José Acatempa, Jutiapa.

---

## 📁 Estructura del Código Fuente

```text
analizador/
├── DERCAS.md                     # Documento de Especificaciones y Requerimientos de Software
├── DOCUMENTACION_TECNICA.md      # Manual de Arquitectura de Software y Referencia Técnica
├── README.md                     # Guía de instalación, uso y documentación general
├── requirements.txt              # Dependencias de Python del proyecto
├── package.json                  # Dependencias y scripts de Node.js (Vercel)
├── vercel.json                   # Configuración de despliegue Serverless en Vercel
├── main.py                       # Interfaz de línea de comandos (CLI) interactiva
├── pipeline.py                   # Orquestador del pipeline agrometeorológico y financiero
├── server.py                     # Servidor HTTP multihilo local en Python
│
├── api/                          # Endpoints Serverless (Node.js para Vercel)
│   ├── analyze.js                # API REST /api/analyze (Inferencia, física y finanzas)
│   └── maga-price.js             # API REST /api/maga-price (Scraper en tiempo real MAGA)
│
├── config/                       # Módulos de configuración global
│   ├── __init__.py
│   └── settings.py               # Dataclasses tipadas (Geo, Suelo, Clima, Precios MAGA)
│
├── core/                         # Motor analítico, hidrológico y matemático
│   ├── __init__.py
│   ├── input_validator.py        # Validación y sanitización estricta de entradas (Hardening)
│   ├── data_fetcher.py           # Descarga de ERA5 (Open-Meteo) y NOAA PSL con caché
│   ├── soil_balance.py           # Física de suelos (Saxton & Rawls) y balance hídrico (FAO-56)
│   ├── rain_streak_analyzer.py   # Análisis de rachas por etapas fenológicas y canícula
│   ├── models.py                 # Ensamble XGBoost/Logit, CV por años y calibración
│   ├── agronomy_economics.py     # Geometría del terreno, densidad de siembra y finanzas
│   └── maga_scraper.py           # Extractor de precios mayoristas oficiales del MAGA
│
├── front/                        # Interfaz Web de Usuario (SPA Moderna)
│   ├── index.html                # Estructura semántica, calculadora y visor de PDF
│   ├── css/
│   │   └── style.css             # Estilos de diseño editorial, glassmorphism y modo móvil
│   ├── js/
│   │   ├── app.js                # Orquestador de eventos, cálculos reactivos y PDF
│   │   ├── charts.js             # Gráficos dinámicos de balance hídrico (Chart.js)
│   │   ├── terrain.js            # Motor vectorial CAD para parcelas (HTML5 Canvas)
│   │   └── vendor/
│   │       └── html2pdf.bundle.min.js # Motor de renderizado PDF local
│   ├── fonts/                    # Tipografías vectoriales locales
│   └── img/                      # Fotografías optimizadas de parcelas en Jutiapa
│
└── reporting/                    # Motor de generación de reportes del backend
    ├── __init__.py
    ├── visualizer.py             # Generación de planos y curvas de balance (Matplotlib)
    └── pdf_exporter.py           # Generador de dictamen técnico oficial (ReportLab)
```

---

## 🚀 Instalación y Requisitos

### Requisitos Previos
* **Python 3.10 o superior** (para ejecución del motor Python, CLI o servidor local multihilo).
* **Node.js 18 o superior** (opcional, únicamente si se desea desplegar con Vercel Serverless).

### 1. Clonar el Repositorio y Crear Entorno Virtual
```bash
# En Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1

# En Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar Dependencias de Python
```bash
pip install -r requirements.txt
```

---

## 💻 Modos de Ejecución

El sistema ofrece tres modalidades de ejecución:

### 1. Servidor Web Local Multihilo (Recomendado para Producción Local)
Inicia el servidor HTTP multihilo que sirve la interfaz web y la API REST en el puerto 8000:
```bash
python server.py 8000
```
Abre tu navegador en: [http://localhost:8000](http://localhost:8000).

### 2. Interfaz de Línea de Comandos (CLI Headless)
Permite realizar análisis automatizados y generar informes directamente desde la terminal:

```bash
# Ejecución con parámetros por defecto (Calderas, Jutiapa):
python main.py

# Ejecución con parámetros personalizados:
python main.py --date 2026-06-01 --lat 14.267 --lon -90.133 --width 100 --length 70 --capital 7200 --corn-type blanco
```

#### Parámetros Disponibles en el CLI:
* `--date`: Fecha tentativa de siembra en formato `AAAA-MM-DD` (ej. `2026-06-01`).
* `--lat`: Latitud geográfica de la parcela (Rango permitido: `14.240` a `14.290`).
* `--lon`: Longitud geográfica de la parcela (Rango permitido: `-90.160` a `-90.110`).
* `--width`: Ancho de la parcela en metros (por defecto: `100.0`).
* `--length`: Largo de la parcela en metros (por defecto: `70.0`).
* `--capital`: Capital de inversión propio aportado en Quetzales (por defecto: `7200.0`).
* `--corn-type`: Tipo de maíz (`blanco`).
* `--force-refresh`: Fuerza la descarga de datos desde Open-Meteo y NOAA ignorando la caché local.
* `--no-pdf`: Omite la generación del archivo PDF físico en la carpeta `output/`.

### 3. Despliegue Serverless en Vercel
El repositorio incluye los endpoints en `api/` y la configuración `vercel.json` listos para ser desplegados con un clic mediante:
```bash
npx vercel
```

---

## 🌐 Endpoints de la API REST

### `POST /api/analyze`
Ejecuta el análisis agrometeorológico, balance hídrico, geometría de la parcela y estado financiero.
* **Payload de Entrada (JSON):**
```json
{
  "date": "2026-06-01",
  "lat": 14.267,
  "lon": -90.133,
  "shape_type": "cuadrilatero",
  "sides": [100.0, 70.0, 90.0, 65.0],
  "capital": 7200.0,
  "corn_type": "blanco"
}
```
* **Respuesta Exitosa (JSON):**
Contiene la probabilidad calibrada, clasificación del semáforo, fase ENSO, geometría del terreno ($m^2, mz, ha$), recomendaciones de densidad, estado P&L detallado, análisis de sensibilidad, serie temporal del balance hídrico y reporte fenológico de rachas.

### `GET /api/maga-price`
Retorna el precio mayorista del maíz blanco de primera obtenido en tiempo real desde el portal oficial del MAGA.
* **Respuesta de Ejemplo (JSON):**
```json
{
  "producto": "Maíz blanco, de primera",
  "mercado": "La Terminal",
  "medida": "Quintal",
  "precio": 235.0,
  "fecha": "09/10/2026",
  "fuente": "MAGA Guatemala - Precios Diarios de Mercados Mayoristas",
  "estado": "en_linea"
}
```

---

## 📚 Documentación Técnica Detallada

Para consultar la fundamentación matemática completa, las ecuaciones de Saxton & Rawls, la arquitectura de capas, el diseño del validador de entradas y las especificaciones de software, consulte:
* [DOCUMENTACION_TECNICA.md](file:///c:/Users/gimen/Downloads/analizador/DOCUMENTACION_TECNICA.md): Manual técnico exhaustivo de la arquitectura de software.
* [DERCAS.md](file:///c:/Users/gimen/Downloads/analizador/DERCAS.md): Documento de Requerimientos y Criterios de Aceptación.

---

## 🏛️ Fuentes y Referencias Oficiales

1. **ERA5 Reanalysis:** ECMWF / Copernicus Climate Change Service vía [Open-Meteo](https://open-meteo.com/).
2. **Índices ENSO:** NOAA Physical Sciences Laboratory ([PSL NOAA](https://psl.noaa.gov/)).
3. **Precios Mayoristas:** Ministerio de Agricultura, Ganadería y Alimentación de Guatemala ([MAGA DIPLAN](https://precios.maga.gob.gt/diarios/diarios.html)).
4. **Física de Suelos:** Saxton, K. E., & Rawls, W. J. (2006). *Soil Water Characteristic Estimates*. SSSAJ.
5. **Balance Hídrico:** Allen et al. (1998). *Crop Evapotranspiration*. FAO Irrigation and Drainage Paper No. 56.
