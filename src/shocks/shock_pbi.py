"""
Shock macro en PBI (Opción 1: observado vs baseline AR en marzo–abril 2020)

- Usa baseline de exógenas (AR) ya guardado en outputs/exog_forecast_ar.csv
- Reemplaza D_ln_PBI_Desestacionalizado en 2020-03 y 2020-04 por el valor observado del Excel
- Simula VARX pre-COVID segun la ventana configurada con innovaciones endogenas=0
- Devuelve:
  (i) trayectoria baseline (sin COVID) de endógenas,
  (ii) trayectoria con shock macro (COVID-macro),
  (iii) gap = shock - baseline

Coloca este archivo al lado de tus scripts.
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    INPUT_FILE, DATE_COL, ENDOG, EXOG, TRAIN_END, SCENARIO_START, SHOCK_MONTHS,
    H, MAX_LAG, OUT_DIR, configure_runtime
)
from src.data.loader import slice_window
from src.diagnostics.diagnostics import estimate_varx_ols, stability_roots, residual_diagnostics


# ----------------------------
# Carga de datos
# ----------------------------
def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.set_index(DATE_COL).sort_index()
    df.index = pd.to_datetime(df.index.date)
    return df


def load_exog_baseline(path: str) -> pd.DataFrame:
    ex = pd.read_csv(path, parse_dates=["fecha"])
    ex = ex.set_index("fecha").sort_index()
    # asegurar freq MS (1er día del mes)
    ex.index = pd.to_datetime(ex.index.date)
    ex = ex.asfreq("MS")
    return ex


# ----------------------------
# Selección de rezagos VARX (igual que baseline)
# ----------------------------
def pick_varx_lag_by_bic(df_pre: pd.DataFrame, p_max=12, alpha=0.05, use_whiteness=True):
    best = None
    for p in range(1, p_max + 1):
        try:
            fit = estimate_varx_ols(df_pre, p)
            eigvals = stability_roots(fit["A"])
            stable = bool(np.all(np.abs(eigvals) < 1))
            bic_total = float(np.sum([fit["results"][y].bic for y in ENDOG]))

            ok_white = True
            if use_whiteness:
                resid = np.column_stack([fit["results"][y].resid for y in ENDOG])
                diag = residual_diagnostics(resid, lags=12)
                ok_white = bool((diag["lb_pvalue"] > alpha).all())

            if stable and ok_white:
                if (best is None) or (bic_total < best["bic_total"]):
                    best = {"p": p, "fit": fit, "bic_total": bic_total}
        except Exception:
            continue

    if best is None:
        p = 12
        fit = estimate_varx_ols(df_pre, p)
        return p, fit, {"note": "fallback_p12"}
    return best["p"], best["fit"], best


# ----------------------------
# Simulación determinística VARX (innovación = 0)
# ----------------------------
def simulate_varx(df_all: pd.DataFrame, fit, p: int, exog_future: pd.DataFrame) -> pd.DataFrame:
    start = pd.to_datetime(SCENARIO_START)
    idx = pd.date_range(start=start, periods=H, freq="MS")

    y_sim = pd.DataFrame(index=idx, columns=ENDOG, dtype=float)

    # historia endógena requerida
    hist_start = (pd.to_datetime(TRAIN_END) - pd.offsets.MonthBegin(p))
    hist_idx = pd.date_range(start=hist_start, end=pd.to_datetime(TRAIN_END), freq="MS")
    y_hist = df_all.loc[hist_idx, ENDOG].copy()
    if y_hist.isna().any().any():
        raise ValueError("Faltan datos endógenos en el historial requerido para la simulación.")

    x_cols = list(fit["X_columns"])

    for t in idx:
        x_vec = []
        for name in x_cols:
            if name == "const":
                x_vec.append(1.0)
                continue

            if "_L" in name:
                base, Lk = name.rsplit("_L", 1)
                k = int(Lk)
                lag_date = pd.to_datetime((t - pd.offsets.MonthBegin(k)).date())
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

        for ycol in ENDOG:
            params = fit["results"][ycol].params
            y_sim.loc[t, ycol] = float(np.dot(x_vec, params))

    return y_sim


def diffs_to_levels(df_all: pd.DataFrame, diffs: pd.DataFrame) -> pd.DataFrame:
    base_date = pd.to_datetime(TRAIN_END)
    vol0 = float(df_all.loc[base_date, "Vol_total"])
    mora0 = float(df_all.loc[base_date, "Mora_total"])
    if vol0 <= 0:
        raise ValueError(f"Vol_total en {TRAIN_END} debe ser positivo.")

    lnvol0 = float(np.log(vol0))

    out = diffs.copy()
    out["Mora_total_level"] = mora0 + out["D_Mora_total"].cumsum()
    out["Ln_Vol_total_level"] = lnvol0 + out["D_ln_Vol_total"].cumsum()
    out["Vol_total_level"] = np.exp(out["Ln_Vol_total_level"])
    return out


# ----------------------------
# Construcción exógenas con shock PBI (Opción 1)
# ----------------------------
def build_exog_with_pbi_shock(df_all: pd.DataFrame, exog_base: pd.DataFrame) -> pd.DataFrame:
    ex = exog_base.copy()

    # tomamos observado solo para D_ln_PBI_Desestacionalizado en 2020-03 y 2020-04
    for m in SHOCK_MONTHS:
        d = pd.to_datetime(m)
        # valor observado en el excel
        obs = float(df_all.loc[d, "D_ln_PBI_Desestacionalizado"])
        # baseline AR
        base = float(ex.loc[d, "D_ln_PBI_Desestacionalizado"])
        shock = obs - base
        # aplicar (equivale a reemplazar por el observado)
        ex.loc[d, "D_ln_PBI_Desestacionalizado"] = base + shock

    return ex


def main():
    configure_runtime()

    df_all = load_excel(INPUT_FILE)

    # dataset para estimación VARX
    df_use = df_all[ENDOG + EXOG].dropna()
    df_pre = slice_window(df_use, "pre_covid")

    # 1) elegir p y estimar VARX pre-COVID
    p, fit, info = pick_varx_lag_by_bic(df_pre, p_max=MAX_LAG, use_whiteness=True)
    print("=== SHOCK MACRO (PBI) ===")
    print(f"p seleccionado = {p} | info = {info}")

    # 2) cargar exógenas baseline (AR) ya generadas
    ex_path = os.path.join(OUT_DIR, "exog_forecast_ar.csv")
    exog_base = load_exog_baseline(ex_path)

    # asegurar horizonte H y fechas correctas
    start = pd.to_datetime(SCENARIO_START)
    idx = pd.date_range(start=start, periods=H, freq="MS")
    exog_base = exog_base.reindex(idx)
    if exog_base.isna().any().any():
        raise ValueError("exog_forecast_ar.csv no cubre el horizonte o tiene NA.")

    # 3) construir exógenas con shock (solo PBI en mar/abr 2020)
    exog_shock = build_exog_with_pbi_shock(df_all, exog_base)

    # guardar exógenas con shock
    ex_shock_path = os.path.join(OUT_DIR, "exog_future_pbi_shock.csv")
    exog_shock.to_csv(ex_shock_path, index_label="fecha")
    print(f"Exógenas con shock PBI guardadas en: {ex_shock_path}")

    # 4) simular endógenas (baseline vs shock)
    y_base = simulate_varx(df_use, fit, p, exog_base)
    y_shock = simulate_varx(df_use, fit, p, exog_shock)

    # 5) (opcional) reconstruir niveles
    has_levels = ("Vol_total" in df_all.columns) and ("Mora_total" in df_all.columns)
    if has_levels:
        y_base_lvl = diffs_to_levels(df_all, y_base)
        y_shock_lvl = diffs_to_levels(df_all, y_shock)
    else:
        y_base_lvl = y_base.copy()
        y_shock_lvl = y_shock.copy()

    # 6) construir gaps
    gap = y_shock_lvl.copy()
    for col in y_base_lvl.columns:
        if col in y_shock_lvl.columns:
            gap[col] = y_shock_lvl[col] - y_base_lvl[col]

    # 7) guardar salidas
    paths = pd.concat(
        [
            y_base_lvl.add_prefix("base_"),
            y_shock_lvl.add_prefix("shockPBI_"),
        ],
        axis=1
    )
    paths_path = os.path.join(OUT_DIR, "paths_baseline_vs_pbi_shock.csv")
    paths.to_csv(paths_path, index_label="fecha")
    print(f"Trayectorias guardadas en: {paths_path}")

    gap_path = os.path.join(OUT_DIR, "gap_pbi_shock_minus_baseline.csv")
    gap.to_csv(gap_path, index_label="fecha")
    print(f"Gaps guardados en: {gap_path}")

    # quick log para verificar magnitud del shock en PBI mar/abr
    for m in SHOCK_MONTHS:
        d = pd.to_datetime(m)
        print(
            f"{d.date()} | PBI base={exog_base.loc[d,'D_ln_PBI_Desestacionalizado']:.6f} "
            f"| PBI obs={df_all.loc[d,'D_ln_PBI_Desestacionalizado']:.6f} "
            f"| shock={exog_shock.loc[d,'D_ln_PBI_Desestacionalizado']-exog_base.loc[d,'D_ln_PBI_Desestacionalizado']:.6f}"
        )


if __name__ == "__main__":
    main()
