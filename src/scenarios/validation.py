"""
Validación predictiva fuera de muestra.

Etapa 10b del flujo VARX. Calcula métricas de error de pronóstico:
RMSE, MAE, MAPE y Theil-U para evaluar la capacidad predictiva del modelo.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def theil_u(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    raise NotImplementedError


def full_report(y_true: np.ndarray, y_pred: np.ndarray, label: str = "") -> pd.DataFrame:
    raise NotImplementedError


if __name__ == "__main__":
    print("validation.py — pendiente de implementación")
