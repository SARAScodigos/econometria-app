"""
Desestacionalización mediante regresión con dummies mensuales.

Flujo de uso:
  1. Ejecutar seasonality.py y revisar la columna 'es_estacional'.
  2. Agregar a VARIABLES_ESTACIONALES las variables que mostraron estacionalidad
     significativa (p_valor < 0.05 en la prueba F conjunta de dummies).
  3. Ejecutar este script: estima la componente estacional para cada variable
     de la lista y guarda las series ajustadas.

Método: se reutiliza el mismo modelo que usa seasonality.py —
    y_t = constante + tendencia_t + dummies_mensuales + error_t
La componente estacional en el período t es la contribución de la dummy mensual
correspondiente. La serie ajustada es:
    y_t_SA = y_t − componente_estacional_t
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import DATE_COL, OUT_DIR, DESEASONALIZE_INPUT_FILE, configure_runtime

# ---------------------------------------------------------------------------
# Configuración de rutas
# ---------------------------------------------------------------------------
ARCHIVO_DATOS = Path(DESEASONALIZE_INPUT_FILE)
ARCHIVO_SALIDA = Path(OUT_DIR) / "datos_desestacionalizados.xlsx"
ALPHA = 0.05

# ---------------------------------------------------------------------------
# LISTA DE VARIABLES A DESESTACIONALIZAR
# Editar esta lista con los nombres de las variables que seasonality.py
# identificó como estacionales (es_estacional == "Sí").
# ---------------------------------------------------------------------------
VARIABLES_ESTACIONALES: list[str] = [
    # "Vol_comerciales",
    # "Mora_comerciales",
    # "Vol_consumo",
    # "Mora_consumo",
    # "Vol_hipotecarios",
    # "Mora_hipotecarios",
    # "Vol_microcreditos",
    "Mora_microcreditos",
    # "Vol_total",
    "Mora_total",
    # "Tasa_Ref",
    # "PBI_Desestacionalizado",
]


# ---------------------------------------------------------------------------
# Funciones auxiliares (comparten lógica con seasonality.py)
# ---------------------------------------------------------------------------
def convertir_fechas(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_datetime(serie, unit="D", origin="1899-12-30", errors="coerce")
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def estimar_componente_estacional(
    datos: pd.DataFrame, variable: str
) -> tuple[pd.Series, pd.Series, object]:
    """Estima el modelo con dummies y devuelve la componente estacional.

    Returns
    -------
    componente : pd.Series
        Contribución de las dummies mensuales para cada observación.
        Para el mes de referencia (enero) vale 0.
    serie_ajustada : pd.Series
        Serie original menos la componente estacional.
    modelo : RegressionResultsWrapper
        Resultado completo de OLS para inspección.
    """
    muestra = datos[[DATE_COL, variable]].copy()
    muestra[variable] = pd.to_numeric(muestra[variable], errors="coerce")
    muestra = muestra.dropna()

    if len(muestra) <= 13:
        raise ValueError(f"{variable}: observaciones insuficientes para desestacionalizar")

    meses = pd.Categorical(muestra[DATE_COL].dt.month, categories=range(1, 13))
    dummies = pd.get_dummies(meses, prefix="mes", drop_first=True, dtype=float)

    explicativas = pd.DataFrame(
        {"tendencia": np.arange(1, len(muestra) + 1, dtype=float)},
        index=muestra.index,
    )
    explicativas = pd.concat([explicativas, dummies.set_axis(muestra.index)], axis=1)
    explicativas = sm.add_constant(explicativas, has_constant="add")

    modelo = sm.OLS(muestra[variable], explicativas).fit()

    # Columnas de dummies en el modelo
    columnas_mes = [c for c in explicativas.columns if c.startswith("mes_")]

    # Componente estacional = suma ponderada de las dummies (enero = 0 por construcción)
    componente = explicativas[columnas_mes].dot(modelo.params[columnas_mes])
    componente.index = muestra.index

    serie_ajustada = muestra[variable] - componente
    serie_ajustada.name = f"{variable}_SA"

    return componente, serie_ajustada, modelo


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    configure_runtime()
    if not VARIABLES_ESTACIONALES:
        print(
            "VARIABLES_ESTACIONALES está vacía.\n"
            "Ejecuta primero seasonality.py, identifica las variables estacionales\n"
            "y agrégalas a la lista en este script."
        )
        return

    datos = pd.read_excel(ARCHIVO_DATOS, sheet_name="Sheet1")
    datos[DATE_COL] = convertir_fechas(datos[DATE_COL])

    columnas_faltantes = [v for v in VARIABLES_ESTACIONALES if v not in datos.columns]
    if columnas_faltantes:
        raise KeyError(f"Columnas no encontradas en el Excel: {columnas_faltantes}")

    print("\nDesestacionalización — método: regresión con dummies mensuales")
    print(f"{'Variable':<30} {'Coef. estacional máx':>22} {'Coef. estacional mín':>22}")
    print("-" * 76)

    series_ajustadas: dict[str, pd.Series] = {}
    resumen_filas = []

    for variable in VARIABLES_ESTACIONALES:
        componente, serie_ajustada, modelo = estimar_componente_estacional(datos, variable)

        coef_max = float(componente.max())
        coef_min = float(componente.min())
        print(f"{variable:<30} {coef_max:>22.6f} {coef_min:>22.6f}")

        series_ajustadas[serie_ajustada.name] = serie_ajustada
        resumen_filas.append({
            "variable_original": variable,
            "variable_ajustada": serie_ajustada.name,
            "componente_max": coef_max,
            "componente_min": coef_min,
            "rango_componente": coef_max - coef_min,
            "R2_modelo": float(modelo.rsquared),
        })

    # Alinear todas las series ajustadas con el índice de fechas
    df_sa = pd.DataFrame(series_ajustadas)
    df_sa.insert(0, DATE_COL, datos[DATE_COL].values[: len(df_sa)])

    # Guardar
    ARCHIVO_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ARCHIVO_SALIDA, engine="openpyxl") as writer:
        df_sa.to_excel(writer, sheet_name="Series_SA", index=False)
        pd.DataFrame(resumen_filas).to_excel(writer, sheet_name="Resumen", index=False)

    print(f"\nSeries ajustadas guardadas en: {ARCHIVO_SALIDA}")
    print(f"Variables desestacionalizadas: {len(VARIABLES_ESTACIONALES)}")
    print("\nResumen de coeficientes estacionales:")
    print(pd.DataFrame(resumen_filas).to_string(index=False, float_format=lambda v: f"{v:.6f}"))


if __name__ == "__main__":
    main()
