"""
Contrafactual COVID - Escenario Independiente.
Usa Sigma del VARX pre-COVID, diagonaliza, y aplica shocks Mar/Abr sin mezcla contemporanea.
"""

import sys
from pathlib import Path
import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import INPUT_FILE, ENDOG, H, SHOCK_MONTHS, configure_runtime
from src.data.loader import load_and_prepare, slice_window, covid_innovation_vectors
from src.diagnostics.diagnostics import estimate_varx_ols
from covidshock_irf import irf_matrices, response_with_two_shocks


def main():
    configure_runtime()

    df_all = load_and_prepare(INPUT_FILE)
    df_pre = slice_window(df_all, "pre_covid")

    # p fijo pre-COVID
    p = 12
    fit = estimate_varx_ols(df_pre, p)
    Sigma = fit["Sigma"]
    A_list = fit["A"]

    # Shocks observados Mar/Abr 2020 (innovaciones reducidas)
    e_map, table = covid_innovation_vectors(df_all, fit, p, SHOCK_MONTHS)
    e_mar = e_map[SHOCK_MONTHS[0]]
    e_abr = e_map[SHOCK_MONTHS[1]]

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
