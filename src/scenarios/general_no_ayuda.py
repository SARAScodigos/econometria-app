"""Escenario general: COVID observado, sin intervención gubernamental.

Produce tres trayectorias para el modelo agregado:
  1. Real observada.
  2. Pronosticada con exógenas observadas.
  3. Pronosticada apagando D_Intervencion_Gob.

El VARX se estima en diferencias con la muestra completa y p=12.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.settings import (  # noqa: E402
    DATE_COL,
    ENDOG,
    EXOG,
    OUT_DIR,
    SAMPLE_END,
    SAMPLE_START,
    SCENARIO_END,
    SCENARIO_START,
    TRAIN_END,
    VARX_MODEL_FILE,
    configure_runtime,
)
from src.data.loader import load_and_prepare, slice_window  # noqa: E402
from src.diagnostics.diagnostics import estimate_varx_ols  # noqa: E402
from src.scenarios.simulate_varx import (  # noqa: E402
    apply_exog_overrides,
    reconstruct_total_levels,
    simulate_varx_path,
)

P_FINAL = 12
INTERVENTION_COL = "D_Intervencion_Gob"
OUTPUT_FILE = Path(OUT_DIR) / "escenario_general_sin_intervencion.xlsx"


def load_raw_data(path: str) -> pd.DataFrame:
    """Carga el Excel completo con niveles y transformadas."""
    df = pd.read_excel(path)
    if DATE_COL not in df.columns:
        raise ValueError(f"El archivo debe tener columna '{DATE_COL}'")
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df = df.set_index(DATE_COL).sort_index()
    df.index = pd.to_datetime(df.index.date)
    return df


def build_scenarios() -> dict[str, pd.DataFrame]:
    """Estima el VARX general y construye escenarios observado/sin ayuda."""
    configure_runtime()

    raw_df = load_raw_data(VARX_MODEL_FILE)
    model_df = slice_window(load_and_prepare(VARX_MODEL_FILE), "full")
    fit = estimate_varx_ols(model_df, P_FINAL)

    scenario_idx = pd.date_range(SCENARIO_START, SCENARIO_END, freq="MS")
    exog_observed = model_df.loc[scenario_idx, EXOG].copy()
    exog_no_aid = apply_exog_overrides(exog_observed, {INTERVENTION_COL: 0})

    pred_observed = simulate_varx_path(
        df_history=model_df,
        fit=fit,
        endog_cols=ENDOG,
        exog_future=exog_observed,
        start=SCENARIO_START,
        end=SCENARIO_END,
    )
    pred_no_aid = simulate_varx_path(
        df_history=model_df,
        fit=fit,
        endog_cols=ENDOG,
        exog_future=exog_no_aid,
        start=SCENARIO_START,
        end=SCENARIO_END,
    )
    real = model_df.loc[scenario_idx, ENDOG].copy()

    diffs = pd.concat(
        [
            real.add_suffix("_real"),
            pred_observed.add_suffix("_pred_observado"),
            pred_no_aid.add_suffix("_pred_sin_ayuda"),
        ],
        axis=1,
    )
    for col in ENDOG:
        diffs[f"{col}_impacto_ayuda"] = (
            pred_observed[col] - pred_no_aid[col]
        )

    levels_real = raw_df.loc[scenario_idx, ["Vol_total", "Mora_total"]].rename(
        columns={
            "Vol_total": "Vol_total_real",
            "Mora_total": "Mora_total_real",
        }
    )
    levels_observed = reconstruct_total_levels(
        raw_df,
        pred_observed,
        base_date=TRAIN_END,
        suffix="pred_observado",
    )
    levels_no_aid = reconstruct_total_levels(
        raw_df,
        pred_no_aid,
        base_date=TRAIN_END,
        suffix="pred_sin_ayuda",
    )
    levels = pd.concat([levels_real, levels_observed, levels_no_aid], axis=1)
    levels["Vol_total_impacto_ayuda"] = (
        levels["Vol_total_pred_observado"] - levels["Vol_total_pred_sin_ayuda"]
    )
    levels["Mora_total_impacto_ayuda"] = (
        levels["Mora_total_pred_observado"] - levels["Mora_total_pred_sin_ayuda"]
    )

    metadata = pd.DataFrame(
        [
            {"campo": "archivo", "valor": VARX_MODEL_FILE},
            {"campo": "ventana_estimacion", "valor": f"{SAMPLE_START} a {SAMPLE_END}"},
            {"campo": "ventana_escenario", "valor": f"{SCENARIO_START} a {SCENARIO_END}"},
            {"campo": "p", "valor": P_FINAL},
            {"campo": "endogenas", "valor": ", ".join(ENDOG)},
            {"campo": "exogenas", "valor": ", ".join(EXOG)},
            {
                "campo": "escenario_sin_ayuda",
                "valor": f"{INTERVENTION_COL}=0; D_Covid se mantiene observado",
            },
        ]
    )

    return {
        "metadata": metadata,
        "diferencias": diffs,
        "niveles": levels,
        "exog_observadas": exog_observed,
        "exog_sin_ayuda": exog_no_aid,
    }


def main() -> None:
    outputs = build_scenarios()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        outputs["metadata"].to_excel(writer, sheet_name="Metadata", index=False)
        outputs["diferencias"].to_excel(writer, sheet_name="Diferencias", index_label="fecha")
        outputs["niveles"].to_excel(writer, sheet_name="Niveles", index_label="fecha")
        outputs["exog_observadas"].to_excel(
            writer,
            sheet_name="Exog_observadas",
            index_label="fecha",
        )
        outputs["exog_sin_ayuda"].to_excel(
            writer,
            sheet_name="Exog_sin_ayuda",
            index_label="fecha",
        )

    print("=== Escenario general sin intervención ===")
    print(f"Archivo guardado en: {OUTPUT_FILE}")
    print("\nÚltimas filas en niveles:")
    print(outputs["niveles"].tail().to_string())


if __name__ == "__main__":
    main()
