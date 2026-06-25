from __future__ import annotations

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QProgressBar, QMessageBox, QSplitter, QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.gui.app_state import AppState
from src.gui.widgets.results_table import ResultsTable
from src.gui.widgets.column_selector import ColumnSelector

_COLOR_MAP = {
    "Sí":    "#F1E5C6",   # alerta suave: estacional
    "No":    "#DCEADF",   # validación suave: no estacional
    "Error": "#F2D6D2",   # error suave
}


# ---------------------------------------------------------------------------
# Worker: prueba F de estacionalidad
# ---------------------------------------------------------------------------

class _TestWorker(QThread):
    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, df: pd.DataFrame, variables: list[str]) -> None:
        super().__init__()
        self._df = df
        self._variables = variables

    def run(self) -> None:
        try:
            from src.seasonality.seasonality import probar_estacionalidad

            results: list[dict] = []
            for var in self._variables:
                try:
                    results.append(probar_estacionalidad(self._df, var))
                except Exception as exc:
                    results.append({
                        "variable": var,
                        "n_observaciones": 0,
                        "estadistico_F": float("nan"),
                        "p_valor": float("nan"),
                        "es_estacional": "Error",
                        "decision": str(exc),
                    })
            self.completed.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Worker: desestacionalización
# ---------------------------------------------------------------------------

class _DeseasonWorker(QThread):
    completed = pyqtSignal(object, object)   # df_sa, df_summary (DataFrames)
    failed = pyqtSignal(str)

    def __init__(self, df: pd.DataFrame, variables: list[str]) -> None:
        super().__init__()
        self._df = df
        self._variables = variables

    def run(self) -> None:
        try:
            from src.seasonality.deseasonalize import estimar_componente_estacional

            series_adj: dict[str, pd.Series] = {}
            summary_rows: list[dict] = []

            for var in self._variables:
                try:
                    comp, sa, model = estimar_componente_estacional(self._df, var)
                    series_adj[sa.name] = sa.reset_index(drop=True)
                    summary_rows.append({
                        "variable_original": var,
                        "variable_ajustada": sa.name,
                        "componente_max": round(float(comp.max()), 6),
                        "componente_min": round(float(comp.min()), 6),
                        "rango_estacional": round(float(comp.max() - comp.min()), 6),
                        "R²_modelo": round(float(model.rsquared), 4),
                    })
                except Exception as exc:
                    summary_rows.append({
                        "variable_original": var,
                        "variable_ajustada": "—",
                        "componente_max": float("nan"),
                        "componente_min": float("nan"),
                        "rango_estacional": float("nan"),
                        "R²_modelo": float("nan"),
                        "error": str(exc),
                    })

            if series_adj:
                df_sa = pd.DataFrame(series_adj)
                fecha_vals = self._df["fecha"].reset_index(drop=True)
                df_sa.insert(0, "fecha", fecha_vals.values[: len(df_sa)])
            else:
                df_sa = pd.DataFrame()

            self.completed.emit(df_sa, pd.DataFrame(summary_rows))
        except Exception as exc:
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Tab
# ---------------------------------------------------------------------------

