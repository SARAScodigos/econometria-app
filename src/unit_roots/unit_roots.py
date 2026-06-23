"""
Pruebas de raíz unitaria: ADF, PP y KPSS en niveles y en primeras diferencias.

Etapa 4 del flujo VARX. Determina el orden de integración de las series
antes de decidir especificación VARX en niveles o en diferencias.
"""

import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def adf_test(series: pd.Series, maxlag: int = 12) -> dict:
    raise NotImplementedError


def pp_test(series: pd.Series) -> dict:
    raise NotImplementedError


def kpss_test(series: pd.Series) -> dict:
    raise NotImplementedError


def run_all(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    raise NotImplementedError


if __name__ == "__main__":
    print("unit_roots.py — pendiente de implementación")
