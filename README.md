# EconometriApp — UDEP

Aplicación de escritorio para análisis econométrico de series de tiempo, construida con PyQt6. Funciona como un mini-SPSS: el usuario carga su propio archivo, elige las columnas y ejecuta las pruebas paso a paso.

---

## Requisitos

- Python 3.11+
- Dependencias en `requirements.txt`

```bash
pip install -r requirements.txt
```

---

## Ejecución

```bash
python main.py
```

---

## Flujo de trabajo (GUI)

### Pestaña 1 — Datos

1. Clic en **Examinar…** y selecciona un `.xlsx`, `.xls` o `.csv`.
2. Si es Excel, elige la hoja en el desplegable.
3. La app detecta automáticamente el tipo de cada columna (numérico, fecha, texto).
4. Selecciona la **columna de fecha** y marca las **variables de análisis**.
5. Clic en **Confirmar y cargar datos →** — la app salta automáticamente a la pestaña siguiente.

### Pestaña 2 — Estacionalidad

**Sección 1: Prueba F de estacionalidad**

- Selecciona las variables a evaluar (todas marcadas por defecto).
- Clic en **Ejecutar Prueba F**.
- La prueba estima el modelo:  
  `y_t = constante + tendencia_t + dummies_mensuales + ε_t`  
  H₀: los coeficientes de las 11 dummies son conjuntamente cero.
- Los resultados aparecen en tabla con código de color:
  - Verde → no estacional
  - Ámbar → estacional (rechaza H₀)
  - Rojo → error en la variable
- Clic en **Exportar Excel** para guardar los resultados donde quieras.

**Sección 2: Desestacionalización**

- Las variables identificadas como estacionales quedan pre-seleccionadas automáticamente.
- Puedes ajustar la selección.
- Clic en **Desestacionalizar** — aplica regresión con dummies, resta la componente estacional.
- El resumen muestra el rango de la componente y el R² del modelo.
- Clic en **Exportar datos desestacionalizados** para guardar el archivo SA.

### Pestaña 3 — Raíz Unitaria *(próximamente)*

Pruebas ADF y KPSS sobre niveles y transformadas.

### Pestaña 4 — Transformaciones *(próximamente)*

Logaritmos y primeras diferencias sobre las variables seleccionadas.

---

## Estructura del proyecto

```
econometria-app/
├── main.py                         # Punto de entrada
├── data/                           # Archivos de datos de entrada
├── outputs/                        # Resultados exportados
└── src/
    ├── gui/
    │   ├── app_state.py            # Estado compartido entre pestañas
    │   ├── main_window.py          # Ventana principal (QTabWidget + estilos)
    │   ├── tabs/
    │   │   ├── data_tab.py         # Carga y configuración de datos
    │   │   └── seasonality_tab.py  # Prueba F + desestacionalización
    │   └── widgets/
    │       ├── results_table.py    # Tabla reutilizable con exportar
    │       └── column_selector.py  # Lista de checkboxes de columnas
    ├── seasonality/
    │   ├── seasonality.py          # Prueba F conjunta de dummies mensuales
    │   └── deseasonalize.py        # Ajuste estacional por regresión
    ├── unit_roots/
    │   ├── unit_roots.py           # ADF y KPSS
    │   └── transform_stationarity.py  # Log y primeras diferencias
    ├── cointegration/
    │   └── johansen.py             # Test de Johansen
    ├── model/
    │   ├── varx.py                 # Estimación VARX completo
    │   ├── varx_precovid.py        # VARX muestra pre-COVID
    │   ├── vecmx.py                # VECMX
    │   └── lag_selection.py        # Selección de rezagos (AIC/BIC/HQ)
    ├── diagnostics/
    │   └── diagnostics.py          # Diagnósticos de residuos
    ├── shocks/
    │   ├── irf.py                  # Funciones impulso-respuesta
    │   └── shock_pbi.py            # Choque de PBI
    ├── scenarios/
    │   ├── baseline.py             # Escenario base sin COVID
    │   ├── counterfactual_covid.py
    │   ├── escenarios_macro.py
    │   └── ...
    ├── causality/
    │   └── granger.py              # Causalidad de Granger
    └── descriptive/
        └── plots.py                # Gráficos descriptivos
```

---

## Módulos de análisis (independientes del GUI)

Todos los módulos en `src/` pueden ejecutarse directamente desde la terminal:

```bash
# Prueba de estacionalidad
python -m src.seasonality.seasonality

# Desestacionalización
python -m src.seasonality.deseasonalize

# Raíz unitaria (ADF + KPSS)
python -m src.unit_roots.unit_roots

# Transformar a estacionario (log + diferencias)
python -m src.unit_roots.transform_stationarity

# Modelo VARX
python -m src.model.varx
```

Los resultados se guardan en `outputs/`.
