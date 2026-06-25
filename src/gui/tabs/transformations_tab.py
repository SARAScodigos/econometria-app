from __future__ import annotations

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.app_state import AppState
from src.gui.widgets.column_selector import ColumnSelector
from src.gui.widgets.results_table import ResultsTable


_TRANSFORMS = {
    "Sugerida automática": "auto",
    "Primera diferencia": "difference",
    "Logaritmo": "log",
    "Diferencia logarítmica": "log_difference",
}

_COLOR_MAP = {
    "Creada": "#DCEADF",
    "Error": "#F2D6D2",
}


class TransformationsTab(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._summary_df: pd.DataFrame | None = None
        self._build()
        state.active_data_changed.connect(self._on_active_data_changed)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        self._status_lbl = QLabel(
            "Activa variables en Datos para crear transformaciones."
        )
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(
            "color:#65717D; padding:6px 12px; background:#F3F6F8;"
            "border:1px solid #D7DEE6; border-radius:4px; font-size:12px;"
        )
        root.addWidget(self._status_lbl)

        box = QGroupBox("Crear variables transformadas")
        box_l = QVBoxLayout(box)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Transformación:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(list(_TRANSFORMS))
        mode_row.addWidget(self._mode_combo)

        self._run_btn = QPushButton("Crear transformación")
        self._run_btn.setObjectName("primaryBtn")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._run_transform)
        mode_row.addWidget(self._run_btn)
        mode_row.addStretch()
        box_l.addLayout(mode_row)

        self._cols = ColumnSelector("Variables activas a transformar:", min_height=130)
        self._cols.setMaximumHeight(190)
        box_l.addWidget(self._cols)

        note = QLabel(
            "Se transforman las variables seleccionadas de la lista. "
            "Las nuevas columnas se agregan al panel de Datos y quedan activas. "
            "Puedes apagarlas allí antes de correr nuevas pruebas."
        )
        note.setObjectName("noteLabel")
        note.setWordWrap(True)
        box_l.addWidget(note)

        self._results = ResultsTable("Resumen de transformaciones")
        box_l.addWidget(self._results)
        root.addWidget(box)

    def _on_active_data_changed(self) -> None:
        if not self._state.is_loaded:
            self._run_btn.setEnabled(False)
            return

        cols = list(self._state.active_cols)
        self._cols.set_columns(cols)
        self._run_btn.setEnabled(bool(cols))
        available = len(self._state.available_analysis_cols())
        self._status_lbl.setText(
            f"{len(cols)} variables activas  ·  {available} variables disponibles en memoria"
        )
        self._status_lbl.setStyleSheet(
            "color:#1F5F74; padding:6px 12px; background:#EAF3F5;"
            "border:1px solid #A9C7CE; border-radius:4px; font-size:12px; font-weight:bold;"
        )

    def _run_transform(self) -> None:
        variables = self._cols.get_selected()
        if not variables:
            QMessageBox.warning(self, "Sin variables", "Selecciona al menos una variable.")
            return

        df = self._state.get_working_df()
        if df is None:
            return

        transform = _TRANSFORMS[self._mode_combo.currentText()]
        rows: list[dict[str, object]] = []

        for variable in variables:
            try:
                applied_transform = (
                    self._suggest_transform(variable)
                    if transform == "auto"
                    else transform
                )
                series, new_name = self._build_series(df, variable, applied_transform)
                final_name = self._state.add_transformed_column(
                    source_col=variable,
                    new_col=new_name,
                    values=series,
                    transform=applied_transform,
                )
                rows.append(
                    {
                        "variable_original": variable,
                        "variable_creada": final_name or new_name,
                        "transformacion": self._transform_label(applied_transform),
                        "observaciones_validas": int(series.dropna().shape[0]),
                        "estado": "Creada",
                        "detalle": "Pendiente de validar con ADF/KPSS",
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        "variable_original": variable,
                        "variable_creada": "—",
                        "transformacion": self._mode_combo.currentText(),
                        "observaciones_validas": 0,
                        "estado": "Error",
                        "detalle": str(exc),
                    }
                )

        self._summary_df = pd.DataFrame(rows)
        self._results.set_data(
            self._summary_df,
            color_col="estado",
            color_map=_COLOR_MAP,
        )

    def _build_series(
        self,
        df: pd.DataFrame,
        variable: str,
        transform: str,
    ) -> tuple[pd.Series, str]:
        if variable not in df.columns:
            raise KeyError(f"No existe la columna {variable}")

        series = pd.to_numeric(df[variable], errors="coerce")
        if transform == "difference":
            return series.diff(), f"D_{variable}"

        if (series.dropna() <= 0).any():
            raise ValueError("contiene valores <= 0; no se puede aplicar logaritmo")

        logged = np.log(series)
        if transform == "log":
            return logged, f"Ln_{variable}"
        if transform == "log_difference":
            return logged.diff(), f"D_ln_{variable}"

        raise ValueError(f"Transformación no reconocida: {transform}")

    def _suggest_transform(self, variable: str) -> str:
        normalized = variable.lower()
        if normalized.startswith(("vol_", "vol")) or "pbi" in normalized:
            return "log_difference"
        return "difference"

    def _transform_label(self, transform: str) -> str:
        labels = {value: key for key, value in _TRANSFORMS.items()}
        return labels.get(transform, transform)
