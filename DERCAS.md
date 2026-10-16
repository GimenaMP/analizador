# DERCAS: Documento de Especificaciones, Requerimientos y Criterios de Aceptación
## Sistema Abierto de Viabilidad Agrícola y Proyección Agrometeorológica para Cultivo de Maíz (Jutiapa, Guatemala)

**Versión:** 2.5.0  
**Fecha:** Octubre 2026  
**Ámbito Geográfico Exclusivo:** Calderas, San José Acatempa, Jutiapa (Guatemala) [Lat: 14.240° a 14.290° N, Lon: -90.160° a -90.110° W]  
**Modalidad de Acceso:** Sistema Abierto (Público, sin autenticación ni gestión de credenciales)  
**Arquitectura de Ejecución:** Dual Runtime (Servidor Python Multihilo Local / Serverless Vercel en Node.js)

---

## 1. Introducción y Visión General

El presente documento describe formalmente las especificaciones de software, requerimientos funcionales (RF), requerimientos no funcionales (RNF), criterios de aceptación y matrices de trazabilidad para el **Sistema Abierto de Viabilidad Agrícola y Proyección Agrometeorológica**.

El sistema fue diseñado para mitigar el alto riesgo agroclimático característico del Corredor Seco oriental de Guatemala —específicamente en la micro-región de Calderas, San José Acatempa, Jutiapa—, en donde la variabilidad intraestival de las lluvias, las canículas prolongadas y los episodios ENSO (El Niño / La Niña) comprometen sistemáticamente la producción de granos básicos.

### Principios Arquitectónicos Fundamentales
1. **Acceso Abierto Universal:** Cero barreras de autenticación, sin contraseñas, roles de usuario ni persistencia de datos sensibles. Orientado a pequeños productores, extensionistas rurales y cooperativas.
2. **Cómputo Dinámico en Tiempo Real:** Todos los valores numéricos, proyecciones de rendimiento, balances hídricos, densidades y tablas financieras se calculan en tiempo de ejecución a partir de las entradas proporcionadas por el usuario. No se emplean plantillas con valores estáticos simulados.
3. **Rigurosidad Científica y Datos Reales:** Ingesta directa de reanálisis satelital ERA5 (Open-Meteo), series macroclimáticas de NOAA Physical Sciences Laboratory, física de suelos calibrada (Saxton & Rawls, 2006), balance hídrico continuo (FAO-56) y precios oficiales mayoristas del Ministerio de Agricultura, Ganadería y Alimentación (MAGA).
4. **Seguridad y Hardening de Entradas:** Validación estricta y sanitización de tipos, rangos de coordenadas, linderos de terreno y montos de capital, protegiendo al sistema contra inyecciones SQL, XSS, Path Traversal y ataques por denegación de servicio (DoS).

---

## 2. Requerimientos Funcionales (RF)

### RF-01: Selección y Validación de Fecha Tentativa de Siembra
* **Descripción:** El sistema debe proporcionar una interfaz con selector de fecha que permita establecer la fecha tentativa de siembra del cultivo de maíz, validando su correspondencia con los ciclos agrícolas de la región.
* **Detalle Técnico:**
  * Componente de fecha con validación en cliente y servidor en formato `AAAA-MM-DD`.
  * Verificación contra el calendario agronómico de Jutiapa:
    * **Época de Primera:** Mayo a Julio (siembras habituales con el inicio de la temporada de lluvias).
    * **Época de Postrera:** Agosto a Octubre (aprovechamiento de las lluvias tardías previas a la estación seca).
    * **Época Marginal / No Recomendada:** Noviembre a Abril (estación seca en el Corredor Seco).
  * Límite de ventana de predicción: Rango temporal calibrado entre 1981 (inicio de reanálisis ERA5) y el horizonte agrícola vigente (2026/2030).
