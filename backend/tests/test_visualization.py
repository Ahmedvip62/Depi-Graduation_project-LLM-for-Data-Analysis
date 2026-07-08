"""Tests for the visualization chart factory."""
import pandas as pd
import pytest
from app.visualization.chart_factory import ChartFactory


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "region": ["North", "South", "East", "West"],
        "sales": [100, 200, 150, 300],
        "profit": [10, 40, 30, 80],
    })


class TestChartFactory:
    def test_bar_chart(self, sample_df):
        spec = {"type": "bar", "x": "region", "y": "sales", "title": "Sales by Region"}
        result = ChartFactory.generate_chart(sample_df, spec)
        assert isinstance(result, str)
        assert "Sales by Region" in result

    def test_line_chart(self, sample_df):
        spec = {"type": "line", "x": "region", "y": "sales"}
        result = ChartFactory.generate_chart(sample_df, spec)
        assert isinstance(result, str)

    def test_pie_chart(self, sample_df):
        spec = {"type": "pie", "x": "region", "y": "sales"}
        result = ChartFactory.generate_chart(sample_df, spec)
        assert isinstance(result, str)

    def test_histogram(self, sample_df):
        spec = {"type": "histogram", "x": "sales"}
        result = ChartFactory.generate_chart(sample_df, spec)
        assert isinstance(result, str)

    def test_box_chart(self, sample_df):
        spec = {"type": "box", "x": "region", "y": "sales"}
        result = ChartFactory.generate_chart(sample_df, spec)
        assert isinstance(result, str)

    def test_unsupported_type_raises(self, sample_df):
        spec = {"type": "unknown_chart", "x": "region", "y": "sales"}
        with pytest.raises(ValueError, match="Unsupported chart type"):
            ChartFactory.generate_chart(sample_df, spec)

    def test_invalid_column_raises(self, sample_df):
        spec = {"type": "bar", "x": "nonexistent", "y": "sales"}
        with pytest.raises(ValueError, match="not found"):
            ChartFactory.generate_chart(sample_df, spec)


class TestChartFactoryCoercion:
    """The executor should render reasonable-but-imperfect model specs instead of
    crashing, without ever substituting a different/static chart."""

    @pytest.fixture
    def df(self):
        return pd.DataFrame({
            "region": ["North", "South", "East", "West", "North", "South"],
            "channel": ["online", "retail", "online", "retail", "online", "retail"],
            "revenue": [100, 200, 150, 300, 120, 220],
            "units": [3, 7, 5, 9, 4, 8],
        })

    def test_grouped_aggregate_with_color(self, df):
        # x + color + numeric y under an aggregate must not collide on reset_index.
        spec = {"type": "bar", "x": "region", "y": "revenue", "color": "channel", "aggregate": "sum"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str) and "data" in result

    def test_y_equals_x_does_not_crash(self, df):
        # Model mistakenly sets y == x; previously raised "cannot insert ... already exists".
        spec = {"type": "bar", "x": "region", "y": "region", "aggregate": "count"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_nonnumeric_y_with_aggregate_falls_back_to_count(self, df):
        # sum over a categorical y is impossible; interpret as count, don't crash.
        spec = {"type": "bar", "x": "region", "y": "channel", "aggregate": "sum"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_count_path_no_y(self, df):
        spec = {"type": "bar", "x": "region", "aggregate": "count"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_unknown_color_is_dropped_not_fatal(self, df):
        spec = {"type": "bar", "x": "region", "y": "revenue", "color": "not_a_column", "aggregate": "sum"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_unknown_y_is_dropped(self, df):
        # Unknown y dropped; x-only bar becomes a count, still renders.
        spec = {"type": "bar", "x": "region", "y": "not_a_column"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_histogram_with_categorical_y_does_not_crash(self, df):
        spec = {"type": "histogram", "x": "revenue", "y": "region"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_top_n_limits_categories(self, df):
        spec = {"type": "bar", "x": "region", "aggregate": "count", "top_n": 2, "sort": "desc"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_unknown_x_still_raises(self, df):
        # The chart's spine is non-negotiable: a bad x is a real error, no fallback.
        spec = {"type": "bar", "x": "nonexistent"}
        with pytest.raises(ValueError, match="not found"):
            ChartFactory.generate_chart(df, spec)

    def test_missing_type_raises(self, df):
        with pytest.raises(ValueError, match="type is required"):
            ChartFactory.generate_chart(df, {"x": "region"})

    def test_apply_filters_slicing(self, df):
        # Apply filters: revenue > 120 and channel == online
        spec = {
            "type": "bar",
            "x": "region",
            "y": "revenue",
            "aggregate": "sum",
            "filters": [
                {"column": "revenue", "operator": "gt", "value": 120},
                {"column": "channel", "operator": "eq", "value": "online"}
            ]
        }
        # Under these filters, only one row matches: region=East, revenue=150
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)
        assert "East" in result
        assert "North" not in result  # North online has revenue=100 & 120 (not > 120)

    def test_auto_aggregation_for_duplicates(self, df):
        # df contains duplicate regions (North, South, East, West, North, South)
        # We don't supply aggregate here; it should auto-aggregate to sum because y is numeric
        spec = {"type": "bar", "x": "region", "y": "revenue"}
        result = ChartFactory.generate_chart(df, spec)
        assert isinstance(result, str)

    def test_dynamic_schema_builder(self):
        from app.api.chat import get_chart_plan_schema
        schema = get_chart_plan_schema(["col_a", "col_b"])
        assert "col_a" in schema["properties"]["charts"]["items"]["properties"]["x"]["enum"]
        assert "col_b" in schema["properties"]["charts"]["items"]["properties"]["x"]["enum"]
        assert "invalid" not in schema["properties"]["charts"]["items"]["properties"]["x"]["enum"]
