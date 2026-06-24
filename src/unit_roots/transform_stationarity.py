"""
Genera transformaciones usuales para trabajar con series estacionarias.

Entrada por defecto:
    econometria-app/data/Data No estacionaria.xlsx

Salida por defecto:
    econometria-app/outputs/datos_transformados_estacionarios.xlsx

Transformaciones aplicadas:
  - Variables de volumen y PBI:
      Ln_variable = log(variable)
      D_ln_variable = diferencia del logaritmo

  - Variables de mora y tasa:
      D_variable = primera diferencia

El script no sobrescribe el Excel original.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

BASE_DIR = Path(__file__).resolve().parents[2]
ARCHIVO_DATOS = BASE_DIR / "data" / "Data estacional.xlsx"
ARCHIVO_SALIDA = BASE_DIR / "outputs" / "datos_transformados_estacionarios.xlsx"
DATE_COL = "fecha"

VARIABLES_LOG_DIFF = [
    "Vol_comerciales",
    "Vol_consumo",
    "Vol_hipotecarios",
    "Vol_microcreditos",
    "Vol_total",
    "PBI_Desestacionalizado",
]

VARIABLES_DIFF = [
    "Mora_comerciales",
    "Mora_consumo",
    "Mora_hipotecarios",
    "Mora_microcreditos",
    "Mora_total",
    "Tasa_Ref",
]


def convertir_fechas(serie: pd.Series) -> pd.Series:
    """Convierte fechas de Excel o texto a datetime."""
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_datetime(serie, unit="D", origin="1899-12-30", errors="coerce")
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def agregar_log_diferencia(datos: pd.DataFrame, variable: str) -> list[str]:
    """Agrega logaritmo y primera diferencia del logaritmo."""
    if variable not in datos.columns:
        raise KeyError(f"No existe la columna {variable}")

    serie = pd.to_numeric(datos[variable], errors="coerce")
    if (serie.dropna() <= 0).any():
        raise ValueError(
            f"{variable}: contiene valores <= 0; no se puede aplicar logaritmo"
        )

    nombre_log = f"Ln_{variable}"
    nombre_d_log = f"D_ln_{variable}"
    datos[nombre_log] = np.log(serie)
    datos[nombre_d_log] = datos[nombre_log].diff()
    return [nombre_log, nombre_d_log]


def agregar_diferencia(datos: pd.DataFrame, variable: str) -> str:
    """Agrega primera diferencia simple."""
    if variable not in datos.columns:
        raise KeyError(f"No existe la columna {variable}")

    nombre_d = f"D_{variable}"
    datos[nombre_d] = pd.to_numeric(datos[variable], errors="coerce").diff()
    return nombre_d


def transformar_datos(datos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve el DataFrame transformado y una tabla resumen."""
    salida = datos.copy()
    creadas = []

    if DATE_COL in salida.columns:
        salida[DATE_COL] = convertir_fechas(salida[DATE_COL])
        salida = salida.sort_values(DATE_COL).reset_index(drop=True)

    for variable in VARIABLES_LOG_DIFF:
        columnas = agregar_log_diferencia(salida, variable)
        creadas.append(
            {
                "variable_original": variable,
                "transformacion": "logaritmo y primera diferencia logarítmica",
                "columnas_creadas": ", ".join(columnas),
            }
        )

    for variable in VARIABLES_DIFF:
        columna = agregar_diferencia(salida, variable)
        creadas.append(
            {
                "variable_original": variable,
                "transformacion": "primera diferencia",
                "columnas_creadas": columna,
            }
        )

    resumen = pd.DataFrame(creadas)
    return salida, resumen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera logs y primeras diferencias para series no estacionarias."
    )
    parser.add_argument(
        "--input",
        default=str(ARCHIVO_DATOS),
        help="Ruta del Excel de entrada.",
    )
    parser.add_argument(
        "--output",
        default=str(ARCHIVO_SALIDA),
        help="Ruta del Excel de salida.",
    )
    parser.add_argument(
        "--dropna",
        action="store_true",
        help="Elimina la primera fila con NaN generado por las diferencias.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archivo_datos = Path(args.input)
    archivo_salida = Path(args.output)

    datos = pd.read_excel(archivo_datos, sheet_name="Sheet1")
    datos_transformados, resumen = transformar_datos(datos)

    if args.dropna:
        columnas_creadas = [
            columna
            for columnas in resumen["columnas_creadas"]
            for columna in columnas.split(", ")
        ]
        datos_transformados = datos_transformados.dropna(subset=columnas_creadas)

    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(archivo_salida, engine="openpyxl") as writer:
        datos_transformados.to_excel(writer, sheet_name="Datos_transformados", index=False)
        resumen.to_excel(writer, sheet_name="Resumen_transformaciones", index=False)

    print("\nTransformaciones para estacionariedad")
    print(f"Archivo leído: {archivo_datos}")
    print(f"Archivo guardado: {archivo_salida}\n")
    print(resumen.to_string(index=False))


if __name__ == "__main__":
    main()
