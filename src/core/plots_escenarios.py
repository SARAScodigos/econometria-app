"""
Graficos de escenarios (base, independiente, no independiente) vs observado.
Se grafican las series de ENDOG (diferencias) desde 2020-03 en adelante.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from covidshock_config import INPUT_FILE, DATE_COL, ENDOG, ENDOG_LEVELS, H, OUT_DIR, configure_runtime
from covidshock_data import load_and_prepare, covid_innovation_vectors
from covidshock_estimation import estimate_varx_ols
from covidshock_irf import irf_matrices, response_with_two_shocks


def build_counterfactual_series(df_all, fit, e_mar, e_abr, scenario):
    """
    Devuelve serie contrafactual en diferencias (ENDOG) a partir de 2020-03.
    scenario: "base" | "independent" | "non_independent"
    """
    Sigma = fit["Sigma"]
    A_list = fit["A"]

    if scenario == "base":
        e0 = e_mar
        e1 = e_abr
    else:
        Sigma_ind = np.diag(np.diag(Sigma))
        S_ind = np.linalg.cholesky(Sigma_ind)
        u_mar = np.linalg.solve(S_ind, e_mar)
        u_abr = np.linalg.solve(S_ind, e_abr)
        if scenario == "independent":
            e0 = S_ind @ u_mar
            e1 = S_ind @ u_abr
        elif scenario == "non_independent":
            S_full = np.linalg.cholesky(Sigma)
            e0 = S_full @ u_mar
            e1 = S_full @ u_abr
        else:
            raise ValueError("scenario: base | independent | non_independent")

    Psi = irf_matrices(A_list, H)
    irf_df = response_with_two_shocks(Psi, e0, e1, H)

    start = pd.to_datetime("2020-03-01")
    dates = pd.date_range(start=start, periods=H + 1, freq="MS")
    irf_df = irf_df.set_index("h")
    out = pd.DataFrame(index=dates)
    for col in ENDOG:
        out[col] = irf_df[col].values
    return out


def diffs_to_levels(diffs_df, df_levels, base_date="2020-02-01"):
    levels = pd.DataFrame(index=diffs_df.index)
    for endog_col, level_col in zip(ENDOG, ENDOG_LEVELS):
        base_level = float(df_levels.loc[base_date, level_col])
        if endog_col.startswith("D_ln_"):
            base_log = np.log(base_level)
            levels[level_col] = np.exp(base_log + diffs_df[endog_col].cumsum())
        else:
            levels[level_col] = base_level + diffs_df[endog_col].cumsum()
    return levels


def plot_scenarios(df_obs, base_df, ind_df, non_df, out_prefix, ylabel, col_names):
    os.makedirs(OUT_DIR, exist_ok=True)
    for col in col_names:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df_obs.index, df_obs[col].values, label="Observado")
        ax.plot(base_df.index, base_df[col].values, label="Base")
        ax.plot(ind_df.index, ind_df[col].values, label="Independiente")
        ax.plot(non_df.index, non_df[col].values, label="No-independiente")
        ax.axhline(0, linewidth=1)
        ax.set_title(f"Escenarios – {col}")
        ax.set_xlabel("Fecha")
        ax.set_ylabel(ylabel)
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, f"{out_prefix}_{col}.png"), dpi=200)
        plt.close(fig)


def main():
    configure_runtime()

    df_all = load_and_prepare(INPUT_FILE)
    df_pre = df_all.loc["2002-01-01":"2020-02-01"].copy()

    p = 12
    fit = estimate_varx_ols(df_pre, p)

    e_map, _ = covid_innovation_vectors(df_all, fit, p, ["2020-03-01", "2020-04-01"])
    e_mar = e_map["2020-03-01"]
    e_abr = e_map["2020-04-01"]

    base_df = build_counterfactual_series(df_all, fit, e_mar, e_abr, "base")
    ind_df = build_counterfactual_series(df_all, fit, e_mar, e_abr, "independent")
    non_df = build_counterfactual_series(df_all, fit, e_mar, e_abr, "non_independent")

    obs = df_all.loc["2020-03-01":base_df.index[-1], ENDOG].copy()

    plot_scenarios(
        obs, base_df, ind_df, non_df,
        out_prefix="escenarios_diff",
        ylabel="Diferencia",
        col_names=ENDOG,
    )

    # Niveles observados desde el Excel completo
    df_raw = pd.read_excel(INPUT_FILE)
    if DATE_COL not in df_raw.columns:
        raise ValueError(f"El archivo debe tener una columna '{DATE_COL}'.")
    df_raw[DATE_COL] = pd.to_datetime(df_raw[DATE_COL])
    df_raw = df_raw.set_index(DATE_COL).sort_index()
    obs_levels = df_raw.loc["2020-03-01":base_df.index[-1], ENDOG_LEVELS].copy()
    base_levels = diffs_to_levels(base_df, df_raw)
    ind_levels = diffs_to_levels(ind_df, df_raw)
    non_levels = diffs_to_levels(non_df, df_raw)

    plot_scenarios(
        obs_levels, base_levels, ind_levels, non_levels,
        out_prefix="escenarios_niveles",
        ylabel="Nivel",
        col_names=ENDOG_LEVELS,
    )
    print("=== OK ===")
    print(f"Graficos: {OUT_DIR}/escenarios_{ENDOG[0]}.png y {OUT_DIR}/escenarios_{ENDOG[1]}.png")


if __name__ == "__main__":
    main()
