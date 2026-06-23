"""
Utilidades comunes de visualización compartidas entre etapas del flujo VARX.
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import OUT_DIR


def save_fig(fig: plt.Figure, filename: str, dpi: int = 300):
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(f"{OUT_DIR}/{filename}", dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def add_pandemic_line(ax: plt.Axes, date: str = "2020-03-01", label: str = "Mar-2020"):
    ax.axvline(pd.Timestamp(date), color="black", linestyle="--", linewidth=1)
    ax.text(pd.Timestamp(date), ax.get_ylim()[1], f"  {label}", va="top", fontsize=8)
