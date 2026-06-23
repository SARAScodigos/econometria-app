"""
Depuración de series: valores faltantes, atípicos, quiebres estructurales
y cambios metodológicos.

Etapa 1b del flujo VARX: se ejecuta tras la carga (loader.py) y antes del
análisis descriptivo.
"""

import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def detect_outliers(df: pd.DataFrame, z_thresh: float = 3.5) -> pd.DataFrame:
    raise NotImplementedError


def handle_missing(df: pd.DataFrame, method: str = "linear") -> pd.DataFrame:
    raise NotImplementedError


def detect_structural_breaks(series: pd.Series):
    raise NotImplementedError


if __name__ == "__main__":
    print("cleaner.py — pendiente de implementación")
