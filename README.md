# Sistema Abierto de Viabilidad Agrícola y Proyección Agrometeorológica (Maíz - Jutiapa)

Plataforma agrometeorológica y de proyección financiera para la evaluación de viabilidad de siembra de maíz en **Calderas, San José Acatempa, Jutiapa (Guatemala)** y regiones del Corredor Seco oriental.

El sistema funciona como un **sistema abierto** (sin autenticación, sin contraseñas ni roles), activando el pipeline predictivo en tiempo real bajo demanda.

---

## 🌾 Características Principales

* **Descarga Automática por Coordenadas (Sin CSV manuales):**
  * Clima diario reanálisis ERA5 vía **Open-Meteo Archive API** (Precipitación, Evapotranspiración FAO-56 $ET_0$, Temperatura media).
  * Índices macroclimáticos ENSO (**MEI v2** y **Niño 3.4**) desde **NOAA Physical Sciences Laboratory (PSL)**.
* **Física de Suelos y Balance Hídrico (FAO-56):**
  * Estimación de capacidad de campo y marchitez permanente con pedotransferencia de **Saxton & Rawls (2006)**.
  * Modelo hidrológico tipo cubo (*bucket*) continuo y seguimiento de rachas secas (*dry spells*).
  * Simulación de ventana crítica (60 días) cuantificando estrés hídrico ($ET_a / ET_c$) y eventos de anegamiento.
* **Modelos Predictivos y Calibración Probabilística:**
  * Modelos de Gradient Boosting regularizado (**XGBoost**) y **Regresión Logística**.
  * Validación cruzada temporal out-of-fold agrupada por año completo (**GroupKFold**) para evitar fuga de información temporal.
  * Métricas de desempeño: Área bajo la curva ROC (**AUC**) y **Brier Skill Score (BSS)** frente a la climatología local.
  * Calibración sigmoidea de probabilidades con `CalibratedClassifierCV`.
* **Semáforo Agronómico de Colores (RF-03):**
  * 🟢 **Verde (Óptimo, $\ge 60\%$):** Proceder con la siembra.
  * 🟡 **Amarillo (Alerta / Condicionado, $35\% - 59\%$):** Variedades precoces, labranza de conservación.
  * 🔴 **Rojo (No Sembrar, $< 35\%$):** Alto riesgo de fracaso hídrico.
* **Modelado Geométrico del Terreno (RF-05):**
  * Conversión de dimensiones métricas a metros cuadrados ($m^2$), manzanas ($mz$) y hectáreas ($ha$).
  * Generación de plano esquemático a escala con cotas y orientación cardinal.
* **Recomendación de Densidad de Siembra (RF-06):**
  * Cálculo de plantas por $m^2$ y por manzana ajustado al nivel de riesgo hídrico.
  * Cálculo de semilla comercial requerida (en bolsas o libras) y distanciamiento entre surcos y posturas.
* **Proyección Financiera y Tabla P&L (RF-07):**
  * Estimación de rendimiento en quintales ($qq$) y costos operativos desglosados.
  * Precios oficiales actualizados del **MAGA (DIPLAN / SIMPA)** con fecha de corte explícita.
  * Cálculo de Utilidad Neta, ROI (\%), Relación Beneficio/Costo y Punto de Equilibrio.
  * Evaluación de suficiencia de capital y análisis de sensibilidad de escenarios.
* **Exportación de Informes en PDF (RF-08):**
  * Generación de reporte formal con márgenes estándar y distribución ordenada.

---

## 📁 Estructura del Proyecto

```text
analizador/
├── DERCAS.md                     # Documento de Especificaciones y Criterios de Aceptación
├── README.md                     # Guía de instalación y uso
├── requirements.txt              # Dependencias de Python
├── main.py                       # CLI interactivo y ejecutable principal
├── pipeline.py                   # Orquestador del pipeline agrometeorológico
├── config/
│   ├── __init__.py
│   └── settings.py               # Configuraciones tipadas (Geo, Suelo, Agro, Precios MAGA)
├── core/
│   ├── __init__.py
│   ├── data_fetcher.py           # Descarga ERA5 y NOAA PSL con caché local y reintentos
│   ├── soil_balance.py           # Física de suelos Saxton & Rawls y balance FAO-56
│   ├── models.py                 # XGBoost, Logit, CV por años, calibración y semáforo
│   └── agronomy_economics.py     # Terreno (RF-05), Densidad (RF-06), Finanzas MAGA (RF-07)
├── front/
│   └── skills/
│       └── frontend-design/      # Guía y lineamientos de diseño visual e identidad moderna
│           └── SKILL.md
└── reporting/
    ├── __init__.py
    ├── visualizer.py             # Gráficos de balance hídrico, plano y calibración
    └── pdf_exporter.py           # Generación de informe PDF maquetado (RF-08)
```

---

## 🚀 Instalación y Requisitos

1. Asegúrate de tener Python 3.10 o superior instalado.
2. Clona o descarga el repositorio y crea un entorno virtual (opcional pero recomendado):

```bash
python -m venv .venv
# En Windows (PowerShell):
.venv\Scripts\Activate.ps1
# En Linux/macOS:
source .venv/bin/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

---

## 💻 Uso del Sistema

### Ejecución Básica (Valores por defecto para Calderas, Jutiapa)
```bash
python main.py
```

### Ejecución Personalizada con Parámetros Específicos
```bash
python main.py --date 2026-06-01 --lat 14.267 --lon -90.133 --width 100 --length 70 --capital 6500 --corn-type blanco
```

### Parámetros Disponibles:
* `--date`: Fecha tentativa de siembra en formato `AAAA-MM-DD` (ej. `2026-06-01`).
* `--lat`: Latitud geográfica de la parcela (por defecto: `14.267`).
* `--lon`: Longitud geográfica de la parcela (por defecto: `-90.133`).
* `--width`: Ancho del terreno en metros (por defecto: `100.0`).
* `--length`: Largo del terreno en metros (por defecto: `70.0`).
* `--capital`: Capital disponible para la siembra en Quetzales (por defecto: `6500.0`).
* `--corn-type`: Variedad de maíz (`blanco` o `amarillo`).
* `--force-refresh`: Fuerza la descarga de datos desde Open-Meteo y NOAA ignorando la caché.
* `--no-pdf`: Omite la generación del archivo PDF.

---

## 📊 Documentos de Especificación

Para consultar los requerimientos funcionales (RF-01 al RF-08), los requerimientos no funcionales (RNF-01 al RNF-04), y las matrices de trazabilidad, consulta el archivo [DERCAS.md](file:///c:/Users/gimen/Downloads/analizador/DERCAS.md).
