import os
import warnings
import numpy as np

# =============================
# Parametros editables
# =============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_FILE = os.path.join(BASE_DIR, "data", "Data estacionaria.xlsx")
DATE_COL = "fecha"

# Endogenas (agregado)
ENDOG = ["D_ln_Vol_total", "D_Mora_total"]
ENDOG_LEVELS = ["Vol_total", "Mora_total"]

# Exogenas
EXOG = ["D_ln_PBI_Desestacionalizado", "D_Tasa_Ref"]

# Ventana de estimacion pre-COVID
TRAIN_END = "2020-02-01"

# Meses para calibrar shock COVID (Mar y Abr 2020)
SHOCK_MONTHS = ["2020-03-01", "2020-04-01"]

# Horizonte IRF (meses)
H = 48

# Rezagos maximos a evaluar
MAX_LAG = 12

# Carpeta de salida
OUT_DIR = os.path.join(BASE_DIR, "outputs")


def configure_runtime():
    warnings.filterwarnings("ignore", category=UserWarning)
    np.set_printoptions(suppress=True, precision=6)
    os.makedirs(OUT_DIR, exist_ok=True)
