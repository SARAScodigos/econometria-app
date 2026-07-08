"""
Baseline SIN COVID (mundo normal):
- Estima VARX pre-COVID segun la ventana configurada
- Pronostica exógenas con AR(p) elegido por BIC
- Simula endógenas H meses hacia adelante con innovaciones = 0
- Reconstruye niveles (Vol_total y Mora_total) desde 2020-02

Coloca este archivo en la misma carpeta que tus scripts.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.ar_model import AutoReg

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    INPUT_FILE, DATE_COL, ENDOG, EXOG, TRAIN_START, TRAIN_END, SCENARIO_START,
    H, MAX_LAG, OUT_DIR, configure_runtime
)
from src.data.loader import slice_window
from src.diagnostics.diagnostics import estimate_varx_ols, stability_roots, residual_diagnostics


# ----------------------------
# Utilidades
# ----------------------------
def load_full_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.set_index(DATE_COL).sort_index()
    # índice mensual normalizado al primer día del mes (como ya haces)
    df.index = pd.to_datetime(df.index.date)
    return df


def pick_varx_lag_by_bic(df_pre: pd.DataFrame, p_max=12, alpha=0.05, use_whiteness=True):
    """
    Elige p por BIC total (suma de BIC por ecuación) sujeto a:
    - estabilidad (raíces < 1)
    - (opcional) Ljung-Box pvalue > alpha en todas las ecuaciones
    Si no encuentra ninguno, retorna p=12.
    """
    best = None
    for p in range(1, p_max + 1):
        try:
            fit = estimate_varx_ols(df_pre, p)
            eigvals = stability_roots(fit["A"])
            stable = bool(np.all(np.abs(eigvals) < 1))

            # BIC total (suma)
            bic_total = float(np.sum([fit["results"][y].bic for y in ENDOG]))

            ok_white = True
            if use_whiteness:
                resid = np.column_stack([fit["results"][y].resid for y in ENDOG])
                diag = residual_diagnostics(resid, lags=12)
                ok_white = bool((diag["lb_pvalue"] > alpha).all())

            if stable and ok_white:
                if (best is None) or (bic_total < best["bic_total"]):
                    best = {
                        "p": p, "fit": fit, "bic_total": bic_total,
                        "stable": stable, "ok_white": ok_white
                    }
        except Exception:
            continue

    if best is None:
        # fallback duro a 12
        p = 12
        fit = estimate_varx_ols(df_pre, p)
        return p, fit, {"note": "fallback_p12"}
    return best["p"], best["fit"], best


def fit_ar_bic(series: pd.Series, p_max=12):
    """
    Ajusta AR(p) para p=1..p_max y elige p por BIC.
    """
    y = series.dropna().astype(float)
    best = None
    for p in range(1, p_max + 1):
        try:
            model = AutoReg(y, lags=p, old_names=False).fit()
            bic = float(model.bic)
            if (best is None) or (bic < best["bic"]):
                best = {"p": p, "model": model, "bic": bic}
        except Exception:
            continue
    if best is None:
        raise ValueError("No pude ajustar ningún AR(p). Revisa la serie.")
    return best["model"], best["p"], best["bic"]


def forecast_ar(model, steps: int, start_date: pd.Timestamp):
    """
    Pronóstico AR para 'steps' meses, devolviendo serie con índice mensual.
    """
    fc = model.forecast(steps=steps)
    idx = pd.date_range(start=start_date, periods=steps, freq="MS")
    return pd.Series(fc, index=idx)


def simulate_varx_baseline(df_all: pd.DataFrame, fit, p: int, exog_future: pd.DataFrame):
    """
    Simula y_t (ENDOG) desde SCENARIO_START por H meses con innovaciones = 0.
    Usa la ecuación estimada (params por ecuación) y alimenta:
    - rezagos endógenos: observados hasta 2020-02 + simulados
    - exógenas: exog_future (índice MS)
    """
    start = pd.to_datetime(SCENARIO_START)
    idx = pd.date_range(start=start, periods=H, freq="MS")

    # contenedor de simulación
    y_sim = pd.DataFrame(index=idx, columns=ENDOG, dtype=float)

    # historial endógeno: necesitamos valores desde (2020-02 - p meses) hasta 2020-02
    hist_start = (pd.to_datetime(TRAIN_END) - pd.offsets.MonthBegin(p))
    hist_idx = pd.date_range(start=hist_start, end=pd.to_datetime(TRAIN_END), freq="MS")

    y_hist = df_all.loc[hist_idx, ENDOG].copy()
    if y_hist.isna().any().any():
        raise ValueError("Faltan datos endógenos en el historial requerido para la simulación.")

    # simula iterativamente
    for t in idx:
        # construir vector X en el mismo orden que en la estimación
        x_cols = list(fit["X_columns"])
        x_vec = []

        for name in x_cols:
            if name == "const":
                x_vec.append(1.0)
                continue

            if "_L" in name:
                base, Lk = name.rsplit("_L", 1)
                k = int(Lk)
                lag_date = (t - pd.offsets.MonthBegin(k)).normalize()
                lag_date = pd.to_datetime(lag_date.date())

                # rezagos pueden estar en historia o ya simulados
                if lag_date in y_sim.index:
                    x_vec.append(float(y_sim.loc[lag_date, base]))
                else:
                    x_vec.append(float(y_hist.loc[lag_date, base]))
                continue

            if name in EXOG:
                x_vec.append(float(exog_future.loc[t, name]))
                continue

            raise ValueError(f"No reconozco regressor: {name}")

        x_vec = np.array(x_vec, dtype=float)

        # y_t = X_t * beta (innovación = 0)
        for i, ycol in enumerate(ENDOG):
            params = fit["results"][ycol].params
            y_sim.loc[t, ycol] = float(np.dot(x_vec, params))

    return y_sim


def diffs_to_levels(df_all: pd.DataFrame, diffs: pd.DataFrame):
    """
    Reconstruye niveles desde TRAIN_END:
    - Mora_total_level = Mora_total(TRAIN_END) + cumsum(D_Mora_total)
    - Vol_total_level = exp( ln(Vol_total(TRAIN_END)) + cumsum(D_ln_Vol_total) )
    """
    base_date = pd.to_datetime(TRAIN_END)
    vol0 = float(df_all.loc[base_date, "Vol_total"])
    mora0 = float(df_all.loc[base_date, "Mora_total"])

    if vol0 <= 0:
        raise ValueError(f"Vol_total en {TRAIN_END} debe ser positivo para reconstruccion log.")

    lnvol0 = float(np.log(vol0))

    out = diffs.copy()
    out["Mora_total_baseline"] = mora0 + out["D_Mora_total"].cumsum()
    out["Ln_Vol_total_baseline"] = lnvol0 + out["D_ln_Vol_total"].cumsum()
    out["Vol_total_baseline"] = np.exp(out["Ln_Vol_total_baseline"])
    return out


def main():
    configure_runtime()

    # 1) cargar excel completo
    df_all = load_full_excel(INPUT_FILE)

    # 2) armar dataset VARX (solo columnas necesarias y sin NA)
    needed = ENDOG + EXOG
    df_use = df_all[needed].copy().dropna()

    # ventana pre-COVID
    df_pre = slice_window(df_use, "pre_covid")

    # 3) elegir p por BIC (+ estabilidad; + opcional Ljung-Box)
    p, fit, info = pick_varx_lag_by_bic(df_pre, p_max=MAX_LAG, use_whiteness=True)
    print("=== BASELINE SIN COVID ===")
    print(f"Ventana pre-COVID: {TRAIN_START} a {TRAIN_END}")
    print(f"p seleccionado = {p} | info = {info}")

    # 4) estimar AR para exogenas y pronosticar H meses desde SCENARIO_START
    start_fc = pd.to_datetime(SCENARIO_START)
    exog_future = pd.DataFrame(index=pd.date_range(start=start_fc, periods=H, freq="MS"))

    ar_specs = {}
    for x in EXOG:
        ar_model, ar_p, ar_bic = fit_ar_bic(df_pre[x], p_max=12)
        exog_future[x] = forecast_ar(ar_model, steps=H, start_date=start_fc)
        ar_specs[x] = {"ar_p": ar_p, "bic": ar_bic}
        print(f"AR({ar_p}) para {x} | BIC={ar_bic:.3f}")

    # 4.b) mostrar y guardar serie proyectada de PBI
    pbi_diff_col = "D_ln_PBI_Desestacionalizado"
    pbi_level_col = "PBI_Desestacionalizado"
    if pbi_diff_col in exog_future.columns:
        pbi_proj = exog_future[[pbi_diff_col]].copy()
        if pbi_level_col in df_all.columns:
            base_date = pd.to_datetime(TRAIN_END)
            pbi0 = float(df_all.loc[base_date, pbi_level_col])
            if pbi0 > 0:
                ln_pbi0 = float(np.log(pbi0))
                pbi_proj["Ln_PBI_baseline"] = ln_pbi0 + pbi_proj[pbi_diff_col].cumsum()
                pbi_proj["PBI_baseline"] = np.exp(pbi_proj["Ln_PBI_baseline"])
        print("Serie PBI proyectada (baseline):")
        print(pbi_proj.to_string())
        pbi_out_path = os.path.join(OUT_DIR, "pbi_proyectado_baseline.csv")
        pbi_proj.to_csv(pbi_out_path, index_label="fecha")
        print(f"PBI proyectado guardado en: {pbi_out_path}")
    else:
        print("No encontré D_ln_PBI_Desestacionalizado en exógenas. No se guarda PBI proyectado.")

    # 5) simular baseline endógeno (en diferencias)
    y_base = simulate_varx_baseline(df_use, fit, p, exog_future)

    # renombrar para claridad
    y_base = y_base.rename(columns={
        "D_ln_Vol_total": "D_ln_Vol_total",
        "D_Mora_total": "D_Mora_total"
    })

    # 6) reconstruir niveles si están disponibles
    baseline = y_base.copy()
    if ("Vol_total" in df_all.columns) and ("Mora_total" in df_all.columns):
        baseline = diffs_to_levels(df_all, baseline)
        print("Reconstrucción a niveles: OK (Vol_total_baseline, Mora_total_baseline).")
    else:
        print("No encontré Vol_total/Mora_total en el Excel. Solo entrego diferencias.")

    # 7) guardar outputs
    out_path = os.path.join(OUT_DIR, "baseline_sin_covid.csv")
    baseline.to_csv(out_path, index_label="fecha")
    print(f"Baseline guardado en: {out_path}")

    # también guarda exógenas pronosticadas
    ex_path = os.path.join(OUT_DIR, "exog_forecast_ar.csv")
    exog_future.to_csv(ex_path, index_label="fecha")
    print(f"Exógenas AR guardadas en: {ex_path}")


if __name__ == "__main__":
    main()
