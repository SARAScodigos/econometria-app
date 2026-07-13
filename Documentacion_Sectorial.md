# Manual de Modelamiento Sectorial (Objetivo Específico 2)

Este manual contiene las instrucciones detalladas de ejecución, las decisiones de modelado y los resultados del análisis sectorial para los cuatro tipos de crédito de las Cajas Municipales (CMAC): **Comerciales, Consumo, Hipotecarios y Microcréditos**.

---

## 1. Estructura de Ejecución: Cómo Correr Cada Prueba por Separado

El pipeline sectorial está diseñado para ejecutarse de manera modular y transparente. A continuación se detalla cómo operar cada fase metodológica independientemente:

### Fase A: Cointegración de Johansen (Niveles)
Esta prueba verifica si existe relación de largo plazo en niveles. Se debe correr utilizando el python del entorno virtual (`.venv`) y especificando el sector que se desea analizar mediante el argumento `--sector`.

* **Comerciales:**
  ```bash
  ./.venv/bin/python src/cointegration/johansen.py --input data/datos_varx.xlsx --output outputs/resultados_comerciales/johansen_comerciales.xlsx --sector comerciales
  ```
* **Consumo:**
  ```bash
  ./.venv/bin/python src/cointegration/johansen.py --input data/datos_varx.xlsx --output outputs/resultados_consumo/johansen_consumo.xlsx --sector consumo
  ```
* **Hipotecarios:**
  ```bash
  ./.venv/bin/python src/cointegration/johansen.py --input data/datos_varx.xlsx --output outputs/resultados_hipotecarios/johansen_hipotecarios.xlsx --sector hipotecarios
  ```
* **Microcréditos:**
  ```bash
  ./.venv/bin/python src/cointegration/johansen.py --input data/datos_varx.xlsx --output outputs/resultados_microcreditos/johansen_microcreditos.xlsx --sector microcreditos
  ```

* **Salida:** Genera un libro de Excel `johansen_<sector>.xlsx` en la carpeta del sector, conteniendo el resumen de la prueba Trace y Max-Eigen.

---

### Fase B: Estimación VARX, Selección de Rezagos, Validación y Gráficos (Completo por Sector)
La estimación del modelo VARX, la simulación de escenarios contrafactuales, la validación predictiva y la creación de gráficos se ejecutan de manera integral mediante un script lanzador por cada tipo de crédito:

* **Comerciales:**
  ```bash
  ./.venv/bin/python src/scenarios/run_comerciales.py
  ```
* **Consumo:**
  ```bash
  ./.venv/bin/python src/scenarios/run_consumo.py
  ```
* **Hipotecarios:**
  ```bash
  ./.venv/bin/python src/scenarios/run_hipotecarios.py
  ```
* **Microcréditos:**
  ```bash
  ./.venv/bin/python src/scenarios/run_microcreditos.py
  ```

---

## 2. Flexibilidad del Modelo: ¿Cómo cambiar el máximo de rezagos a evaluar?

El proceso de selección del rezago óptimo evalúa de manera automática todos los rezagos desde $p=1$ hasta un límite superior.

