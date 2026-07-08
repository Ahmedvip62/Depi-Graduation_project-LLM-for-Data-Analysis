import logging
import math
from typing import Any, List, Optional

import numpy as np
import pandas as pd

from app.models.schemas import ColumnProfile, DataProfile

logger = logging.getLogger(__name__)

# Common boolean-ish string tokens (lowercased).
_BOOL_TOKENS = {
    "true", "false", "yes", "no", "y", "n", "t", "f", "0", "1",
    "on", "off",
}


def _json_safe(value: Any) -> Any:
    """Convert a single value to a JSON-serializable python primitive."""
    if value is None:
        return None
    # pandas / numpy NA-like
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        try:
            return pd.Timestamp(value).isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        f = float(value)
        return None if math.isnan(f) else f
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.ndarray,)):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (int, float, str, bool)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return value
    # Stringify anything exotic after known scalar conversions.
    try:
        return str(value)
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        f = float(value)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


class DataProfiler:
    @staticmethod
    def _is_datetime_object(series: pd.Series) -> bool:
        """Detect object columns that parse to datetime for >80% of a sample."""
        non_null = series.dropna()
        if non_null.empty:
            return False
        sample = non_null.head(200)
        try:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        except Exception:
            return False
        valid = parsed.notna().sum()
        return len(sample) > 0 and (valid / len(sample)) > 0.80

    @staticmethod
    def _looks_boolean(series: pd.Series) -> bool:
        non_null = series.dropna()
        if non_null.empty:
            return False
        uniques = pd.unique(non_null)
        if len(uniques) != 2:
            return False
        tokens = {str(v).strip().lower() for v in uniques}
        return tokens.issubset(_BOOL_TOKENS)

    @staticmethod
    def _semantic_type(
        series: pd.Series,
        name: str,
        unique_count: int,
        row_count: int,
    ) -> str:
        # boolean: a true bool dtype, or a 2-value STRING column of bool-ish tokens.
        # Numeric 0/1 columns stay continuous (they're often flags used in
        # correlations/charts), so only sniff bool tokens on non-numeric data.
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if not pd.api.types.is_numeric_dtype(series) and DataProfiler._looks_boolean(series):
            return "boolean"

        # datetime (native dtype)
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        is_numeric = pd.api.types.is_numeric_dtype(series)
        is_object = (
            pd.api.types.is_object_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
        )

        # datetime (object that parses)
        if is_object and DataProfiler._is_datetime_object(series):
            return "datetime"

        # id: high uniqueness AND (name has 'id' OR integer-like)
        uniqueness = (unique_count / row_count) if row_count else 0.0
        name_has_id = "id" in str(name).lower()
        integer_like = pd.api.types.is_integer_dtype(series)
        if uniqueness > 0.9 and (name_has_id or integer_like):
            return "id"

        # continuous: numeric not id/boolean
        if is_numeric:
            return "continuous"

        # categorical: object/category with low cardinality
        if is_object:
            threshold = max(20, int(0.05 * row_count)) if row_count else 20
            if unique_count <= threshold:
                return "categorical"
            return "text"

        # final conservative classification
        return "categorical"

    @staticmethod
    def _top_values(series: pd.Series, limit: int = 5) -> List[dict]:
        try:
            counts = series.dropna().value_counts().head(limit)
        except Exception:
            return []
        result = []
        for value, count in counts.items():
            result.append({"value": _json_safe(value), "count": int(count)})
        return result

    @staticmethod
    def profile(df: pd.DataFrame, filename: str) -> DataProfile:
        row_count = int(len(df))
        column_count = int(len(df.columns))

        columns = {}
        datetime_columns: List[str] = []
        numeric_columns: List[str] = []
        categorical_columns: List[str] = []

        total_cells = row_count * column_count if column_count else 0
        total_missing = 0

        for col in df.columns:
            series = df[col]
            dtype = str(series.dtype)
            null_count = int(series.isnull().sum())
            total_missing += null_count

            try:
                unique_count = int(series.nunique(dropna=True))
            except Exception:
                unique_count = 0

            missing_pct = round((null_count / row_count) * 100, 4) if row_count else 0.0

            semantic_type = DataProfiler._semantic_type(
                series, col, unique_count, row_count
            )

            # Sample values (JSON-safe)
            sample_values = [
                _json_safe(v) for v in series.dropna().head(3).tolist()
            ]

            min_val = max_val = mean_val = median_val = std_val = None
            skewness_val = None
            outlier_count_val = None
            top_values: List[dict] = []

            is_numeric = pd.api.types.is_numeric_dtype(series)
            non_null = series.dropna()

            if is_numeric and semantic_type in ("continuous", "id") and not non_null.empty:
                min_val = _safe_float(series.min())
                max_val = _safe_float(series.max())
                mean_val = _safe_float(series.mean())
                median_val = _safe_float(series.median())
                try:
                    std_val = _safe_float(series.std())
                except Exception:
                    std_val = None
                # Skewness
                try:
                    skew_raw = non_null.skew()
                    skewness_val = _safe_float(skew_raw)
                except Exception:
                    skewness_val = None
                # Outlier count (IQR-based)
                try:
                    q1 = non_null.quantile(0.25)
                    q3 = non_null.quantile(0.75)
                    iqr = q3 - q1
                    lower = q1 - 1.5 * iqr
                    upper = q3 + 1.5 * iqr
                    outlier_count_val = int(((non_null < lower) | (non_null > upper)).sum())
                except Exception:
                    outlier_count_val = None
            elif semantic_type == "datetime" and not non_null.empty:
                # Provide min/max as isoformat strings.
                try:
                    parsed = (
                        non_null
                        if pd.api.types.is_datetime64_any_dtype(series)
                        else pd.to_datetime(non_null, errors="coerce").dropna()
                    )
                    if not parsed.empty:
                        min_val = _json_safe(parsed.min())
                        max_val = _json_safe(parsed.max())
                except Exception:
                    pass

            # top_values for categorical/id (and boolean for convenience)
            if semantic_type in ("categorical", "id", "boolean"):
                top_values = DataProfiler._top_values(series, limit=5)

            columns[col] = ColumnProfile(
                name=str(col),
                dtype=dtype,
                semantic_type=semantic_type,
                null_count=null_count,
                unique_count=unique_count,
                missing_pct=float(missing_pct),
                sample_values=sample_values,
                min_value=min_val,
                max_value=max_val,
                mean_value=mean_val,
                median_value=median_val,
                std_value=std_val,
                skewness=skewness_val,
                outlier_count=outlier_count_val,
                top_values=top_values,
            )

            if semantic_type == "datetime":
                datetime_columns.append(str(col))
            elif semantic_type == "continuous":
                numeric_columns.append(str(col))
            elif semantic_type in ("categorical", "boolean"):
                categorical_columns.append(str(col))

        overall_missing_pct = (
            round((total_missing / total_cells) * 100, 4) if total_cells else 0.0
        )

        # memory
        try:
            memory_bytes = int(df.memory_usage(deep=True).sum())
        except Exception:
            memory_bytes = 0

        # correlations among continuous numeric columns
        correlations = None
        if len(numeric_columns) >= 2:
            try:
                corr_df = df[numeric_columns].corr(numeric_only=True)
                corr_df = corr_df.round(3)
                correlations = {}
                for r in corr_df.index:
                    row_dict = {}
                    for c in corr_df.columns:
                        val = _safe_float(corr_df.loc[r, c])
                        row_dict[str(c)] = val if val is not None else 0.0
                    correlations[str(r)] = row_dict
            except Exception:
                logger.exception("Failed to compute correlations")
                correlations = None

        file_type = filename.split(".")[-1].lower() if "." in filename else "unknown"

        return DataProfile(
            row_count=row_count,
            column_count=column_count,
            columns=columns,
            file_name=filename,
            file_type=file_type,
            missing_pct=float(overall_missing_pct),
            memory_bytes=memory_bytes,
            correlations=correlations,
            datetime_columns=datetime_columns,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
        )
