"""
Prueba de cointegración de Johansen entre variables endógenas en niveles.

Etapa posterior a confirmar que las variables son I(1):
  - Si las endógenas en niveles cointegran: usar VECM/VECMX.
  - Si no cointegran: usar VARX en primeras diferencias.

Importante:
Johansen se aplica sobre las variables en niveles, no sobre las primeras
diferencias. Por eso el script toma ENDOG_LEVELS como punto de partida.
Si el modelo usa D_ln_Vol_total, la variable en nivel compatible es
Ln_Vol_total; si usa D_Mora_total, la variable en nivel es Mora_total.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import BASE_DIR, DATE_COL, ENDOG, ENDOG_LEVELS, INPUT_FILE, OUT_DIR

POSIBLES_ARCHIVOS_DATOS = [
    Path(INPUT_FILE),
    Path(BASE_DIR) / "data" / "Data estacionaria.xlsx",
]
ARCHIVO_DATOS = next(
    (archivo for archivo in POSIBLES_ARCHIVOS_DATOS if archivo.exists()),
    Path(INPUT_FILE),
)
ARCHIVO_RESULTADOS = Path(OUT_DIR) / "resultados_johansen.xlsx"
ALPHA = 0.05

CRIT_INDEX = {
    0.10: 0,
    0.05: 1,
    0.01: 2,
}


def preparar_variables_johansen(
    df: pd.DataFrame,
    endog_levels: list[str],
    endog_transformadas: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    """
    Obtiene las variables en niveles para Johansen usando ENDOG_LEVELS.

    Si una variable de ENDOG_LEVELS se modela como diferencia logarítmica
    en ENDOG, por ejemplo Vol_total -> D_ln_Vol_total, Johansen usa
    Ln_Vol_total. Si esa columna no existe pero Vol_total sí existe, la crea.
    """
    datos = df.copy()
    variables_johansen = []

    for variable_nivel in endog_levels:
        variable_d_log = f"D_ln_{variable_nivel}"
        variable_log = f"Ln_{variable_nivel}"

        if variable_d_log in endog_transformadas:
            if variable_log not in datos.columns:
                if variable_nivel not in datos.columns:
                    raise KeyError(
                        f"No existe {variable_log} ni {variable_nivel} para Johansen"
                    )

                serie = pd.to_numeric(datos[variable_nivel], errors="coerce")
                if (serie.dropna() <= 0).any():
                    raise ValueError(
                        f"{variable_nivel}: contiene valores <= 0; no se puede crear {variable_log}"
                    )
                datos[variable_log] = np.log(serie)

            variables_johansen.append(variable_log)
        else:
            variables_johansen.append(variable_nivel)

    return datos, variables_johansen


def limpiar_datos_johansen(
    df: pd.DataFrame,
    endog_cols: list[str],
) -> pd.DataFrame:
    """Prepara las variables endógenas en niveles para Johansen."""
    faltantes = [columna for columna in endog_cols if columna not in df.columns]
    if faltantes:
        raise KeyError(
            "No se encontraron estas columnas para Johansen: "
            + ", ".join(faltantes)
        )

    datos = df[endog_cols].apply(pd.to_numeric, errors="coerce")
    datos = datos.replace([np.inf, -np.inf], np.nan).dropna()

    if len(datos) < 24:
        raise ValueError("Johansen requiere una muestra razonable; hay menos de 24 observaciones válidas")

    return datos


def contar_rank_johansen(
    estadisticos: np.ndarray,
    criticos: np.ndarray,
    alpha: float = ALPHA,
) -> int:
    """Cuenta cuántas hipótesis de rango se rechazan secuencialmente."""
    crit_idx = CRIT_INDEX[alpha]
    rank = 0

    for estadistico, valores_criticos in zip(estadisticos, criticos):
        if estadistico > valores_criticos[crit_idx]:
            rank += 1
        else:
            break

    return rank


def tabla_johansen(
    estadisticos: np.ndarray,
    criticos: np.ndarray,
    tipo: str,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Construye tabla de resultados para trace o max-eigen."""
    crit_idx = CRIT_INDEX[alpha]
    filas = []

    for rango, (estadistico, valores_criticos) in enumerate(zip(estadisticos, criticos)):
        filas.append(
            {
                "tipo_prueba": tipo,
                "H0": f"r <= {rango}",
                "estadistico": float(estadistico),
                "critico_90": float(valores_criticos[0]),
                "critico_95": float(valores_criticos[1]),
                "critico_99": float(valores_criticos[2]),
                "rechaza_H0": bool(estadistico > valores_criticos[crit_idx]),
            }
        )

    return pd.DataFrame(filas)