* **Criterios de Aceptación:**
  * CA-01.1: El usuario puede seleccionar libremente la fecha dentro del rango admitido sin requerir inicio de sesión.
  * CA-01.2: El sistema clasifica y muestra automáticamente la etiqueta de época ("Época de Primera", "Época de Postrera" o "Fuera de Temporada").
  * CA-01.3: Cualquier cadena no conforme al formato de fecha estándar o con caracteres no numéricos es rechazada por el validador de entradas.

---

### RF-02: Activación Dinámica del Pipeline Agrometeorológico
* **Descripción:** Cada solicitud del usuario debe activar en tiempo real el pipeline agrometeorológico integral, descargando o recuperando de caché los datos climáticos diarios ERA5 y los índices ENSO globales para las coordenadas del predio.
* **Detalle Técnico:**
  * Conexión con **Open-Meteo Archive API** (`https://archive-api.open-meteo.com/v1/archive`) y **Open-Meteo Forecast API** para la serie histórica continua de:
    * Precipitación diaria acumulada ($mm$)
    * Evapotranspiración de referencia Penman-Monteith ($ET_0$, $mm$)
    * Temperatura media diaria a 2 metros (°C)
  * Descarga y parseo de anomalías oceánicas y atmosféricas desde **NOAA PSL**:
    * Índice Multivariado ENSO (**MEI v2**): `meiv2.data`
    * Índice de Anomalías de Temperatura Superficial del Mar (**Niño 3.4**): `nino34.long.anom.data`
  * Mecanismo de persistencia local en caché (`.cache/`) y memoria en ejecución con TTL para optimizar la latencia y respetar las cuotas de tasa de las APIs externas.
  * Algoritmo de reintentos con retroceso exponencial (*exponential backoff*) ante códigos HTTP 429 o latencias elevadas.
* **Criterios de Aceptación:**
  * CA-02.1: El pipeline orquesta secuencialmente: Validación $\rightarrow$ Descarga/Caché $\rightarrow$ Física de Suelos $\rightarrow$ Inferencia ML $\rightarrow$ Geometría $\rightarrow$ Densidad $\rightarrow$ Finanzas $\rightarrow$ Rachas Fenológicas.
  * CA-02.2: Emisión continua de eventos de progreso para alimentar el indicador visual de 4 fases en la interfaz gráfica.

---

### RF-03: Semáforo Agronómico Predictivo y Calibración de Probabilidad
* **Descripción:** El sistema debe sintetizar el riesgo agroclimático de la siembra mediante un semáforo de 3 estados, calculado a partir de un ensamble de modelos de aprendizaje automático calibrados:
  * 🟢 **Verde (Siembra Recomendada / Óptimo):** Probabilidad calibrada $\ge 60\%$. Régimen hídrico suficiente para soportar la evapotranspiración del cultivo.
  * 🟡 **Amarillo (Siembra Condicionada / Alerta):** Probabilidad calibrada entre $35\%$ y $59\%$. Riesgo moderado de déficit hídrico o canícula; requiere variedades precoces y prácticas de retención de humedad.
  * 🔴 **Rojo (No Se Recomienda Sembrar / Alto Riesgo):** Probabilidad calibrada $< 35\%$. Elevado riesgo de pérdida total por estrés hídrico severo o anegamiento perjudicial.
* **Detalle Técnico:**
  * Modelado supervisado con **XGBoost 3.4** (`tree_method="hist"`, regularización L1 `reg_alpha=0.5`, regularización L2 `reg_lambda=5.0`) y **Regresión Logística Regularizada**.
  * Validación cruzada temporal sin fuga de información agrupada estrictamente por año agrícola (**GroupKFold**, $k=5$).
  * Calibración sigmoidea de probabilidades mediante **CalibratedClassifierCV** (método Platt / isotónico).
  * Evaluación con métricas probabilísticas rigurosas: **ROC-AUC** y **Brier Skill Score (BSS)** frente a la climatología histórica local.
