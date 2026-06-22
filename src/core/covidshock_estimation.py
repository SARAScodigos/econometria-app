import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox

from covidshock_config import ENDOG, EXOG
from covidshock_data import make_lagged_matrix


def estimate_varx_ols(df: pd.DataFrame, p: int):
    Y, X = make_lagged_matrix(df, ENDOG, EXOG, p)

    results = {}
    residuals = []

    for ycol in ENDOG:
        model = sm.OLS(Y[ycol].values, X.values).fit()
        results[ycol] = model
        residuals.append(model.resid)

    resid = np.column_stack(residuals)
    Sigma = np.cov(resid.T, bias=False)

    n = len(ENDOG)
    A = []
    for k in range(p):
        Ak = np.zeros((n, n))
        for eq_i, ycol in enumerate(ENDOG):
            params = results[ycol].params
            start = 1 + k * n
            stop = start + n
            Ak[eq_i, :] = params[start:stop]
        A.append(Ak)

    B = np.zeros((n, len(EXOG)))
    for eq_i, ycol in enumerate(ENDOG):
        params = results[ycol].params
        exog_start = 1 + n * p
        B[eq_i, :] = params[exog_start:exog_start + len(EXOG)]

    return {
        "p": p, "results": results, "Sigma": Sigma, "A": A, "B": B,
        "Y_index": Y.index, "X_columns": X.columns
    }

'''
#no se selecciona el numero de rezagos por BIC sino directamente 12 como numero fijo
def select_lag_by_ic(df: pd.DataFrame, max_lag=12):
    rows = []
    for p in range(1, max_lag + 1):
        try:
            fit = estimate_varx_ols(df, p)
            aic = np.mean([fit["results"][y].aic for y in ENDOG])
            bic = np.mean([fit["results"][y].bic for y in ENDOG])
            rows.append({"p": p, "AIC_mean": aic, "BIC_mean": bic})
        except Exception:
            continue
    ic = pd.DataFrame(rows).sort_values("p").reset_index(drop=True)
    p_aic = int(ic.loc[ic["AIC_mean"].idxmin(), "p"])
    p_bic = int(ic.loc[ic["BIC_mean"].idxmin(), "p"])
    return ic, p_aic, p_bic
'''

def companion_matrix(A_list):
    n = A_list[0].shape[0]
    p = len(A_list)
    top = np.hstack(A_list)
    if p == 1:
        return top
    I = np.eye(n * (p - 1))
    zeros = np.zeros((n * (p - 1), n))
    bottom = np.hstack([I, zeros])
    return np.vstack([top, bottom])


def stability_roots(A_list):
    C = companion_matrix(A_list)
    return np.linalg.eigvals(C)


def residual_diagnostics(resid: np.ndarray, lags=12):
    out = []
    for i, col in enumerate(ENDOG):
        r = resid[:, i]
        lb = acorr_ljungbox(r, lags=[lags], return_df=True)
        out.append({
            "eq": col,
            "lb_stat": float(lb["lb_stat"].iloc[0]),
            "lb_pvalue": float(lb["lb_pvalue"].iloc[0])
        })
    return pd.DataFrame(out)


if __name__ == "__main__":
    from covidshock_config import INPUT_FILE, MAX_LAG, configure_runtime
    from covidshock_data import load_and_prepare

    configure_runtime()

    df_all = load_and_prepare(INPUT_FILE)
    df_test = df_all.loc["2002-01-01":"2022-12-01"].copy()

    p = 12
    fit = estimate_varx_ols(df_test, p)
    eigvals = stability_roots(fit["A"])
    stable = bool(np.all(np.abs(eigvals) < 1))

    resid = np.column_stack([fit["results"][y].resid for y in ENDOG])
    diag = residual_diagnostics(resid, lags=12)

    print("=== VARX TEST ===")
    print(f"p(fijo) = {p}")
    print(f"Estable (|eig|<1): {stable} | max|eig|={float(np.max(np.abs(eigvals))):.4f}")
    print("Ljung-Box (lag 12):")
    print(diag.to_string(index=False))
