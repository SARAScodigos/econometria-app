"""
Generación de gráficos para cuantificar el impacto neto del rescate/ayuda.
Grafica la diferencia matemática (Real Observado - Contrafactual Sin Ayuda)
tanto en niveles como en diferencias, desde 2019/06 hasta 2022/12.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configurar ruta del proyecto
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    DATE_COL,
    ENDOG,
    ENDOG_LEVELS,
    SCENARIO_START,
    SCENARIO_END,
    OUT_DIR,
    configure_runtime,
)
from src.scenarios.general_no_ayuda import build_scenarios

PLOT_START = "2019-06-01"
SHOCK_DATE = pd.Timestamp(SCENARIO_START)

def prepare_impact_data():
    """Calcula la diferencia (Real - Sin Ayuda) desde PLOT_START."""
    outputs = build_scenarios()
    df_diff_scenario = outputs["diferencias"]
    df_level_scenario = outputs["niveles"]
    
    # Rango total para graficar
    full_idx = pd.date_range(start=PLOT_START, end=df_level_scenario.index[-1], freq="MS")
    
    df_impact_lvl = pd.DataFrame(index=full_idx)
    df_impact_diff = pd.DataFrame(index=full_idx)
    
    # Segmentos de fecha
    hist_idx = full_idx[full_idx < SHOCK_DATE]
    scen_idx = full_idx[full_idx >= SHOCK_DATE]
    
    # 1. Niveles (Real - Sin Ayuda)
    # Volumen
    df_impact_lvl.loc[hist_idx, "Vol_total_impact"] = 0.0
    df_impact_lvl.loc[scen_idx, "Vol_total_impact"] = (
        df_level_scenario.loc[scen_idx, "Vol_total_real"] - 
        df_level_scenario.loc[scen_idx, "Vol_total_pred_sin_ayuda"]
    )
    # Morosidad
    df_impact_lvl.loc[hist_idx, "Mora_total_impact"] = 0.0
    df_impact_lvl.loc[scen_idx, "Mora_total_impact"] = (
        df_level_scenario.loc[scen_idx, "Mora_total_real"] - 
        df_level_scenario.loc[scen_idx, "Mora_total_pred_sin_ayuda"]
    )
    
    # 2. Diferencias (Real - Sin Ayuda)
    # Variación del Volumen
    df_impact_diff.loc[hist_idx, "D_ln_Vol_total_impact"] = 0.0
    df_impact_diff.loc[scen_idx, "D_ln_Vol_total_impact"] = (
        df_diff_scenario.loc[scen_idx, "D_ln_Vol_total_real"] - 
        df_diff_scenario.loc[scen_idx, "D_ln_Vol_total_pred_sin_ayuda"]
    )
    # Variación de la Morosidad
    df_impact_diff.loc[hist_idx, "D_Mora_total_impact"] = 0.0
    df_impact_diff.loc[scen_idx, "D_Mora_total_impact"] = (
        df_diff_scenario.loc[scen_idx, "D_Mora_total_real"] - 
        df_diff_scenario.loc[scen_idx, "D_Mora_total_pred_sin_ayuda"]
    )
    
    return df_impact_lvl, df_impact_diff

def apply_impact_style(ax, title, ylabel):
    """Aplica formato de gráfico de impacto con área sombreada y línea en cero."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')
    
    ax.tick_params(colors='#333333', which='both')
    ax.grid(True, linestyle="--", alpha=0.5, color="#cccccc")
    
    ax.set_title(title, fontsize=12, fontweight='bold', pad=12, color='#111111')
    ax.set_ylabel(ylabel, fontsize=10, fontweight='semibold', color='#333333')
    ax.set_xlabel("Fecha", fontsize=10, fontweight='semibold', color='#333333')
    
    # Eje X de fecha de 2019/06 a 2022/12
    ax.set_xlim(pd.Timestamp(PLOT_START), pd.Timestamp(SCENARIO_END))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    
    # Línea vertical del shock
    ax.axvline(SHOCK_DATE, color='#7f8c8d', linestyle=':', linewidth=1.5, alpha=0.9, label='Shock COVID-19 (Marzo 2020)')
    # Línea horizontal en Y=0 (referencia)
    ax.axhline(0, color='#333333', linestyle='-', linewidth=1.2, alpha=0.8)
    # Mostrar leyenda
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.85)

