"""RAG Search API — 法律文档语义检索"""

from fastapi import APIRouter
from pydantic import BaseModel
from backend.main import doc_store

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: dict = {}


class SearchResult(BaseModel):
    query: str
    results: list
    total_found: int


@router.post("/search", response_model=SearchResult)
async def search_documents(req: SearchRequest):
    if doc_store is None:
        return SearchResult(query=req.query, results=[], total_found=0)

    results = doc_store.search(req.query, req.top_k, req.filters)
    return SearchResult(query=req.query, results=results, total_found=len(results))


@router.get("/sources")
async def get_sources():
    return {
        "sources": [
            {"name": "中德税收协定 (2014)", "articles": "第5条第1-6款", "language": "zh"},
            {"name": "德国租税通则 (AO)", "articles": "§12-13 PE定义", "language": "de/zh"},
            {"name": "OECD 税收协定范本注释 (2017)", "articles": "第5条注释", "language": "en/zh"},
            {"name": "BEPS 行动计划7最终报告 (2015)", "articles": "防止人为规避PE", "language": "en/zh"},
            {"name": "德国商法典 (HGB)", "articles": "§238-263 簿记+年报", "language": "de/zh"},
            {"name": "欧盟最低税指令 2022/2523", "articles": "支柱二实施", "language": "en/zh"},
        ]
    }
