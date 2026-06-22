"""
Escenarios con shock macro (PBI observado vs baseline AR en 2020-03/04)
+ shock financiero endógeno calibrado k=2 (en 2020-03/04)

Genera tres escenarios:
- base_macro: solo shock PBI, u_t = 0
- independiente: u_t = chol(diag(Sigma)) * e_t
- no_independiente: u_t = chol(Sigma) * e_t

Outputs:
- outputs/paths_escenarios_k2.csv
- outputs/gaps_escenarios_k2.csv
"""

import os
import numpy as np
import pandas as pd

from covidshock_config import (
    INPUT_FILE, DATE_COL, ENDOG, EXOG, TRAIN_END, SHOCK_MONTHS, H, MAX_LAG, OUT_DIR, configure_runtime
)
from covidshock_estimation import estimate_varx_ols, stability_roots, residual_diagnostics


def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.set_index(DATE_COL).sort_index()
    df.index = pd.to_datetime(df.index.date)
    return df


def load_exog_csv(path: str) -> pd.DataFrame:
    ex = pd.read_csv(path, delimiter=",")
    if ex.shape[1] == 1:
        # Reintenta con separador ; si todo vino en una sola columna
        ex = pd.read_csv(path, sep=";", engine="python")

    # Caso 1: tiene columna 'fecha'
    if "fecha" in ex.columns:
        ex["fecha"] = pd.to_datetime(ex["fecha"])
        ex = ex.set_index("fecha").sort_index()

    # Caso 2: el índice viene como primera columna "Unnamed: 0"
    elif "Unnamed: 0" in ex.columns:
        ex["Unnamed: 0"] = pd.to_datetime(ex["Unnamed: 0"])
        ex = ex.set_index("Unnamed: 0").sort_index()
        ex.index.name = "fecha"

    # Caso 3: la primera columna es la fecha, pero con otro nombre
    else:
        first = ex.columns[0]
        ex[first] = pd.to_datetime(ex[first])
        ex = ex.set_index(first).sort_index()
        ex.index.name = "fecha"

    ex.index = pd.to_datetime(ex.index.date)
    ex = ex.asfreq("MS")
    return ex


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


def simulate_varx_with_u(df_all: pd.DataFrame, fit, p: int, exog_future: pd.DataFrame, u_map: dict) -> pd.DataFrame:
    """
    Simulación determinística, pero permitiendo u_t específico en ciertos meses.
    u_map: dict {Timestamp: np.array([u_vol, u_mora])}
    """
    start = pd.to_datetime("2020-03-01")
    idx = pd.date_range(start=start, periods=H, freq="MS")

    y_sim = pd.DataFrame(index=idx, columns=ENDOG, dtype=float)

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

        u_t = u_map.get(pd.to_datetime(t.date()), np.zeros(len(ENDOG), dtype=float))

        for j, ycol in enumerate(ENDOG):
            params = fit["results"][ycol].params
            y_sim.loc[t, ycol] = float(np.dot(x_vec, params) + u_t[j])

    return y_sim


def diffs_to_levels(df_all: pd.DataFrame, diffs: pd.DataFrame) -> pd.DataFrame:
    base_date = pd.to_datetime(TRAIN_END)
    vol0 = float(df_all.loc[base_date, "Vol_total"])
    mora0 = float(df_all.loc[base_date, "Mora_total"])
    if vol0 <= 0:
        raise ValueError("Vol_total en 2020-02 debe ser positivo.")

    lnvol0 = float(np.log(vol0))

    out = diffs.copy()
    out["Mora_total_level"] = mora0 + out["D_Mora_total"].cumsum()
    out["Ln_Vol_total_level"] = lnvol0 + out["D_ln_Vol_total"].cumsum()
    out["Vol_total_level"] = np.exp(out["Ln_Vol_total_level"])
    return out


