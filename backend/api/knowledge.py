"""Knowledge Graph API — PE知识图谱查询与可视化"""

from fastapi import APIRouter
from pydantic import BaseModel
from backend.main import kg_builder

router = APIRouter()


class GraphQueryRequest(BaseModel):
    node_type: str = "all"
    max_depth: int = 2


@router.get("/graph")
async def get_full_graph():
    if kg_builder is None:
        return {"nodes": [], "edges": []}
    return kg_builder.export_graph()


@router.post("/query")
async def query_graph(req: GraphQueryRequest):
    if kg_builder is None:
        return {"nodes": [], "edges": [], "paths": []}

    paths = kg_builder.find_paths(req.node_type, req.max_depth)
    return {"paths": paths, "node_type": req.node_type}


@router.get("/compliance-path/{risk_level}")
async def compliance_path(risk_level: str):
    """四层推理：法条→PE触发条件→风险后果→合规行动"""
    if kg_builder is None:
        return {"layers": []}

    result = kg_builder.compliance_chain(risk_level)
    return {"risk_level": risk_level, "chain": result}
