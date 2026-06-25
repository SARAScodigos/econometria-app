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
    background-color: #F1F5F9;
}
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    color: #1E293B;
}

/* ── Tabs ─────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background: #FFFFFF;
    border-top: none;
}
QTabBar::tab {
    background: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    padding: 9px 22px;
    min-width: 130px;
    color: #64748B;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #2563EB;
    border-top: 2px solid #2563EB;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background: #EFF6FF;
    color: #1D4ED8;
}

/* ── GroupBox ─────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 6px;
    background: #FFFFFF;
    font-weight: 600;
    color: #374151;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    left: 12px;
    color: #1E293B;
}

/* ── Buttons ──────────────────────────────────────────── */
QPushButton#primaryBtn {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton#primaryBtn:hover   { background-color: #1D4ED8; }
QPushButton#primaryBtn:disabled { background-color: #93C5FD; color: #DBEAFE; }

QPushButton#successBtn {
    background-color: #16A34A;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton#successBtn:hover   { background-color: #15803D; }
QPushButton#successBtn:disabled { background-color: #86EFAC; color: #DCFCE7; }

QPushButton#secondaryBtn {
    background-color: #FFFFFF;
    color: #374151;
    border: 1px solid #D1D5DB;
    border-radius: 5px;
    padding: 7px 16px;
}
QPushButton#secondaryBtn:hover    { background-color: #F9FAFB; border-color: #9CA3AF; }
QPushButton#secondaryBtn:disabled { color: #9CA3AF; border-color: #E5E7EB; }

QPushButton#smallBtn {
    background-color: #F8FAFC;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 11px;
}
QPushButton#smallBtn:hover { background-color: #EFF6FF; border-color: #BFDBFE; }

/* ── Tables ───────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    gridline-color: #F1F5F9;
    background: #FFFFFF;
    alternate-background-color: #F8FAFC;
}
QTableWidget::item          { padding: 4px 8px; }
QTableWidget::item:selected { background-color: #DBEAFE; color: #1E293B; }
QHeaderView::section {
    background-color: #F8FAFC;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #F1F5F9;
    padding: 6px 10px;
    font-weight: 600;
    color: #475569;
}

/* ── Lists ────────────────────────────────────────────── */
QListWidget {
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    background: #FFFFFF;
    alternate-background-color: #F8FAFC;
}
QListWidget::item       { padding: 4px 6px; }
QListWidget::item:hover { background: #EFF6FF; }

/* ── ComboBox ─────────────────────────────────────────── */
QComboBox {
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 5px 8px;
    background: #FFFFFF;
    min-width: 120px;
}
QComboBox:hover        { border-color: #9CA3AF; }
QComboBox::drop-down   { border: none; width: 22px; }

/* ── ProgressBar ──────────────────────────────────────── */
QProgressBar {
    border: 1px solid #E2E8F0;
    border-radius: 3px;
    background: #F1F5F9;
    text-align: center;
}
QProgressBar::chunk { background-color: #2563EB; border-radius: 2px; }

/* ── Splitter ─────────────────────────────────────────── */
QSplitter::handle         { background: #E2E8F0; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical   { height: 2px; }

/* ── Named labels ─────────────────────────────────────── */
QLabel#tableTitle   { font-size: 14px; font-weight: bold; color: #1E293B; }
QLabel#filePath     { color: #64748B; font-style: italic; }
QLabel#infoLabel    { color: #16A34A; font-weight: bold; }
QLabel#noteLabel    { color: #64748B; font-size: 12px; }
QLabel#sectionLabel { font-weight: 600; color: #374151; font-size: 12px; }
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
        lbl.setStyleSheet("color:#94A3B8; font-size:15px;")
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
        header.setStyleSheet("background:#1E3A5F;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        titles = QWidget()
        tl = QVBoxLayout(titles)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(1)
        app_lbl = QLabel("EconometriApp")
        app_lbl.setStyleSheet("color:#FFFFFF; font-size:17px; font-weight:bold;")
        sub_lbl = QLabel("Análisis de Series de Tiempo · UDEP")
        sub_lbl.setStyleSheet("color:#93C5FD; font-size:11px;")
        tl.addWidget(app_lbl)
        tl.addWidget(sub_lbl)
        hl.addWidget(titles)
        hl.addStretch()

        self._header_info = QLabel("")
        self._header_info.setStyleSheet("color:#BAE6FD; font-size:11px;")
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
