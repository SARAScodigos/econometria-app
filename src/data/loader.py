import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import DATE_COL, ENDOG, EXOG, WINDOWS


def load_and_prepare(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No encuentro '{path}'. Colocalo junto al script o ajusta INPUT_FILE."
        )
    df = pd.read_excel(path)

    if DATE_COL not in df.columns:
        raise ValueError(f"El archivo debe tener una columna con nombre '{DATE_COL}'.")

    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.set_index(DATE_COL).sort_index()

    needed = ENDOG + EXOG
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    df_use = df[needed].copy().dropna()
    df_use.index = pd.to_datetime(df_use.index.date)
    return df_use


def slice_window(df: pd.DataFrame, window: str, copy: bool = True) -> pd.DataFrame:
    """Devuelve una ventana temporal definida en settings.WINDOWS."""
    if window not in WINDOWS:
        valid = ", ".join(sorted(WINDOWS))
        raise ValueError(f"Ventana desconocida '{window}'. Opciones validas: {valid}")

    start, end = WINDOWS[window]
    out = df.loc[start:end] #recortar fechas
    return out.copy() if copy else out #debbolver el df

#===============================TAREA PAR ALA CASA ===============================

def make_lagged_matrix(df: pd.DataFrame, endog_cols, exog_cols, p: int):
    Y = df[endog_cols].copy()
    X_exog = df[exog_cols].copy()

    lagged = []
    lagged_names = []
    for k in range(1, p + 1):
        lagged.append(Y.shift(k))
        lagged_names += [f"{col}_L{k}" for col in endog_cols]

    X_lags = pd.concat(lagged, axis=1)
    X_lags.columns = lagged_names

    X = pd.concat([X_lags, X_exog], axis=1)
    X = sm.add_constant(X, has_constant="add")

    data = pd.concat([Y, X], axis=1).dropna()
    Y_aligned = data[endog_cols]
    X_aligned = data.drop(columns=endog_cols)
    return Y_aligned, X_aligned


def build_one_step_forecast(df_all: pd.DataFrame, fit, p: int, target_date: str):
    t = pd.to_datetime(target_date)

    if t not in df_all.index:
        raise ValueError(f"La fecha {target_date} no esta en el indice del dataset.")

    Xcols = list(fit["X_columns"])
    n = len(ENDOG)

    x_vec = []
    for name in Xcols:
        if name == "const":
            x_vec.append(1.0)
            continue

        if "_L" in name:
            base, Lk = name.rsplit("_L", 1)
            k = int(Lk)
            lag_date = t - pd.offsets.MonthBegin(k)
            lag_date = pd.to_datetime(lag_date.date())
            if lag_date not in df_all.index:
                raise ValueError(f"No existe {lag_date.date()} para rezago {k}.")
            x_vec.append(float(df_all.loc[lag_date, base]))
            continue

        if name in EXOG:
            x_vec.append(float(df_all.loc[t, name]))
            continue

        raise ValueError(f"No reconozco columna en regresores: {name}")

    x_vec = np.array(x_vec)

    y_pred = np.zeros(n)
    y_obs = df_all.loc[t, ENDOG].values.astype(float)

    for i, ycol in enumerate(ENDOG):
        params = fit["results"][ycol].params
        y_pred[i] = float(np.dot(x_vec, params))

    e_t = y_obs - y_pred
    return y_pred, y_obs, e_t


def covid_innovation_vector(df_all: pd.DataFrame, fit, p: int, months: list):
    rows = []
    e_list = []
    for m in months:
        y_pred, y_obs, e_t = build_one_step_forecast(df_all, fit, p, m)
        e_list.append(e_t)
        rows.append({
            "date": m,
            f"pred_{ENDOG[0]}": y_pred[0], f"obs_{ENDOG[0]}": y_obs[0], f"e_{ENDOG[0]}": e_t[0],
            f"pred_{ENDOG[1]}": y_pred[1], f"obs_{ENDOG[1]}": y_obs[1], f"e_{ENDOG[1]}": e_t[1],
        })
    e_covid = np.mean(np.vstack(e_list), axis=0)
    table = pd.DataFrame(rows)
    return e_covid, table


def covid_innovation_vectors(df_all, fit, p, months):
    e_map = {}
    rows = []
    for m in months:
        y_pred, y_obs, e_t = build_one_step_forecast(df_all, fit, p, m)
        e_map[m] = e_t
        rows.append({
            "date": m,
            "pred_vol": y_pred[0], "obs_vol": y_obs[0], "e_vol": e_t[0],
            "pred_mora": y_pred[1], "obs_mora": y_obs[1], "e_mora": e_t[1],
        })
    return e_map, pd.DataFrame(rows)
