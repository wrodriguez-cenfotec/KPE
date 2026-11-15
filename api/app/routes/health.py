from fastapi import APIRouter

from ..config import settings
from ..llm.provider import LLMError, get_provider

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/llm")
def health_llm():
    try:
        models = get_provider().models()
    except LLMError:
        return {"reachable": False, "models": [], "chat_model": settings.llm_chat_model, "embed_model": settings.llm_embed_model,
                "message": "No se pudo conectar con Jan. Revise que el servidor local de Jan esté encendido en el puerto 1337."}
    chat_ok, embed_ok = settings.llm_chat_model in models, settings.llm_embed_model in models
    if chat_ok and embed_ok:
        msg = "Jan está disponible y los dos modelos están cargados."
    else:
        missing = [m for m, ok in ((settings.llm_chat_model, chat_ok), (settings.llm_embed_model, embed_ok)) if not ok]
        msg = "Jan responde, pero falta este modelo: " + ", ".join(missing) + ". Copie el nombre exacto desde la lista de modelos."
    return {"reachable": True, "models": models, "chat_model": settings.llm_chat_model, "embed_model": settings.llm_embed_model,
            "chat_model_loaded": chat_ok, "embed_model_loaded": embed_ok, "message": msg}
