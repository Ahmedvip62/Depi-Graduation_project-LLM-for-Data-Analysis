from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "ENV", "environment", "env"),
    )
    ollama_host: str = "http://localhost:11434"

    # Primary answering model. Gemma 4 12B supports text + image in Ollama.
    model_name: str = "gemma4:12b"
    # Small, fast model used for intent routing / classification.
    router_model_name: str = "gemma4:e4b"
    # Embedding model used by the RAG layer.
    embedding_model: str = "all-MiniLM-L6-v2"

    # Token budget for assembled RAG context.
    max_context_tokens: int = 6000
    # Visible context window used by the frontend token meter.
    context_window_tokens: int = Field(
        default=256000,
        validation_alias=AliasChoices("CONTEXT_WINDOW_TOKENS", "context_window_tokens"),
    )

    # Multimodal chat limits. Images are sent directly to Ollama as base64.
    image_chat_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("IMAGE_CHAT_ENABLED", "image_chat_enabled"),
    )
    max_chat_images: int = Field(
        default=3,
        validation_alias=AliasChoices("MAX_CHAT_IMAGES", "max_chat_images"),
    )
    max_chat_image_mb: int = Field(
        default=5,
        validation_alias=AliasChoices("MAX_CHAT_IMAGE_MB", "max_chat_image_mb"),
    )

    chroma_persist_directory: str = "./chroma_data"

    allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost",
        validation_alias=AliasChoices(
            "ALLOWED_ORIGINS", "CORS_ORIGINS", "allowed_origins", "cors_origins"
        ),
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()