* **Criterios de Aceptación:**
  * CA-03.1: Despliegue del porcentaje exacto de viabilidad hídrica ($0.0\%$ a $100.0\%$).
  * CA-03.2: Indicación de la fase climática ENSO activa (El Niño, La Niña o Neutro) y directiva agronómica accionable.

---

### RF-04: Balance Hídrico Diario y Análisis de Rachas Fenológicas
* **Descripción:** El sistema debe modelar la humedad del suelo día por día durante el ciclo vegetativo del maíz (120 días) y realizar un análisis pormenorizado de rachas consecutivas secas y lluviosas.
* **Detalle Técnico:**
  * **Balance Hídrico Continuo (FAO-56):**
    * Cálculo de evapotranspiración del cultivo: $ET_c(t) = K_c(t) \times ET_0(t)$ utilizando la curva de coeficientes fenológicos para maíz blanco ($K_{c,ini} = 0.40$, $K_{c,mid} = 1.20$, $K_{c,end} = 0.60$).
    * Factor de reducción por estrés hídrico $K_s(t)$ en función del agotamiento del agua fácilmente aprovechable ($RAW$).
    * Evapotranspiración real: $ET_a(t) = K_s(t) \times ET_c(t)$.
    * Relación estricta de viabilidad fenológica: $\frac{\sum ET_a}{\sum ET_c} \ge 0.90$.
  * **Análisis de Rachas por Etapas Fenológicas (`core/rain_streak_analyzer.py`):**
    * **Etapa 1: Germinación y Emergencia (Días 1–15):** Demanda 20–40 mm. Alerta por asfixia si ocurren $>5$ días consecutivos con $>15$ mm/día; alerta por fallo de germinación si ocurren $>7$ días con $<1.0$ mm/día.
    * **Etapa 2: Desarrollo Vegetativo (Días 16–55):** Demanda 150–250 mm. Alerta por estrés si ocurren $>10$ días secos ($<1.5$ mm) o detección de canícula temprana.
    * **Etapa 3: Floración y Polinización [Fase Crítica] (Días 56–75):** Demanda 80–120 mm ($7-10$ mm/día). Fallo letal por desecación de estigmas si ocurren $>4$ días con $<2.0$ mm/día; lavado de polen si ocurren $>6$ días con $>25$ mm/día.
    * **Etapa 4: Llenado de Grano y Maduración (Días 76–120):** Demanda 150–250 mm. Riesgo de aborto de grano si ocurren $>6$ días secos en días 76–95; riesgo de pudrición de mazorca si ocurren $>10$ días con $>15$ mm.
* **Criterios de Aceptación:**
  * CA-04.1: Gráfica interactiva con curva de reservas de suelo ($s / TAW$), precipitación diaria ($mm$) y umbral de capacidad de campo.
  * CA-04.2: Resumen fenológico con cómputo de la racha seca más larga, racha húmeda más larga y diagnóstico de canícula.

---

### RF-05: Modelado Geométrico de Parcelas Agrícolas
* **Descripción:** El sistema debe permitir el ingreso y renderizado vectorial de parcelas agrícolas con diversas geometrías (regulares e irregulares), calculando automáticamente el perímetro y la superficie exacta.
* **Detalle Técnico:**
  * **Topologías Soportadas:**
    1. **Rectángulo:** Parámetros de ancho ($m$) y largo ($m$). Área: $A = w \times l$.
    2. **Cuadrilátero Irregular (4 lados desiguales: Norte, Este, Sur, Oeste):** Agrimensura de campo utilizada por extensionistas: Área mediante el producto de semilados opuestos: $A = \left(\frac{a + c}{2}\right) \times \left(\frac{b + d}{2}\right)$.
    3. **Triángulo (3 linderos desiguales):** Fórmula de Herón con semiperímetro $s = \frac{a+b+c}{2}$: $A = \sqrt{s(s-a)(s-b)(s-c)}$. Validación estricta de la desigualdad triangular.
    4. **Polígonos Arbitrarios de $N$ Vértices:** Algoritmo del área de Gauss / Fórmula Shoelace.
  * **Conversión de Unidades Agrarias Oficiales:**
    * Metros cuadrados ($m^2$)
    * Manzanas ($mz$): En Guatemala, $1\text{ manzana} = 7,000.0\ m^2$ ($10,000\text{ varas}^2$).
    * Hectáreas ($ha$): $1\text{ hectárea} = 10,000.0\ m^2$.
