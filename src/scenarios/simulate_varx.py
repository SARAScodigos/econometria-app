"""Utilidades reutilizables para simular escenarios con un VARX estimado."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


def simulate_varx_path(
    df_history: pd.DataFrame,
    fit: dict,
    endog_cols: list[str],
    exog_future: pd.DataFrame,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Simula una trayectoria VARX con innovaciones iguales a cero.

    Usa los valores observados antes de ``start`` como historia inicial y luego
    alimenta recursivamente los valores simulados.
    """
    p = int(fit["p"])
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    idx = pd.date_range(start=start_dt, end=end_dt, freq="MS")

    y_sim = pd.DataFrame(index=idx, columns=endog_cols, dtype=float)
    x_cols = list(fit["X_columns"])

    for t in idx:
        x_vec = []
        for name in x_cols:
            if name == "const":
                x_vec.append(1.0)
                continue

            if "_L" in name:
                base, lag_label = name.rsplit("_L", 1)
                lag = int(lag_label)
                lag_date = (t - pd.offsets.MonthBegin(lag)).normalize()
                if lag_date in y_sim.index and pd.notna(y_sim.loc[lag_date, base]):
                    x_vec.append(float(y_sim.loc[lag_date, base]))
                else:
                    x_vec.append(float(df_history.loc[lag_date, base]))
                continue

            x_vec.append(float(exog_future.loc[t, name]))

        x_vec = np.asarray(x_vec, dtype=float)
        for ycol in endog_cols:
            params = fit["results"][ycol].params
            y_sim.loc[t, ycol] = float(np.dot(x_vec, params))

    return y_sim


def apply_exog_overrides(
    exog: pd.DataFrame,
    overrides: Mapping[str, float | int | pd.Series],
) -> pd.DataFrame:
    """Devuelve una copia de exógenas con columnas reemplazadas por escenario."""
    out = exog.copy()
    for col, value in overrides.items():
        if col not in out.columns:
            raise KeyError(f"No existe la exógena '{col}' para construir escenario")
        if isinstance(value, pd.Series):
            out[col] = value.reindex(out.index).to_numpy()
        else:
            out[col] = value
    return out


def reconstruct_total_levels(
    raw_df: pd.DataFrame,
    diffs: pd.DataFrame,
    base_date: str,
    suffix: str,
) -> pd.DataFrame:
    """Reconstruye Vol_total y Mora_total desde diferencias simuladas."""
    base_dt = pd.to_datetime(base_date)
    vol0 = float(raw_df.loc[base_dt, "Vol_total"])
    mora0 = float(raw_df.loc[base_dt, "Mora_total"])
    if vol0 <= 0:
        raise ValueError("Vol_total base debe ser positivo para reconstruir logaritmos")

    out = pd.DataFrame(index=diffs.index)
    out[f"Ln_Vol_total_{suffix}"] = np.log(vol0) + diffs["D_ln_Vol_total"].cumsum()
    out[f"Vol_total_{suffix}"] = np.exp(out[f"Ln_Vol_total_{suffix}"])
    out[f"Mora_total_{suffix}"] = mora0 + diffs["D_Mora_total"].cumsum()
    return out
