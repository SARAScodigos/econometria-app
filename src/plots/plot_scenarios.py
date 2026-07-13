"""
Generación de gráficos científicos para el Escenario General (OB1).
Muestra la trayectoria histórica y cómo se ramifican los tres escenarios
(Real Observado, Simulado con Ayuda, Simulado sin Ayuda) a partir de Marzo 2020.
Genera gráficos para Niveles y para Diferencias.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configurar ruta del proyecto (src/plots/plot_scenarios.py -> parents[2] es el root)
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    VARX_MODEL_FILE,
    DATE_COL,
    ENDOG,
    ENDOG_LEVELS,
    SCENARIO_START,
    SCENARIO_END,
    TRAIN_END,
    OUT_DIR,
    configure_runtime,
)
from src.scenarios.general_no_ayuda import build_scenarios

# Parámetros del gráfico
PLOT_START = "2018-01-01"
SHOCK_DATE = pd.Timestamp(SCENARIO_START)

def prepare_combined_data():
    """Ejecuta los escenarios y los combina con la historia pre-COVID."""
    # 1. Obtener datos de la simulación
    outputs = build_scenarios()
    df_diff_scenario = outputs["diferencias"]
    df_level_scenario = outputs["niveles"]
    
    # 2. Cargar datos históricos completos para completar la historia
    raw_df = pd.read_excel(VARX_MODEL_FILE)
    raw_df[DATE_COL] = pd.to_datetime(raw_df[DATE_COL])
    raw_df = raw_df.set_index(DATE_COL).sort_index()
    raw_df.index = pd.to_datetime(raw_df.index.date)
    
    # Rango total para graficar
    full_idx = pd.date_range(start=PLOT_START, end=df_level_scenario.index[-1], freq="MS")
    
    # 3. Crear DataFrames combinados
    levels_comb = pd.DataFrame(index=full_idx)
    diffs_comb = pd.DataFrame(index=full_idx)
    
    # Fecha límite de historia
    hist_idx = full_idx[full_idx < SHOCK_DATE]
    scen_idx = full_idx[full_idx >= SHOCK_DATE]
    
    # Población para Niveles
    for lvl_col in ENDOG_LEVELS:
        # Historia: los tres escenarios son idénticos al valor real histórico
        for suffix in ["_real", "_pred_observado", "_pred_sin_ayuda"]:
            col_name = f"{lvl_col}{suffix}"
            levels_comb.loc[hist_idx, col_name] = raw_df.loc[hist_idx, lvl_col]
            # Escenario: copiamos los datos simulados
            levels_comb.loc[scen_idx, col_name] = df_level_scenario.loc[scen_idx, col_name]
            
    # Población para Diferencias
    for diff_col in ENDOG:
        for suffix in ["_real", "_pred_observado", "_pred_sin_ayuda"]:
            col_name = f"{diff_col}{suffix}"
            diffs_comb.loc[hist_idx, col_name] = raw_df.loc[hist_idx, diff_col]
            diffs_comb.loc[scen_idx, col_name] = df_diff_scenario.loc[scen_idx, col_name]
            
    return levels_comb, diffs_comb

def apply_scientific_style(ax, title, ylabel):
    """Aplica formato estético y científico al gráfico."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')
    
    ax.tick_params(colors='#333333', which='both')
    ax.grid(True, linestyle="--", alpha=0.5, color="#cccccc")
    
    ax.set_title(title, fontsize=12, fontweight='bold', pad=12, color='#111111')
    ax.set_ylabel(ylabel, fontsize=10, fontweight='semibold', color='#333333')
    ax.set_xlabel("Fecha", fontsize=10, fontweight='semibold', color='#333333')
    
    # Formato de fechas
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    
    # Establecer los límites del eje X explícitamente de 2018-01-01 a 2022-12-01
    ax.set_xlim(pd.Timestamp(PLOT_START), pd.Timestamp(SCENARIO_END))
    
    # Línea vertical del shock COVID-19
    ax.axvline(SHOCK_DATE, color='#7f8c8d', linestyle=':', linewidth=1.5, alpha=0.9)
    # Región sombreada del escenario (post-shock)
    ax.axvspan(SHOCK_DATE, pd.Timestamp(SCENARIO_END), color='#f1f2f6', alpha=0.5, label='Periodo de Escenario')

