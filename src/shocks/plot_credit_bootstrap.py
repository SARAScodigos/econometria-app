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
    INPUT_FILE, DATE_COL, ENDOG, EXOG, TRAIN_END, SCENARIO_START, SHOCK_MONTHS,
    H, MAX_LAG, OUT_DIR, configure_runtime
)
from src.data.loader import slice_window
from src.diagnostics.diagnostics import estimate_varx_ols, stability_roots, residual_diagnostics


# ----------------------------
# IO helpers
# ----------------------------
def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.set_index(DATE_COL).sort_index()
    df.index = pd.to_datetime(df.index.date)
    return df


def load_exog_csv_robust(path: str) -> pd.DataFrame:
    """Lee CSV de exógenas aunque la columna fecha se llame distinto."""
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


# ----------------------------
# Model selection
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
# Bootstrap: moving-block sampling of residual vectors
# ----------------------------
def moving_block_bootstrap(resid: np.ndarray, H: int, block_len: int, rng: np.random.Generator):
    """
    resid: (T x K) matriz de residuos pre-COVID (vectoriales)
    retorna: (H x K) innovación bootstrap para el horizonte
    """
    T, K = resid.shape
    if block_len <= 1:
        idx = rng.integers(0, T, size=H)
        return resid[idx, :]

    max_start = T - block_len
    if max_start <= 0:
        # Si la serie es corta, cae a iid
        idx = rng.integers(0, T, size=H)
        return resid[idx, :]

    n_blocks = int(np.ceil(H / block_len))
    starts = rng.integers(0, max_start + 1, size=n_blocks)

    blocks = [resid[s:s + block_len, :] for s in starts]
    out = np.vstack(blocks)[:H, :]
    return out


# ----------------------------
# Simulation with exog + optional deterministic u_t + stochastic bootstrap eps_t
# ----------------------------
def simulate_future(df_all: pd.DataFrame, fit, p: int, exog_future: pd.DataFrame, u_map: dict, eps: np.ndarray):
    """
    df_all: data with ENDOG + EXOG for hist
    exog_future: DataFrame indexed from SCENARIO_START for H months, columns EXOG
    u_map: dict {Timestamp: np.array([u_vol, u_mora])} deterministic shock only in shock months
    eps: (H x K) stochastic innovations (bootstrap), added every month

    returns DataFrame (H x K) for ENDOG
    """
    start = pd.to_datetime(SCENARIO_START)
    idx = pd.date_range(start=start, periods=H, freq="MS")
    K = len(ENDOG)

    y_sim = pd.DataFrame(index=idx, columns=ENDOG, dtype=float)

    # history needed for lags
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
        e_t = eps[t_i, :]  # bootstrap innovation

        for j, ycol in enumerate(ENDOG):
            params = fit["results"][ycol].params
            y_sim.loc[t, ycol] = float(np.dot(x_vec, params) + u_t[j] + e_t[j])

    return y_sim