def main():
    configure_runtime()

    # --- Load data ---
    df_all = load_excel(INPUT_FILE)
    df_use = df_all[ENDOG + EXOG].dropna()
    df_pre = df_use.loc["2002-01-01":TRAIN_END].copy()

    # --- Estimate VARX pre-COVID ---
    p, fit, info = pick_varx_lag_by_bic(df_pre, p_max=MAX_LAG, use_whiteness=True)
    Sigma = fit["Sigma"]
    print("=== ESCENARIOS k=2 (macro + financiero) ===")
    print(f"p={p} | info={info}")
    print("Sigma=\n", Sigma)

    # --- Load exogenous paths ---
    ex_base = load_exog_csv(os.path.join(OUT_DIR, "exog_forecast_ar.csv"))
    ex_pbi_shock = load_exog_csv(os.path.join(OUT_DIR, "exog_future_pbi_shock.csv"))
    start = pd.to_datetime("2020-03-01")
    idx = pd.date_range(start=start, periods=H, freq="MS")
    ex_base = ex_base.reindex(idx)
    ex_pbi_shock = ex_pbi_shock.reindex(idx)

    if ex_base.isna().any().any() or ex_pbi_shock.isna().any().any():
        raise ValueError("Exógenas no cubren el horizonte o tienen NA.")

    # --- Build financial shocks u_t (k=2) for Mar/Apr ---
    k = 2.0
    e = np.array([-k, +k], dtype=float)  # crédito abajo, mora arriba

    # Independent: Sigma diagonal
    Sigma_ind = np.diag(np.diag(Sigma))
    S_ind = np.linalg.cholesky(Sigma_ind)

    # Non-independent: full Sigma
    S_full = np.linalg.cholesky(Sigma)

    u_ind = S_ind @ e
    u_full = S_full @ e

    u_map_base = {}  # u=0
    u_map_ind = {pd.to_datetime(m): u_ind.copy() for m in SHOCK_MONTHS}
    u_map_full = {pd.to_datetime(m): u_full.copy() for m in SHOCK_MONTHS}

    # --- Simulate (all use macro shock in exog_pbi_shock) ---
    y_base_macro = simulate_varx_with_u(df_use, fit, p, ex_pbi_shock, u_map_base)
    y_ind = simulate_varx_with_u(df_use, fit, p, ex_pbi_shock, u_map_ind)
    y_full = simulate_varx_with_u(df_use, fit, p, ex_pbi_shock, u_map_full)

    # --- Also keep "no-covid" baseline for gaps (optional but useful) ---
    y_nocovid = simulate_varx_with_u(df_use, fit, p, ex_base, {})  # u=0

    # levels
    has_levels = ("Vol_total" in df_all.columns) and ("Mora_total" in df_all.columns)
    if has_levels:
        y_base_macro = diffs_to_levels(df_all, y_base_macro)
        y_ind = diffs_to_levels(df_all, y_ind)
        y_full = diffs_to_levels(df_all, y_full)
        y_nocovid = diffs_to_levels(df_all, y_nocovid)

    # --- Save paths ---
    paths = pd.concat(
        [
            y_nocovid.add_prefix("nocovid_"),
            y_base_macro.add_prefix("macro_base_"),
            y_ind.add_prefix("macro_indep_"),
            y_full.add_prefix("macro_noindep_"),
        ],
        axis=1
    )
    out_paths = os.path.join(OUT_DIR, "paths_escenarios_k2.csv")
    paths.to_csv(out_paths, index_label="fecha")
    print("Guardado:", out_paths)

    # --- Gaps vs no-covid baseline (interpretable) ---
    gaps = pd.DataFrame(index=paths.index)
    for col in y_nocovid.columns:
        gaps[f"gap_macro_base_{col}"] = y_base_macro[col] - y_nocovid[col]
        gaps[f"gap_macro_indep_{col}"] = y_ind[col] - y_nocovid[col]
        gaps[f"gap_macro_noindep_{col}"] = y_full[col] - y_nocovid[col]

    out_gaps = os.path.join(OUT_DIR, "gaps_escenarios_k2.csv")
    gaps.to_csv(out_gaps, index_label="fecha")
    print("Guardado:", out_gaps)

    # quick check
    print("u_ind (k=2) =", u_ind)
    print("u_full(k=2) =", u_full)


if __name__ == "__main__":
    main()
