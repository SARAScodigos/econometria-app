import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    INPUT_FILE, DATE_COL, ENDOG, EXOG, TRAIN_END, SHOCK_MONTHS, H, MAX_LAG, OUT_DIR, configure_runtime
)
from src.diagnostics.diagnostics import estimate_varx_ols, stability_roots, residual_diagnostics


def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.set_index(DATE_COL).sort_index()
    df.index = pd.to_datetime(df.index.date)
    return df


def load_exog_csv_robust(path: str) -> pd.DataFrame:
    ex = pd.read_csv(path)
    if "fecha" in ex.columns:
        ex["fecha"] = pd.to_datetime(ex["fecha"])
        ex = ex.set_index("fecha").sort_index()
    elif "Unnamed: 0" in ex.columns:
        ex["Unnamed: 0"] = pd.to_datetime(ex["Unnamed: 0"])
        ex = ex.set_index("Unnamed: 0").sort_index()
        ex.index.name = "fecha"
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


def simulate_future(df_all: pd.DataFrame, fit, p: int, exog_future: pd.DataFrame, u_map: dict, eps: np.ndarray):
    start = pd.to_datetime("2020-03-01")
    idx = pd.date_range(start=start, periods=H, freq="MS")
    K = len(ENDOG)

    y_sim = pd.DataFrame(index=idx, columns=ENDOG, dtype=float)

    hist_start = (pd.to_datetime(TRAIN_END) - pd.offsets.MonthBegin(p))
    hist_idx = pd.date_range(start=hist_start, end=pd.to_datetime(TRAIN_END), freq="MS")
    y_hist = df_all.loc[hist_idx, ENDOG].copy()
    if y_hist.isna().any().any():
        raise ValueError("Faltan datos endógenos en el historial requerido para la simulación.")

    x_cols = list(fit["X_columns"])

    for t_i, t in enumerate(idx):
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
        u_t = u_map.get(pd.to_datetime(t.date()), np.zeros(K, dtype=float))
        e_t = eps[t_i, :]

        for j, ycol in enumerate(ENDOG):
            params = fit["results"][ycol].params
            y_sim.loc[t, ycol] = float(np.dot(x_vec, params) + u_t[j] + e_t[j])

    return y_sim


def diffs_to_levels_credit(df_all: pd.DataFrame, diffs: pd.DataFrame) -> pd.Series:
    base_date = pd.to_datetime(TRAIN_END)
    vol0 = float(df_all.loc[base_date, "Vol_total"])
    if vol0 <= 0:
        raise ValueError("Vol_total en 2020-02 debe ser positivo.")
    lnvol0 = float(np.log(vol0))
    ln_path = lnvol0 + diffs["D_ln_Vol_total"].cumsum()
    return np.exp(ln_path)


