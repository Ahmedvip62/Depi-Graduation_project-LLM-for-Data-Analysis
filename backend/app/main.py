from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.router import api_router

app = FastAPI(
    title="Universal AI Platform Backend",
    description="Backend for the Domain-Agnostic AI Platform",
    version="0.1.0"
)

# CORS. The spec forbids credentials with a wildcard origin, so when origins
# is "*" we disable credentials and allow all origins via regex instead.
_origins = settings.cors_origins
if "*" in _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Universal AI Platform Backend"}
