# DERCAS: Documento de Especificaciones, Requerimientos y Criterios de Aceptación
## Sistema Abierto de Viabilidad Agrícola y Proyección Agrometeorológica para Cultivo de Maíz (Jutiapa, Guatemala)

**Versión:** 2.0.0  
**Fecha:** Septiembre 2026  
**Ámbito Geográfico:** Calderas, San José Acatempa, Jutiapa (Guatemala) y zonas del Corredor Seco oriental  
**Modalidad de Acceso:** Sistema Abierto (Público, sin autenticación ni gestión de credenciales)

---

## 1. Introducción y Visión General

El presente documento describe los requerimientos funcionales y no funcionales para un sistema abierto de análisis agrometeorológico y proyección financiera enfocado en el cultivo de maíz en Jutiapa, Guatemala. 

Dado que opera como una plataforma de libre acceso orientada a productores agrícolas, técnicos de extensión rural, cooperativas y tomadores de decisión, **el sistema no cuenta con módulos de autenticación, control de usuarios, gestión de credenciales ni perfiles de administración**. Cualquier visitante puede ingresar de manera directa e inmediata a las herramientas de predicción, modelado de terreno y simulación económica.

El objetivo central es mitigar el riesgo climático asociado a la variabilidad de la precipitación, la canícula y los fenómenos ENSO (El Niño / La Niña) en el oriente de Guatemala, combinando reanálisis climático de alta resolución (ERA5 / Open-Meteo), física de suelos (Saxton & Rawls, 2006), balance hídrico fenológico (FAO-56), modelos de aprendizaje automático calibrados (XGBoost / Logistic Regression) y modelos económicos con precios de referencia del Ministerio de Agricultura, Ganadería y Alimentación (MAGA).

---

## 2. Requerimientos Funcionales (RF)

### RF-01: Selección de Fecha Tentativa de Siembra
* **Descripción:** El sistema debe proporcionar una interfaz moderna con un componente de calendario interactivo para que el usuario seleccione libremente la fecha tentativa de siembra.
* **Detalle Técnico:**
  * Debe permitir fechas históricas para validación/backtesting o fechas para el ciclo de siembra actual/próximo (ej. Mayo a Diciembre).
  * Validar si la fecha seleccionada cae dentro o fuera de la ventana agroclimática óptima de primera o postrera en Jutiapa.
* **Criterios de Aceptación:**
  * CA-01.1: El usuario puede seleccionar día, mes y año sin restricciones de sesión.
  * CA-01.2: El sistema notifica de forma informativa si la fecha seleccionada se ubica fuera del rango habitual de siembra (Mayo a Diciembre).

---

### RF-02: Activación Dinámica del Pipeline por Petición
* **Descripción:** Cada vez que el usuario realice una petición (ingresando coordenadas, dimensiones e indicando su fecha), el sistema debe activar en tiempo real el pipeline de machine learning. Esto comprende la descarga automática de datos meteorológicos ERA5 vía Open-Meteo Archive y los índices ENSO (MEI v2, Niño 3.4) desde NOAA PSL, ejecutando el preprocesamiento, el balance hídrico y la inferencia del modelo XGBoost.
* **Detalle Técnico:**
  * Conexión con Open-Meteo Archive API (`https://archive-api.open-meteo.com/v1/archive`) para variables diarias: `precipitation_sum`, `et0_fao_evapotranspiration`, `temperature_2m_mean`.
  * Descarga y parseo tabular de series mensuales NOAA PSL (`meiv2.data` y `nino34.long.anom.data`).
  * Mecanismo de persistencia/caché local para evitar sobrecargar las APIs externas y prevenir bloqueos por límite de peticiones (HTTP 429).
  * Ejecución de validación cruzada temporal (`GroupKFold` agrupado por año) y calibración de probabilidad mediante `CalibratedClassifierCV`.
* **Criterios de Aceptación:**
  * CA-02.1: El pipeline se ejecuta de forma reproducible a partir de las coordenadas geográficas ingresadas.
  * CA-02.2: Manejo de reintentos automáticos con retroceso exponencial (*exponential backoff*) ante fallas de red o límites de tasa.
  * CA-02.3: La salida incluye la probabilidad calibrada de viabilidad y métricas de desempeño ($AUC$, $Brier\ Skill\ Score$).

---

