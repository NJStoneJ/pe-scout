"""PE-Scout FastAPI Backend — 智能PE分析后端服务"""

import sys, logging
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.agents.pe_agent import PEAgent
from backend.rag.document_store import DocumentStore
from backend.knowledge_graph.pe_graph import PEGraphBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pe_agent = None
doc_store = None
kg_builder = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pe_agent, doc_store, kg_builder
    logger.info("PE-Scout Backend starting...")

    pe_agent = PEAgent()
    doc_store = DocumentStore()
    kg_builder = PEGraphBuilder()

    await doc_store.initialize()

    logger.info("PE-Scout Backend ready")
    yield

    logger.info("PE-Scout Backend shutting down...")
    if doc_store:
        doc_store.close()
    logger.info("Shutdown complete")


# Import routers after globals to break circular imports
from backend.api.pe_analysis import router as pe_router
from backend.api.chat import router as chat_router
from backend.api.rag import router as rag_router
from backend.api.knowledge import router as kg_router


app = FastAPI(
    title="PE-Scout API",
    description="中德常设机构风险分析智能后端 · LLM Agent + RAG + Knowledge Graph",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(pe_router, prefix="/api/pe", tags=["PE Analysis"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat Agent"])
app.include_router(rag_router, prefix="/api/rag", tags=["RAG Search"])
app.include_router(kg_router, prefix="/api/kg", tags=["Knowledge Graph"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0.0", "modules": {
        "agent": pe_agent is not None,
        "rag": doc_store is not None,
        "kg": kg_builder is not None,
    }}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
