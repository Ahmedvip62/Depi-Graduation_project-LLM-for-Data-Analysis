from fastapi import APIRouter

from app.config import settings

router = APIRouter()

SUPPORTED_IMAGE_MIME_TYPES = ["image/png", "image/jpeg", "image/webp"]
STREAM_COMMANDS = ["show_dashboard", "download_report"]
SUPPORTED_CHART_TYPES = ["bar", "line", "scatter", "pie", "histogram", "heatmap", "box"]
SUPPORTED_CHART_AGGREGATIONS = ["sum", "mean", "median", "min", "max", "count"]


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "universal-analyst-backend",
        "environment": settings.environment,
    }


@router.get("/capabilities")
def capabilities():
    """Expose safe UI capability metadata without leaking secrets."""
    return {
        "model_name": settings.model_name,
        "router_model_name": settings.router_model_name,
        "image_chat_enabled": settings.image_chat_enabled,
        "max_chat_images": settings.max_chat_images,
        "max_chat_image_mb": settings.max_chat_image_mb,
        "supported_image_mime_types": SUPPORTED_IMAGE_MIME_TYPES,
        "context_window_tokens": settings.context_window_tokens,
        "dynamic_visuals_only": True,
        "supported_chart_types": SUPPORTED_CHART_TYPES,
        "supported_chart_aggregations": SUPPORTED_CHART_AGGREGATIONS,
        "chart_persistence_enabled": True,
        "report_export_enabled": True,
        "stream_commands": STREAM_COMMANDS,
    }
