from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal


_REGISTRY_COLUMNS = [
    "base_name",
    "current_name",
    "source_name",
    "stage",
    "transform",
    "is_seasonal",
    "is_stationary",
    "status",
]


class AppState(QObject):
    """Single source of truth shared across all tabs."""

    data_loaded = pyqtSignal()
    active_data_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        # Backward-compatible fields used by the current GUI.
        self.df: pd.DataFrame | None = None
        self.file_path: str = ""
        self.date_col: str = ""
        self.analysis_cols: list[str] = []

        # Pipeline-aware fields for the econometric workflow.
        self.raw_df: pd.DataFrame | None = None
        self.current_df: pd.DataFrame | None = None
        self.active_cols: list[str] = []
        self.variable_registry = pd.DataFrame(columns=_REGISTRY_COLUMNS)

    @property
    def is_loaded(self) -> bool:
        return self.current_df is not None

    def load(
        self,
        df: pd.DataFrame,
        file_path: str,
        date_col: str,
        analysis_cols: list[str],
    ) -> None:
        self.df = df
        self.raw_df = df.copy()
        self.current_df = df.copy()
        self.file_path = file_path
        self.date_col = date_col
        self.analysis_cols = list(analysis_cols)
        self.active_cols = list(analysis_cols)
        self.variable_registry = self._initial_registry(analysis_cols)
        self.data_loaded.emit()
        self.active_data_changed.emit()

    def get_working_df(self) -> pd.DataFrame | None:
        """Copy with the date column renamed to 'fecha' for analysis modules."""
        if self.current_df is None:
            return None
        df = self.current_df.copy()
        if self.date_col and self.date_col != "fecha":
            df = df.rename(columns={self.date_col: "fecha"})
        return df

    def set_current_data(
        self,
        df: pd.DataFrame,
        active_cols: list[str],
        registry_rows: list[dict[str, object]] | None = None,
    ) -> None:
        """Replace the active in-memory dataset used by later tabs."""
        self.current_df = df.copy()
        self.df = self.current_df
        self.active_cols = self._unique_cols(active_cols)
        self.analysis_cols = list(self.active_cols)

        if registry_rows:
            self._append_registry_rows(registry_rows)

        self.active_data_changed.emit()

    def set_deseasonalized_data(
        self,
        df_sa: pd.DataFrame,
        summary: pd.DataFrame,
    ) -> None:
        """Add seasonally adjusted columns and make them the active versions."""
        current = self.get_working_df()
        if current is None or df_sa.empty:
            return

        adjusted_cols = [col for col in df_sa.columns if col != "fecha"]
        for col in adjusted_cols:
            current[col] = pd.NA
            n = min(len(current), len(df_sa[col]))
            current.loc[current.index[:n], col] = df_sa[col].iloc[:n].to_numpy()

        replacements = self._summary_replacements(summary)
        active_cols = [
            replacements.get(col, col)
            for col in self.active_cols
            if col in current.columns or col in replacements
        ]
        for adjusted in replacements.values():
            if adjusted not in active_cols:
                active_cols.append(adjusted)

        registry_rows = [
            {
                "base_name": self._base_name(original),
                "current_name": adjusted,
                "source_name": original,
                "stage": "seasonal_adjusted",
                "transform": "seasonal_dummy_adjustment",
                "is_seasonal": "adjusted",
                "is_stationary": "pending",
                "status": "pending_unit_root_test",
            }
            for original, adjusted in replacements.items()
            if adjusted in current.columns
        ]

        self.set_current_data(current, active_cols, registry_rows)

    def register_stationarity_results(self, results: pd.DataFrame) -> None:
        """Store ADF/KPSS status in the variable registry when that tab exists."""
        if results.empty or "variable" not in results.columns:
            return

        registry = self.variable_registry.copy()
        for _, row in results.iterrows():
            variable = str(row["variable"])
            mask = registry["current_name"] == variable
            if not mask.any():
                continue
            registry.loc[mask, "is_stationary"] = row.get("estacionaria", "pending")
            registry.loc[mask, "status"] = (
                "active_final"
                if row.get("estacionaria") == "Sí"
                else "requires_transformation"
            )
        self.variable_registry = registry
        self.active_data_changed.emit()

    def add_transformed_column(
        self,
        source_col: str,
        new_col: str,
        values: pd.Series,
        transform: str,
    ) -> None:
        """Add a derived column and mark it as pending validation."""
        current = self.get_working_df()
        if current is None:
            return

        current[new_col] = values.reset_index(drop=True)
        active_cols = [
            new_col if col == source_col else col
            for col in self.active_cols
        ]
        if new_col not in active_cols:
            active_cols.append(new_col)

        self.set_current_data(
            current,
            active_cols,
            [
                {
                    "base_name": self._base_name(source_col),
                    "current_name": new_col,
                    "source_name": source_col,
                    "stage": "transformed",
                    "transform": transform,
                    "is_seasonal": "inherits_source",
                    "is_stationary": "pending",
                    "status": "pending_unit_root_test",
                }
            ],
        )

    def _initial_registry(self, cols: list[str]) -> pd.DataFrame:
        rows = [
            {
                "base_name": col,
                "current_name": col,
                "source_name": "",
                "stage": "original",
                "transform": "none",
                "is_seasonal": "pending",
                "is_stationary": "pending",
                "status": "loaded",
            }
            for col in cols
        ]
        return pd.DataFrame(rows, columns=_REGISTRY_COLUMNS)

    def _append_registry_rows(self, rows: list[dict[str, object]]) -> None:
        new_rows = pd.DataFrame(rows, columns=_REGISTRY_COLUMNS)
        self.variable_registry = pd.concat(
            [self.variable_registry, new_rows],
            ignore_index=True,
        )

    def _summary_replacements(self, summary: pd.DataFrame) -> dict[str, str]:
        required = {"variable_original", "variable_ajustada"}
        if summary.empty or not required.issubset(summary.columns):
            return {}

        replacements: dict[str, str] = {}
        for _, row in summary.iterrows():
            original = str(row["variable_original"])
            adjusted = str(row["variable_ajustada"])
            if adjusted and adjusted != "—":
                replacements[original] = adjusted
        return replacements

    def _base_name(self, variable: str) -> str:
        matches = self.variable_registry[
            self.variable_registry["current_name"] == variable
        ]
        if not matches.empty:
            return str(matches.iloc[-1]["base_name"])
        return variable

    def _unique_cols(self, cols: list[str]) -> list[str]:
        unique: list[str] = []
        for col in cols:
            if col and col not in unique:
                unique.append(col)
        return unique
