"""
Análisis exploratorio: estadísticos descriptivos, correlaciones y ACF/PACF.

Etapa 2 del flujo VARX.
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def plot_acf_pacf(series: pd.Series, lags: int = 24):
    raise NotImplementedError


def correlation_matrix(df: pd.DataFrame):
    raise NotImplementedError


if __name__ == "__main__":
    print("eda.py — pendiente de implementación")
