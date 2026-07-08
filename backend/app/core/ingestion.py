import io
import json
import logging
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pdfplumber

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {"csv", "json", "parquet", "pdf", "sqlite", "db"}


class IngestionEngine:
    @staticmethod
    def parse_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if extension == "csv":
            try:
                return pd.read_csv(io.BytesIO(file_bytes))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Could not read CSV file: {exc}") from exc
        elif extension == "json":
            return IngestionEngine._parse_json(file_bytes)
        elif extension == "parquet":
            try:
                return pd.read_parquet(io.BytesIO(file_bytes))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Could not read Parquet file: {exc}") from exc
        elif extension == "pdf":
            return IngestionEngine._parse_pdf(file_bytes)
        elif extension in ("sqlite", "db"):
            return IngestionEngine._parse_sqlite(file_bytes)
        else:
            raise ValueError(
                f"Unsupported file format: '{extension}'. "
                f"Supported: {SUPPORTED_EXTENSIONS}"
            )

    @staticmethod
    def _parse_json(file_bytes: bytes) -> pd.DataFrame:
        """Parse JSON into a DataFrame, tolerating both arrays and single objects.

        A top-level array of records becomes rows; a single object is normalized to
        one row (or, when its values are arrays/records, flattened). NDJSON (one
        JSON object per line) is detected as a fallback.
        """
        text = file_bytes.decode("utf-8-sig", errors="replace").strip()
        if not text:
            raise ValueError("The JSON file is empty.")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fall back to newline-delimited JSON.
            try:
                return pd.read_json(io.StringIO(text), lines=True)
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Could not parse JSON file: {exc}") from exc

        if isinstance(data, list):
            if not data:
                raise ValueError("The JSON array is empty.")
            return pd.json_normalize(data)
        if isinstance(data, dict):
            # A dict of equal-length lists -> columns; otherwise a single record.
            values = list(data.values())
            if values and all(isinstance(v, list) for v in values):
                try:
                    return pd.DataFrame(data)
                except ValueError:
                    return pd.json_normalize(data)
            return pd.json_normalize(data)
        raise ValueError("JSON must be an object or an array of objects.")

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> pd.DataFrame:
        """Extract tables from PDF pages. Each table is processed independently."""
        all_frames: list[pd.DataFrame] = []

        try:
            pdf_ctx = pdfplumber.open(io.BytesIO(file_bytes))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Could not open PDF file: {exc}") from exc

        with pdf_ctx as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        logger.warning(
                            "Skipping empty/header-only table on page %d, table %d",
                            page_num,
                            table_idx,
                        )
                        continue
                    try:
                        header = table[0]
                        rows = table[1:]
                        # Filter rows that don't match header column count
                        valid_rows = [r for r in rows if len(r) == len(header)]
                        if valid_rows:
                            df = pd.DataFrame(valid_rows, columns=header)
                            all_frames.append(df)
                    except Exception as exc:
                        logger.warning(
                            "Failed to parse table on page %d: %s",
                            page_num,
                            exc,
                        )

        if not all_frames:
            logger.warning("No tables found in PDF")
            return pd.DataFrame()

        # If multiple tables have the same columns, concatenate them
        # Otherwise return only the first (largest) one
        if len(all_frames) == 1:
            return all_frames[0]

        # Try to concat tables with matching columns
        first_cols = set(all_frames[0].columns)
        compatible = [f for f in all_frames if set(f.columns) == first_cols]
        if len(compatible) == len(all_frames):
            return pd.concat(compatible, ignore_index=True)

        logger.info(
            "Multiple tables with different schemas found; returning largest."
        )
        return max(all_frames, key=len)

    @staticmethod
    def _parse_sqlite(file_bytes: bytes) -> pd.DataFrame:
        """Parse a SQLite database file — reads the largest table."""
        # SQLite needs a file on disk, write to temp
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        conn = None
        try:
            try:
                conn = sqlite3.connect(tmp_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
            except sqlite3.DatabaseError as exc:
                raise ValueError(
                    "Could not read SQLite database (file may be corrupt or not a database)."
                ) from exc

            if not tables:
                logger.warning("No tables found in SQLite database")
                return pd.DataFrame()

            # Read all tables, return the largest
            frames = {}
            for table_name in tables:
                try:
                    df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
                    frames[table_name] = df
                except Exception as exc:
                    logger.warning("Failed to read table %s: %s", table_name, exc)

            if not frames:
                return pd.DataFrame()

            largest = max(frames.items(), key=lambda kv: len(kv[1]))
            logger.info("SQLite: using table '%s' (%d rows)", largest[0], len(largest[1]))
            return largest[1]
        finally:
            if conn is not None:
                conn.close()
            Path(tmp_path).unlink(missing_ok=True)