* **Criterios de Aceptación:**
  * CA-05.1: Plano interactivo en tiempo real renderizado sobre HTML5 Canvas con cotas métricas, orientación cardinal (Rosa de los Vientos) y vértices escalados.
  * CA-05.2: Actualización instantánea en pantalla de $m^2$, $mz$ y perímetro al modificar cualquier lindero.

---

### RF-06: Determinación de Densidad de Siembra y Cálculo de Semilla
* **Descripción:** El sistema debe calcular la población vegetal óptima y los requerimientos de semilla comercial en función del área y del semáforo agroclimático.
* **Detalle Técnico:**
  * **Densidad Dinámica según Riesgo Hídrico:**
    * Escenario Favorable (Verde): $5.8\text{ plantas}/m^2$ ($40,600\text{ plantas}/mz$). Distanciamiento: $80\text{ cm}$ entre surcos $\times 22\text{ cm}$ entre posturas.
    * Escenario Moderado (Amarillo): $4.4\text{ plantas}/m^2$ ($30,800\text{ plantas}/mz$). Distanciamiento: $85\text{ cm}$ entre surcos $\times 27\text{ cm}$ entre posturas.
    * Escenario Severo (Rojo): $3.6\text{ plantas}/m^2$ ($25,200\text{ plantas}/mz$). Distanciamiento: $90\text{ cm}$ entre surcos $\times 31\text{ cm}$ entre posturas.
  * **Cálculo de Semilla Comercial Requerida:**
    * Corrección por poder germinativo ($88\%$) y supervivencia en campo ($92\%$): $\text{Semillas Totales} = \frac{\text{Plantas Totales}}{0.88 \times 0.92} \approx \text{Plantas Totales} \times 1.235$.
    * Conversión a bolsas comerciales ($60,000\text{ semillas/bolsa}$) y libras ($\approx 1,400\text{ semillas/lb}$).
* **Criterios de Aceptación:**
  * CA-06.1: Desglose claro de plantas totales, semillas requeridas, bolsas comerciales, libras y distanciamiento de siembra.

---

### RF-07: Proyección Financiera con Precios Mayoristas Oficiales del MAGA
* **Descripción:** El sistema debe calcular el Estado de Pérdidas y Ganancias (P&L) proyectado tomando directamente el capital de inversión propio aportado por el productor y el precio oficial diario del quintal de maíz blanco del MAGA.
* **Detalle Técnico:**
  * Ingesta de precios desde el Sistema de Información de Mercados de Productos Agrícolas (SIMPA / DIPLAN) del MAGA (`https://precios.maga.gob.gt/diarios/diarios.html` - Mercado La Terminal).
  * Scraping automatizado en tiempo real con respaldo de caché local (TTL 10 min) y precio base verificado de Q 235.00/quintal.
  * **Modelo de Rendimiento Ajustado:** Rendimiento base de $65.0\text{ qq}/mz$ ponderado por la viabilidad climática del modelo: $\text{Rendimiento} = 65.0 \times (0.40 + 0.60 \times P_{\text{calibrada}})$.
  * **Fórmulas Financieras Aplicadas:**
    * $\text{Producción Total (qq)} = \text{Rendimiento (qq/mz)} \times \text{Superficie (mz)}$
    * $\text{Ingreso Bruto (Q)} = \text{Producción Total (qq)} \times \text{Precio MAGA (Q/qq)}$
    * $\text{Utilidad Neta (Q)} = \text{Ingreso Bruto (Q)} - \text{Capital Invertido (Q)}$
    * $\text{ROI (\%)} = \left(\frac{\text{Utilidad Neta}}{\text{Capital Invertido}}\right) \times 100$
    * $\text{Punto de Equilibrio (qq)} = \frac{\text{Capital Invertido (Q)}}{\text{Precio MAGA (Q/qq)}}$
    * $\text{Inversión por Quintal (Q/qq)} = \frac{\text{Capital Invertido (Q)}}{\text{Producción Total (qq)}}$
  * **Matriz de Sensibilidad de Escenarios:**
    1. Escenario Optimista: Régimen pluvial favorable (+15% sobre rendimiento base).
    2. Escenario Proyectado: Resultado ponderado del modelo agrometeorológico.
    3. Escenario Pesimista: Déficit hídrico severo o canícula extendida (-55% de rendimiento).
