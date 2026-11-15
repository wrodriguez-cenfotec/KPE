import threading

from fastapi import APIRouter

from ..bootstrap import runner

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/bootstrap/status")
def bootstrap_status():
    return runner.status()


@router.post("/reindex")
def reindex():
    from ..rag.indexing import reindex_all
    runner.state.update(stage="index", detail=None, chunks_done=0, chunks_total=0)
    threading.Thread(target=reindex_all, args=(runner.state,), name="reindex", daemon=True).start()
    return {"status": "reindexing"}
