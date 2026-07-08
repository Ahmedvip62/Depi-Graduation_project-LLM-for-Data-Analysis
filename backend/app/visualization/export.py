"""Chart export utilities: PNG via kaleido, CSV from underlying data."""
import io
import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.io as pio

logger = logging.getLogger(__name__)


def export_chart_png(chart_json: str, width: int = 1200, height: int = 600) -> bytes:
    """Convert a Plotly JSON figure to a PNG image bytes."""
    fig_dict = json.loads(chart_json)
    fig = pio.from_json(json.dumps(fig_dict))
    return fig.to_image(format="png", width=width, height=height, engine="kaleido")


def export_chart_csv(df: pd.DataFrame, columns: Optional[list] = None) -> str:
    """Export underlying chart data as CSV string."""
    if columns:
        available = [c for c in columns if c in df.columns]
        return df[available].to_csv(index=False)
    return df.to_csv(index=False)
