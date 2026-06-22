"""
Contrafactual COVID (pre-COVID VARX):
Inyecta e_2020-03 (t=0) y e_2020-04 (t=1) usando la MA del VARX pre-COVID.
No grafica; solo reporta medidas clave.
"""

import numpy as np
import pandas as pd

from covidshock_config import INPUT_FILE, ENDOG, H, configure_runtime
from covidshock_data import load_and_prepare, covid_innovation_vectors
from covidshock_estimation import estimate_varx_ols
from covidshock_irf import irf_matrices, response_with_two_shocks


def summarize_irf(irf_df, horizons=(0, 1, 6, 12, 24, 48)):
    out = []
    h_vals = irf_df["h"].values
    for col in ENDOG:
        series = irf_df[col].values
        max_idx = int(np.argmax(series))
        min_idx = int(np.argmin(series))
        max_abs_idx = int(np.argmax(np.abs(series)))
        row = {
            "variable": col,
            "max": float(series[max_idx]),
            "h_max": int(h_vals[max_idx]),
            "min": float(series[min_idx]),
            "h_min": int(h_vals[min_idx]),
            "max_abs": float(series[max_abs_idx]),
            "h_max_abs": int(h_vals[max_abs_idx]),
            "cum_sum": float(np.sum(series)),
        }
        for h in horizons:
            if h in h_vals:
                row[f"impact_h{h}"] = float(series[int(h)])
        out.append(row)
    return pd.DataFrame(out)


def main():
    configure_runtime()

    df_all = load_and_prepare(INPUT_FILE)
    df_pre = df_all.loc["2002-01-01":"2020-02-01"].copy()

    # p fijo pre-COVID
    p = 12
    fit = estimate_varx_ols(df_pre, p)
    A_list = fit["A"]

    # Estado inicial (2020-02)
    y0 = df_all.loc["2020-02-01", ENDOG].values.astype(float)

    # Shocks observados Mar/Abr 2020
    e_map, table = covid_innovation_vectors(df_all, fit, p, ["2020-03-01", "2020-04-01"])
    e_mar = e_map["2020-03-01"]
    e_abr = e_map["2020-04-01"]
    sig_e = np.sqrt(np.diag(fit["Sigma"]))
    # Renombrar columnas a ENDOG para consistencia
    table = table.rename(columns={
        "pred_vol": f"pred_{ENDOG[0]}",
        "obs_vol": f"obs_{ENDOG[0]}",
        "e_vol": f"e_{ENDOG[0]}",
        "pred_mora": f"pred_{ENDOG[1]}",
        "obs_mora": f"obs_{ENDOG[1]}",
        "e_mora": f"e_{ENDOG[1]}",
    })
    table[f"z_{ENDOG[0]}"] = table[f"e_{ENDOG[0]}"] / sig_e[0]
    table[f"z_{ENDOG[1]}"] = table[f"e_{ENDOG[1]}"] / sig_e[1]

    # Respuesta MA pre-COVID
    Psi = irf_matrices(A_list, H)
    irf_df = response_with_two_shocks(Psi, e_mar, e_abr, H)

    summary = summarize_irf(irf_df)

    print("=== CONTRAFACTUAL COVID (pre-COVID VARX) ===")
    print(f"p = {p}")
    print(f"Estado inicial (2020-02): {dict(zip(ENDOG, y0))}")
    print("\nShocks (e_t = y_obs - y_pred):")
    print(table.to_string(index=False))
    print("\nResumen IRF (medidas clave):")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
