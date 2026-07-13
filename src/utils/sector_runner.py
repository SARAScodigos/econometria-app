"""
Utilidad central para ejecutar el pipeline de modelamiento, simulación,
validación y graficación de un tipo de crédito sectorial (CMAC).
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    VARX_MODEL_FILE,
    DATE_COL,
    EXOG,
    SECTOR_CONFIG,
    SAMPLE_START,
    SAMPLE_END,
    TRAIN_END,
    SCENARIO_START,
    SCENARIO_END,
    OUT_DIR,
    MAX_LAG,
    configure_runtime,
)
from src.data.loader import load_and_prepare, slice_window
from src.diagnostics.diagnostics import (
    estimate_varx_ols,
    stability_roots,
    residual_diagnostics,
    varx_diagnostics,
    coefficient_table,
)
from src.scenarios.simulate_varx import simulate_varx_path, apply_exog_overrides

# Helper para métricas de error
def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))

def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = np.abs(y_true) > 1e-5
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)

def theil_u(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    num = np.sqrt(np.mean((y_true - y_pred) ** 2))
    den = np.sqrt(np.mean(y_true ** 2)) + np.sqrt(np.mean(y_pred ** 2))
    if den < 1e-8:
        return 0.0
    return float(num / den)

def get_metrics_series(y_true: pd.Series, y_pred: pd.Series, name: str) -> pd.Series:
    y_t = y_true.dropna().to_numpy()
    y_p = y_pred.reindex(y_true.index).dropna().to_numpy()
    min_len = min(len(y_t), len(y_p))
    y_t = y_t[:min_len]
    y_p = y_p[:min_len]
    return pd.Series({
        "Variable": name,
        "RMSE": rmse(y_t, y_p),
        "MAE": mae(y_t, y_p),
        "MAPE (%)": mape(y_t, y_p),
        "Theil-U": theil_u(y_t, y_p)
    })

# Helper genérico para reconstruir niveles sectoriales
def reconstruct_sector_levels(
    raw_df: pd.DataFrame,
    diffs: pd.DataFrame,
    base_date: str,
    vol_col: str,
    mora_col: str,
    diff_vol_col: str,
    diff_mora_col: str,
    suffix: str,
) -> pd.DataFrame:
    base_dt = pd.to_datetime(base_date)
    vol0 = float(raw_df.loc[base_dt, vol_col])
    mora0 = float(raw_df.loc[base_dt, mora_col])
    if vol0 <= 0:
        raise ValueError(f"Volumen base de {vol_col} debe ser positivo para reconstruir logaritmos")

    out = pd.DataFrame(index=diffs.index)
    out[f"Ln_{vol_col}_{suffix}"] = np.log(vol0) + diffs[diff_vol_col].cumsum()
    out[f"{vol_col}_{suffix}"] = np.exp(out[f"Ln_{vol_col}_{suffix}"])
    out[f"{mora_col}_{suffix}"] = mora0 + diffs[diff_mora_col].cumsum()
    return out

def system_information_criteria(fit: dict, n_obs: int, endog_cols, exog_cols) -> tuple[float, float]:
    """Calcula AIC/BIC multivariado del sistema VARX."""
    sign, logdet = np.linalg.slogdet(fit["Sigma"])
    if sign <= 0:
        return np.nan, np.nan

    k_endog = len(endog_cols)
    k_exog = len(exog_cols)
    p = int(fit["p"])
    params_per_eq = 1 + k_endog * p + k_exog
    params_system = k_endog * params_per_eq

    aic = logdet + (2 * params_system / n_obs)
    bic = logdet + (np.log(n_obs) * params_system / n_obs)
    return float(aic), float(bic)

def apply_scientific_style(ax, start_date, title, ylabel, show_legend=True):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')
    ax.tick_params(colors='#333333', which='both')
    ax.grid(True, linestyle="--", alpha=0.5, color="#cccccc")
    ax.set_title(title, fontsize=11, fontweight='bold', pad=10, color='#111111')
    ax.set_ylabel(ylabel, fontsize=9, fontweight='semibold', color='#333333')
    ax.set_xlabel("Fecha", fontsize=9, fontweight='semibold', color='#333333')
    
    ax.set_xlim(pd.Timestamp(start_date), pd.Timestamp(SCENARIO_END))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    
    ax.axvline(pd.Timestamp(SCENARIO_START), color='#7f8c8d', linestyle=':', linewidth=1.5, alpha=0.9, label='Shock COVID-19 (Marzo 2020)')
    ax.axvspan(pd.Timestamp(SCENARIO_START), pd.Timestamp(SCENARIO_END), color='#f1f2f6', alpha=0.5, label='Periodo de Escenario')
    if show_legend:
        ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="none", framealpha=0.85, fontsize=8)

def run_sector_pipeline(sector_name: str) -> None:
    """Ejecuta el pipeline completo de estimación, simulación y validación de un sector."""
    configure_runtime()
    
    if sector_name not in SECTOR_CONFIG:
        raise ValueError(f"Sector '{sector_name}' no definido en SECTOR_CONFIG de settings.py")
        
    config = SECTOR_CONFIG[sector_name]
    endog_cols = config["ENDOG"]
    endog_levels = config["ENDOG_LEVELS"]
    diff_vol_col = endog_cols[0]
    diff_mora_col = endog_cols[1]
    vol_col = endog_levels[0]
    mora_col = endog_levels[1]
    
    output_dir = Path(OUT_DIR) / f"resultados_{sector_name}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n==================================================")
    print(f"INICIANDO PIPELINE SECTORIAL: {sector_name.upper()}")
    print(f"Endógenas: {endog_cols}")
    print(f"Niveles: {endog_levels}")
    print(f"Resultados en: {output_dir}")
    print(f"==================================================")
    
    # Cargar datos
    df_prepared = load_and_prepare(VARX_MODEL_FILE, needed=endog_cols + EXOG)
    df_raw = pd.read_excel(VARX_MODEL_FILE)
    df_raw[DATE_COL] = pd.to_datetime(df_raw[DATE_COL])
    df_raw = df_raw.set_index(DATE_COL).sort_index()
    df_raw.index = pd.to_datetime(df_raw.index.date)
    
    # 1. SELECCIÓN DE REZAGOS (LAG SELECTION) - Ventana Pre-COVID
    df_pre = slice_window(df_prepared, "pre_covid")
    
    lag_rows = []
    best_p = 12
    best_fit = None
    
    print("\n--- Evaluación de Criterios de Selección de Rezagos (p) ---")
    for p in range(1, MAX_LAG + 1):
        try:
            fit = estimate_varx_ols(df_pre, p, endog_cols=endog_cols)
            eigvals = stability_roots(fit["A"])
            stable = bool(np.all(np.abs(eigvals) < 1))
            resid = np.column_stack([fit["results"][y].resid for y in endog_cols])
            diag = residual_diagnostics(resid, endog_cols=endog_cols, lags=12)
            ok_white = bool((diag["lb_pvalue"] > 0.05).all())
            
            n_obs = len(fit["Y_index"])
            aic_mean = np.mean([fit["results"][y].aic for y in endog_cols])
            bic_mean = np.mean([fit["results"][y].bic for y in endog_cols])
            aic_system, bic_system = system_information_criteria(fit, n_obs, endog_cols, EXOG)
            
            lb_pvals = {f"LB_pvalue_{row['eq']}": float(row['lb_pvalue']) for _, row in diag.iterrows()}
            
            row_dict = {
                "p": p,
                "n_obs": n_obs,
                "AIC_mean": float(aic_mean),
                "BIC_mean": float(bic_mean),
                "AIC_system": float(aic_system),
                "BIC_system": float(bic_system),
                "estable": stable,
                "ruido_blanco": ok_white
            }
            row_dict.update(lb_pvals)
            lag_rows.append(row_dict)
        except Exception:
            continue
            
    df_lag_selection = pd.DataFrame(lag_rows)
    print(df_lag_selection.to_string(index=False))
    
    # Seleccionar p óptimo basado en estabilidad y AIC/BIC del sistema
    df_stable = df_lag_selection[df_lag_selection["estable"] == True]
    
    if not df_stable.empty:
        df_stable_white = df_stable[df_stable["ruido_blanco"] == True]
        if not df_stable_white.empty:
            best_idx = df_stable_white["BIC_system"].idxmin()
            best_p = int(df_stable_white.loc[best_idx, "p"])
            print(f"Criterio: Seleccionado p={best_p} (Min BIC sistema con estabilidad y ruido blanco)")
        else:
            best_idx = df_stable["BIC_system"].idxmin()
            best_p = int(df_stable.loc[best_idx, "p"])
            print(f"Criterio: Seleccionado p={best_p} (Min BIC sistema con estabilidad únicamente)")
        best_fit = estimate_varx_ols(df_pre, best_p, endog_cols=endog_cols)
    else:
        print("Advertencia: Ningún rezago candidato es estable. Fallback p=12.")
        best_p = 12
        best_fit = estimate_varx_ols(df_pre, 12, endog_cols=endog_cols)
        
    print(f"1) Rezago óptimo seleccionado: p = {best_p}")
    
    # 2. ESTIMACIÓN CON MUESTRA COMPLETA (VENTANA FULL)
    df_full = slice_window(df_prepared, "full")
    fit_full = estimate_varx_ols(df_full, best_p, endog_cols=endog_cols)
    
    diagnostics = varx_diagnostics(fit_full, endog_cols=endog_cols, lb_lags=12)
    coefficients = coefficient_table(fit_full, endog_cols=endog_cols, cov_type="HC3")
    
    varx_file_path = output_dir / f"resultados_varx_{sector_name}.xlsx"
    with pd.ExcelWriter(varx_file_path, engine="openpyxl") as writer:
        coefficients.to_excel(writer, sheet_name="Coeficientes_HC3", index=False)
        diagnostics["stability"].to_excel(writer, sheet_name="Estabilidad", index=False)
        diagnostics["stability_roots"].to_excel(writer, sheet_name="Raices_AR", index=False)
        diagnostics["ljung_box"].to_excel(writer, sheet_name="Ljung_Box", index=False)
        diagnostics["jarque_bera"].to_excel(writer, sheet_name="Jarque_Bera", index=False)
        diagnostics["heteroskedasticity"].to_excel(writer, sheet_name="Heterocedasticidad", index=False)
        pd.DataFrame(fit_full["Sigma"], index=endog_cols, columns=endog_cols).to_excel(writer, sheet_name="Sigma_residuos")
        df_lag_selection.to_excel(writer, sheet_name="Seleccion_Rezagos", index=False)
        
    print(f"2) Estimación del modelo exportada a: {varx_file_path}")
    
    # 3. SIMULACIÓN DE ESCENARIOS CONTRAFACTUALES
    scenario_idx = pd.date_range(SCENARIO_START, SCENARIO_END, freq="MS")
    exog_observed = df_full.loc[scenario_idx, EXOG].copy()
    exog_no_aid = apply_exog_overrides(exog_observed, {"D_Intervencion_Gob": 0})
    
    # Simular con ayuda
    pred_observed = simulate_varx_path(
        df_history=df_full,
        fit=fit_full,
        endog_cols=endog_cols,
        exog_future=exog_observed,
        start=SCENARIO_START,
        end=SCENARIO_END
    )
    # Simular sin ayuda
    pred_no_aid = simulate_varx_path(
        df_history=df_full,
        fit=fit_full,
        endog_cols=endog_cols,
        exog_future=exog_no_aid,
        start=SCENARIO_START,
        end=SCENARIO_END
    )
    
    real_diff = df_full.loc[scenario_idx, endog_cols].copy()
    
    # Combinar diferencias
    diffs = pd.concat([
        real_diff.add_suffix("_real"),
        pred_observed.add_suffix("_pred_observado"),
        pred_no_aid.add_suffix("_pred_sin_ayuda")
    ], axis=1)
    
    # Reconstruir niveles
    levels_real = df_raw.loc[scenario_idx, endog_levels].rename(
        columns={vol_col: f"{vol_col}_real", mora_col: f"{mora_col}_real"}
    )
    levels_observed = reconstruct_sector_levels(
        df_raw, pred_observed, "2020-02-01", vol_col, mora_col, diff_vol_col, diff_mora_col, "pred_observado"
    )
    levels_no_aid = reconstruct_sector_levels(
        df_raw, pred_no_aid, "2020-02-01", vol_col, mora_col, diff_vol_col, diff_mora_col, "pred_sin_ayuda"
    )
    
    levels = pd.concat([levels_real, levels_observed, levels_no_aid], axis=1)
    
    # Calcular impactos netos
    diffs[f"{diff_vol_col}_impacto_ayuda"] = diffs[f"{diff_vol_col}_real"] - diffs[f"{diff_vol_col}_pred_sin_ayuda"]
    diffs[f"{diff_mora_col}_impacto_ayuda"] = diffs[f"{diff_mora_col}_real"] - diffs[f"{diff_mora_col}_pred_sin_ayuda"]
    
    levels[f"{vol_col}_impacto_ayuda"] = levels[f"{vol_col}_real"] - levels[f"{vol_col}_pred_sin_ayuda"]
    levels[f"{mora_col}_impacto_ayuda"] = levels[f"{mora_col}_real"] - levels[f"{mora_col}_pred_sin_ayuda"]
    
    scenario_file_path = output_dir / f"escenario_{sector_name}_sin_intervencion.xlsx"
    with pd.ExcelWriter(scenario_file_path, engine="openpyxl") as writer:
        diffs.to_excel(writer, sheet_name="Diferencias", index_label="fecha")
        levels.to_excel(writer, sheet_name="Niveles", index_label="fecha")
        
    print(f"3) Escenarios simulados exportados a: {scenario_file_path}")
    
    # 4. VALIDACIÓN PREDICTIVA (BACKTESTING)
    # A. Periodo Normal (Pre-COVID, 2018-2019)
    train_end_normal = "2017-12-01"
    val_start_normal = "2018-01-01"
    val_end_normal = "2019-12-01"
    val_idx_normal = pd.date_range(val_start_normal, val_end_normal, freq="MS")
    
    df_train_val = df_prepared.loc[:train_end_normal].copy()
    fit_val_normal = estimate_varx_ols(df_train_val, best_p, endog_cols=endog_cols)
    
    exog_val_normal = df_prepared.loc[val_idx_normal, EXOG].copy()
    pred_diff_val_normal = simulate_varx_path(
        df_history=df_prepared.loc[:train_end_normal],
        fit=fit_val_normal,
        endog_cols=endog_cols,
        exog_future=exog_val_normal,
        start=val_start_normal,
        end=val_end_normal
    )
    
    pred_lvl_val_normal = reconstruct_sector_levels(
        df_raw, pred_diff_val_normal, train_end_normal, vol_col, mora_col, diff_vol_col, diff_mora_col, "pred_normal"
    )
    
    real_diff_normal = df_prepared.loc[val_idx_normal, endog_cols]
    real_lvl_normal = df_raw.loc[val_idx_normal, endog_levels]
    
    metrics_normal = []
    metrics_normal.append(get_metrics_series(real_diff_normal[diff_vol_col], pred_diff_val_normal[diff_vol_col], f"{diff_vol_col} (Dif)"))
    metrics_normal.append(get_metrics_series(real_diff_normal[diff_mora_col], pred_diff_val_normal[diff_mora_col], f"{diff_mora_col} (Dif)"))
    metrics_normal.append(get_metrics_series(real_lvl_normal[vol_col], pred_lvl_val_normal[f"{vol_col}_pred_normal"], f"{vol_col} (Nivel)"))
    metrics_normal.append(get_metrics_series(real_lvl_normal[mora_col], pred_lvl_val_normal[f"{mora_col}_pred_normal"], f"{mora_col} (Nivel)"))
    df_metrics_normal = pd.DataFrame(metrics_normal)
    
    # B. Periodo COVID (2020-03 a 2022-12)
    metrics_covid = []
    metrics_covid.append(get_metrics_series(real_diff[diff_vol_col], pred_observed[diff_vol_col], f"{diff_vol_col} (Dif)"))
    metrics_covid.append(get_metrics_series(real_diff[diff_mora_col], pred_observed[diff_mora_col], f"{diff_mora_col} (Dif)"))
    metrics_covid.append(get_metrics_series(levels[f"{vol_col}_real"], levels[f"{vol_col}_pred_observado"], f"{vol_col} (Nivel)"))
    metrics_covid.append(get_metrics_series(levels[f"{mora_col}_real"], levels[f"{mora_col}_pred_observado"], f"{mora_col} (Nivel)"))
    df_metrics_covid = pd.DataFrame(metrics_covid)
    
    validation_file_path = output_dir / f"resultados_validacion_{sector_name}.xlsx"
    with pd.ExcelWriter(validation_file_path, engine="openpyxl") as writer:
        df_metrics_normal.to_excel(writer, sheet_name="Val_Normal_2018_2019", index=False)
        df_metrics_covid.to_excel(writer, sheet_name="Val_COVID_2020_2022", index=False)
        
    print(f"4) Resultados de validación exportados a: {validation_file_path}")
    
    # ==========================================================
    # 5. GENERACIÓN DE GRÁFICOS CIENTÍFICOS
    # ==========================================================
    PLOT_START = "2018-01-01"
    full_plot_idx = pd.date_range(start=PLOT_START, end=levels.index[-1], freq="MS")
    
    levels_comb = pd.DataFrame(index=full_plot_idx)
    diffs_comb = pd.DataFrame(index=full_plot_idx)
    
    hist_plot_idx = full_plot_idx[full_plot_idx < pd.Timestamp(SCENARIO_START)]
    scen_plot_idx = full_plot_idx[full_plot_idx >= pd.Timestamp(SCENARIO_START)]
    
    for suffix in ["_real", "_pred_observado", "_pred_sin_ayuda"]:
        # Niveles
        levels_comb.loc[hist_plot_idx, f"{vol_col}{suffix}"] = df_raw.loc[hist_plot_idx, vol_col]
        levels_comb.loc[scen_plot_idx, f"{vol_col}{suffix}"] = levels.loc[scen_plot_idx, f"{vol_col}{suffix}"]
        
        levels_comb.loc[hist_plot_idx, f"{mora_col}{suffix}"] = df_raw.loc[hist_plot_idx, mora_col]
        levels_comb.loc[scen_plot_idx, f"{mora_col}{suffix}"] = levels.loc[scen_plot_idx, f"{mora_col}{suffix}"]
        
        # Diferencias
        diffs_comb.loc[hist_plot_idx, f"{diff_vol_col}{suffix}"] = df_prepared.loc[hist_plot_idx, diff_vol_col]
        diffs_comb.loc[scen_plot_idx, f"{diff_vol_col}{suffix}"] = diffs.loc[scen_plot_idx, f"{diff_vol_col}{suffix}"]
        
        diffs_comb.loc[hist_plot_idx, f"{diff_mora_col}{suffix}"] = df_prepared.loc[hist_plot_idx, diff_mora_col]
        diffs_comb.loc[scen_plot_idx, f"{diff_mora_col}{suffix}"] = diffs.loc[scen_plot_idx, f"{diff_mora_col}{suffix}"]
        
    c_real = "#2c3e50"
    c_pred = "#2980b9"
    c_no_aid = "#c0392b"
    
    # 5.A. GRÁFICO PANEL DE SCENARIOS (NIVELES)
    fig_lvl, (ax_vol, ax_mor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    ax_vol.plot(levels_comb.index, levels_comb[f"{vol_col}_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_vol.plot(levels_comb.index, levels_comb[f"{vol_col}_pred_observado"], color=c_pred, linewidth=2, label="Modelo (Con Ayuda)")
    ax_vol.plot(levels_comb.index, levels_comb[f"{vol_col}_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    apply_scientific_style(ax_vol, PLOT_START, f"Volumen de Crédito - {sector_name.capitalize()}", "Millones de Soles (Nivel)")
    
    ax_mor.plot(levels_comb.index, levels_comb[f"{mora_col}_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_mor.plot(levels_comb.index, levels_comb[f"{mora_col}_pred_observado"], color=c_pred, linewidth=2, label="Modelo (Con Ayuda)")
    ax_mor.plot(levels_comb.index, levels_comb[f"{mora_col}_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    apply_scientific_style(ax_mor, PLOT_START, f"Tasa de Morosidad - {sector_name.capitalize()}", "Porcentaje (%)")
    
    fig_lvl.suptitle(f"Escenarios de Cartera y Morosidad - {sector_name.capitalize()}\nPeriodo: 2018-01 a 2022-12", 
                     fontsize=13, fontweight="bold", y=0.98)
    fig_lvl.tight_layout()
    fig_lvl.savefig(plots_dir / f"escenarios_niveles_panel_{sector_name}.png", dpi=300)
    plt.close(fig_lvl)
    
    # 5.B. GRÁFICO PANEL DE SCENARIOS (DIFERENCIAS)
    fig_diff, (ax_dvol, ax_dmor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    ax_dvol.plot(diffs_comb.index, diffs_comb[f"{diff_vol_col}_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_dvol.plot(diffs_comb.index, diffs_comb[f"{diff_vol_col}_pred_observado"], color=c_pred, linewidth=2, label="Modelo (Con Ayuda)")
    ax_dvol.plot(diffs_comb.index, diffs_comb[f"{diff_vol_col}_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    ax_dvol.axhline(0, color="gray", linewidth=0.8, linestyle="-.")
    apply_scientific_style(ax_dvol, PLOT_START, f"Variación del Volumen (Dif) - {sector_name.capitalize()}", "Variación Logarítmica")
    
    ax_dmor.plot(diffs_comb.index, diffs_comb[f"{diff_mora_col}_real"], color=c_real, linewidth=2.5, label="Observado Real")
    ax_dmor.plot(diffs_comb.index, diffs_comb[f"{diff_mora_col}_pred_observado"], color=c_pred, linewidth=2, label="Modelo (Con Ayuda)")
    ax_dmor.plot(diffs_comb.index, diffs_comb[f"{diff_mora_col}_pred_sin_ayuda"], color=c_no_aid, linewidth=2, linestyle="--", label="Contrafactual (Sin Ayuda)")
    ax_dmor.axhline(0, color="gray", linewidth=0.8, linestyle="-.")
    apply_scientific_style(ax_dmor, PLOT_START, f"Variación de Morosidad (Dif) - {sector_name.capitalize()}", "Puntos Porcentuales")
    
    fig_diff.suptitle(f"Variaciones Mensuales en Diferencias - {sector_name.capitalize()}\nPeriodo: 2018-01 a 2022-12", 
                      fontsize=13, fontweight="bold", y=0.98)
    fig_diff.tight_layout()
    fig_diff.savefig(plots_dir / f"escenarios_diferencias_panel_{sector_name}.png", dpi=300)
    plt.close(fig_diff)
    
    # 5.C. GRÁFICO PANEL DE IMPACTO NETO (REAL - SIN AYUDA) desde 2019/06
    PLOT_IMPACT_START = "2019-06-01"
    impact_plot_idx = pd.date_range(start=PLOT_IMPACT_START, end=levels.index[-1], freq="MS")
    
    lvl_impact = pd.DataFrame(index=impact_plot_idx)
    diff_impact = pd.DataFrame(index=impact_plot_idx)
    
    hist_imp_idx = impact_plot_idx[impact_plot_idx < pd.Timestamp(SCENARIO_START)]
    scen_imp_idx = impact_plot_idx[impact_plot_idx >= pd.Timestamp(SCENARIO_START)]
    
    # Niveles
    lvl_impact.loc[hist_imp_idx, "Vol_impact"] = 0.0
    lvl_impact.loc[scen_imp_idx, "Vol_impact"] = levels.loc[scen_imp_idx, f"{vol_col}_impacto_ayuda"]
    lvl_impact.loc[hist_imp_idx, "Mora_impact"] = 0.0
    lvl_impact.loc[scen_imp_idx, "Mora_impact"] = levels.loc[scen_imp_idx, f"{mora_col}_impacto_ayuda"]
    
    # Diferencias
    diff_impact.loc[hist_imp_idx, "Vol_diff_impact"] = 0.0
    diff_impact.loc[scen_imp_idx, "Vol_diff_impact"] = diffs.loc[scen_imp_idx, f"{diff_vol_col}_impacto_ayuda"]
    diff_impact.loc[hist_imp_idx, "Mora_diff_impact"] = 0.0
    diff_impact.loc[scen_imp_idx, "Mora_diff_impact"] = diffs.loc[scen_imp_idx, f"{diff_mora_col}_impacto_ayuda"]
    
    # Panel de Impacto en Niveles
    fig_imp_lvl, (ax_ivol, ax_imor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    ax_ivol.plot(lvl_impact.index, lvl_impact["Vol_impact"], color="#16a085", linewidth=2.5, label="Impacto Neto (Real - Sin Ayuda)")
    ax_ivol.fill_between(lvl_impact.index, lvl_impact["Vol_impact"], 0, where=(lvl_impact["Vol_impact"] >= 0), interpolate=True, color="#16a085", alpha=0.25, label="Volumen Sostenido")
    ax_ivol.axhline(0, color='#333333', linestyle='-', linewidth=1.2, alpha=0.8)
    apply_scientific_style(ax_ivol, PLOT_IMPACT_START, f"Efecto Neto sobre Volumen de Crédito - {sector_name.capitalize()}", "Millones de Soles")
    
    ax_imor.plot(lvl_impact.index, lvl_impact["Mora_impact"], color="#c0392b", linewidth=2.5, label="Impacto Neto (Real - Sin Ayuda)")
    ax_imor.fill_between(lvl_impact.index, lvl_impact["Mora_impact"], 0, where=(lvl_impact["Mora_impact"] <= 0), interpolate=True, color="#c0392b", alpha=0.2, label="Morosidad Evitada")
    ax_imor.fill_between(lvl_impact.index, lvl_impact["Mora_impact"], 0, where=(lvl_impact["Mora_impact"] > 0), interpolate=True, color="#27ae60", alpha=0.25, label="Incremento en Morosidad")
    ax_imor.axhline(0, color='#333333', linestyle='-', linewidth=1.2, alpha=0.8)
    apply_scientific_style(ax_imor, PLOT_IMPACT_START, f"Efecto Neto sobre Tasa de Morosidad - {sector_name.capitalize()}", "Puntos Porcentuales")
    
    fig_imp_lvl.suptitle(f"Diferencia Neta Real vs. Contrafactual Sin Ayuda - {sector_name.capitalize()}\nPeriodo: 2019-06 a 2022-12", 
                         fontsize=13, fontweight="bold", y=0.98)
    fig_imp_lvl.tight_layout()
    fig_imp_lvl.savefig(plots_dir / f"impacto_niveles_panel_{sector_name}.png", dpi=300)
    plt.close(fig_imp_lvl)
    
    # Panel de Impacto en Diferencias
    fig_imp_diff, (ax_idvol, ax_idmor) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True)
    
    ax_idvol.plot(diff_impact.index, diff_impact["Vol_diff_impact"], color="#16a085", linewidth=2.5, label="Diferencia en Crecimiento")
    ax_idvol.fill_between(diff_impact.index, diff_impact["Vol_diff_impact"], 0, where=(diff_impact["Vol_diff_impact"] >= 0), interpolate=True, color="#16a085", alpha=0.25, label="Impulso Mensual")
    ax_idvol.fill_between(diff_impact.index, diff_impact["Vol_diff_impact"], 0, where=(diff_impact["Vol_diff_impact"] < 0), interpolate=True, color="#c0392b", alpha=0.15, label="Desaceleración")
    ax_idvol.axhline(0, color='#333333', linestyle='-', linewidth=1.2, alpha=0.8)
    apply_scientific_style(ax_idvol, PLOT_IMPACT_START, f"Diferencia en Tasa de Crecimiento del Crédito - {sector_name.capitalize()}", "Variación Logarítmica")
    
    ax_idmor.plot(diff_impact.index, diff_impact["Mora_diff_impact"], color="#c0392b", linewidth=2.5, label="Diferencia en Variación")
    ax_idmor.fill_between(diff_impact.index, diff_impact["Mora_diff_impact"], 0, where=(diff_impact["Mora_diff_impact"] <= 0), interpolate=True, color="#c0392b", alpha=0.2, label="Reducción Mensual")
    ax_idmor.fill_between(diff_impact.index, diff_impact["Mora_diff_impact"], 0, where=(diff_impact["Mora_diff_impact"] > 0), interpolate=True, color="#27ae60", alpha=0.25, label="Incremento Mensual")
    ax_idmor.axhline(0, color='#333333', linestyle='-', linewidth=1.2, alpha=0.8)
    apply_scientific_style(ax_idmor, PLOT_IMPACT_START, f"Diferencia en Variación Mensual de Morosidad - {sector_name.capitalize()}", "Puntos Porcentuales")
    
    fig_imp_diff.suptitle(f"Diferencia Neta en Diferencias Mensuales - {sector_name.capitalize()}\nPeriodo: 2019-06 a 2022-12", 
                          fontsize=13, fontweight="bold", y=0.98)
    fig_imp_diff.tight_layout()
    fig_imp_diff.savefig(plots_dir / f"impacto_diferencias_panel_{sector_name}.png", dpi=300)
    plt.close(fig_imp_diff)
    
    print(f"5) Cuatro paneles de gráficos exportados a: {plots_dir}")
    print(f"==================================================")
    print(f"PIPELINE COMPLETADO CON ÉXITO PARA: {sector_name.upper()}")
    print(f"==================================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_sector_pipeline(sys.argv[1])
    else:
        print("Uso: python sector_runner.py <nombre_del_sector>")
