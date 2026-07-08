"""Tests for the file ingestion engine."""
import pandas as pd
from app.core.ingestion import IngestionEngine


class TestIngestionEngine:
    def test_parse_csv(self, sample_csv_bytes):
        df = IngestionEngine.parse_file(sample_csv_bytes, "test.csv")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["id", "name", "value"]

    def test_parse_json(self, sample_json_bytes):
        df = IngestionEngine.parse_file(sample_json_bytes, "test.json")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_unsupported_format_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unsupported"):
            IngestionEngine.parse_file(b"hello", "test.xyz")

    def test_empty_csv(self):
        empty_csv = b"col_a,col_b\n"
        df = IngestionEngine.parse_file(empty_csv, "empty.csv")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ["col_a", "col_b"]
