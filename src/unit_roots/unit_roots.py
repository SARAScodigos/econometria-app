"""
Comprobación de estacionariedad mediante pruebas de raíz unitaria.

Este script lee el archivo de datos, aplica ADF y KPSS a las variables
seleccionadas, y guarda un resumen en Excel.

Interpretación:
  - ADF:
      H0 = la serie tiene raíz unitaria, es decir, no es estacionaria.
      p < 0.05 => se rechaza H0 => evidencia de estacionariedad.

  - KPSS:
      H0 = la serie es estacionaria.
      p < 0.05 => se rechaza H0 => evidencia de no estacionariedad.

Una variable se marca como estacionaria cuando ambas pruebas son consistentes:
ADF rechaza raíz unitaria y KPSS no rechaza estacionariedad.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tools.sm_exceptions import InterpolationWarning

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

BASE_DIR = Path(__file__).resolve().parents[2]
ARCHIVO_DATOS = BASE_DIR / "data" / "Data estacional.xlsx"
ARCHIVO_RESULTADOS = BASE_DIR / "outputs" / "resultados_raiz_unitaria.xlsx"
ALPHA = 0.05

VARIABLES_NIVELES = [
    "Vol_comerciales",
    "Mora_comerciales",
    "Vol_consumo",
    "Mora_consumo",
    "Vol_hipotecarios",
    "Mora_hipotecarios",
    "Vol_microcreditos",
    "Mora_microcreditos",
    "Vol_total",
    "Mora_total",
    "Tasa_Ref",
    "PBI_Desestacionalizado",
]

VARIABLES_TRANSFORMADAS = [
    "D_ln_Vol_comerciales",
    "D_Mora_comerciales",
    "D_ln_Vol_consumo",
    "D_Mora_consumo",
    "D_ln_Vol_hipotecarios",
    "D_Mora_hipotecarios",
    "D_ln_Vol_microcreditos",
    "D_Mora_microcreditos",
    "D_ln_Vol_total",
    "D_Mora_total",
    "D_Tasa_Ref",
    "D_ln_PBI_Desestacionalizado",
]


def limpiar_serie(series: pd.Series) -> pd.Series:
    """Convierte una serie a numérica y elimina NaN/infinitos."""
    limpia = pd.to_numeric(series, errors="coerce")
    limpia = limpia.replace([np.inf, -np.inf], np.nan).dropna()
    return limpia.astype(float)


def adf_test(series: pd.Series, alpha: float = ALPHA) -> dict[str, object]:
    """Ejecuta la prueba ADF."""
    y = limpiar_serie(series)
    if len(y) < 12:
        raise ValueError("ADF requiere al menos 12 observaciones válidas")

    stat, p_value, used_lag, nobs, critical_values, icbest = adfuller(
        y,
        autolag="AIC",
        regression="c",
    )

    return {
        "prueba": "ADF",
        "estadistico": float(stat),
        "p_valor": float(p_value),
        "rezagos": int(used_lag),
        "n_observaciones": int(nobs),
        "criterio": float(icbest) if icbest is not None else np.nan,
        "rechaza_H0": bool(p_value < alpha),
        "conclusion": "Estacionaria" if p_value < alpha else "No estacionaria",
        "valor_critico_1%": float(critical_values["1%"]),
        "valor_critico_5%": float(critical_values["5%"]),
        "valor_critico_10%": float(critical_values["10%"]),
    }


def kpss_test(series: pd.Series, alpha: float = ALPHA) -> dict[str, object]:
    """Ejecuta la prueba KPSS."""
    y = limpiar_serie(series)
    if len(y) < 12:
        raise ValueError("KPSS requiere al menos 12 observaciones válidas")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InterpolationWarning)
        stat, p_value, used_lag, critical_values = kpss(
            y,
            regression="c",
            nlags="auto",
        )

    return {
        "prueba": "KPSS",
        "estadistico": float(stat),
        "p_valor": float(p_value),
        "rezagos": int(used_lag),
        "n_observaciones": int(len(y)),
        "criterio": np.nan,
        "rechaza_H0": bool(p_value < alpha),
        "conclusion": "No estacionaria" if p_value < alpha else "Estacionaria",
        "valor_critico_1%": float(critical_values["1%"]),
        "valor_critico_5%": float(critical_values["5%"]),
        "valor_critico_10%": float(critical_values["10%"]),
    }


def clasificar_estacionariedad(adf: dict[str, object], kpss_result: dict[str, object]) -> str:
    """Combina ADF y KPSS en una decisión práctica."""
    adf_estacionaria = bool(adf["rechaza_H0"])
    kpss_estacionaria = not bool(kpss_result["rechaza_H0"])

    if adf_estacionaria and kpss_estacionaria:
        return "Sí"
    if not adf_estacionaria and not kpss_estacionaria:
        return "No"
    return "Mixta"


def evaluar_variable(
    datos: pd.DataFrame,
    variable: str,
    alpha: float = ALPHA,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Evalúa una variable con ADF y KPSS."""
    adf = adf_test(datos[variable], alpha=alpha)
    kpss_result = kpss_test(datos[variable], alpha=alpha)
    estacionaria = clasificar_estacionariedad(adf, kpss_result)

    resumen = {
        "variable": variable,
        "n_observaciones": int(limpiar_serie(datos[variable]).shape[0]),
        "adf_p_valor": adf["p_valor"],
        "kpss_p_valor": kpss_result["p_valor"],
        "estacionaria": estacionaria,
        "decision": "Usar esta serie" if estacionaria == "Sí" else "Revisar transformación",
    }

    detalle = []
    for resultado in [adf, kpss_result]:
        fila = {"variable": variable}
        fila.update(resultado)
        detalle.append(fila)

    return resumen, detalle