class SeasonalityTab(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._test_worker: _TestWorker | None = None
        self._deseason_worker: _DeseasonWorker | None = None
        self._df_sa: pd.DataFrame | None = None
        self._build()
        state.data_loaded.connect(self._on_data_loaded)
        state.active_data_changed.connect(self._on_data_loaded)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        main_split = QSplitter(Qt.Orientation.Vertical)

        # ── Sección 1: Prueba F ──────────────────────────────────────────
        test_box = QGroupBox("1. Prueba F de Estacionalidad  (dummies mensuales)")
        test_root = QVBoxLayout(test_box)

        test_split = QSplitter(Qt.Orientation.Horizontal)

        left1 = QWidget()
        ll1 = QVBoxLayout(left1)
        ll1.setContentsMargins(0, 0, 4, 0)

        self._test_cols = ColumnSelector("Variables a evaluar:", min_height=180)
        ll1.addWidget(self._test_cols)

        self._run_test_btn = QPushButton("Ejecutar Prueba F")
        self._run_test_btn.setObjectName("primaryBtn")
        self._run_test_btn.setEnabled(False)
        self._run_test_btn.clicked.connect(self._run_test)
        ll1.addWidget(self._run_test_btn)

        self._test_bar = QProgressBar()
        self._test_bar.setRange(0, 0)
        self._test_bar.setVisible(False)
        self._test_bar.setMaximumHeight(6)
        ll1.addWidget(self._test_bar)
        ll1.addStretch()

        test_split.addWidget(left1)

        self._test_results = ResultsTable("Resultados  ·  H₀: no existe estacionalidad mensual")
        test_split.addWidget(self._test_results)
        test_split.setSizes([260, 700])

        test_root.addWidget(test_split)
        main_split.addWidget(test_box)

        # ── Sección 2: Desestacionalización ─────────────────────────────
        desa_box = QGroupBox("2. Desestacionalización")
        desa_root = QVBoxLayout(desa_box)

        note = QLabel(
            "Las variables identificadas como estacionales quedan pre-seleccionadas. "
            "Puedes ajustar la selección antes de ejecutar."
        )
        note.setWordWrap(True)
        note.setObjectName("noteLabel")
        desa_root.addWidget(note)

        desa_split = QSplitter(Qt.Orientation.Horizontal)

        left2 = QWidget()
        ll2 = QVBoxLayout(left2)
        ll2.setContentsMargins(0, 0, 4, 0)

        self._desa_cols = ColumnSelector("Variables a desestacionalizar:", min_height=120)
        ll2.addWidget(self._desa_cols)

        self._run_desa_btn = QPushButton("Desestacionalizar")
        self._run_desa_btn.setObjectName("successBtn")
        self._run_desa_btn.setEnabled(False)
        self._run_desa_btn.clicked.connect(self._run_deseason)
        ll2.addWidget(self._run_desa_btn)

        self._desa_bar = QProgressBar()
        self._desa_bar.setRange(0, 0)
        self._desa_bar.setVisible(False)
        self._desa_bar.setMaximumHeight(6)
        ll2.addWidget(self._desa_bar)

        self._export_sa_btn = QPushButton("Exportar datos desestacionalizados")
        self._export_sa_btn.setObjectName("secondaryBtn")
        self._export_sa_btn.setEnabled(False)
        self._export_sa_btn.clicked.connect(self._export_sa)
        ll2.addWidget(self._export_sa_btn)
        ll2.addStretch()

        desa_split.addWidget(left2)

        self._desa_results = ResultsTable("Resumen de ajuste estacional")
        desa_split.addWidget(self._desa_results)
        desa_split.setSizes([260, 700])

        desa_root.addWidget(desa_split)
        main_split.addWidget(desa_box)
        main_split.setSizes([1, 1])
        root.addWidget(main_split)

    # ------------------------------------------------------------------
    # State change
    # ------------------------------------------------------------------

    def _on_data_loaded(self) -> None:
        state = self._state
        cols = state.active_cols
        self._test_cols.set_columns(cols)
        self._desa_cols.set_columns(cols, checked=[])   # vacío hasta correr el test
        self._run_test_btn.setEnabled(bool(cols))

    # ------------------------------------------------------------------
    # Prueba F
    # ------------------------------------------------------------------

    def _run_test(self) -> None:
        variables = self._test_cols.get_selected()
        if not variables:
            QMessageBox.warning(self, "Sin variables", "Selecciona al menos una variable.")
            return

        df = self._state.get_working_df()
        if df is None:
            return

        self._run_test_btn.setEnabled(False)
        self._test_bar.setVisible(True)

        self._test_worker = _TestWorker(df, variables)
        self._test_worker.completed.connect(self._on_test_done)
        self._test_worker.failed.connect(self._on_test_error)
        self._test_worker.start()

    def _on_test_done(self, results: list[dict]) -> None:
        self._run_test_btn.setEnabled(True)
        self._test_bar.setVisible(False)

        df = pd.DataFrame(results)
        # Formatear decimales para visualización
        for col in ("estadistico_F", "p_valor"):
            if col in df.columns:
                df[col] = df[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "—")

        self._test_results.set_data(df, color_col="es_estacional", color_map=_COLOR_MAP)
        self._state.register_seasonality_results(df)

        # Pre-seleccionar variables estacionales en la sección 2
        seasonal = [r["variable"] for r in results if r.get("es_estacional") == "Sí"]
        all_vars = [r["variable"] for r in results]
        self._desa_cols.set_columns(all_vars, checked=seasonal)
        self._run_desa_btn.setEnabled(True)

    def _on_test_error(self, msg: str) -> None:
        self._run_test_btn.setEnabled(True)
        self._test_bar.setVisible(False)
        QMessageBox.critical(self, "Error en la prueba", msg)

    # ------------------------------------------------------------------
    # Desestacionalización
    # ------------------------------------------------------------------

    def _run_deseason(self) -> None:
        variables = self._desa_cols.get_selected()
        if not variables:
            QMessageBox.warning(self, "Sin variables", "Selecciona al menos una variable.")
            return

        df = self._state.get_working_df()
        if df is None:
            return

        self._run_desa_btn.setEnabled(False)
        self._desa_bar.setVisible(True)

        self._deseason_worker = _DeseasonWorker(df, variables)
        self._deseason_worker.completed.connect(self._on_deseason_done)
        self._deseason_worker.failed.connect(self._on_deseason_error)
        self._deseason_worker.start()

    def _on_deseason_done(
        self, df_sa: pd.DataFrame, df_summary: pd.DataFrame
    ) -> None:
        self._run_desa_btn.setEnabled(True)
        self._desa_bar.setVisible(False)
        self._df_sa = df_sa
        self._desa_results.set_data(df_summary)
        self._state.set_deseasonalized_data(df_sa, df_summary)
        self._export_sa_btn.setEnabled(not df_sa.empty)

    def _on_deseason_error(self, msg: str) -> None:
        self._run_desa_btn.setEnabled(True)
        self._desa_bar.setVisible(False)
        QMessageBox.critical(self, "Error en desestacionalización", msg)

    def _export_sa(self) -> None:
        if self._df_sa is None or self._df_sa.empty:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar datos desestacionalizados", "",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                self._df_sa.to_csv(path, index=False)
            else:
                if not path.lower().endswith(".xlsx"):
                    path += ".xlsx"
                self._df_sa.to_excel(path, index=False)
            QMessageBox.information(self, "Exportado", f"Guardado en:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