### RF-03: Gráfica de Probabilidad de Viabilidad por Semáforo de Colores
* **Descripción:** El sistema debe mostrar una representación gráfica basada en los resultados del modelo predictivo utilizando una escala de colores estricta:
  * **Rojo:** Probabilidad baja de éxito o alto riesgo de fracaso hídrico ($Probabilidad < 0.35$).
  * **Amarillo:** Probabilidad normal / moderada (riesgo moderado o alerta: $0.35 \le Probabilidad < 0.60$).
  * **Verde:** Probabilidad óptima y viable para proceder con la siembra ($Probabilidad \ge 0.60$).
* **Criterios de Aceptación:**
  * CA-03.1: Cada nivel del semáforo debe ir acompañado de una recomendación agronómica explícita (ej. uso de variedades precoces, labranza de conservación o postergación de siembra).
  * CA-03.2: Desplegar el estado del fenómeno ENSO (El Niño, La Niña, Neutral) correspondiente a la fecha de análisis.

---

### RF-04: Visualización del Comportamiento de Lluvias y Balance Hídrico
* **Descripción:** El sistema debe mostrar un gráfico dinámico del comportamiento de las precipitaciones y el balance hídrico, abarcando desde la fecha de siembra seleccionada por el usuario hasta la fecha estimada de finalización de la cosecha (ventana fenológica de 60 a 120 días).
* **Detalle Técnico:**
  * Representación de precipitación diaria ($mm$), evapotranspiración del cultivo ($ET_c = K_c \times ET_0$), fracción de agua disponible en el suelo ($s/TAW$) y ocurrencia de periodos secos (*dry spells*) o eventos de anegamiento ($s - TAW \ge 15\ mm$).
* **Criterios de Aceptación:**
  * CA-04.1: Gráfica con doble eje o subpaneles que relacione lluvia acumulada, demanda hídrica y reservas del suelo.
  * CA-04.2: Resaltado visual de periodos críticos de sequía intraestival (canícula) durante la etapa de floración/llenado de grano.

---

### RF-05: Modelado Geométrico del Terreno
* **Descripción:** El sistema debe permitir al usuario ingresar las dimensiones o coordenadas de su terreno para modelarlo de manera gráfica en una ventana interactiva simulando un plano a escala.
* **Detalle Técnico:**
  * Entrada mediante ancho ($m$) y largo ($m$), o polígono de vértices geográficos.
  * Cálculo y conversión automática de superficie a metros cuadrados ($m^2$), manzanas ($mz$, donde $1\ mz = 7,000\ m^2$ en Guatemala) y hectáreas ($ha$).
  * Renderizado esquemático del lote con orientación cardinal y cotas de dimensión.
* **Criterios de Aceptación:**
  * CA-05.1: Validación de dimensiones numéricas positivas ($> 0$).
  * CA-05.2: Despliegue visual del plano perimetral con escala métrica legible y área neta calculada en $m^2$, $mz$ y $ha$.

---

### RF-06: Recomendación de Densidad de Siembra
* **Descripción:** El sistema debe calcular y mostrar la cantidad ideal de maíz que se puede sembrar por metro cuadrado en función de las condiciones agroclimáticas evaluadas.
* **Detalle Técnico:**
  * Ajuste de densidad base (habitualmente 5 a 6.5 plantas/$m^2$, equivalentes a 35,000 a 45,000 plantas/$mz$) según el nivel de riesgo hídrico predicho:
    * En escenario favorable (Semáforo Verde): Densidad normal a alta (ej. 5.5 a 6.0 plantas/$m^2$).
    * En escenario de estrés hídrico (Semáforo Amarillo o Rojo): Reducción de densidad (ej. 4.0 a 4.5 plantas/$m^2$) para disminuir la competencia por agua.
  * Estimación de kilogramos o bolsas de semilla comercial requeridas (tomando en cuenta \% de germinación y pérdidas de campo).
  * Recomendación de espaciamiento entre surcos ($cm$) y entre posturas ($cm$).
* **Criterios de Aceptación:**
  * CA-06.1: Visualización del número total de plantas/semillas para el área modelada.
  * CA-06.2: Indicación de distanciamiento recomendado para siembra tradicional y mecanizada.

---

