from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QGroupBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QCheckBox, QSplitter,
)
from PyQt6.QtCore import Qt

from src.gui.app_state import AppState

_DATE_HINTS = {"fecha", "date", "periodo", "period", "time", "mes", "year", "año"}


class DataTab(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._df: pd.DataFrame | None = None
        self._file_path: str = ""
        self._checkboxes: list[QCheckBox] = []
        self._syncing_control = False
        self._build()
        state.active_data_changed.connect(self._populate_active_control)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # 1. Cargar archivo
        file_group = QGroupBox("Cargar Archivo")
        fl = QVBoxLayout(file_group)

        file_row = QHBoxLayout()
        self._file_label = QLabel("Ningún archivo seleccionado")
        self._file_label.setObjectName("filePath")
        file_row.addWidget(self._file_label, 1)
        browse_btn = QPushButton("Examinar…")
        browse_btn.setObjectName("primaryBtn")
        browse_btn.clicked.connect(self._browse)
        file_row.addWidget(browse_btn)
        fl.addLayout(file_row)

        sheet_row = QHBoxLayout()
        sheet_row.addWidget(QLabel("Hoja Excel:"))
        self._sheet_combo = QComboBox()
        self._sheet_combo.setEnabled(False)
        self._sheet_combo.currentTextChanged.connect(self._on_sheet_change)
        sheet_row.addWidget(self._sheet_combo)
        sheet_row.addStretch()
        fl.addLayout(sheet_row)
        root.addWidget(file_group, 0)

        content_split = QSplitter(Qt.Orientation.Vertical)

        # 2. Configurar columnas
        col_group = QGroupBox("Configurar Columnas")
        col_layout = QHBoxLayout(col_group)

        left = QVBoxLayout()
        left.addWidget(QLabel("Columna de fecha:"))
        self._date_combo = QComboBox()
        self._date_combo.setEnabled(False)
        self._date_combo.setMinimumWidth(180)
        left.addWidget(self._date_combo)
        left.addStretch()
        col_layout.addLayout(left)

        right = QVBoxLayout()
        right.addWidget(QLabel("Control de variables (marca las que deseas usar en las pruebas):"))
        self._col_table = QTableWidget()
        self._col_table.setColumnCount(6)
        self._col_table.setHorizontalHeaderLabels(
            ["Variable", "Etapa / tipo", "Estado", "Estacionalidad", "Estacionariedad", "Activa"]
        )
        self._col_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._col_table.verticalHeader().setVisible(False)
        self._col_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._col_table.setMinimumHeight(260)
        right.addWidget(self._col_table)
        col_layout.addLayout(right, 1)
        content_split.addWidget(col_group)

        # 3. Vista previa
        preview_group = QGroupBox("Vista previa (primeras 50 filas)")
        prev_layout = QVBoxLayout(preview_group)
        self._preview = QTableWidget()
        self._preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._preview.verticalHeader().setVisible(False)
        self._preview.setMinimumHeight(260)
        prev_layout.addWidget(self._preview)
        content_split.addWidget(preview_group)
        content_split.setSizes([360, 420])
        root.addWidget(content_split, 1)

        # 4. Confirmar
        confirm_row = QHBoxLayout()
        self._info_label = QLabel("")
        self._info_label.setObjectName("infoLabel")
        confirm_row.addWidget(self._info_label)
        confirm_row.addStretch()
        self._confirm_btn = QPushButton("Confirmar y cargar datos →")
        self._confirm_btn.setObjectName("primaryBtn")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._confirm)
        confirm_row.addWidget(self._confirm_btn)
        root.addLayout(confirm_row)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de datos", "",
            "Archivos de datos (*.xlsx *.xls *.csv);;Excel (*.xlsx *.xls);;CSV (*.csv)",
        )
        if not path:
            return
        self._file_path = path
        self._file_label.setText(Path(path).name)

        if path.lower().endswith(".csv"):
            self._sheet_combo.clear()
            self._sheet_combo.setEnabled(False)
            self._load_data()
        else:
            try:
                xl = pd.ExcelFile(path)
                self._sheet_combo.blockSignals(True)
                self._sheet_combo.clear()
                self._sheet_combo.addItems(xl.sheet_names)
                self._sheet_combo.blockSignals(False)
                self._sheet_combo.setEnabled(True)
                self._load_data()
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo:\n{exc}")

    def _on_sheet_change(self, _: str) -> None:
        if self._file_path:
            self._load_data()

    def _load_data(self) -> None:
        try:
            if self._file_path.lower().endswith(".csv"):
                df = pd.read_csv(self._file_path)
            else:
                sheet = self._sheet_combo.currentText() or 0
                df = pd.read_excel(self._file_path, sheet_name=sheet)
            self._df = df
            self._populate_col_table(df)
            self._populate_preview(df)
            self._confirm_btn.setEnabled(True)
            self._info_label.setText(f"{len(df):,} filas · {len(df.columns)} columnas")
        except Exception as exc:
            QMessageBox.critical(self, "Error al leer el archivo", str(exc))

    # ------------------------------------------------------------------
    # Column / preview population
    # ------------------------------------------------------------------

    def _populate_col_table(self, df: pd.DataFrame) -> None:
        self._syncing_control = True
        self._checkboxes = []
        self._date_combo.blockSignals(True)
        self._date_combo.clear()
        self._date_combo.addItems(df.columns.tolist())
        for col in df.columns:
            if col.lower() in _DATE_HINTS or any(h in col.lower() for h in _DATE_HINTS):
                self._date_combo.setCurrentText(col)
                break
        self._date_combo.setEnabled(True)
        self._date_combo.blockSignals(False)

        self._col_table.clearContents()
        self._col_table.setRowCount(len(df.columns))
        for r, col in enumerate(df.columns):
            dtype = df[col].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                tipo, include = "Numérico", True
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                tipo, include = "Fecha", False
            else:
                tipo, include = "Texto / Fecha", False

            self._col_table.setItem(r, 0, QTableWidgetItem(col))
            self._col_table.setItem(r, 1, QTableWidgetItem(tipo))
            self._col_table.setItem(r, 2, QTableWidgetItem("pre-carga"))
            self._col_table.setItem(r, 3, QTableWidgetItem("pendiente"))
            self._col_table.setItem(r, 4, QTableWidgetItem("pendiente"))

            chk = QCheckBox()
            chk.setChecked(include)
            self._checkboxes.append(chk)

            cell_w = QWidget()
            cell_l = QHBoxLayout(cell_w)
            cell_l.addWidget(chk)
            cell_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_l.setContentsMargins(0, 0, 0, 0)
            self._col_table.setCellWidget(r, 5, cell_w)
        self._syncing_control = False

    def _populate_active_control(self) -> None:
        if not self._state.is_loaded:
            return

        scroll_value = self._col_table.verticalScrollBar().value()
        self._syncing_control = True
        self._checkboxes = []
        control = self._state.variable_control_df()

        self._col_table.clearContents()
        self._col_table.setRowCount(len(control))
        for r, (_, row) in enumerate(control.iterrows()):
            variable = str(row["variable"])
            values = [
                variable,
                str(row["etapa"]),
                str(row["estado"]),
                str(row["estacionalidad"]),
                str(row["estacionariedad"]),
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._col_table.setItem(r, c, item)

            chk = QCheckBox()
            chk.setChecked(variable in self._state.active_cols)
            chk.stateChanged.connect(self._on_active_checkbox_changed)
            self._checkboxes.append(chk)

            cell_w = QWidget()
            cell_l = QHBoxLayout(cell_w)
            cell_l.addWidget(chk)
            cell_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_l.setContentsMargins(0, 0, 0, 0)
            self._col_table.setCellWidget(r, 5, cell_w)

        self._col_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._col_table.horizontalHeader().setStretchLastSection(True)
        self._col_table.verticalScrollBar().setValue(scroll_value)
        self._syncing_control = False

    def _on_active_checkbox_changed(self) -> None:
        if self._syncing_control or not self._state.is_loaded:
            return

        selected = [
            self._col_table.item(r, 0).text()
            for r, chk in enumerate(self._checkboxes)
            if chk.isChecked() and self._col_table.item(r, 0) is not None
        ]
        self._state.set_active_cols(selected)
        self._info_label.setText(f"{len(selected)} variables activas")

    def _populate_preview(self, df: pd.DataFrame) -> None:
        head = df.head(50)
        self._preview.setRowCount(len(head))
        self._preview.setColumnCount(len(head.columns))
        self._preview.setHorizontalHeaderLabels(list(head.columns))
        for r, (_, row) in enumerate(head.iterrows()):
            for c, val in enumerate(row):
                self._preview.setItem(r, c, QTableWidgetItem(str(val)))

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _confirm(self) -> None:
        if self._df is None:
            return

        date_col = self._date_combo.currentText()
        selected = [
            self._col_table.item(r, 0).text()
            for r, chk in enumerate(self._checkboxes)
            if chk.isChecked() and self._col_table.item(r, 0).text() != date_col
        ]

        if not selected:
            QMessageBox.warning(
                self, "Sin variables",
                "Marca al menos una variable de análisis (diferente a la columna de fecha)."
            )
            return

        df = self._df.copy()
        col = df[date_col]
        if pd.api.types.is_numeric_dtype(col):
            df[date_col] = pd.to_datetime(
                col, unit="D", origin="1899-12-30", errors="coerce"
            )
        else:
            df[date_col] = pd.to_datetime(col, errors="coerce", dayfirst=True)

        self._state.load(df, self._file_path, date_col, selected)
        self._info_label.setText(
            f"✓  {len(selected)} variables cargadas · {len(df):,} filas"
        )
