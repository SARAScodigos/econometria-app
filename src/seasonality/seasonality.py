"""Prueba de estacionalidad mediante una regresión con dummies mensuales.

Para cada variable se estima:

    y_t = constante + tendencia_t + dummies_mensuales + error_t

Enero es el mes de referencia. La hipótesis nula de la prueba F es que los
coeficientes de las otras once dummies mensuales son conjuntamente cero.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (
    DATE_COL,
    OUT_DIR,
    SEASONALITY_INPUT_FILE,
    SEASONALITY_VARIABLES,
    configure_runtime,
)

ARCHIVO_DATOS = Path(SEASONALITY_INPUT_FILE)
ARCHIVO_RESULTADOS = Path(OUT_DIR) / "resultados_estacionalidad.xlsx"
ALPHA = 0.05

VARIABLES = SEASONALITY_VARIABLES


def convertir_fechas(serie: pd.Series) -> pd.Series:
    """Convierte fechas de Excel o textos de fecha a ``datetime``."""
    if pd.api.types.is_numeric_dtype(serie):
        # Excel cuenta los días desde 1899-12-30.
        return pd.to_datetime(serie, unit="D", origin="1899-12-30", errors="coerce")
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def probar_estacionalidad(
    datos: pd.DataFrame, variable: str, alpha: float = ALPHA
) -> dict[str, object]:
    """Estima la regresión y ejecuta la prueba F conjunta de las dummies."""
    muestra = datos[[DATE_COL, variable]].copy()
    muestra[variable] = pd.to_numeric(muestra[variable], errors="coerce")
    muestra = muestra.dropna()

    if len(muestra) <= 13:
        raise ValueError(f"{variable}: no hay suficientes observaciones para la prueba")

    meses = pd.Categorical(muestra[DATE_COL].dt.month, categories=range(1, 13))
    dummies = pd.get_dummies(meses, prefix="mes", drop_first=True, dtype=float)

    # La tendencia evita atribuir a los meses un patrón que solo proviene del
    # crecimiento o caída secular de la serie.
    explicativas = pd.DataFrame(
        {"tendencia": np.arange(1, len(muestra) + 1, dtype=float)},
        index=muestra.index,
    )
    explicativas = pd.concat([explicativas, dummies.set_axis(muestra.index)], axis=1)
    explicativas = sm.add_constant(explicativas, has_constant="add")

    modelo = sm.OLS(muestra[variable], explicativas).fit()
    columnas_mes = [columna for columna in explicativas if columna.startswith("mes_")]

    # H0: beta_febrero = ... = beta_diciembre = 0.
    restricciones = np.zeros((len(columnas_mes), explicativas.shape[1]))
    for fila, columna in enumerate(columnas_mes):
        restricciones[fila, explicativas.columns.get_loc(columna)] = 1.0

    prueba_f = modelo.f_test(restricciones)
    estadistico_f = float(np.asarray(prueba_f.fvalue).squeeze())
    p_valor = float(np.asarray(prueba_f.pvalue).squeeze())

    return {
        "variable": variable,
        "n_observaciones": int(modelo.nobs),
        "estadistico_F": estadistico_f,
        "p_valor": p_valor,
        "es_estacional": "Sí" if p_valor < alpha else "No",
        "decision": "Rechazar H0" if p_valor < alpha else "No rechazar H0",
    }


def main() -> None:
    configure_runtime()
    datos = pd.read_excel(ARCHIVO_DATOS, sheet_name="Sheet1")

    columnas_faltantes = [
        columna for columna in [DATE_COL, *VARIABLES] if columna not in datos.columns
    ]
    if columnas_faltantes:
        raise KeyError(
            "No se encontraron estas columnas en el Excel: "
            + ", ".join(columnas_faltantes)
        )

    datos[DATE_COL] = convertir_fechas(datos[DATE_COL])
    if datos[DATE_COL].isna().all():
        raise ValueError(f"No fue posible interpretar la columna '{DATE_COL}'")

    resultados = pd.DataFrame(
        [probar_estacionalidad(datos, variable) for variable in VARIABLES]
    )
    resultados.to_excel(ARCHIVO_RESULTADOS, index=False)

    print("\nPrueba F conjunta de dummies mensuales")
    print(f"H0: no existe estacionalidad mensual | nivel de significancia = {ALPHA:.0%}\n")
    print(resultados.to_string(index=False, float_format=lambda valor: f"{valor:.6f}"))
    print(f"\nResultados guardados en: {ARCHIVO_RESULTADOS}")


if __name__ == "__main__":
    main()
