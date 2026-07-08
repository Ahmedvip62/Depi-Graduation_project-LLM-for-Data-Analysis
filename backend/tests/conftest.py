import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_csv_bytes():
    """Sample CSV file content for testing."""
    return b"id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300\n"


@pytest.fixture
def sample_json_bytes():
    """Sample JSON file content for testing."""
    return b'[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'
