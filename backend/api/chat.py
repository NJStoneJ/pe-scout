"""Chat Agent API — 自然语言 PE 咨询对话"""

from fastapi import APIRouter
from pydantic import BaseModel
from backend.agents.pe_agent import PEAgent
from backend.main import pe_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: dict = {}
    history: list = []


class ChatResponse(BaseModel):
    reply: str
    suggested_actions: list = []
    extracted_facts: dict = {}
    confidence: float = 0.0


@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest):
    if pe_agent is None:
        return ChatResponse(reply="Agent not initialized", confidence=0)

    response = pe_agent.process_message(req.message, req.context, req.history)
    return ChatResponse(**response)


@router.get("/suggestions")
async def get_suggestions():
    return {
        "suggestions": [
            "如果我的德国仓库除了存储还增加了展示功能，会构成PE吗？",
            "工程停工3个月还算在12个月工期里吗？",
            "什么是反碎片化规则（BEPS行动7）？",
            "PE构成后触发哪些HGB合规义务？",
            "德国国内法AO的PE定义和双边协定有什么不同？",
            "跨境电商只用亚马逊FBA仓会有PE风险吗？",
        ]
    }
