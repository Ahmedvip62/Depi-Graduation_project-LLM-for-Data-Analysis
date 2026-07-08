"""Tests for the data profiler."""
import pandas as pd
from app.core.profiler import DataProfiler


class TestDataProfiler:
    def test_profile_basic(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        profile = DataProfiler.profile(df, "test.csv")

        assert profile.row_count == 3
        assert profile.column_count == 2
        assert profile.file_name == "test.csv"
        assert profile.file_type == "csv"
        assert "a" in profile.columns
        assert "b" in profile.columns

    def test_profile_numeric_stats(self):
        df = pd.DataFrame({"val": [10.0, 20.0, 30.0]})
        profile = DataProfiler.profile(df, "nums.csv")

        col = profile.columns["val"]
        assert col.min_value == 10.0
        assert col.max_value == 30.0
        assert col.mean_value == 20.0
        assert col.null_count == 0

    def test_profile_with_nulls(self):
        df = pd.DataFrame({"x": [1, None, 3]})
        profile = DataProfiler.profile(df, "nulls.csv")

        assert profile.columns["x"].null_count == 1
