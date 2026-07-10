"""
Estimacion VARX con toda la muestra disponible.
Selecciona p por ruido blanco + estabilidad y reporta diagnosticos.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import ENDOG, EXOG, OUT_DIR, SAMPLE_START, SAMPLE_END, VARX_MODEL_FILE, configure_runtime
from src.data.loader import load_and_prepare, slice_window
from src.diagnostics.diagnostics import (
    coefficient_table,
    estimate_varx_ols,
    stability_roots,
    residual_diagnostics,
    varx_diagnostics,
)


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
    df_all = slice_window(load_and_prepare(VARX_MODEL_FILE), "full")
    lb_lags = 12
    p_candidates = [12]
    p, fit, eigvals, diag = choose_p_by_whiteness(df_all, p_candidates, lb_lags, alpha=0.05)

    stable = bool(np.all(np.abs(eigvals) < 1))
    max_eig = float(np.max(np.abs(eigvals)))
    diagnostics = varx_diagnostics(fit, lb_lags=lb_lags)
    coefficients = coefficient_table(fit, cov_type="HC3")
    output_path = Path(OUT_DIR) / "resultados_varx_total.xlsx"

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        coefficients.to_excel(writer, sheet_name="Coeficientes_HC3", index=False)
        diagnostics["stability"].to_excel(writer, sheet_name="Estabilidad", index=False)
        diagnostics["stability_roots"].to_excel(writer, sheet_name="Raices_AR", index=False)
        diagnostics["ljung_box"].to_excel(writer, sheet_name="Ljung_Box", index=False)
        diagnostics["jarque_bera"].to_excel(writer, sheet_name="Jarque_Bera", index=False)
        diagnostics["heteroskedasticity"].to_excel(
            writer,
            sheet_name="Heterocedasticidad",
            index=False,
        )
        pd.DataFrame(fit["Sigma"], index=ENDOG, columns=ENDOG).to_excel(
            writer,
            sheet_name="Sigma_residuos",
        )

    print("=== VARX TOTAL ===")
    print(f"Ventana: {SAMPLE_START} a {SAMPLE_END}")
    print(f"p(elegido) = {p}")
    print(f"Estable (|eig|<1): {stable} | max|eig|={max_eig:.4f}")
    print(f"Ljung-Box (lag {lb_lags}):")
    print(diag.to_string(index=False))
    print("ENDOG:", ENDOG)
    print("EXOG:", EXOG)
    print("\nJarque-Bera (normalidad de residuos):")
    print(diagnostics["jarque_bera"].to_string(index=False))
    print("\nHeterocedasticidad (Breusch-Pagan / White):")
    print(diagnostics["heteroskedasticity"].to_string(index=False))
    print("\nCoeficientes principales con errores robustos HC3:")
    key_vars = ["D_Covid", "D_Intervencion_Gob", "D_ln_PBI_Desestacionalizado", "D_Tasa_Ref"]
    key_rows = coefficients[coefficients["variable"].isin(key_vars)]
    print(key_rows.to_string(index=False))
    print(f"\nResultados guardados en: {output_path}")


if __name__ == "__main__":
    main()
