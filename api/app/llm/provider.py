from typing import Protocol


class LLMError(Exception):
    """Raised when the model server cannot be reached or answers with an error."""


class LLMProvider(Protocol):
    def chat(self, messages: list[dict], **opts) -> dict:
        """Returns {"content": str, "usage": dict}."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def models(self) -> list[str]:
        ...


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        from ..config import settings
        if settings.llm_provider == "mock":
            from .mock_provider import MockProvider
            _provider = MockProvider()
        else:
            from .jan_provider import JanProvider
            _provider = JanProvider()
    return _provider


def set_provider(provider: LLMProvider | None) -> None:
    global _provider
    _provider = provider