def main():
    configure_runtime()
    
    # Cargar datos de impacto
    lvl_impact, diff_impact = prepare_impact_data()
    
    plots_dir = Path(OUT_DIR) / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    # Colores
    c_vol = "#16a085"   # Verde azulado (Impacto positivo en crédito es bueno)
    c_mora = "#c0392b"  # Rojo (Morosidad menor en real es negativa/reducción del riesgo)
    
    # ==========================================
    # 1. GRÁFICO DE IMPACTO EN NIVELES
    # ==========================================
    fig_lvl, (ax_vol, ax_mor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    # Subplot A: Crédito (Real - Sin Ayuda)
    # Un valor positivo significa que la ayuda mantuvo el crédito más alto que el contrafactual
    ax_vol.plot(lvl_impact.index, lvl_impact["Vol_total_impact"], color=c_vol, linewidth=2.5, label="Impacto Neto (Real - Sin Ayuda)")
    ax_vol.fill_between(lvl_impact.index, lvl_impact["Vol_total_impact"], 0, 
                        where=(lvl_impact["Vol_total_impact"] >= 0), interpolate=True, color=c_vol, alpha=0.25, 
                        label="Volumen Sostenido por la Ayuda")
    apply_impact_style(ax_vol, "Efecto Neto sobre el Volumen de Crédito (Real - Sin Ayuda)", "Millones de Soles")
    ax_vol.text(SHOCK_DATE + pd.DateOffset(months=1), ax_vol.get_ylim()[1]*0.8, 
                "Choque COVID-19\nMarzo 2020", color="#7f8c8d", fontsize=9, fontweight="bold")
    
    # Subplot B: Morosidad (Real - Sin Ayuda)
    # Un valor negativo significa que la ayuda evitó un exceso de morosidad (la morosidad real fue menor)
    ax_mor.plot(lvl_impact.index, lvl_impact["Mora_total_impact"], color=c_mora, linewidth=2.5, label="Impacto Neto (Real - Sin Ayuda)")
    ax_mor.fill_between(lvl_impact.index, lvl_impact["Mora_total_impact"], 0, 
                        where=(lvl_impact["Mora_total_impact"] <= 0), interpolate=True, color=c_mora, alpha=0.2,
                        label="Tasa de Morosidad Evitada")
    # También rellenar en rojo si hubiera exceso (en este caso es negativo)
    ax_mor.fill_between(lvl_impact.index, lvl_impact["Mora_total_impact"], 0, 
                        where=(lvl_impact["Mora_total_impact"] > 0), interpolate=True, color="#27ae60", alpha=0.25,
                        label="Incremento en Morosidad")
    apply_impact_style(ax_mor, "Efecto Neto sobre la Tasa de Morosidad (Real - Sin Ayuda)", "Puntos Porcentuales")
    
    fig_lvl.suptitle("Diferencia Neta entre Escenario Real Observado y Contrafactual Sin Ayuda\n(Cuantificación del Efecto del Rescate Gubernamental en Niveles)", 
                     fontsize=14, fontweight="bold", y=0.98, color="#111111")
    fig_lvl.tight_layout()
    fig_lvl.savefig(plots_dir / "impacto_niveles_panel.png", dpi=300)
    plt.close(fig_lvl)
    
    # ==========================================
    # 2. GRÁFICO DE IMPACTO EN DIFERENCIAS
    # ==========================================
    fig_diff, (ax_dvol, ax_dmor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    # Subplot A: Variación Log del Crédito (Real - Sin Ayuda)
    ax_dvol.plot(diff_impact.index, diff_impact["D_ln_Vol_total_impact"], color=c_vol, linewidth=2.5, label="Diferencia en Crecimiento")
    ax_dvol.fill_between(diff_impact.index, diff_impact["D_ln_Vol_total_impact"], 0, 
                        where=(diff_impact["D_ln_Vol_total_impact"] >= 0), interpolate=True, color=c_vol, alpha=0.25,
                        label="Impulso Mensual de Crecimiento")
    ax_dvol.fill_between(diff_impact.index, diff_impact["D_ln_Vol_total_impact"], 0, 
                        where=(diff_impact["D_ln_Vol_total_impact"] < 0), interpolate=True, color="#c0392b", alpha=0.15,
                        label="Desaceleración Relativa")
    apply_impact_style(ax_dvol, "Diferencia en Tasa de Crecimiento del Crédito (Real - Sin Ayuda)", "Variación Logarítmica")
    
    # Subplot B: Variación Mensual de Morosidad (Real - Sin Ayuda)
    ax_dmor.plot(diff_impact.index, diff_impact["D_Mora_total_impact"], color=c_mora, linewidth=2.5, label="Diferencia en Variación")
    ax_dmor.fill_between(diff_impact.index, diff_impact["D_Mora_total_impact"], 0, 
                        where=(diff_impact["D_Mora_total_impact"] <= 0), interpolate=True, color=c_mora, alpha=0.2,
                        label="Reducción Mensual de Morosidad")
    ax_dmor.fill_between(diff_impact.index, diff_impact["D_Mora_total_impact"], 0, 
                        where=(diff_impact["D_Mora_total_impact"] > 0), interpolate=True, color="#27ae60", alpha=0.25,
                        label="Incremento Mensual de Morosidad")
    apply_impact_style(ax_dmor, "Diferencia en Variación Mensual de Morosidad (Real - Sin Ayuda)", "Puntos Porcentuales")
    
    fig_diff.suptitle("Diferencia Neta entre Escenario Real Observado y Contrafactual Sin Ayuda\n(Cuantificación del Efecto del Rescate Gubernamental en Diferencias)", 
                      fontsize=14, fontweight="bold", y=0.98, color="#111111")
    fig_diff.tight_layout()
    fig_diff.savefig(plots_dir / "impacto_diferencias_panel.png", dpi=300)
    plt.close(fig_diff)
    
    print("\n" + "="*50)
    print("¡Gráficos de impacto neto generados con éxito!")
    print(f"Panel de Impacto en Niveles: {plots_dir / 'impacto_niveles_panel.png'}")
    print(f"Panel de Impacto en Diferencias: {plots_dir / 'impacto_diferencias_panel.png'}")
    print("="*50)

if __name__ == "__main__":
    main()