def run_all(
    df: pd.DataFrame,
    cols: Iterable[str],
    alpha: float = ALPHA,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ejecuta ADF y KPSS para una lista de columnas."""
    resumen_filas = []
    detalle_filas = []

    for columna in cols:
        if columna not in df.columns:
            resumen_filas.append(
                {
                    "variable": columna,
                    "n_observaciones": 0,
                    "adf_p_valor": np.nan,
                    "kpss_p_valor": np.nan,
                    "estacionaria": "No evaluada",
                    "decision": "No existe en el archivo",
                }
            )
            continue

        try:
            resumen, detalle = evaluar_variable(df, columna, alpha=alpha)
            resumen_filas.append(resumen)
            detalle_filas.extend(detalle)
        except Exception as exc:
            resumen_filas.append(
                {
                    "variable": columna,
                    "n_observaciones": int(limpiar_serie(df[columna]).shape[0]),
                    "adf_p_valor": np.nan,
                    "kpss_p_valor": np.nan,
                    "estacionaria": "Error",
                    "decision": str(exc),
                }
            )

    return pd.DataFrame(resumen_filas), pd.DataFrame(detalle_filas)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Comprueba estacionariedad con ADF y KPSS."
    )
    parser.add_argument(
        "--input",
        default=str(ARCHIVO_DATOS),
        help="Ruta del Excel de entrada.",
    )
    parser.add_argument(
        "--output",
        default=str(ARCHIVO_RESULTADOS),
        help="Ruta del Excel de salida.",
    )
    parser.add_argument(
        "--solo-transformadas",
        action="store_true",
        help="Evalúa solo columnas transformadas: D_*, D_ln_*.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archivo_datos = Path(args.input)
    archivo_resultados = Path(args.output)

    datos = pd.read_excel(archivo_datos, sheet_name="Sheet1")
    variables = VARIABLES_TRANSFORMADAS if args.solo_transformadas else [
        *VARIABLES_NIVELES,
        *VARIABLES_TRANSFORMADAS,
    ]

    resumen, detalle = run_all(datos, variables)

    archivo_resultados.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(archivo_resultados, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
        detalle.to_excel(writer, sheet_name="Detalle_ADF_KPSS", index=False)

    print("\nPruebas de raíz unitaria: ADF y KPSS")
    print(f"Archivo leído: {archivo_datos}")
    print(f"Nivel de significancia: {ALPHA:.0%}\n")
    print(resumen.to_string(index=False, float_format=lambda valor: f"{valor:.6f}"))
    print(f"\nResultados guardados en: {archivo_resultados}")


if __name__ == "__main__":
    main()
