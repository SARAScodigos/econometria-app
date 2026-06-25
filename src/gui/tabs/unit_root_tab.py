from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.gui.app_state import AppState
from src.gui.widgets.column_selector import ColumnSelector
from src.gui.widgets.results_table import ResultsTable


_COLOR_MAP = {
    "Sí": "#DCEADF",
    "No": "#F1E5C6",
    "Mixta": "#E5E1F0",
    "Error": "#F2D6D2",
    "No evaluada": "#E9EEF3",
}


class _UnitRootWorker(QThread):
    completed = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, df: pd.DataFrame, variables: list[str]) -> None:
        super().__init__()
        self._df = df
        self._variables = variables

    def run(self) -> None:
        try:
            from src.unit_roots.unit_roots import run_all

            resumen, detalle = run_all(self._df, self._variables)
            self.completed.emit(resumen, detalle)
        except Exception as exc:
            self.failed.emit(str(exc))


class UnitRootTab(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._worker: _UnitRootWorker | None = None
        self._summary_df: pd.DataFrame | None = None
        self._detail_df: pd.DataFrame | None = None
        self._build()
        state.active_data_changed.connect(self._on_active_data_changed)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        self._status_lbl = QLabel(
            "Activa variables en la pestaña Datos para ejecutar ADF/KPSS."
        )
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(
            "color:#65717D; padding:6px 12px; background:#F3F6F8;"
            "border:1px solid #D7DEE6; border-radius:4px; font-size:12px;"
        )
        root.addWidget(self._status_lbl)

        test_box = QGroupBox("Pruebas de Raíz Unitaria  (ADF + KPSS)")
        test_root = QVBoxLayout(test_box)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 4, 0)

        self._cols = ColumnSelector("Variables activas a evaluar:", min_height=220)
        left_l.addWidget(self._cols)

        self._run_btn = QPushButton("Ejecutar ADF/KPSS")
        self._run_btn.setObjectName("primaryBtn")
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._run_tests)
        left_l.addWidget(self._run_btn)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.setVisible(False)
        self._bar.setMaximumHeight(6)
        left_l.addWidget(self._bar)

        self._export_btn = QPushButton("Exportar resultados")
        self._export_btn.setObjectName("secondaryBtn")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_results)
        left_l.addWidget(self._export_btn)

        self._registry_lbl = QLabel("")
        self._registry_lbl.setObjectName("noteLabel")
        self._registry_lbl.setWordWrap(True)
        left_l.addWidget(self._registry_lbl)
        left_l.addStretch()

        splitter.addWidget(left)

        self._results = ResultsTable("Resumen  ·  decisión combinada ADF/KPSS")
        splitter.addWidget(self._results)
        splitter.setSizes([280, 720])
        test_root.addWidget(splitter)
        root.addWidget(test_box)

        detail_box = QGroupBox("Detalle estadístico")
        detail_l = QVBoxLayout(detail_box)
        self._details = ResultsTable("Detalle por prueba")
        detail_l.addWidget(self._details)
        root.addWidget(detail_box)

    def _on_active_data_changed(self) -> None:
        if not self._state.is_loaded:
            self._run_btn.setEnabled(False)
            return

        cols = list(self._state.active_cols)
        self._cols.set_columns(cols)
        self._run_btn.setEnabled(bool(cols))

        fname = Path(self._state.file_path).name if self._state.file_path else "datos"
        n_rows = len(self._state.current_df) if self._state.current_df is not None else 0
        self._status_lbl.setText(
            f"Dataset activo: {fname}  ·  {n_rows:,} filas  ·  {len(cols)} variables activas"
        )
        self._status_lbl.setStyleSheet(
            "color:#1F5F74; padding:6px 12px; background:#EAF3F5;"
            "border:1px solid #A9C7CE; border-radius:4px; font-size:12px; font-weight:bold;"
        )
        self._update_registry_note()

    def _run_tests(self) -> None:
        variables = self._cols.get_selected()
        if not variables:
            QMessageBox.warning(self, "Sin variables", "Selecciona al menos una variable.")
            return

        df = self._state.get_working_df()
        if df is None:
            return

        self._run_btn.setEnabled(False)
        self._bar.setVisible(True)
        self._worker = _UnitRootWorker(df, variables)
        self._worker.completed.connect(self._on_done)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _on_done(self, summary: pd.DataFrame, detail: pd.DataFrame) -> None:
        self._run_btn.setEnabled(True)
        self._bar.setVisible(False)

        self._summary_df = summary.copy()
        self._detail_df = detail.copy()

        display_summary = self._format_results(summary)
        display_detail = self._format_results(detail)
        self._results.set_data(
            display_summary,
            color_col="estacionaria",
            color_map=_COLOR_MAP,
        )
        self._details.set_data(display_detail)
        self._state.register_stationarity_results(summary)
        self._export_btn.setEnabled(True)
        self._update_registry_note()

    def _on_error(self, msg: str) -> None:
        self._run_btn.setEnabled(True)
        self._bar.setVisible(False)
        QMessageBox.critical(self, "Error en pruebas de raíz unitaria", msg)

    def _export_results(self) -> None:
        if self._summary_df is None or self._summary_df.empty:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar resultados de raíz unitaria",
            "",
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return

        try:
            if path.lower().endswith(".csv"):
                self._summary_df.to_csv(path, index=False)
            else:
                if not path.lower().endswith(".xlsx"):
                    path += ".xlsx"
                with pd.ExcelWriter(path, engine="openpyxl") as writer:
                    self._summary_df.to_excel(writer, sheet_name="Resumen", index=False)
                    if self._detail_df is not None:
                        self._detail_df.to_excel(
                            writer,
                            sheet_name="Detalle_ADF_KPSS",
                            index=False,
                        )
            QMessageBox.information(self, "Exportado", f"Guardado en:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))

    def _format_results(self, df: pd.DataFrame) -> pd.DataFrame:
        display = df.copy()
        for col in display.columns:
            if "p_valor" in col or "estadistico" in col or col.startswith("valor_critico"):
                display[col] = display[col].map(
                    lambda x: f"{x:.4f}" if pd.notna(x) else "—"
                )
        return display

    def _update_registry_note(self) -> None:
        stationary = len(self._state.stationary_cols)
        non_stationary = len(self._state.non_stationary_cols)
        if stationary == 0 and non_stationary == 0:
            self._registry_lbl.setText(
                "Las variables que no pasen la prueba quedarán marcadas para transformación."
            )
            return
        self._registry_lbl.setText(
            f"Estacionarias: {stationary}  ·  Requieren transformación: {non_stationary}"
        )
