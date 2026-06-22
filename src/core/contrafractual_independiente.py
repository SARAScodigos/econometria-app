"""
Contrafactual COVID - Escenario Independiente.
Usa Sigma del VARX pre-COVID, diagonaliza, y aplica shocks Mar/Abr sin mezcla contemporanea.
"""

import numpy as np

from covidshock_config import INPUT_FILE, ENDOG, H, configure_runtime
from covidshock_data import load_and_prepare, covid_innovation_vectors
from covidshock_estimation import estimate_varx_ols
from covidshock_irf import irf_matrices, response_with_two_shocks


def main():
    configure_runtime()

    df_all = load_and_prepare(INPUT_FILE)
    df_pre = df_all.loc["2002-01-01":"2020-02-01"].copy()

    # p fijo pre-COVID
    p = 12
    fit = estimate_varx_ols(df_pre, p)
    Sigma = fit["Sigma"]
    A_list = fit["A"]

    # Shocks observados Mar/Abr 2020 (innovaciones reducidas)
    e_map, table = covid_innovation_vectors(df_all, fit, p, ["2020-03-01", "2020-04-01"])
    e_mar = e_map["2020-03-01"]
    e_abr = e_map["2020-04-01"]

    # Sigma independiente (diagonal) y su Cholesky
    Sigma_ind = np.diag(np.diag(Sigma))
    S_ind = np.linalg.cholesky(Sigma_ind)

    # u_t = S_ind^{-1} e_t  (shocks en sigmas)
    u_mar = np.linalg.solve(S_ind, e_mar)
    u_abr = np.linalg.solve(S_ind, e_abr)

    # e_t_ind = S_ind u_t
    e_mar_ind = S_ind @ u_mar
    e_abr_ind = S_ind @ u_abr

    # IRF con shocks secuenciales
    Psi = irf_matrices(A_list, H)
    irf_ind = response_with_two_shocks(Psi, e_mar_ind, e_abr_ind, H)

    print("=== CONTRAFACTUAL INDEPENDIENTE ===")
    print(f"p = {p}")
    print("Sigma (diag):", np.diag(Sigma_ind))
    print("e_mar_ind:", e_mar_ind)
    print("e_abr_ind:", e_abr_ind)
    print("\nIRF (head):")
    print(irf_ind.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
