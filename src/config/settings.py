import os
import warnings
import numpy as np

# =============================
# Parametros editables
# =============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Carpeta de salida
OUT_DIR = os.path.join(BASE_DIR, "outputs")

INPUT_FILE = os.path.join(BASE_DIR, "data", "Data estacionaria.xlsx")
DATE_COL = "fecha"

# Insumos por etapa
#========Comenzar por la estacionaldiad =====================================
SEASONALITY_INPUT_FILE = os.path.join(BASE_DIR, "data", "Data No estacional CMAC.xlsx")
DESEASONALIZE_INPUT_FILE = SEASONALITY_INPUT_FILE

#============== Ahora la estacionariedad ====================================
UNIT_ROOTS_FILE = os.path.join(BASE_DIR, "data", "datos_transformados_estacionarios.xlsx")
CORRECTION_UNIT_ROOT_FILE = UNIT_ROOTS_FILE

#======================= Ahora archivo para cointegracion de Johansen ===================
COINTEGRATION_FILE = UNIT_ROOTS_FILE


# Endogenas (agregado)
ENDOG = ["D_ln_Vol_total", "D_Mora_total"]
ENDOG_LEVELS = ["Vol_total", "Mora_total"]

# Exogenas
EXOG = ["D_ln_PBI_Desestacionalizado", "D_Tasa_Ref"]

# Variables en niveles/originales para pruebas de estacionalidad mensual
SEASONALITY_VARIABLES = [
    "Vol_comerciales",
    "Mora_comerciales",
    "Vol_consumo",
    "Mora_consumo",
    "Vol_hipotecarios",
    "Mora_hipotecarios",
    "Vol_microcreditos",
    "Mora_microcreditos",
    "Vol_total",
    "Mora_total",
    "Tasa_Ref",
    "PBI_Desestacionalizado",
]

VARIABLES_NIVELES_UNIT_ROOTS = SEASONALITY_VARIABLES


VARIABLES_TRANSFORMADAS_I = [
    "D_ln_Vol_comerciales",
    "D_Mora_comerciales",
    "D_ln_Vol_consumo",
    "D_Mora_consumo",
    "D_ln_Vol_hipotecarios",
    "D_Mora_hipotecarios",
    "D_ln_Vol_microcreditos",
    "D_Mora_microcreditos",
    "D_ln_Vol_total",
    "D_Mora_total",
    "D_Tasa_Ref",
    "D_ln_PBI_Desestacionalizado",
]

# Ventanas de muestra
SAMPLE_START = "2002-01-01"
SAMPLE_END = "2022-12-01"

# Ventana de estimacion pre-COVID: dinamica normal antes del shock
TRAIN_START = SAMPLE_START
TRAIN_END = "2020-02-01"

# Periodo post-shock usado para escenarios contrafactuales
SCENARIO_START = "2020-03-01"
SCENARIO_END = SAMPLE_END

# Meses para calibrar shock COVID inicial (Mar y Abr 2020)
SHOCK_MONTHS = ["2020-03-01", "2020-04-01"]

# Ventana de medidas de alivio/rescate. Ajustar cuando se defina la proxy final.
AID_START = "2020-05-01"
AID_END = "2022-11-01"

# Horizonte IRF (meses)
H = 48

# Rezagos maximos a evaluar
MAX_LAG = 12




WINDOWS = {
    "full": (SAMPLE_START, SAMPLE_END),
    "pre_covid": (TRAIN_START, TRAIN_END),
    "scenario": (SCENARIO_START, SCENARIO_END),
    "aid": (AID_START, AID_END),
}


def configure_runtime():
    warnings.filterwarnings("ignore", category=UserWarning)
    np.set_printoptions(suppress=True, precision=6)
    os.makedirs(OUT_DIR, exist_ok=True)
