import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import ENDOG


def irf_matrices(A_list, H):
    n = A_list[0].shape[0]
    p = len(A_list)
    Psi = [np.eye(n)]
    for h in range(1, H + 1):
        acc = np.zeros((n, n))
        for k in range(1, p + 1):
            if h - k >= 0:
                acc += A_list[k - 1] @ Psi[h - k]
        Psi.append(acc)
    return Psi


def orthogonalizer(Sigma, scenario: str):
    if scenario in ("base", "independent"):
        Sigma_diag = np.diag(np.diag(Sigma))
        return np.linalg.cholesky(Sigma_diag)
    if scenario == "non_independent":
        return np.linalg.cholesky(Sigma)
    raise ValueError("scenario: base | independent | non_independent")


def scenario_response_from_e(Psi, e0, scenario: str, Sigma, H, add_t1_second_shock=True):
    n = len(ENDOG)
    S = orthogonalizer(Sigma, scenario)

    u0 = np.linalg.solve(S, e0)
    e0_used = S @ u0

    u1 = np.zeros(n)
    if scenario in ("independent", "non_independent") and add_t1_second_shock:
        idx_other = int(np.argmin(np.abs(u0)))
        u1[idx_other] = 1.0
    e1_used = S @ u1

    resp = np.zeros((H + 1, n))
    for h in range(0, H + 1):
        resp[h, :] += Psi[h] @ e0_used
        if h >= 1 and np.any(e1_used):
            resp[h, :] += Psi[h - 1] @ e1_used

    df_resp = pd.DataFrame(resp, columns=ENDOG)
    df_resp.insert(0, "h", np.arange(H + 1))
    return df_resp, u0, e0_used, u1, e1_used


def response_with_two_shocks(Psi, e0, e1, H):
    n = len(e0)
    resp = np.zeros((H + 1, n))
    for h in range(H + 1):
        resp[h, :] += Psi[h] @ e0
        if h >= 1:
            resp[h, :] += Psi[h - 1] @ e1
    df = pd.DataFrame(resp, columns=ENDOG)
    df.insert(0, "h", np.arange(H + 1))
    return df


def shock_size_table(Sigma, e_map, scenario):
    S = orthogonalizer(Sigma, scenario)
    sig_e = np.sqrt(np.diag(Sigma))

    out = []
    for date, e in e_map.items():
        z = e / sig_e
        u = np.linalg.solve(S, e)
        out.append({
            "date": date,
            "e_vol": e[0], "e_mora": e[1],
            "sigma_e_vol": sig_e[0], "sigma_e_mora": sig_e[1],
            "z_vol": z[0], "z_mora": z[1],
            "u_vol": u[0], "u_mora": u[1],
        })
    return pd.DataFrame(out)

def scenario_response_two_observed_shocks(
    Psi,
    e0,
    e1,
    Sigma,
    H,
    scenario: str,
    base_only_first_shock: bool = True
):
    """
    Genera IRF para:
    - base: diag(Sigma) y (por defecto) solo shock Marzo (e1=0)
    - independent: diag(Sigma) y shocks Marzo+Abril
    - non_independent: Sigma completa y shocks Marzo+Abril

    Nota: usa shocks observados (innovaciones reducidas) e0,e1 y aplica
    el supuesto contemporáneo vía Cholesky (S).
    """
    scenario = scenario.lower()
    S = orthogonalizer(Sigma, scenario if scenario != "independent" else "base")

    if scenario == "base" and base_only_first_shock:
        e1 = np.zeros_like(e1)

    # Map e -> u -> e (consistente con el supuesto contemporáneo)
    u0 = np.linalg.solve(S, e0)
    u1 = np.linalg.solve(S, e1)

    e0_used = S @ u0
    e1_used = S @ u1

    df = response_with_two_shocks(Psi, e0_used, e1_used, H)
    return df, u0, u1, e0_used, e1_used