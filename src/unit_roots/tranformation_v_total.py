"""Diagnóstico especial de transformaciones para Vol_microcreditos.

Este script compara alternativas para la variable clave del objetivo general:

1. D_ln_Vol_microcreditos con pruebas ADF/KPSS usando constante.
2. D_ln_Vol_microcreditos con pruebas ADF/KPSS usando constante y tendencia.
3. D12_ln_Vol_microcreditos, crecimiento logarítmico interanual, usando constante.

No modifica el archivo de datos. Solo crea un reporte para decidir qué
transformación es más defendible antes de pasar a cointegración o VARX.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (  # noqa: E402
    DATE_COL,
    OUT_DIR,
    SAMPLE_END,
    SAMPLE_START,
    TRAIN_END,
    TRAIN_START,
    UNIT_ROOTS_FILE,
)

ALPHA = 0.05
LEVEL_COL = "Vol_microcreditos"
LOG_COL = "Ln_Vol_microcreditos"
D_LOG_COL = "D_ln_Vol_microcreditos"
D12_LOG_COL = "D12_ln_Vol_microcreditos"

ARCHIVO_DATOS = Path(UNIT_ROOTS_FILE)
ARCHIVO_SALIDA = Path(OUT_DIR) / "diagnostico_transformacion_vol_microcredito.xlsx"


def convertir_fechas(serie: pd.Series) -> pd.Series:
    """Convierte fechas de Excel o texto a datetime."""
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_datetime(serie, unit="D", origin="1899-12-30", errors="coerce")
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)


def limpiar_serie(serie: pd.Series) -> pd.Series:
    """Convierte una serie a numérica y elimina NaN/infinitos."""
    limpia = pd.to_numeric(serie, errors="coerce")
    limpia = limpia.replace([np.inf, -np.inf], np.nan).dropna()
    return limpia.astype(float)


def preparar_datos(datos: pd.DataFrame) -> pd.DataFrame:
    """Asegura fecha, logaritmo, diferencia logarítmica e interanual."""
    salida = datos.copy()
    if DATE_COL not in salida.columns:
        raise KeyError(f"No existe la columna de fecha '{DATE_COL}'")
    if LEVEL_COL not in salida.columns and D_LOG_COL not in salida.columns:
        raise KeyError(f"No existe '{LEVEL_COL}' ni '{D_LOG_COL}' en el archivo")

    salida[DATE_COL] = convertir_fechas(salida[DATE_COL])
    salida = salida.sort_values(DATE_COL).reset_index(drop=True)

    if LOG_COL not in salida.columns:
        if LEVEL_COL not in salida.columns:
            raise KeyError(f"No se puede crear {LOG_COL}: falta {LEVEL_COL}")
        nivel = pd.to_numeric(salida[LEVEL_COL], errors="coerce")
        if (nivel.dropna() <= 0).any():
            raise ValueError(f"{LEVEL_COL} contiene valores <= 0; no se puede aplicar log")
        salida[LOG_COL] = np.log(nivel)

    if D_LOG_COL not in salida.columns:
        salida[D_LOG_COL] = salida[LOG_COL].diff()

    salida[D12_LOG_COL] = salida[LOG_COL].diff(12)
    return salida


def filtrar_ventana(datos: pd.DataFrame, inicio: str, fin: str) -> pd.DataFrame:
    """Filtra el DataFrame entre dos fechas inclusivas."""
    inicio_dt = pd.to_datetime(inicio)
    fin_dt = pd.to_datetime(fin)
    return datos[(datos[DATE_COL] >= inicio_dt) & (datos[DATE_COL] <= fin_dt)].copy()


def adf_test(serie: pd.Series, regression: str, alpha: float = ALPHA) -> dict[str, object]:
    """Ejecuta ADF con especificación determinística configurable."""
    y = limpiar_serie(serie)
    if len(y) < 12:
        raise ValueError("ADF requiere al menos 12 observaciones válidas")

    stat, p_value, used_lag, nobs, critical_values, icbest = adfuller(
        y,
        autolag="AIC",
        regression=regression,
    )
    return {
        "adf_estadistico": float(stat),
        "adf_p_valor": float(p_value),
        "adf_rezagos": int(used_lag),
        "adf_nobs": int(nobs),
        "adf_criterio": float(icbest) if icbest is not None else np.nan,
        "adf_rechaza_H0": bool(p_value < alpha),
        "adf_conclusion": "Estacionaria" if p_value < alpha else "No estacionaria",
        "adf_critico_5%": float(critical_values["5%"]),
    }


def kpss_test(serie: pd.Series, regression: str, alpha: float = ALPHA) -> dict[str, object]:
    """Ejecuta KPSS con especificación determinística configurable."""
    y = limpiar_serie(serie)
    if len(y) < 12:
        raise ValueError("KPSS requiere al menos 12 observaciones válidas")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InterpolationWarning)
        stat, p_value, used_lag, critical_values = kpss(
            y,
            regression=regression,
            nlags="auto",
        )
    return {
        "kpss_estadistico": float(stat),
        "kpss_p_valor": float(p_value),
        "kpss_rezagos": int(used_lag),
        "kpss_nobs": int(len(y)),
        "kpss_rechaza_H0": bool(p_value < alpha),
        "kpss_conclusion": "No estacionaria" if p_value < alpha else "Estacionaria",
        "kpss_critico_5%": float(critical_values["5%"]),
    }


def clasificar(adf: dict[str, object], kpss_result: dict[str, object]) -> str:
    """Combina ADF y KPSS."""
    adf_estacionaria = bool(adf["adf_rechaza_H0"])
    kpss_estacionaria = not bool(kpss_result["kpss_rechaza_H0"])
    if adf_estacionaria and kpss_estacionaria:
        return "Sí"
    if not adf_estacionaria and not kpss_estacionaria:
        return "No"
    return "Mixta"


def evaluar_escenario(
    datos: pd.DataFrame,
    ventana: str,
    variable: str,
    escenario: str,
    regression: str,
) -> dict[str, object]:
    """Evalúa una transformación en una ventana concreta."""
    serie = datos[variable]
    y = limpiar_serie(serie)
    adf = adf_test(serie, regression=regression)
    kpss_result = kpss_test(serie, regression=regression)
    estacionaria = clasificar(adf, kpss_result)
    return {
        "ventana": ventana,
        "escenario": escenario,
        "variable": variable,
        "regression": regression,
        "n_observaciones": int(len(y)),
        **adf,
        **kpss_result,
        "estacionaria": estacionaria,
        "decision": "Candidata principal" if estacionaria == "Sí" else "Revisar",
    }


def run_diagnostics(datos: pd.DataFrame) -> pd.DataFrame:
    """Ejecuta los tres escenarios en ventana completa y pre-COVID."""
    datos = preparar_datos(datos)
    ventanas = {
        "Full": filtrar_ventana(datos, SAMPLE_START, SAMPLE_END),
        "Pre_COVID": filtrar_ventana(datos, TRAIN_START, TRAIN_END),
    }
    escenarios = [
        (D_LOG_COL, "D_ln con constante", "c"),
        (D_LOG_COL, "D_ln con constante y tendencia", "ct"),
        (D12_LOG_COL, "D12_ln interanual con constante", "c"),
    ]

    filas = []
    for nombre_ventana, datos_ventana in ventanas.items():
        for variable, escenario, regression in escenarios:
            try:
                filas.append(
                    evaluar_escenario(
                        datos_ventana,
                        ventana=nombre_ventana,
                        variable=variable,
                        escenario=escenario,
                        regression=regression,
                    )
                )
            except Exception as exc:
                filas.append(
                    {
                        "ventana": nombre_ventana,
                        "escenario": escenario,
                        "variable": variable,
                        "regression": regression,
                        "n_observaciones": 0,
                        "adf_p_valor": np.nan,
                        "kpss_p_valor": np.nan,
                        "estacionaria": "Error",
                        "decision": str(exc),
                    }
                )
    return pd.DataFrame(filas)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compara transformaciones candidatas para Vol_microcreditos."
    )
    parser.add_argument(
        "--input",
        default=str(ARCHIVO_DATOS),
        help="Ruta del Excel de entrada.",
    )
    parser.add_argument(
        "--sheet",
        default="Datos_transformados",
        help="Hoja del Excel de entrada.",
    )
    parser.add_argument(
        "--output",
        default=str(ARCHIVO_SALIDA),
        help="Ruta del Excel de salida.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archivo_datos = Path(args.input)
    archivo_salida = Path(args.output)

    datos = pd.read_excel(archivo_datos, sheet_name=args.sheet)
    resumen = run_diagnostics(datos)

    archivo_salida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(archivo_salida, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="Diagnostico", index=False)

    columnas = [
        "ventana",
        "escenario",
        "variable",
        "n_observaciones",
        "adf_p_valor",
        "kpss_p_valor",
        "estacionaria",
        "decision",
    ]
    print("\nDiagnóstico de transformaciones para Vol_microcreditos")
    print(f"Archivo leído: {archivo_datos}")
    print(f"Resultados guardados en: {archivo_salida}\n")
    print(resumen[columnas].to_string(index=False, float_format=lambda valor: f"{valor:.6f}"))


if __name__ == "__main__":
    main()