def main():
    configure_runtime()

    df_all = load_excel(INPUT_FILE)
    if "Vol_total" not in df_all.columns:
        raise ValueError("No existe columna Vol_total en el Excel.")

    df_use = df_all[ENDOG + EXOG].dropna()
    df_pre = df_use.loc["2002-01-01":TRAIN_END].copy()

    p, fit, info = pick_varx_lag_by_bic(df_pre, p_max=MAX_LAG, use_whiteness=True)
    Sigma = fit["Sigma"]

    ex_base = load_exog_csv_robust(os.path.join(OUT_DIR, "exog_forecast_ar.csv"))
    ex_pbi_shock = load_exog_csv_robust(os.path.join(OUT_DIR, "exog_future_pbi_shock.csv"))

    start = pd.to_datetime("2020-03-01")
    idx_future = pd.date_range(start=start, periods=H, freq="MS")
    ex_base = ex_base.reindex(idx_future)
    ex_pbi_shock = ex_pbi_shock.reindex(idx_future)

    if ex_base.isna().any().any() or ex_pbi_shock.isna().any().any():
        raise ValueError("Exógenas no cubren el horizonte o tienen NA.")

    k = 2.0
    e_struct = np.array([-k, +k], dtype=float)
    Sigma_ind = np.diag(np.diag(Sigma))
    S_ind = np.linalg.cholesky(Sigma_ind)
    S_full = np.linalg.cholesky(Sigma)

    u_ind = S_ind @ e_struct
    u_full = S_full @ e_struct

    u_map_base = {}
    u_map_ind = {pd.to_datetime(m): u_ind.copy() for m in SHOCK_MONTHS}
    u_map_full = {pd.to_datetime(m): u_full.copy() for m in SHOCK_MONTHS}

    eps_zero = np.zeros((H, len(ENDOG)), dtype=float)

    y_nocovid = simulate_future(df_use, fit, p, ex_base, u_map={}, eps=eps_zero)
    y_base = simulate_future(df_use, fit, p, ex_pbi_shock, u_map=u_map_base, eps=eps_zero)
    y_ind = simulate_future(df_use, fit, p, ex_pbi_shock, u_map=u_map_ind, eps=eps_zero)
    y_full = simulate_future(df_use, fit, p, ex_pbi_shock, u_map=u_map_full, eps=eps_zero)

    levels = pd.DataFrame(index=idx_future)
    levels["nocovid"] = diffs_to_levels_credit(df_all, y_nocovid)
    levels["macro_base"] = diffs_to_levels_credit(df_all, y_base)
    levels["macro_indep"] = diffs_to_levels_credit(df_all, y_ind)
    levels["macro_noindep"] = diffs_to_levels_credit(df_all, y_full)

    obs_hist = df_all.loc["2019-01-01":TRAIN_END, "Vol_total"].dropna()
    last_date = pd.to_datetime(TRAIN_END)
    last_val = float(obs_hist.loc[last_date])
    idx_branch = pd.DatetimeIndex([last_date]).append(idx_future)

    plot_series = {
        "nocovid": np.r_[last_val, levels["nocovid"].to_numpy()],
        "macro_base": np.r_[last_val, levels["macro_base"].to_numpy()],
        "macro_indep": np.r_[last_val, levels["macro_indep"].to_numpy()],
        "macro_noindep": np.r_[last_val, levels["macro_noindep"].to_numpy()],
    }

    plt.figure(figsize=(14, 7))
    plt.plot(obs_hist.index, obs_hist.values, linewidth=2.2, label="Observado (hasta 2020-02)")

    styles = {
        "nocovid": {"ls": "-",  "lw": 2.0, "label": "Baseline sin COVID (AR exógenas)"},
        "macro_base": {"ls": "--", "lw": 2.0, "label": "Shock PBI (base macro)"},
        "macro_indep": {"ls": "-.", "lw": 2.0, "label": "Shock PBI + k=2 indep"},
        "macro_noindep": {"ls": ":",  "lw": 2.4, "label": "Shock PBI + k=2 no-indep"},
    }

    for s, series in plot_series.items():
        plt.plot(idx_branch, series, linestyle=styles[s]["ls"], linewidth=styles[s]["lw"], label=styles[s]["label"])

    plt.axvline(pd.to_datetime("2020-03-01"), linewidth=1.2)
    plt.title("Volumen de crédito: niveles observados y escenarios contrafactuales")
    plt.ylabel("Vol_total (nivel)")
    plt.xlabel("Fecha")
    plt.legend(ncol=2)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()

    out_png = os.path.join(OUT_DIR, "credit_levels_scenarios.png")
    plt.savefig(out_png, dpi=300)
    print("Gráfico guardado en:", out_png)

    out_csv = os.path.join(OUT_DIR, "credit_levels_scenarios.csv")
    levels.to_csv(out_csv, index_label="fecha")
    print("Niveles guardados en:", out_csv)

    print(f"p={p} | k={k} | info={info}")


if __name__ == "__main__":
    main()
