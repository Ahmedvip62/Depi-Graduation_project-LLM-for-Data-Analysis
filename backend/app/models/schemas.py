from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    semantic_type: str = "categorical"
    null_count: int = 0
    unique_count: int = 0
    missing_pct: float = 0.0
    sample_values: List[Any] = Field(default_factory=list)
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_value: Optional[float] = None
    skewness: Optional[float] = None
    outlier_count: Optional[int] = None
    top_values: List[Dict[str, Any]] = Field(default_factory=list)


class DataProfile(BaseModel):
    row_count: int
    column_count: int
    columns: Dict[str, ColumnProfile]
    file_name: str
    file_type: str
    missing_pct: float = 0.0
    memory_bytes: int = 0
    correlations: Optional[Dict[str, Dict[str, float]]] = None
    datetime_columns: List[str] = Field(default_factory=list)
    numeric_columns: List[str] = Field(default_factory=list)
    categorical_columns: List[str] = Field(default_factory=list)


class CleaningRequest(BaseModel):
    session_id: str
    instructions: Optional[str] = None
    create_new_session: bool = False


class CleaningResponse(BaseModel):
    message: str
    session_id: str
    original_rows: int
    cleaned_rows: int
    original_columns: int
    cleaned_columns: int
    actions: List[str]
    explanation: str
    profile: DataProfile
    preview_rows: List[Dict[str, Any]]