"""
Pruebas de causalidad de Granger y evaluación de exogeneidad débil.

Etapa 8 del flujo VARX. Valida la clasificación endógena/exógena y la
dirección de las relaciones dinámicas entre variables.
"""

import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def granger_causality(df: pd.DataFrame, caused: str, causing: str, p: int) -> dict:
    raise NotImplementedError


def weak_exogeneity(fit: dict, endog_cols: list) -> pd.DataFrame:
    raise NotImplementedError


if __name__ == "__main__":
    print("granger.py — pendiente de implementación")