def main():
    configure_runtime()

    # ----------------------------
    # Setup / parameters
    # ----------------------------
    B = 800         # número de réplicas bootstrap (500–2000 es típico)
    block_len = 12  # block bootstrap mensual: 12 meses es razonable (puedes probar 6 y 12)
    seed = 2026
    rng = np.random.default_rng(seed)

    # shock financiero calibrado
    k = 2.0
    e_struct = np.array([-k, +k], dtype=float)  # crédito ↓, mora ↑

    # ----------------------------
    # Load data
    # ----------------------------
    df_all = load_excel(INPUT_FILE)

    # Serie objetivo: crecimiento crédito
    target = "D_ln_Vol_total"  # crecimiento (diferencia log)
    if target not in df_all.columns:
        raise ValueError(f"No existe columna {target} en el Excel.")

    # Subconjunto para estimación
    df_use = df_all[ENDOG + EXOG].dropna()
    df_pre = slice_window(df_use, "pre_covid")

    # ----------------------------
    # Estimate VARX pre-COVID
    # ----------------------------
    p, fit, info = pick_varx_lag_by_bic(df_pre, p_max=MAX_LAG, use_whiteness=True)
    Sigma = fit["Sigma"]

    # residuos vectoriales pre-COVID (mantiene correlación cruzada en el resampling)
    resid_mat = np.column_stack([fit["results"][y].resid for y in ENDOG])
    # opcional: recentrar (normalmente ya está centrado)
    resid_mat = resid_mat - resid_mat.mean(axis=0, keepdims=True)

    # ----------------------------
    # Load exogenous paths
    # ----------------------------
    ex_base = load_exog_csv_robust(os.path.join(OUT_DIR, "exog_forecast_ar.csv"))
    ex_pbi_shock = load_exog_csv_robust(os.path.join(OUT_DIR, "exog_future_pbi_shock.csv"))

    start = pd.to_datetime(SCENARIO_START)
    idx_future = pd.date_range(start=start, periods=H, freq="MS")
    ex_base = ex_base.reindex(idx_future)
    ex_pbi_shock = ex_pbi_shock.reindex(idx_future)

    if ex_base.isna().any().any() or ex_pbi_shock.isna().any().any():
        raise ValueError("Exógenas no cubren el horizonte o tienen NA.")

    # ----------------------------
    # Deterministic u_t for indep / no-indep
    # ----------------------------
    # Independent: diagonal Sigma
    Sigma_ind = np.diag(np.diag(Sigma))
    S_ind = np.linalg.cholesky(Sigma_ind)

    # Non-independent: full Sigma
    S_full = np.linalg.cholesky(Sigma)

    u_ind = S_ind @ e_struct
    u_full = S_full @ e_struct

    u_map_base = {}  # u=0
    u_map_ind = {pd.to_datetime(m): u_ind.copy() for m in SHOCK_MONTHS}
    u_map_full = {pd.to_datetime(m): u_full.copy() for m in SHOCK_MONTHS}

    # ----------------------------
    # Bootstrap simulations
    # ----------------------------
    # guardamos trayectorias (B x H) del target
    scen_names = ["nocovid", "macro_noindep"]
    sims = {s: np.zeros((B, H), dtype=float) for s in scen_names}

    for b in range(B):
        eps = moving_block_bootstrap(resid_mat, H=H, block_len=block_len, rng=rng)

        # 1) No-COVID (baseline exog, u=0)
        y1 = simulate_future(df_use, fit, p, ex_base, u_map={}, eps=eps)
        sims["nocovid"][b, :] = y1[target].to_numpy()

        # 2) Macro + no-indep financial u_t
        y4 = simulate_future(df_use, fit, p, ex_pbi_shock, u_map=u_map_full, eps=eps)
        sims["macro_noindep"][b, :] = y4[target].to_numpy()

    # resumen: media y percentiles
    summary = {}
    for s in scen_names:
        mean = sims[s].mean(axis=0)
        lo = np.percentile(sims[s], 2.5, axis=0)
        hi = np.percentile(sims[s], 97.5, axis=0)
        summary[s] = {"mean": mean, "lo": lo, "hi": hi}

    # ----------------------------
    # Deterministic paths (no bootstrap) for base e independiente
    # ----------------------------
    eps_zero = np.zeros((H, len(ENDOG)), dtype=float)
    y_base_det = simulate_future(df_use, fit, p, ex_pbi_shock, u_map=u_map_base, eps=eps_zero)
    y_ind_det = simulate_future(df_use, fit, p, ex_pbi_shock, u_map=u_map_ind, eps=eps_zero)

    # ----------------------------
    # Build observed history line (2002-01 .. 2020-02)
    # ----------------------------
    obs_hist = df_all.loc["2019-01-01":TRAIN_END, target].dropna()
    # Para "ramificación" visual: agregamos el último punto observado a las trayectorias futuras
    last_date = pd.to_datetime(TRAIN_END)
    last_val = float(obs_hist.loc[last_date])

    idx_branch = pd.DatetimeIndex([last_date]).append(idx_future)
    # series para plot: cada escenario inicia con el último punto observado
    plot_series = {}
    for s in scen_names:
        plot_series[s] = {
            "mean": np.r_[last_val, summary[s]["mean"]],
            "lo": np.r_[last_val, summary[s]["lo"]],
            "hi": np.r_[last_val, summary[s]["hi"]],
        }

    plot_det = {
        "macro_base": np.r_[last_val, y_base_det[target].to_numpy()],
        "macro_indep": np.r_[last_val, y_ind_det[target].to_numpy()],
    }

    # ----------------------------
    # Plot
    # ----------------------------
    plt.figure(figsize=(14, 7))

    # rama principal observada
    plt.plot(obs_hist.index, obs_hist.values, linewidth=2.2, label="Observado (hasta 2020-02)")

    # ramificaciones
    styles = {
        "nocovid": {"ls": "-",  "lw": 2.0, "label": "Baseline sin COVID (AR exógenas)", "color": "green"},
        "macro_noindep": {"ls": ":",  "lw": 2.4, "label": "Shock PBI + k=2 no-indep", "color": "orange"},
    }
    styles_det = {
        "macro_base": {"ls": "--", "lw": 2.0, "label": "Shock PBI (base macro)", "color": "#1f77b4"},
        "macro_indep": {"ls": "-.", "lw": 2.0, "label": "Shock PBI + k=2 indep", "color": "#9467bd"},
    }

    for s in scen_names:
        plt.plot(
            idx_branch,
            plot_series[s]["mean"],
            linestyle=styles[s]["ls"],
            linewidth=styles[s]["lw"],
            label=styles[s]["label"],
            color=styles[s]["color"],
        )
        plt.fill_between(
            idx_branch,
            plot_series[s]["lo"],
            plot_series[s]["hi"],
            color=styles[s]["color"],
            alpha=0.18,
        )

    for s, series in plot_det.items():
        plt.plot(
            idx_branch,
            series,
            linestyle=styles_det[s]["ls"],
            linewidth=styles_det[s]["lw"],
            label=styles_det[s]["label"],
            color=styles_det[s]["color"],
        )

    plt.axvline(pd.to_datetime(SCENARIO_START), linewidth=1.2)
    plt.title("Crecimiento del crédito: serie observada y escenarios contrafactuales (IC 95% bootstrap)")
    plt.ylabel("Δ ln(Vol_total)")
    plt.xlabel("Fecha")
    plt.legend(ncol=2)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()

    out_png = os.path.join(OUT_DIR, "credit_growth_branch_bootstrap95.png")
    plt.savefig(out_png, dpi=300)
    print("Gráfico guardado en:", out_png)

    # también guarda resumen numérico
    out_csv = os.path.join(OUT_DIR, "credit_growth_bootstrap95_summary.csv")
    out = pd.DataFrame(index=idx_future)
    for s in scen_names:
        out[f"{s}_mean"] = summary[s]["mean"]
        out[f"{s}_lo95"] = summary[s]["lo"]
        out[f"{s}_hi95"] = summary[s]["hi"]
    out.to_csv(out_csv, index_label="fecha")
    print("Resumen guardado en:", out_csv)

    # info útil en consola
    print(f"p={p} | B={B} | block_len={block_len} | k={k}")
    print("u_ind=", u_ind, "u_full=", u_full)


if __name__ == "__main__":
    main()
