from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal


class ColumnSelector(QWidget):
    """Lista de columnas con checkboxes y botones de selección masiva."""

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
        self._list.itemChanged.connect(self._on_changed)
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
        """Popula la lista. Si checked=None todos quedan marcados."""
        self._list.blockSignals(True)
        self._list.clear()
        for col in cols:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            state = (
                Qt.CheckState.Checked
                if (checked is None or col in checked)
                else Qt.CheckState.Unchecked
            )
            item.setCheckState(state)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def get_selected(self) -> list[str]:
        return [
            self._list.item(i).text()
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        ]

    def set_label(self, text: str) -> None:
        self._label.setText(text)

    # ------------------------------------------------------------------
    def _on_changed(self) -> None:
        self.selection_changed.emit(self.get_selected())

    def _select_all(self) -> None:
        self._set_all(Qt.CheckState.Checked)

    def _select_none(self) -> None:
        self._set_all(Qt.CheckState.Unchecked)

    def _set_all(self, state: Qt.CheckState) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            self._list.item(i).setCheckState(state)
        self._list.blockSignals(False)
        self.selection_changed.emit(self.get_selected())
