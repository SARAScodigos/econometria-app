from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel,
)
from PyQt6.QtCore import pyqtSignal


class ColumnSelector(QWidget):
    """Lista de columnas con seleccion multiple tipo explorador de archivos."""

    selection_changed = pyqtSignal(list)

    def __init__(
        self,
        title: str = "Variables",
        min_height: int = 150,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._build(title, min_height)

    def _build(self, title: str, min_height: int) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel(title)
        self._label.setObjectName("sectionLabel")
        layout.addWidget(self._label)

        self._list = QListWidget()
        self._list.setMinimumHeight(min_height)
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.itemSelectionChanged.connect(self._on_changed)
        layout.addWidget(self._list)

        row = QHBoxLayout()
        for text, slot in [("Todos", self._select_all), ("Ninguno", self._select_none)]:
            btn = QPushButton(text)
            btn.setObjectName("smallBtn")
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)

    def set_columns(
        self,
        cols: list[str],
        checked: list[str] | None = None,
    ) -> None:
        """Popula la lista. Si checked=None todos quedan seleccionados."""
        self._list.blockSignals(True)
        self._list.clear()
        for col in cols:
            item = QListWidgetItem(col)
            self._list.addItem(item)
            item.setSelected(checked is None or col in checked)
        self._list.blockSignals(False)
        self.selection_changed.emit(self.get_selected())

    def get_selected(self) -> list[str]:
        return [item.text() for item in self._list.selectedItems()]

    def set_label(self, text: str) -> None:
        self._label.setText(text)

    # ------------------------------------------------------------------
    def _on_changed(self) -> None:
        self.selection_changed.emit(self.get_selected())

    def _select_all(self) -> None:
        self._set_all(True)

    def _select_none(self) -> None:
        self._set_all(False)

    def _set_all(self, selected: bool) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setSelected(selected)
        self._list.blockSignals(False)
        self.selection_changed.emit(self.get_selected())