def main():
    configure_runtime()
    
    # Obtener data combinada
    levels, diffs = prepare_combined_data()
    
    # Crear carpeta para guardar gráficos dentro de outputs/plots/
    plots_dir = Path(OUT_DIR) / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Paleta de colores científicos
    c_real = "#2c3e50"       # Azul oscuro/Grisáceo (Observado)
    c_pred = "#2980b9"       # Azul brillante (Simulado con ayuda)
    c_no_aid = "#c0392b"     # Rojo apagado (Simulado sin ayuda)
    
    # ==========================================
    # 1. GRÁFICO DE NIVELES (Panel de 2 subplots)
    # ==========================================
    fig_lvl, (ax_vol, ax_mor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    # Subplot A: Volumen Total
    ax_vol.plot(levels.index, levels["Vol_total_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_vol.plot(levels.index, levels["Vol_total_pred_observado"], color=c_pred, linewidth=2, linestyle="-", label="Modelo (Con Ayuda)")
    ax_vol.plot(levels.index, levels["Vol_total_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    apply_scientific_style(ax_vol, "Volumen Total de Crédito (CMAC)", "Millones de Soles (Nivel)")
    ax_vol.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    
    # Anotación del punto de ramificación en marzo 2020
    ax_vol.text(SHOCK_DATE + pd.DateOffset(months=1), ax_vol.get_ylim()[0] + (ax_vol.get_ylim()[1] - ax_vol.get_ylim()[0])*0.1, 
                "Shock COVID-19\nMarzo 2020", color="#7f8c8d", fontsize=9, fontweight="bold")
    
    # Subplot B: Morosidad Total
    ax_mor.plot(levels.index, levels["Mora_total_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_mor.plot(levels.index, levels["Mora_total_pred_observado"], color=c_pred, linewidth=2, linestyle="-", label="Modelo (Con Ayuda)")
    ax_mor.plot(levels.index, levels["Mora_total_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    apply_scientific_style(ax_mor, "Tasa de Morosidad Total (CMAC)", "Porcentaje (%)")
    
    fig_lvl.suptitle("Impacto del Shock COVID-19 en Niveles de Cartera y Morosidad\nEscenario Real vs. Contrafactual Sin Ayuda Gubernamental", 
                     fontsize=14, fontweight="bold", y=0.98, color="#111111")
    fig_lvl.tight_layout()
    fig_lvl.savefig(plots_dir / "escenarios_niveles_panel.png", dpi=300)
    plt.close(fig_lvl)
    
    # ==========================================
    # 2. GRÁFICO DE DIFERENCIAS (Panel de 2 subplots)
    # ==========================================
    fig_diff, (ax_dvol, ax_dmor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    # Subplot A: Variación Logarítmica del Volumen
    ax_dvol.plot(diffs.index, diffs["D_ln_Vol_total_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_dvol.plot(diffs.index, diffs["D_ln_Vol_total_pred_observado"], color=c_pred, linewidth=2, linestyle="-", label="Modelo (Con Ayuda)")
    ax_dvol.plot(diffs.index, diffs["D_ln_Vol_total_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    ax_dvol.axhline(0, color="gray", linewidth=0.8, linestyle="-.")
    apply_scientific_style(ax_dvol, "Diferencia de Crecimiento del Crédito (D_ln_Vol_total)", "Variación Logarítmica")
    ax_dvol.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    
    # Subplot B: Variación de la Morosidad
    ax_dmor.plot(diffs.index, diffs["D_Mora_total_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_dmor.plot(diffs.index, diffs["D_Mora_total_pred_observado"], color=c_pred, linewidth=2, linestyle="-", label="Modelo (Con Ayuda)")
    ax_dmor.plot(diffs.index, diffs["D_Mora_total_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    ax_dmor.axhline(0, color="gray", linewidth=0.8, linestyle="-.")
    apply_scientific_style(ax_dmor, "Diferencia Mensual de la Morosidad (D_Mora_total)", "Puntos Porcentuales")
    
    fig_diff.suptitle("Impacto del Shock COVID-19 en Variaciones Mensuales (Diferencias)\nEscenario Real vs. Contrafactual Sin Ayuda Gubernamental", 
                      fontsize=14, fontweight="bold", y=0.98, color="#111111")
    fig_diff.tight_layout()
    fig_diff.savefig(plots_dir / "escenarios_diferencias_panel.png", dpi=300)
    plt.close(fig_diff)
    
    print("\n" + "="*50)
    print("¡Gráficos de escenarios generados con éxito!")
    print(f"Panel en Niveles: {plots_dir / 'escenarios_niveles_panel.png'}")
    print(f"Panel en Diferencias: {plots_dir / 'escenarios_diferencias_panel.png'}")
    print("="*50)

if __name__ == "__main__":
    main()
