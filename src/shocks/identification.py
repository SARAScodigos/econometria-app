"""
Identificación de shocks estructurales: ordenamiento de Cholesky fundamentado.

Etapa 9a del flujo VARX. Define el orden causal contemporáneo entre las
variables endógenas para ortogonalizar los shocks antes del análisis IRF.
"""

import sys
from pathlib import Path
import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import ENDOG


def cholesky_decompose(Sigma: np.ndarray) -> np.ndarray:
    return np.linalg.cholesky(Sigma)


def cholesky_diagonal(Sigma: np.ndarray) -> np.ndarray:
    return np.linalg.cholesky(np.diag(np.diag(Sigma)))


if __name__ == "__main__":
    print("identification.py — pendiente de implementación completa")
    print(f"Orden Cholesky actual: {ENDOG}")