### RF-07: Proyección Financiera y Tabla de Pérdidas y Ganancias (P&L)
* **Descripción:** El sistema debe solicitar al usuario el capital promedio de inversión disponible para su cosecha. Con base en este monto y la producción estimada de quintales, generará una tabla detallada de pérdidas y ganancias utilizando los precios oficiales del maíz obtenidos del MAGA, mostrando obligatoriamente la **última fecha de actualización** de dichos precios en la plataforma.
* **Detalle Técnico:**
  * Rendimiento potencial estimado en quintales ($qq$) por manzana o hectárea según la viabilidad del modelo agroclimático.
  * Costos desglosados de producción: preparación de suelo, semilla, fertilización (fórmula y urea), control fitosanitario, mano de obra y cosecha.
  * Precio de venta oficial del quintal de maíz blanco/amarillo tomado de los reportes del Sistema de Información de Mercados Agrícolas (SIMPA/DIPLAN - MAGA).
  * Indicadores de rentabilidad: Ingreso Bruto, Costo Total, Utilidad Neta, Margen de Utilidad (\%), Relación Beneficio/Costo ($B/C$) y Punto de Equilibrio ($qq$).
* **Criterios de Aceptación:**
  * CA-07.1: Mostrar claramente la fecha exacta de la última actualización de precios del MAGA (ej. `"Precios oficiales MAGA - Actualizado al: 2026-09-15"`).
  * CA-07.2: Desplegar la tabla completa de Pérdidas y Ganancias (P&L) tanto para el escenario proyectado como para escenarios de sensibilidad (favorable, medio, adverso).
  * CA-07.3: Si el capital ingresado es inferior a los costos mínimos operativos, emitir advertencia de déficit financiero.

---

### RF-08: Exportación de Informes en Formato PDF
* **Descripción:** El sistema debe permitir al usuario descargar la proyección completa y el informe integral para la toma de decisiones en un archivo PDF ordenado, con márgenes estándar y una distribución limpia de elementos para evitar la superposición de textos.
* **Detalle Técnico:**
  * Generación mediante biblioteca de maquetación tipográfica estructurada.
  * Secciones del informe:
    1. Encabezado con datos del predio, coordenadas y fecha de consulta.
    2. Diagnóstico agrometeorológico y fase ENSO.
    3. Dictamen del modelo con semáforo y probabilidad calibrada.
    4. Dimensiones del terreno y recomendación de densidad de siembra.
    5. Proyección económica y estado de pérdidas y ganancias con cita de precios MAGA.
    6. Gráficos integrados (curva de balance hídrico y plano del terreno).
* **Criterios de Aceptación:**
  * CA-08.1: Documento PDF válido con márgenes uniformes (mínimo 15 mm).
  * CA-08.2: Sin solapamiento de líneas, encabezados o tablas.
  * CA-08.3: Descargable inmediatamente con un solo clic.

---

## 3. Requerimientos No Funcionales (RNF)

### RNF-01: Arquitectura de Acceso Abierto (Sin Autenticación)
* **Descripción:** Al tratarse de una herramienta pública y abierta, la arquitectura del sistema **no incluirá** registros de usuarios, formularios de inicio de sesión (*login*), recuperación de contraseñas, almacenamiento de perfiles ni control de acceso basado en roles.
* **Criterios de Aceptación:**
  * CA-RNF-01.1: Cero barreras de entrada; acceso inmediato a los módulos principales sin requerir correo ni clave.
  * CA-RNF-01.2: Ninguna información sensible o de identidad personal del usuario es obligatoria ni almacenada permanentemente.

---

### RNF-02: Usabilidad e Identidad Visual Moderna
* **Descripción:** La interfaz de usuario debe ser altamente intuitiva, moderna y atractiva, incorporando una paleta de colores representativa del maíz y del departamento de Jutiapa, así como transiciones fluidas y elementos visuales llamativos, descartando por completo diseños rígidos o de estilo anticuado (tipo *vicoder*).
* **Especificación de Diseño:**
  * Colores temáticos: Tonos maíz dorado (`#F59E0B`, `#D97706`), verde agrícola (`#10B981`, `#047857`), tierra fértil (`#78350F`) y fondos neutros modernos estilo *dark/light mode* con tarjetas de superficie limpias y elevación sutil.
  * Tipografía legible y contemporánea (Inter, Outfit o Roboto).
  * Microinteracciones con estados de *hover*, animaciones suaves y retroalimentación interactiva inmediata.

---

