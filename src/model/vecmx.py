"""
Estimación VECMX (Vector Error Correction Model with Exogenous variables).

Etapa 6b del flujo VARX: se usa cuando las variables endógenas son I(1)
y cointegran (prueba de Johansen positiva). Incluye el término de corrección
de error (ECT) estimado por máxima verosimilitud.
"""

import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def estimate_vecmx(df: pd.DataFrame, p: int, rank: int) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    print("vecmx.py — pendiente de implementación")