* **Criterios de Aceptación:**
  * CA-07.1: Exposición visible de la fecha y fuente de los precios oficiales del MAGA.
  * CA-07.2: Todos los montos son calculados dinámicamente según el capital ingresado por el usuario.
  * CA-07.3: Si el capital ingresado se ubica fuera del rango histórico para Jutiapa (Q 2,000 a Q 25,000 por manzana), el sistema emite una advertencia de suficiencia de capital sin bloquear el cálculo.

---

### RF-08: Exportación e Inspección Previa de Informes Oficiales en PDF
* **Descripción:** El sistema debe incorporar un visor interactivo de vista previa del documento antes de la descarga y un motor de exportación a PDF en formato Carta de alta resolución, estructurado en 3 páginas limpias sin solapamiento de textos.
* **Detalle Técnico:**
  * **Arquitectura de Generación Dual:**
    * **Cliente (Front):** Renderizado DOM de alta resolución a PDF mediante `html2pdf.js` y `html2canvas` integrados localmente (`front/js/vendor/html2pdf.bundle.min.js`), operando a 800px de ancho estandarizado para garantizar compatibilidad con navegadores modernos y móviles.
    * **Servidor (CLI/API):** Generación vectorial con ReportLab (`reporting/pdf_exporter.py`).
  * **Estructura Oficial del Dictamen (3 Páginas Carta):**
    * **Página 1: Resumen Ejecutivo y Diagnóstico General:** Membrete oficial, fecha y coordenadas de Calderas, Jutiapa, dictamen de semáforo con probabilidad calibrada, fase ENSO, plano geométrico del lote y cotas métricas.
    * **Página 2: Comportamiento Hídrico y Dinámica Fenológica:** Balance diario suelo-planta (FAO-56), gráfica de precipitación acumulada vs $ET_c$, análisis de rachas secas/húmedas y evaluación de canícula.
    * **Página 3: Proyección Económica y Criterios Agronómicos:** Tabla P&L completa, cálculo de semilla y densidad, matriz de sensibilidad, sello de tiempo de precios MAGA, firmas técnicas y advertencias de responsabilidad.
* **Criterios de Aceptación:**
  * CA-08.1: Visor de vista previa interactivo disponible en la parte inferior de los resultados con botón de descarga directa.
  * CA-08.2: Ausencia de cortes de página irregulares, textos encimados o desbordes en cualquier dispositivo.

---

