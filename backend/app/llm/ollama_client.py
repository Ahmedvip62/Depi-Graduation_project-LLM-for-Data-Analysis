import json
import logging
from typing import Any, AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT = httpx.Timeout(600.0, connect=10.0)


class OllamaClient:
    def __init__(self, model: str | None = None):
        self.base_url = f"{settings.ollama_host}/api"
        self.model = model or settings.model_name

    @staticmethod
    def _usage_from_chunk(data: dict[str, Any]) -> dict[str, Any] | None:
        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        if prompt_tokens is None and completion_tokens is None:
            return None

        prompt_tokens = int(prompt_tokens or 0)
        completion_tokens = int(completion_tokens or 0)
        usage: dict[str, Any] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        for key in (
            "total_duration",
            "load_duration",
            "prompt_eval_duration",
            "eval_duration",
        ):
            if key in data:
                usage[key] = data[key]
        return usage

    async def generate_stream_events(
        self,
        prompt: str,
        num_predict: int | None = None,
        temperature: float | None = None,
        images: list[str] | None = None,
        format: Any | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream Ollama tokens, usage metadata, and real error events.

        `format` maps to Ollama's structured-output field: pass "json" for JSON
        mode, or a JSON-schema dict to force schema-valid output. Older Ollama
        builds ignore an unknown schema shape, so callers should still parse
        defensively.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        if images:
            payload["images"] = images
        if format is not None:
            payload["format"] = format

        options: dict[str, Any] = {}
        if num_predict is not None:
            options["num_predict"] = num_predict
        if temperature is not None:
            options["temperature"] = temperature
        if options:
            payload["options"] = options

        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/generate",
                    json=payload,
                ) as response:
                    if response.is_error:
                        detail_bytes = await response.aread()
                        detail = detail_bytes.decode("utf-8", errors="replace")[:500]
                        message = f"Ollama request failed ({response.status_code}): {detail}"
                        logger.error(message)
                        yield {"type": "error", "message": message}
                        return

                    async for chunk in response.aiter_lines():
                        if not chunk:
                            continue
                        try:
                            data = json.loads(chunk)
                        except json.JSONDecodeError:
                            logger.warning("Skipping malformed Ollama chunk: %s", chunk[:100])
                            continue

                        if data.get("error"):
                            message = f"Ollama generation failed: {data['error']}"
                            logger.error(message)
                            yield {"type": "error", "message": message}
                            return

                        token = data.get("response")
                        if token:
                            yield {"type": "token", "token": token}

                        if data.get("done"):
                            usage = self._usage_from_chunk(data)
                            if usage:
                                yield {"type": "usage", "usage": usage}
        except httpx.ConnectError:
            message = f"Cannot connect to Ollama at {self.base_url}."
            logger.error(message)
            yield {"type": "error", "message": message}
        except httpx.TimeoutException:
            message = "Ollama request timed out."
            logger.error(message)
            yield {"type": "error", "message": message}

    async def generate_stream(
        self,
        prompt: str,
        num_predict: int | None = None,
        temperature: float | None = None,
        images: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        async for event in self.generate_stream_events(
            prompt,
            num_predict=num_predict,
            temperature=temperature,
            images=images,
        ):
            if event.get("type") == "token":
                yield str(event.get("token", ""))
            elif event.get("type") == "error":
                yield f"[Error: {event.get('message', 'Ollama generation failed')}]"


    async def generate_text(
        self,
        prompt: str,
        num_predict: int | None = None,
        temperature: float | None = None,
        images: list[str] | None = None,
        format: Any | None = None,
    ) -> str:
        """Collect a full (non-streaming) completion. Raises on model error.

        Used by non-conversational callers (e.g. the report narrative, the chart
        planner) that need the whole response at once rather than an SSE stream.
        `format` forwards to Ollama structured output (see generate_stream_events).
        """
        parts: list[str] = []
        async for event in self.generate_stream_events(
            prompt,
            num_predict=num_predict,
            temperature=temperature,
            images=images,
            format=format,
        ):
            if event.get("type") == "token":
                parts.append(str(event.get("token", "")))
            elif event.get("type") == "error":
                raise RuntimeError(event.get("message", "Ollama generation failed"))
        return "".join(parts).strip()


def get_ollama_client(model: str | None = None) -> OllamaClient:
    """Factory function to avoid module-level instantiation."""
    return OllamaClient(model)