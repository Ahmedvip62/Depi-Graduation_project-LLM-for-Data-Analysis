from fastapi import APIRouter
from . import health, upload, chat, visualizations, sessions, skills_api, clean, predict

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(visualizations.router, tags=["visualizations"])
api_router.include_router(sessions.router, tags=["sessions"])
api_router.include_router(skills_api.router, prefix="/skills", tags=["skills"])
api_router.include_router(clean.router, tags=["clean"])
api_router.include_router(predict.router, tags=["prediction"])