### RF-09: Sanitización de Entradas y Blindaje contra Inyecciones (Hardening)
* **Descripción:** Todas las entradas provistas por el usuario deben ser rigurosamente verificadas y sanitizadas antes de procesarse en el backend o en el cliente.
* **Detalle Técnico:**
  * Implementación del módulo `core/input_validator.py` (`ValidatedInput`, `validate_and_sanitize`).
  * **Protecciones Activas:**
    * **Inyección XSS:** Eliminación de etiquetas `<script>`, `<iframe>`, manejadores `onload`/`onerror` y stripping HTML.
    * **Inyección SQL:** Filtrado de palabras clave reservadas (`SELECT`, `DROP`, `INSERT`, `DELETE`, `UPDATE`, `UNION`), secuencias de comentarios (`--`) y terminadores (`;`).
    * **Path Traversal:** Eliminación de secuencias `../`, `..\\`, `/` y `\\`.
    * **Límites de Longitud:** Restricción a un máximo de 100 caracteres por campo de texto y 10 KB para el cuerpo HTTP global.
    * **Filtro Geográfico Exclusivo:** Rechazo de cualquier coordenada fuera de la caja envolvente de Calderas, San José Acatempa, Jutiapa (Lat: 14.240 a 14.290, Lon: -90.160 a -90.110).
    * **Límites de Capital:** Aceptación únicamente de montos entre Q 500.00 y Q 150,000.00.
* **Criterios de Aceptación:**
  * CA-09.1: Cualquier payload malicioso genera una respuesta HTTP 400 con mensaje de error descriptivo sin revelar trazas de depuración del servidor.

---

## 3. Requerimientos No Funcionales (RNF)

### RNF-01: Arquitectura Abierta sin Autenticación
* **Descripción:** El sistema opera bajo un paradigma de acceso público y universal. No contiene formularios de registro, inicio de sesión, sesiones persistentes en base de datos ni gestión de roles.
* **Criterios:**
  * CA-RNF-01.1: Cero almacenamiento de identificadores personales del usuario.
  * CA-RNF-01.2: Acceso inmediato e irrestricto a todas las funcionalidades desde cualquier navegador.

### RNF-02: Diseño Visual de Alta Calidad y Experiencia Fluida
* **Descripción:** La interfaz implementa principios de diseño editorial moderno con estética inspirada en el cultivo de maíz y los paisajes de Jutiapa.
* **Criterios:**
  * Paleta cromática: Maíz dorado (`#F59E0B`), verde agrícola (`#10B981`, `#047857`), tierra fértil (`#78350F`) y fondos neutros cálidos con efecto glassmorphism translúcido.
  * Animaciones aceleradas por hardware vía `IntersectionObserver` y transiciones fluidas a 120 FPS, previniendo recálculos sincrónicos de diseño (*layout thrashing*).

### RNF-03: Adaptabilidad Total a Dispositivos Móviles (Mobile Native)
* **Descripción:** La plataforma debe operar de forma óptima en teléfonos inteligentes y tabletas sin distorsión de componentes ni desbordamientos horizontales.
* **Criterios:**
  * CA-RNF-03.1: Metadatos `viewport-fit=cover` e `interactive-widget=resizes-content` para soporte de teclado en pantalla.
  * CA-RNF-03.2: Campos con `inputmode="decimal"` y tamaño tipográfico $\ge 16\text{px}$ para evitar zoom automático en dispositivos iOS (Safari).
  * CA-RNF-03.3: Tablas financieras y de sensibilidad con desplazamiento horizontal contenido (`overflow-x: auto`).

### RNF-04: Rendimiento, Baja Latencia y Resiliencia
* **Descripción:** El pipeline debe optimizar la latencia mediante almacenamiento en caché y ejecución asíncrona.
* **Criterios:**
  * CA-RNF-04.1: Consultas climáticas y de precios en caché responden en menos de 2.0 segundos.
  * CA-RNF-04.2: En caso de indisponibilidad temporal del sitio del MAGA o de Open-Meteo, el sistema activa automáticamente mecanismos de respaldo (*fallback*) garantizando continuidad de servicio.

---

## 4. Matriz de Trazabilidad de Requerimientos

