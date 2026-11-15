import hashlib
import json
import math

from ..config import settings


class MockProvider:
    """Scripted provider for tests. Chat answers come from a queue, embeddings from a hash."""

    def __init__(self, responses: list | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[list[dict]] = []

    def queue(self, *responses) -> None:
        self.responses.extend(responses)

    def chat(self, messages: list[dict], **opts) -> dict:
        self.calls.append(messages)
        item = self.responses.pop(0) if self.responses else {"answer": "Con gusto le ayudo."}
        content = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        return {"content": content, "usage": {"prompt_tokens": 0, "completion_tokens": 0}}

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            words = text.lower().split()
            vec = [0.0] * settings.embed_dim
            for w in words:
                h = int(hashlib.sha256(w.encode()).hexdigest(), 16)
                vec[h % settings.embed_dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out

    def models(self) -> list[str]:
        return [settings.llm_chat_model, settings.llm_embed_model]