* **Cómo modificar el límite (por ejemplo, a 13, 14 o 18 rezagos):**
  Abre el archivo de configuración global [src/config/settings.py](file:///home/sarah/Proyectos-2025/econometria-app/src/config/settings.py) y modifica el parámetro:
  ```python
  MAX_LAG = 12  # Cambia este número al límite que deseas evaluar
  ```
  Al guardar este cambio y volver a ejecutar cualquiera de los scripts sectoriales (`run_<sector>.py`), el sistema automáticamente ampliará o reducirá el rango de evaluación en la terminal y en las hojas de Excel.

---

## 3. Resumen Metodológico de Decisiones y Resultados

### A. Análisis de Tendencias en Niveles y Cointegración de Johansen

Para justificar de manera rigurosa si debemos estimar un modelo **VECMX** (en niveles con términos de corrección de error) o un **VARX en primeras diferencias**, se realizó un análisis en dos etapas:

#### 1. Inspección de Tendencias Determinísticas en Niveles
Al observar las variables sectoriales en niveles para el periodo pre-COVID, se detecta un comportamiento asimétrico en sus componentes determinísticos:
* **Logaritmo de Colocaciones (Volumen):** Las series `Ln_Vol_comerciales`, `Ln_Vol_consumo`, `Ln_Vol_hipotecarios` y `Ln_Vol_microcreditos` muestran una **tendencia lineal determinística de crecimiento** muy clara a lo largo del tiempo.
* **Tasa de Morosidad:** Las series `Mora_comerciales`, `Mora_consumo`, `Mora_hipotecarios` y `Mora_microcreditos` no crecen indefinidamente; oscilan alrededor de una **media constante** (sin tendencia a largo plazo).

Esta asimetría (volumen con tendencia lineal, morosidad con constante) exige especificar la prueba de Johansen con **`det_order=1`** (que asume que hay constante en el espacio de cointegración, pero tendencia lineal en los niveles de los datos). El uso de `det_order=0` (solo constante) sería una especificación incorrecta porque ignoraría la tendencia determinística visible en los créditos.

#### 2. Resultados de la Prueba de Cointegración de Johansen (`det_order=1`, `k_ar_diff=3`)
Al correr la prueba sobre el par de variables en niveles de cada sector, se obtienen las siguientes conclusiones:

| Cartera / Sector | Variables en Niveles | Trace Stat ($r=0$) | Valor Crítico ($95\%$) | Rango ($r$) | Cointegración | Decisión Econométrica |
|---|---|---|---|---|---|---|
| **Comerciales** | $Ln\_Vol\_comerciales$, $Mora\_comerciales$ | 18.19 | 18.40 | 0 | **No** | **VARX en Diferencias:** Al no haber cointegración ($r=0$), estimar en niveles sería espurio. La única opción válida es diferencias. |
| **Consumo** | $Ln\_Vol\_consumo$, $Mora\_consumo$ | 20.30 | 18.40 | 1 | **Sí** | **VARX en Diferencias (por estabilidad):** Matemáticamente se permite VECMX. Sin embargo, en simulaciones de largo plazo bajo quiebres severos (COVID), los VECM propagan errores exponencialmente. Se opta por diferencias para asegurar estabilidad y consistencia. |
| **Hipotecarios** | $Ln\_Vol\_hipotecarios$, $Mora\_hipotecarios$ | 39.64 | 18.40 | 2 | **Rango Completo** | **VARX en Diferencias (conservador):** Rango completo indica que las variables son I(0) o estacionarias en niveles. En este caso, el VECM no está definido. Tomar diferencias es una postura conservadora que elimina derivas lentas. |
| **Microcréditos** | $Ln\_Vol\_microcreditos$, $Mora\_microcreditos$ | 15.20 | 18.40 | 0 | **No** | **VARX en Diferencias:** Sin cointegración ($r=0$). Se modela en diferencias obligatoriamente para evitar regresión espuria. |

---

### B. Selección de Rezagos Sistemática y Diagnóstico Ljung-Box
Para cada sector, se evaluaron los candidatos a nivel de sistema usando el **BIC del sistema completo** (multivariado), condicionado a que el modelo sea dinámicamente estable ($|eig|<1$) y que **ambas ecuaciones del sistema estén libres de autocorrelación** (Ljung-Box p-valor $>0.05$):

* **Comerciales:** Se seleccionó **$p=6$**. Para rezagos menores, Ljung-Box rechaza ruido blanco para el volumen.
* **Consumo:** Se seleccionó **$p=12$**. (Mejora significativa de p-valores frente a $p=11$).
* **Hipotecarios:** Se seleccionó **$p=5$**. 
* **Microcréditos:** Se seleccionó **$p=11$**.

*Nota: La tabla con los p-valores exactos de Ljung-Box de cada ecuación para cada $p$ evaluado se graba de manera transparente en la hoja `"Seleccion_Rezagos"` de `resultados_varx_<sector>.xlsx`.*

---

### C. Precisión de las Predicciones (Periodo COVID 2020-2022)
Métricas de error (fuera de muestra) acumuladas en niveles para la simulación "Con Ayuda" frente al dato real observado:

| Sector / Variable | RMSE | MAE | MAPE (%) | Theil-U | Precisión del Modelo ($100 - \text{MAPE}$) |
|---|---|---|---|---|---|
| **Comerciales** ($p=6$) | | | | | |
| - Volumen | 122.17 | 106.36 | 4.79% | 0.0276 | **95.21%** |
| - Morosidad | 0.0114 | 0.0081 | 7.55% | 0.0561 | **92.45%** |
| **Consumo** ($p=12$) | | | | | |
| - Volumen | 69.99 | 58.54 | 1.10% | 0.0062 | **98.90%** |
| - Morosidad | 0.0019 | 0.0016 | 5.51% | 0.0316 | **94.49%** |
| **Hipotecarios** ($p=5$) | | | | | |
| - Volumen | 376.87 | 325.49 | 22.72% | 0.1311 | **77.28%** |
| - Morosidad | 0.0079 | 0.0055 | 17.02% | 0.0978 | **82.98%** |
| **Microcréditos** ($p=11$) | | | | | |
| - Volumen | 1101.13 | 794.55 | 4.02% | 0.0293 | **95.98%** |
| - Morosidad | 0.0057 | 0.0046 | 7.72% | 0.0472 | **92.28%** |

---

## 4. Directorio de Salidas (Outputs)

Todos los resultados organizados se encuentran en sus respectivas carpetas de salida:

* **Comerciales:** [outputs/resultados_comerciales/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_comerciales/)
  * Gráficas: [outputs/resultados_comerciales/plots/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_comerciales/plots/)
* **Consumo:** [outputs/resultados_consumo/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_consumo/)
  * Gráficas: [outputs/resultados_consumo/plots/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_consumo/plots/)
* **Hipotecarios:** [outputs/resultados_hipotecarios/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_hipotecarios/)
  * Gráficas: [outputs/resultados_hipotecarios/plots/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_hipotecarios/plots/)
* **Microcréditos:** [outputs/resultados_microcreditos/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_microcreditos/)
  * Gráficas: [outputs/resultados_microcreditos/plots/](file:///home/sarah/Proyectos-2025/econometria-app/outputs/resultados_microcreditos/plots/)
