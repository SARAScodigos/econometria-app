"""
Prueba de cointegración de Johansen entre las variables endógenas.

Etapa 5 del flujo VARX. Si las series son I(1), esta prueba determina
si se especifica VECMX (cointegran) o VARX en diferencias (no cointegran).
"""

import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def johansen_test(df: pd.DataFrame, endog_cols: list, det_order: int = 0, k_ar_diff: int = 1) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    print("johansen.py — pendiente de implementación")
