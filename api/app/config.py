import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://host.docker.internal:1337/v1").rstrip("/"))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    llm_chat_model: str = field(default_factory=lambda: os.getenv("LLM_CHAT_MODEL", "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"))
    llm_embed_model: str = field(default_factory=lambda: os.getenv("LLM_EMBED_MODEL", "nomic-embed-text-v2-moe.Q8_0.gguf"))
    embed_dim: int = field(default_factory=lambda: _int("EMBED_DIM", 768))
    llm_timeout_s: int = field(default_factory=lambda: _int("LLM_TIMEOUT_S", 120))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/kpe"))
    integrations_dir: str = field(default_factory=lambda: os.getenv("INTEGRATIONS_DIR", "/var/lib/kpe/integrations"))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "jan"))


settings = Settings()
