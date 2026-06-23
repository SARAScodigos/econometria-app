"""
Estimacion VARX con toda la muestra disponible.
Selecciona p por ruido blanco + estabilidad y reporta diagnosticos.
"""

import sys
from pathlib import Path
import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import INPUT_FILE, ENDOG, EXOG, configure_runtime
from src.data.loader import load_and_prepare
from src.diagnostics.diagnostics import estimate_varx_ols, stability_roots, residual_diagnostics


def choose_p_by_whiteness(df, p_candidates, lb_lags=12, alpha=0.05):
    """
    Elige el primer p estable con Ljung-Box (todas las ecuaciones) > alpha.
    Si ninguno cumple, retorna el ultimo p de la lista.
    """
    best = None
    for p in p_candidates:
        fit = estimate_varx_ols(df, p)
        eigvals = stability_roots(fit["A"])
        stable = bool(np.all(np.abs(eigvals) < 1))
        resid = np.column_stack([fit["results"][y].resid for y in ENDOG])
        diag = residual_diagnostics(resid, lags=lb_lags)
        ok_white = bool((diag["lb_pvalue"] > alpha).all())
        if stable and ok_white:
            return p, fit, eigvals, diag
        best = (p, fit, eigvals, diag)
    return best


def main():
    configure_runtime()
    df_all = load_and_prepare(INPUT_FILE)

    p_candidates = [1, 3, 6, 12]
    p, fit, eigvals, diag = choose_p_by_whiteness(df_all, p_candidates, lb_lags=12, alpha=0.05)

    stable = bool(np.all(np.abs(eigvals) < 1))
    max_eig = float(np.max(np.abs(eigvals)))

    print("=== VARX TOTAL ===")
    print(f"p(elegido) = {p}")
    print(f"Estable (|eig|<1): {stable} | max|eig|={max_eig:.4f}")
    print("Ljung-Box (lag 12):")
    print(diag.to_string(index=False))
    print("ENDOG:", ENDOG)
    print("EXOG:", EXOG)


if __name__ == "__main__":
    main()
