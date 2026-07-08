"""Text chunking strategies for converting DataFrames into embeddable chunks."""
import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)

# Hard cap on the number of row-chunks we ever produce/embed. Without this, a
# large upload (e.g. a 200MB CSV) would generate len(df)/10 row chunks — tens of
# thousands — all embedded synchronously at upload, which can OOM or hang the
# request. The schema + per-column summary chunks (the most useful for grounding
# answers) are always produced in full; row chunks become a bounded representative
# sample once the dataset exceeds the cap.
MAX_ROW_CHUNKS = 200


class TextChunker:
    """Multiple chunking strategies for RAG embedding."""

    @staticmethod
    def chunk_dataframe(
        df: pd.DataFrame,
        strategy: str = "row",
        max_rows_per_chunk: int = 10,
        max_row_chunks: int = MAX_ROW_CHUNKS,
    ) -> List[str]:
        """Dispatch to the chosen chunking strategy."""
        if strategy == "row":
            return TextChunker._chunk_by_rows(df, max_rows_per_chunk, max_row_chunks)
        elif strategy == "column_summary":
            return TextChunker._chunk_by_column_summary(df)
        elif strategy == "schema":
            return TextChunker._chunk_schema_description(df)
        elif strategy == "combined":
            # Schema + per-column summaries (always full) + a bounded row sample.
            chunks = TextChunker._chunk_schema_description(df)
            chunks += TextChunker._chunk_by_column_summary(df)
            chunks += TextChunker._chunk_by_rows(df, max_rows_per_chunk, max_row_chunks)
            return chunks
        else:
            return TextChunker._chunk_by_rows(df, max_rows_per_chunk, max_row_chunks)

    @staticmethod
    def _chunk_by_rows(
        df: pd.DataFrame, max_rows: int = 10, max_chunks: int = MAX_ROW_CHUNKS
    ) -> List[str]:
        """Each chunk is a CSV block of up to max_rows.

        When the full dataset would yield more than `max_chunks` blocks, take an
        evenly-spaced sample of rows first so the chunks still represent the whole
        dataset rather than only its head.
        """
        if df.empty:
            return []

        total_chunks = (len(df) + max_rows - 1) // max_rows
        if total_chunks <= max_chunks:
            source = df
        else:
            # Evenly-spaced rows covering the whole dataset, so the sampled chunks
            # still represent it end-to-end rather than only its head.
            step = max(max_rows * (total_chunks // max_chunks), max_rows)
            source = df.iloc[::step].head(max_chunks * max_rows)

        chunks: List[str] = []
        for i in range(0, len(source), max_rows):
            chunk_df = source.iloc[i : i + max_rows]
            chunks.append(chunk_df.to_csv(index=False))
        return chunks

    @staticmethod
    def _chunk_by_column_summary(df: pd.DataFrame) -> List[str]:
        """One chunk per column with descriptive statistics."""
        chunks = []
        for col in df.columns:
            series = df[col]
            lines = [f"Column: {col}", f"Type: {series.dtype}"]

            if pd.api.types.is_numeric_dtype(series):
                desc = series.describe()
                std_val = desc.get("std")
                std_str = f"{std_val:.2f}" if std_val is not None and not pd.isna(std_val) else "n/a"
                lines.append(
                    f"Stats: mean={desc['mean']:.2f}, std={std_str}, "
                    f"min={desc['min']}, max={desc['max']}"
                )
            else:
                top_values = series.value_counts().head(5)
                lines.append(f"Top values: {dict(top_values)}")

            lines.append(f"Nulls: {series.isnull().sum()}/{len(series)}")
            chunks.append("\n".join(lines))
        return chunks

    @staticmethod
    def _chunk_schema_description(df: pd.DataFrame) -> List[str]:
        """Single chunk describing the entire schema."""
        lines = [f"Dataset has {len(df)} rows and {len(df.columns)} columns.", ""]
        for col in df.columns:
            dtype = str(df[col].dtype)
            uniques = df[col].nunique()
            lines.append(f"- {col} ({dtype}): {uniques} unique values")
        return ["\n".join(lines)]
