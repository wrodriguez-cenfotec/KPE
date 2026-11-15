import httpx

from ..config import settings
from .provider import LLMError


class JanProvider:
    """OpenAI compatible client for the Jan local API server."""

    def __init__(self) -> None:
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
        self.client = httpx.Client(base_url=settings.llm_base_url, headers=headers, timeout=settings.llm_timeout_s)

    def _post(self, path: str, payload: dict) -> dict:
        try:
            r = self.client.post(path, json=payload)
            r.raise_for_status()
            return r.json()
        except httpx.TimeoutException as exc:
            raise LLMError(f"timeout after {settings.llm_timeout_s}s calling {settings.llm_base_url}{path}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"{type(exc).__name__} calling {settings.llm_base_url}{path}: {exc}") from exc

    def chat(self, messages: list[dict], **opts) -> dict:
        payload = {"model": opts.pop("model", settings.llm_chat_model), "messages": messages, **opts}
        data = self._post("/chat/completions", payload)
        return {"content": data["choices"][0]["message"].get("content") or "", "usage": data.get("usage", {})}

    def embed(self, texts: list[str]) -> list[list[float]]:
        data = self._post("/embeddings", {"model": settings.llm_embed_model, "input": texts})
        return [d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"])]

    def models(self) -> list[str]:
        try:
            r = self.client.get("/models", timeout=5)
            r.raise_for_status()
            return [m["id"] for m in r.json().get("data", [])]
        except httpx.HTTPError as exc:
            raise LLMError(str(exc)) from exc
