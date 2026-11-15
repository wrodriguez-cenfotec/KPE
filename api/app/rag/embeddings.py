from ..config import settings
from ..llm.provider import get_provider

BATCH_SIZE = 16


def _task_prefixes() -> tuple[str, str]:
    """nomic-embed-text models expect a task prefix on queries and on documents."""
    if "nomic" in settings.llm_embed_model.lower():
        return "search_query: ", "search_document: "
    return "", ""


def embed_documents(texts: list[str]) -> list[list[float]]:
    _, prefix = _task_prefixes()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        vectors.extend(get_provider().embed([prefix + t for t in texts[i:i + BATCH_SIZE]]))
    return vectors


def embed_query(text: str) -> list[float]:
    prefix, _ = _task_prefixes()
    return get_provider().embed([prefix + text])[0]


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"