def johansen_test(
    df: pd.DataFrame,
    endog_cols: list[str],
    det_order: int = 0,
    k_ar_diff: int = 1,
    alpha: float = ALPHA,
) -> dict[str, object]:
    """Ejecuta Johansen y devuelve decisión de modelo."""
    datos = limpiar_datos_johansen(df, endog_cols)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=np.exceptions.ComplexWarning)
        resultado = coint_johansen(datos, det_order=det_order, k_ar_diff=k_ar_diff)

    rank_trace = contar_rank_johansen(resultado.lr1, resultado.cvt, alpha=alpha)
    rank_maxeig = contar_rank_johansen(resultado.lr2, resultado.cvm, alpha=alpha)
    n_variables = len(endog_cols)

    if rank_trace == 0:
        cointegran_trace = "No"
        decision_modelo = "VARX en diferencias"
        interpretacion = "No se encontró relación de cointegración."
    elif rank_trace < n_variables:
        cointegran_trace = "Sí"
        decision_modelo = "VECMX"
        interpretacion = "Existe al menos un vector de cointegración."
    else:
        cointegran_trace = "Rango completo"
        decision_modelo = "Revisar orden de integración"
        interpretacion = (
            "El rank es igual al número de variables. Esto no es cointegración "
            "propiamente dicha; sugiere revisar si las variables en niveles son I(1)."
        )

    resumen = {
        "variables": ", ".join(endog_cols),
        "n_observaciones": int(len(datos)),
        "det_order": int(det_order),
        "k_ar_diff": int(k_ar_diff),
        "alpha": float(alpha),
        "rank_trace": int(rank_trace),
        "rank_max_eigen": int(rank_maxeig),
        "cointegran_trace": cointegran_trace,
        "decision_modelo": decision_modelo,
        "criterio_decision": "Prueba trace de Johansen; cointegración requiere 0 < rank < n",
        "interpretacion": interpretacion,
    }

    detalle = pd.concat(
        [
            tabla_johansen(resultado.lr1, resultado.cvt, "trace", alpha=alpha),
            tabla_johansen(resultado.lr2, resultado.cvm, "max_eigen", alpha=alpha),
        ],
        ignore_index=True,
    )

    return {
        "resumen": pd.DataFrame([resumen]),
        "detalle": detalle,
        "eigenvalues": pd.DataFrame({"eigenvalue": resultado.eig}),
    }


def leer_excel_datos(path: Path) -> pd.DataFrame:
    """Lee Sheet1 si existe; si no, lee la primera hoja disponible."""
    try:
        return pd.read_excel(path, sheet_name="Sheet1")
    except ValueError:
        return pd.read_excel(path, sheet_name=0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prueba de cointegración de Johansen para decidir VARX vs VECMX."
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
        "--vars",
        nargs="+",
        default=None,
        help=(
            "Variables endógenas en niveles para Johansen. "
            "Si no se indica, se usan ENDOG_LEVELS de settings.py."
        ),
    )
    parser.add_argument(
        "--det-order",
        type=int,
        default=0,
        help="Orden determinístico de Johansen: -1 sin constante, 0 constante, 1 tendencia.",
    )
    parser.add_argument(
        "--k-ar-diff",
        type=int,
        default=1,
        help="Número de rezagos en diferencias para Johansen.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        choices=[0.10, 0.05, 0.01],
        default=ALPHA,
        help="Nivel de significancia.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archivo_datos = Path(args.input)
    archivo_resultados = Path(args.output)

    df = leer_excel_datos(archivo_datos)
    if DATE_COL in df.columns:
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
        df = df.sort_values(DATE_COL)

    if args.vars is None:
        df, variables_johansen = preparar_variables_johansen(df, ENDOG_LEVELS, ENDOG)
        origen_variables = "ENDOG_LEVELS de settings.py"
    else:
        variables_johansen = args.vars
        origen_variables = "argumento --vars"

    resultado = johansen_test(
        df,
        endog_cols=variables_johansen,
        det_order=args.det_order,
        k_ar_diff=args.k_ar_diff,
        alpha=args.alpha,
    )

    archivo_resultados.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(archivo_resultados, engine="openpyxl") as writer:
        resultado["resumen"].to_excel(writer, sheet_name="Resumen", index=False)
        resultado["detalle"].to_excel(writer, sheet_name="Detalle_Johansen", index=False)
        resultado["eigenvalues"].to_excel(writer, sheet_name="Eigenvalues", index=False)

    resumen = resultado["resumen"]
    detalle = resultado["detalle"]

    print("\nPrueba de cointegración de Johansen")
    print(f"Archivo leído: {archivo_datos}")
    print(f"Origen de variables: {origen_variables}")
    print(f"ENDOG_LEVELS: {', '.join(ENDOG_LEVELS)}")
    print(f"Variables usadas en Johansen: {', '.join(variables_johansen)}")
    print(f"Nivel de significancia: {args.alpha:.0%}\n")
    print(resumen.to_string(index=False))
    print("\nDetalle:")
    print(detalle.to_string(index=False, float_format=lambda valor: f"{valor:.6f}"))
    print(f"\nResultados guardados en: {archivo_resultados}")


if __name__ == "__main__":
    main()
