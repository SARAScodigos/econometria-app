from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
)
from PyQt6.QtCore import Qt

from src.gui.app_state import AppState
from src.gui.tabs.data_tab import DataTab
from src.gui.tabs.seasonality_tab import SeasonalityTab

# ---------------------------------------------------------------------------
# Stylesheet global
# ---------------------------------------------------------------------------

_STYLE = """
QMainWindow, QDialog {
    background-color: #EEF2F5;
}
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #1F2933;
}

/* ── Tabs ─────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #D7DEE6;
    background: #FAFBFC;
    border-top: none;
}
QTabBar::tab {
    background: #E9EEF3;
    border: 1px solid #D7DEE6;
    border-bottom: none;
    padding: 9px 22px;
    min-width: 130px;
    color: #5B6673;
}
QTabBar::tab:selected {
    background: #FAFBFC;
    color: #1F5F74;
    border-top: 2px solid #2A7F8F;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background: #DDEAF0;
    color: #20566B;
}

/* ── GroupBox ─────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #D7DEE6;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 6px;
    background: #FAFBFC;
    font-weight: 600;
    color: #2D3742;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    left: 12px;
    color: #1F2933;
}

/* ── Buttons ──────────────────────────────────────────── */
QPushButton#primaryBtn {
    background-color: #2A7F8F;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton#primaryBtn:hover   { background-color: #236C7A; }
QPushButton#primaryBtn:disabled { background-color: #A9C7CE; color: #E8F1F3; }

QPushButton#successBtn {
    background-color: #2F7D5C;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton#successBtn:hover   { background-color: #286B4F; }
QPushButton#successBtn:disabled { background-color: #A9C8B9; color: #E7F0EC; }

QPushButton#secondaryBtn {
    background-color: #FAFBFC;
    color: #2D3742;
    border: 1px solid #C8D0D9;
    border-radius: 5px;
    padding: 7px 16px;
}
QPushButton#secondaryBtn:hover    { background-color: #F2F6F8; border-color: #8EA0AD; }
QPushButton#secondaryBtn:disabled { color: #98A3AD; border-color: #E1E6EB; }

QPushButton#smallBtn {
    background-color: #F3F6F8;
    color: #4C5965;
    border: 1px solid #D7DEE6;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 11px;
}
QPushButton#smallBtn:hover { background-color: #E6F0F3; border-color: #9BB8C1; }

/* ── Tables ───────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #D7DEE6;
    border-radius: 4px;
    gridline-color: #E9EEF3;
    background: #FAFBFC;
    alternate-background-color: #F3F6F8;
}
QTableWidget::item          { padding: 4px 8px; }
QTableWidget::item:selected { background-color: #D6E8ED; color: #1F2933; }
QHeaderView::section {
    background-color: #E9EEF3;
    border: none;
    border-bottom: 1px solid #D7DEE6;
    border-right: 1px solid #DDE4EA;
    padding: 6px 10px;
    font-weight: 600;
    color: #3E4C59;
}

/* ── Lists ────────────────────────────────────────────── */
QListWidget {
    border: 1px solid #D7DEE6;
    border-radius: 4px;
    background: #FAFBFC;
    alternate-background-color: #F3F6F8;
}
QListWidget::item       { padding: 4px 6px; }
QListWidget::item:hover { background: #E6F0F3; }

/* ── ComboBox ─────────────────────────────────────────── */
QComboBox {
    border: 1px solid #C8D0D9;
    border-radius: 4px;
    padding: 5px 8px;
    background: #FAFBFC;
    min-width: 120px;
}
QComboBox:hover        { border-color: #8EA0AD; }
QComboBox::drop-down   { border: none; width: 22px; }

/* ── ProgressBar ──────────────────────────────────────── */
QProgressBar {
    border: 1px solid #D7DEE6;
    border-radius: 3px;
    background: #E9EEF3;
    text-align: center;
}
QProgressBar::chunk { background-color: #2A7F8F; border-radius: 2px; }

/* ── Splitter ─────────────────────────────────────────── */
QSplitter::handle         { background: #D7DEE6; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical   { height: 2px; }

/* ── Named labels ─────────────────────────────────────── */
QLabel#tableTitle   { font-size: 14px; font-weight: bold; color: #1F2933; }
QLabel#filePath     { color: #65717D; font-style: italic; }
QLabel#infoLabel    { color: #2F7D5C; font-weight: bold; }
QLabel#noteLabel    { color: #65717D; font-size: 12px; }
QLabel#sectionLabel { font-weight: 600; color: #2D3742; font-size: 12px; }
"""


# ---------------------------------------------------------------------------
# Placeholder tab for future stages
# ---------------------------------------------------------------------------

class _PlaceholderTab(QWidget):
    def __init__(self, message: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#8EA0AD; font-size:15px;")
        layout.addWidget(lbl)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._state = AppState()
        self.setWindowTitle("EconometriApp — UDEP")
        self.resize(1200, 780)
        self.setStyleSheet(_STYLE)
        self._build()

    def _build(self) -> None:
        # Header
        header = QWidget()
        header.setFixedHeight(54)
        header.setStyleSheet("background:#213743;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        titles = QWidget()
        tl = QVBoxLayout(titles)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(1)
        app_lbl = QLabel("EconometriApp")
        app_lbl.setStyleSheet("color:#FFFFFF; font-size:17px; font-weight:bold;")
        sub_lbl = QLabel("Análisis de Series de Tiempo · UDEP")
        sub_lbl.setStyleSheet("color:#9CC7D1; font-size:11px;")
        tl.addWidget(app_lbl)
        tl.addWidget(sub_lbl)
        hl.addWidget(titles)
        hl.addStretch()

        self._header_info = QLabel("")
        self._header_info.setStyleSheet("color:#B9DDE4; font-size:11px;")
        self._header_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hl.addWidget(self._header_info)

        # Tabs
        self._tabs = QTabWidget()
        self._data_tab = DataTab(self._state)
        self._season_tab = SeasonalityTab(self._state)

        self._tabs.addTab(self._data_tab,   "  Datos  ")
        self._tabs.addTab(self._season_tab, "  Estacionalidad  ")
        self._tabs.addTab(
            _PlaceholderTab("Raíz Unitaria — próximamente"),
            "  Raíz Unitaria  ",
        )
        self._tabs.addTab(
            _PlaceholderTab("Transformaciones (log / diferencias) — próximamente"),
            "  Transformaciones  ",
        )

        # Root
        root = QWidget()
        root_l = QVBoxLayout(root)
        root_l.setContentsMargins(0, 0, 0, 0)
        root_l.setSpacing(0)
        root_l.addWidget(header)
        root_l.addWidget(self._tabs)
        self.setCentralWidget(root)

        # Status bar
        self.statusBar().showMessage("Listo  ·  Carga un archivo en la pestaña Datos para comenzar.")
        self._state.data_loaded.connect(self._on_data_loaded)

    def _on_data_loaded(self) -> None:
        n = len(self._state.analysis_cols)
        rows = len(self._state.df) if self._state.df is not None else 0
        self.statusBar().showMessage(
            f"Datos cargados  ·  {n} variables  ·  {rows:,} observaciones"
        )
        self._header_info.setText(f"{n} variables  ·  {rows:,} obs.")
        # Saltar automáticamente a la pestaña de Estacionalidad
        self._tabs.setCurrentIndex(1)