| Requerimiento | Componente Técnico Responsable | Entrada Principal | Salida / Artefacto Producido |
| :--- | :--- | :--- | :--- |
| **RF-01** | `front/js/app.js` + `core/input_validator.py` | Fecha de siembra (`AAAA-MM-DD`) | Fecha validada y época agrícola |
| **RF-02** | `core/data_fetcher.py` + `pipeline.py` | Coordenadas geográficas (`lat`, `lon`) | Clima diario ERA5 y series ENSO NOAA |
| **RF-03** | `core/models.py` | Variables fenológicas e índices macro | Semáforo (Verde/Amarillo/Rojo) y Probabilidad calibrada |
| **RF-04** | `core/soil_balance.py` + `core/rain_streak_analyzer.py` | Series pluviométricas y $ET_0$ | Curva de balance hídrico y reporte de rachas |
| **RF-05** | `core/agronomy_economics.py` + `front/js/terrain.js` | Dimensiones métricas y linderos | Superficie ($m^2, mz, ha$), perímetro y plano CAD |
| **RF-06** | `core/agronomy_economics.py` | Área calculada y estado de semáforo | Densidad de siembra, semillas, bolsas y distanciamientos |
| **RF-07** | `core/agronomy_economics.py` + `core/maga_scraper.py` | Capital invertido (Q) y precio MAGA | Estado de P&L, ROI, Punto de Equilibrio y Sensibilidad |
| **RF-08** | `front/js/vendor/html2pdf.bundle.min.js` + `reporting/` | Resultados integrales del análisis | Visor previo interactivo y archivo PDF oficial (3 págs.) |
| **RF-09** | `core/input_validator.py` | Petición HTTP cruda | Objeto `ValidatedInput` o excepción `ValidationError` |
| **RNF-01** | `server.py` / `api/analyze.js` | Peticiones HTTP | Ejecución directa sin sesión ni credenciales |
| **RNF-02** | `front/css/style.css` + `front/js/app.js` | Tokens visuales CSS | Interfaz moderna con animaciones de resorte fluidas |
| **RNF-03** | `front/index.html` + `front/css/style.css` | Dimensiones de pantalla | Diseño adaptativo con soporte táctil y anti-zoom móvil |
| **RNF-04** | `core/data_fetcher.py` + `.cache/` | Consultas recurrentes | Respuestas sub-segundo con persistencia en caché |

---

## 5. Fuentes de Datos Oficiales y Base Científica

1. **Reanálisis Climático Diario (1981 - Presente):**
   * ERA5 Reanalysis mediante [Open-Meteo Archive API](https://archive-api.open-meteo.com/v1/archive) y ECMWF Forecast.
2. **Índices Macroclimáticos Globales ENSO:**
   * Multivariate ENSO Index (**MEI v2**): [NOAA Physical Sciences Laboratory](https://psl.noaa.gov/data/correlation/meiv2.data).
   * Oceanic Niño Index (**Niño 3.4**): [NOAA PSL Monthly Long Time Series](https://psl.noaa.gov/data/timeseries/month/data/nino34.long.anom.data).
3. **Física de Suelos y Relaciones Hídricas:**
   * Saxton, K. E., & Rawls, W. J. (2006). *Soil Water Characteristic Estimates by Texture and Organic Matter for Hydrologic Solutions*. Soil Science Society of America Journal.
   * Parámetros texturales calibrados para Calderas, Jutiapa: 26% Arcilla, 52% Arena, 1.8% Materia Orgánica.
4. **Evapotranspiración y Demanda del Cultivo:**
   * Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration - Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56.
5. **Precios Oficiales del Mercado de Granos Básicos:**
   * Ministerio de Agricultura, Ganadería y Alimentación (MAGA) de Guatemala: Dirección de Planeamiento (DIPLAN) / Sistema de Información de Mercados de Productos Agrícolas (SIMPA).
   * Registro: Precios Diarios de Mercados Mayoristas (Mercado La Terminal, Ciudad de Guatemala - Maíz blanco, de primera).
