"""
Validación predictiva fuera de muestra del modelo VARX.
Calcula métricas de error (RMSE, MAE, MAPE, Theil-U) para evaluar:
1. La capacidad predictiva en régimen normal (Backtesting Pre-COVID: 2018-2019).
2. El ajuste del modelo en el periodo COVID (2020-2022) bajo la intervención.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    VARX_MODEL_FILE,
    DATE_COL,
    ENDOG,
    ENDOG_LEVELS,
    EXOG,
    OUT_DIR,
    configure_runtime,
)
from src.data.loader import load_and_prepare
from src.diagnostics.diagnostics import estimate_varx_ols
from src.scenarios.simulate_varx import simulate_varx_path, reconstruct_total_levels

# Métricas de error clásicas
def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))

def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    # Evitar divisiones por cero o valores insignificantes
    mask = np.abs(y_true) > 1e-5
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)

def theil_u(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coeficiente de desigualdad U de Theil (U1). Rango: [0, 1]."""
    num = np.sqrt(np.mean((y_true - y_pred) ** 2))
    den = np.sqrt(np.mean(y_true ** 2)) + np.sqrt(np.mean(y_pred ** 2))
    if den < 1e-8:
        return 0.0
    return float(num / den)

def get_metrics_series(y_true: pd.Series, y_pred: pd.Series, name: str) -> pd.Series:
    y_t = y_true.dropna().to_numpy()
    y_p = y_pred.reindex(y_true.index).dropna().to_numpy()
    
    # Sincronizar tamaños
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

def main():
    configure_runtime()
    
    # 1. Cargar datos preparados y crudos
    df_prepared = load_and_prepare(VARX_MODEL_FILE)
    df_raw = pd.read_excel(VARX_MODEL_FILE)
    df_raw[DATE_COL] = pd.to_datetime(df_raw[DATE_COL])
    df_raw = df_raw.set_index(DATE_COL).sort_index()
    df_raw.index = pd.to_datetime(df_raw.index.date)
    
    # ==========================================================
    # VALIDACIÓN 1: RÉGIMEN NORMAL (Pre-COVID, 2018-2019)
    # ==========================================================
    # Entrenar desde el inicio (2002-01-01) hasta 2017-12-01
    train_end = "2017-12-01"
    val_start = "2018-01-01"
    val_end = "2019-12-01"
    p = 12
    
    # Filtrar ventana de entrenamiento y estimar modelo
    df_train = df_prepared.loc[:train_end].copy()
    fit_normal = estimate_varx_ols(df_train, p)
    
    # Generar predicciones fuera de muestra
    val_idx = pd.date_range(val_start, val_end, freq="MS")
    exog_val = df_prepared.loc[val_idx, EXOG].copy()
        
    pred_diff_normal = simulate_varx_path(
        df_history=df_prepared.loc[:train_end],
        fit=fit_normal,
        endog_cols=ENDOG,
        exog_future=exog_val,
        start=val_start,
        end=val_end
    )
    
    # Reconstruir niveles
    pred_lvl_normal = reconstruct_total_levels(
        raw_df=df_raw,
        diffs=pred_diff_normal,
        base_date=train_end,
        suffix="pred_normal"
    )
    
    # Obtener valores reales observados para la validación
    real_diff = df_prepared.loc[val_idx, ENDOG]
    real_lvl = df_raw.loc[val_idx, ENDOG_LEVELS]
    
    # Calcular métricas para el periodo de validación normal
    metrics_normal = []
    # Diferencias
    metrics_normal.append(get_metrics_series(real_diff["D_ln_Vol_total"], pred_diff_normal["D_ln_Vol_total"], "D_ln_Vol_total (Dif)"))
    metrics_normal.append(get_metrics_series(real_diff["D_Mora_total"], pred_diff_normal["D_Mora_total"], "D_Mora_total (Dif)"))
    # Niveles
    metrics_normal.append(get_metrics_series(real_lvl["Vol_total"], pred_lvl_normal["Vol_total_pred_normal"], "Vol_total (Nivel)"))
    metrics_normal.append(get_metrics_series(real_lvl["Mora_total"], pred_lvl_normal["Mora_total_pred_normal"], "Mora_total (Nivel)"))
    df_metrics_normal = pd.DataFrame(metrics_normal)
    
    # ==========================================================
    # VALIDACIÓN 2: PERIODO COVID (2020-03-01 a 2022-12-01)
    # ==========================================================
    # Cargamos el escenario simulado "con ayuda" obtenido del modelo completo
    # Estimar el modelo completo
    fit_full = estimate_varx_ols(df_prepared, p)
    covid_start = "2020-03-01"
    covid_end = "2022-12-01"
    covid_idx = pd.date_range(covid_start, covid_end, freq="MS")
    
    exog_covid = df_prepared.loc[covid_idx, EXOG].copy()
        
    pred_diff_covid = simulate_varx_path(
        df_history=df_prepared,
        fit=fit_full,
        endog_cols=ENDOG,
        exog_future=exog_covid,
        start=covid_start,
        end=covid_end
    )
    
    pred_lvl_covid = reconstruct_total_levels(
        raw_df=df_raw,
        diffs=pred_diff_covid,
        base_date="2020-02-01",  # Un mes antes del shock
        suffix="pred_covid"
    )
    
    real_diff_covid = df_prepared.loc[covid_idx, ENDOG]
    real_lvl_covid = df_raw.loc[covid_idx, ENDOG_LEVELS]
    
    # Calcular métricas para el periodo de validación COVID
    metrics_covid = []
    # Diferencias
    metrics_covid.append(get_metrics_series(real_diff_covid["D_ln_Vol_total"], pred_diff_covid["D_ln_Vol_total"], "D_ln_Vol_total (Dif)"))
    metrics_covid.append(get_metrics_series(real_diff_covid["D_Mora_total"], pred_diff_covid["D_Mora_total"], "D_Mora_total (Dif)"))
    # Niveles
    metrics_covid.append(get_metrics_series(real_lvl_covid["Vol_total"], pred_lvl_covid["Vol_total_pred_covid"], "Vol_total (Nivel)"))
    metrics_covid.append(get_metrics_series(real_lvl_covid["Mora_total"], pred_lvl_covid["Mora_total_pred_covid"], "Mora_total (Nivel)"))
    df_metrics_covid = pd.DataFrame(metrics_covid)
    
    # ==========================================================
    # EXPORTAR Y MOSTRAR RESULTADOS
    # ==========================================================
    output_path = Path(OUT_DIR) / "resultados_validacion.xlsx"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_metrics_normal.to_excel(writer, sheet_name="Val_Normal_2018_2019", index=False)
        df_metrics_covid.to_excel(writer, sheet_name="Val_COVID_2020_2022", index=False)
        
    print("\n" + "="*50)
    print("=== VALIDACIÓN DE CAPACIDAD PREDICTIVA (VARX) ===")
    print(f"Resultados guardados en: {output_path}")
    print("\n1) Muestra Normal (Pre-COVID: 2018-01 a 2019-12) - Fuera de Muestra:")
    print(df_metrics_normal.to_string(index=False))
    print("\n2) Muestra con Shock (COVID: 2020-03 a 2022-12) - Simulación con Ayuda:")
    print(df_metrics_covid.to_string(index=False))
    print("="*50)

if __name__ == "__main__":
    main()