### RNF-03: Rendimiento y Respuesta Asíncrona
* **Descripción:** Dado que el pipeline analítico se activa bajo demanda y procesa peticiones web hacia APIs externas (Open-Meteo y NOAA), el sistema debe integrar indicadores visuales de carga (como *spinners* o barras de progreso) para mantener informado al usuario durante la ejecución del modelo.
* **Criterios de Aceptación:**
  * CA-RNF-03.1: Cada etapa del pipeline (1/4 Descarga de clima, 2/4 Índices ENSO, 3/4 Balance hídrico, 4/4 Inferencia) emite progreso y estado.
  * CA-RNF-03.2: Implementación de almacenamiento en caché para datos meteorológicos e índices mensuales ya descargados, reduciendo el tiempo de reejecución a menos de 3 segundos en consultas repetidas.

---

### RNF-04: Calidad y Estándares de Generación de Reportes PDF
* **Descripción:** El motor de exportación de documentos PDF debe garantizar una maquetación profesional y estructurada, aplicando márgenes estándar y un control riguroso del tamaño de fuentes para impedir el solapamiento de caracteres o líneas de texto.
* **Criterios de Aceptación:**
  * CA-RNF-04.1: Renderizado vectorial nítido de tipografía e inserción de gráficos en alta resolución (mínimo 150 DPI).
  * CA-RNF-04.2: Paginación automática limpia con números de página, pie de página institucional y advertencias agronómicas claras.

---

## 4. Matriz de Trazabilidad de Requerimientos

| Requerimiento | Componente Técnico Responsable | Entrada Principal | Salida / Artefacto |
| :--- | :--- | :--- | :--- |
| **RF-01** | `UI Calendar / Config` | Fecha tentativa ($AAAA-MM-DD$) | Objeto `Timestamp` validado |
| **RF-02** | `data_fetcher` + `models` | Coordenadas ($Lat, Lon$) y fecha | Dataset enriquecido y modelo calibrado |
| **RF-03** | `models.semaforo` | Probabilidad de viabilidad ($0.0 - 1.0$) | Clasificación: Rojo, Amarillo o Verde |
| **RF-04** | `reporting.visualizer` | Serie temporal de balance hídrico | Gráfica de precipitación, $ET_c$ y suelo |
| **RF-05** | `agronomy_economics.geometry` | Ancho y largo del terreno ($m$) | Área en $m^2, mz, ha$ y plano a escala |
| **RF-06** | `agronomy_economics.density` | Área y nivel de viabilidad | Densidad plantas/$m^2$ y total semillas |
| **RF-07** | `agronomy_economics.finances`| Capital disponible y producción esperada| Tabla de Pérdidas y Ganancias (P&L) |
| **RF-08** | `reporting.pdf_exporter` | Resultados del pipeline integral | Archivo descargable `.pdf` maquetado |
| **RNF-01** | Arquitectura del Sistema | Acceso HTTP directo | Sesión anónima y libre de credenciales |
| **RNF-02** | Frontend & UI Styling | Tokens de diseño temático | Interfaz moderna inspirada en Jutiapa/Maíz |
| **RNF-03** | Pipeline Asíncrono + Caché | Consultas a Open-Meteo y NOAA | Notificación de progreso y caché local |
| **RNF-04** | Motor de Documentos PDF | Plantilla de maquetación estructurada | PDF con márgenes estándar sin colisiones |

---

## 5. Fuentes de Datos y Precios de Referencia

1. **Clima Diario (1981 - Presente):** ERA5 Reanalysis vía [Open-Meteo Archive API](https://archive-api.open-meteo.com/v1/archive).
2. **Índices Macroclimáticos ENSO:**
   * MEI v2 (Multivariate ENSO Index): [NOAA Physical Sciences Laboratory](https://psl.noaa.gov/data/correlation/meiv2.data).
   * Niño 3.4 Anomalies: [NOAA PSL Monthly Long Time Series](https://psl.noaa.gov/data/timeseries/month/data/nino34.long.anom.data).
3. **Precios Oficiales de Mercado de Granos Básicos:**
   * Ministerio de Agricultura, Ganadería y Alimentación (MAGA), Dirección de Planeamiento (DIPLAN) / Sistema de Información de Mercados (SIMPA).
   * Frecuencia de actualización en el sistema: Quincenal / Mensual con sello de tiempo explícito en pantalla e informe.
