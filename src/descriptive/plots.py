import os
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import INPUT_FILE, OUT_DIR

# === Parámetros ===
file_path = INPUT_FILE
start_date = "2018-01-01"
end_date   = "2022-12-01"
pandemia   = pd.Timestamp("2020-03-01")

# === 1) Leer data ===
df = pd.read_excel(file_path)

# === 2) Preparar columnas ===
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

cols = ["Vol_total", "Mora_total", "PBI_Desestacionalizado"]
for c in cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=["fecha"]).sort_values("fecha")

# === 3) Filtrar periodo pre y post COVID ===
dfp = df[(df["fecha"] >= start_date) & (df["fecha"] <= end_date)].copy()

# ==========================================================
# === GRÁFICO 1: CMAC (Volumen y Morosidad) ===============
# ==========================================================

fig1, ax1 = plt.subplots(figsize=(11, 5))

# Línea azul: Volumen
ax1.plot(dfp["fecha"], dfp["Vol_total"], color="blue", linewidth=2, label="Volumen de créditos")
ax1.set_ylabel("Volumen de créditos (Vol_total)", color="blue")
ax1.set_xlabel("Fecha")
ax1.tick_params(axis='y', labelcolor="blue")

# Línea roja: Morosidad
ax2 = ax1.twinx()
ax2.plot(dfp["fecha"], dfp["Mora_total"], color="red", linewidth=2, linestyle=":", label="Morosidad")
ax2.set_ylabel("Morosidad (Mora_total)", color="red")
ax2.tick_params(axis='y', labelcolor="red")

# Línea pandemia
ax1.axvline(pandemia, color="black", linestyle="--", linewidth=1, label="Inicio de la pandemia")
ax1.text(pandemia, ax1.get_ylim()[1], "  Mar-2020", va="top")

# Leyenda conjunta para las series de ambos ejes
handles1, labels1 = ax1.get_legend_handles_labels()
handles2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(handles1 + handles2, labels1 + labels2, loc="best")

ax1.set_title("CMAC: Volumen de créditos y morosidad (2018–2022)")
plt.tight_layout()
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, "plot_cmac_vol_mora.png"))
plt.close(fig1)

# ==========================================================
# === GRÁFICO 2: PBI Desestacionalizado ====================
# ==========================================================

fig2, ax_pbi = plt.subplots(figsize=(11, 5))

ax_pbi.plot(dfp["fecha"], dfp["PBI_Desestacionalizado"], linewidth=2)
ax_pbi.set_ylabel("PBI Desestacionalizado")
ax_pbi.set_xlabel("Fecha")

# Línea pandemia
ax_pbi.axvline(pandemia, linestyle="--", linewidth=1)
ax_pbi.text(pandemia, ax_pbi.get_ylim()[1], "  Mar-2020", va="top")

ax_pbi.set_title("Choque macroeconómico: PBI desestacionalizado (2018–2022)")

plt.tight_layout()
os.makedirs(OUT_DIR, exist_ok=True)
plt.savefig(os.path.join(OUT_DIR, "plot_pbi.png"))
plt.close(fig2)
