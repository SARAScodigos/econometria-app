"""
Selección del número óptimo de rezagos: AIC, BIC, HQIC y criterio de parsimonia.

Etapa 6a del flujo VARX. Evalúa candidatos p y reporta tabla de criterios
de información para apoyar la decisión del investigador.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import ENDOG, EXOG, MAX_LAG, TRAIN_START, TRAIN_END
from src.diagnostics.diagnostics import estimate_varx_ols


def system_information_criteria(fit: dict, n_obs: int) -> tuple[float, float]:
    """Calcula AIC/BIC multivariado del sistema VARX."""
    sign, logdet = np.linalg.slogdet(fit["Sigma"])
    if sign <= 0:
        return np.nan, np.nan

    k_endog = len(ENDOG)
    k_exog = len(EXOG)
    p = int(fit["p"])
    params_per_eq = 1 + k_endog * p + k_exog
    params_system = k_endog * params_per_eq

    aic = logdet + (2 * params_system / n_obs)
    bic = logdet + (np.log(n_obs) * params_system / n_obs)
    return float(aic), float(bic)


def ic_table(df: pd.DataFrame, max_lag: int = MAX_LAG) -> pd.DataFrame:
    rows = []
    for p in range(1, max_lag + 1):
        try:
            fit = estimate_varx_ols(df, p) # Estimacion del modelo VARX para un p determinado por __main__
            aic = float(np.mean([fit["results"][y].aic for y in ENDOG]))
            bic = float(np.mean([fit["results"][y].bic for y in ENDOG]))
            n_obs = int(len(fit["Y_index"]))
            aic_system, bic_system = system_information_criteria(fit, n_obs)
            rows.append({
                "p": p,
                "n_obs": n_obs,
                "AIC_mean": aic,
                "BIC_mean": bic,
                "AIC_system": aic_system,
                "BIC_system": bic_system,
            })
        except Exception:
            continue
    return pd.DataFrame(rows).sort_values("p").reset_index(drop=True)


if __name__ == "__main__":
    from src.config.settings import VARX_MODEL_FILE, configure_runtime
    from src.data.loader import load_and_prepare, slice_window

    configure_runtime()
    df = slice_window(load_and_prepare(VARX_MODEL_FILE), "full")
    tabla = ic_table(df)
    print(f"Ventana de seleccion: {TRAIN_START} a {TRAIN_END}")
    print(tabla.to_string(index=False))
    print(f"Endogenas: {ENDOG}")
    print(f"Exogenas: {EXOG}")
    print(f"\np óptimo AIC: {int(tabla.loc[tabla['AIC_mean'].idxmin(), 'p'])}")
    print(f"p óptimo BIC: {int(tabla.loc[tabla['BIC_mean'].idxmin(), 'p'])}")
    print(f"p óptimo AIC sistema: {int(tabla.loc[tabla['AIC_system'].idxmin(), 'p'])}")
    print(f"p óptimo BIC sistema: {int(tabla.loc[tabla['BIC_system'].idxmin(), 'p'])}")
