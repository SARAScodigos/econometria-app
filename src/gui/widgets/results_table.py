from __future__ import annotations

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class ResultsTable(QWidget):
    """Tabla de resultados reutilizable con botón de exportar."""

    def __init__(self, title: str = "Resultados", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._df: pd.DataFrame | None = None
        self._build(title)

    def _build(self, title: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("tableTitle")
        header.addWidget(self._title_lbl)
        header.addStretch()
        self._export_btn = QPushButton("Exportar Excel")
        self._export_btn.setObjectName("secondaryBtn")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export)
        header.addWidget(self._export_btn)
        layout.addLayout(header)

        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

    def set_title(self, title: str) -> None:
        self._title_lbl.setText(title)

    def set_data(
        self,
        df: pd.DataFrame,
        color_col: str | None = None,
        color_map: dict[str, str] | None = None,
    ) -> None:
        self._df = df.copy()
        self._table.clearContents()

        if df.empty:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        self._table.setRowCount(len(df))
        self._table.setColumnCount(len(df.columns))
        self._table.setHorizontalHeaderLabels(list(df.columns))

        for row_idx, (_, row) in enumerate(df.iterrows()):
            row_color: str | None = None
            if color_col and color_map and color_col in df.columns:
                row_color = color_map.get(str(row[color_col]))

            for col_idx, col_name in enumerate(df.columns):
                val = row[col_name]
                text = str(val) if pd.notna(val) else "—"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if row_color:
                    item.setBackground(QColor(row_color))
                self._table.setItem(row_idx, col_idx, item)

        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._export_btn.setEnabled(True)

    def current_df(self) -> pd.DataFrame | None:
        return self._df

    def _export(self) -> None:
        if self._df is None or self._df.empty:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar resultados", "",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                self._df.to_csv(path, index=False)
            else:
                if not path.lower().endswith(".xlsx"):
                    path += ".xlsx"
                self._df.to_excel(path, index=False)
            QMessageBox.information(self, "Exportado", f"Guardado en:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))
