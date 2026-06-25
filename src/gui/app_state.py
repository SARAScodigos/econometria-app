from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal


class AppState(QObject):
    """Single source of truth shared across all tabs."""

    data_loaded = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.df: pd.DataFrame | None = None
        self.file_path: str = ""
        self.date_col: str = ""
        self.analysis_cols: list[str] = []

    @property
    def is_loaded(self) -> bool:
        return self.df is not None

    def load(
        self,
        df: pd.DataFrame,
        file_path: str,
        date_col: str,
        analysis_cols: list[str],
    ) -> None:
        self.df = df
        self.file_path = file_path
        self.date_col = date_col
        self.analysis_cols = list(analysis_cols)
        self.data_loaded.emit()

    def get_working_df(self) -> pd.DataFrame | None:
        """Copy with the date column renamed to 'fecha' for analysis modules."""
        if self.df is None:
            return None
        df = self.df.copy()
        if self.date_col and self.date_col != "fecha":
            df = df.rename(columns={self.date_col: "fecha"})
        return df
