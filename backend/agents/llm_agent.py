"""LLM-Powered PE Tax Agent — DeepSeek + LangChain 1.3 create_agent"""

import json, logging
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位精通中德税务的 AI 顾问，专长于常设机构（PE）风险分析。

你有以下工具可以调用：
- `analyze_pe_risk`: 对企业的德国业务活动进行PE风险评估。输入JSON格式的15题答案。
- `search_legal_docs`: 搜索中德税收法律条文（协定第5条、AO §12-13、BEPS行动7、HGB等）。
- `calculate_tax_exposure`: 计算PE构成前后的税负差异。
- `get_hgb_checklist`: 获取对应风险等级的HGB合规义务清单。

回答原则：
1. 引用具体的法律条文编号（如"中德协定第5条第3款""AO §12""HGB §238"）
2. 区分"确定构成PE""高风险""中风险""低风险"的场景
3. 如果信息不足，主动询问缺失的关键事实（场所性质、持续时间、是否签合同等）
4. 使用中文回复
5. 在税负问题上给出具体的计算逻辑和参考数字"""


class LLMPEAgent:
    """LLM 驱动的 PE 税务咨询 Agent（LangChain 1.3 + DeepSeek）"""

    def __init__(self, api_key: str = None, model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.agent = None
        self._ready = False

        if api_key:
            self._setup()

    def _setup(self):
        """Initialize agent with LangChain 1.3 create_agent API"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain.agents import create_agent
            from langchain_core.tools import tool

            llm = ChatOpenAI(
                model=self.model,
                base_url=self.base_url,
                api_key=self.api_key,
                temperature=0.3,
                max_tokens=2048,
            )

            @tool
            def analyze_pe_risk(answers_json: str) -> str:
                """对企业的德国业务活动进行PE风险评估。输入为JSON格式的15题答案字典，如 {"1": true, "2": false, ...}。返回风险等级、评分、法律依据和行动建议。"""
                try:
                    answers = json.loads(answers_json)
                    from engine.decision_tree import PEEngine
                    engine = PEEngine()
                    result = engine.evaluate(answers)
                    return json.dumps({
                        "risk_level": result.risk_level,
                        "risk_label": result.risk_label,
                        "total_score": result.total_score,
                        "summary": result.summary,
                        "advice": result.advice[:5],
                        "legal_refs": result.legal_refs[:5],
                    }, ensure_ascii=False, indent=2)
                except Exception as e:
                    return f"评估失败：{e}。请确保输入为有效的JSON格式。"

            @tool
            def search_legal_docs(query: str) -> str:
                """搜索中德税收法律条文。输入自然语言查询（中文或德文），返回最相关的法律文档片段。"""
                try:
                    from backend.rag.document_store import DocumentStore
                    ds = DocumentStore()
                    ds._build_builtin_documents()
                    results = ds.search(query, top_k=5)
                    if not results:
                        return "未找到相关法律条文。"
                    return json.dumps([{
                        "content": r["content"][:200],
                        "source": r["source"],
                        "score": r["score"],
                    } for r in results], ensure_ascii=False, indent=2)
                except Exception as e:
                    return f"法律检索失败：{e}"

            @tool
            def calculate_tax_exposure(profit_eur: float, risk_level: str) -> str:
                """计算PE构成前后的税负差异。参数：profit_eur=德国年税前利润（欧元），risk_level=low/medium/high/constituted。"""
                try:
                    from engine.calculator import TaxExposureCalculator
                    tec = TaxExposureCalculator()
                    exp = tec.calculate(profit_eur, risk_level)
                    return json.dumps({
                        "税前利润EUR": exp.pre_tax_profit_eur,
                        "PE前德国预提税EUR": exp.withholding_tax_eur,
                        "PE后总税负EUR": exp.total_pe_tax_eur,
                        "年度税负差异EUR": exp.annual_tax_difference_eur,
                        "HGB合规成本EUR": exp.hgb_compliance_cost_eur,
                        "年度总暴露EUR": exp.total_annual_exposure_eur,
                        "PE有效税率": f"{exp.corporate_tax_rate}%",
                    }, ensure_ascii=False, indent=2)
                except Exception as e:
                    return f"税负计算失败：{e}"

            @tool
            def get_hgb_checklist(risk_level: str) -> str:
                """获取指定风险等级的HGB合规义务清单。参数：risk_level=low/medium/high/constituted。"""
                try:
                    from engine.decision_tree import PEEngine
                    from utils.hgb_checklist import get_checklist_for_result
                    engine = PEEngine()
                    result = engine.evaluate({
                        1: risk_level != "low",
                        2: risk_level in ("medium", "high", "constituted"),
                        3: risk_level in ("high", "constituted"),
                        8: risk_level in ("high", "constituted"),
                        9: risk_level == "constituted",
                    })
                    cl = get_checklist_for_result(result)
                    sections = []
                    for s in cl["sections"]:
                        items = [f"{i['task']}（{i['legal']}，{i['deadline']}）" for i in s["items"]]
                        sections.append({"title": s["title"], "items": items})
                    return json.dumps({
                        "level_label": cl["level_label"],
                        "sections": sections,
                    }, ensure_ascii=False, indent=2)
                except Exception as e:
                    return f"HGB清单获取失败：{e}"

            tools = [analyze_pe_risk, search_legal_docs, calculate_tax_exposure, get_hgb_checklist]

            self.agent = create_agent(
                model=llm,
                tools=tools,
                system_prompt=SYSTEM_PROMPT,
            )

            self._ready = True
            logger.info(f"LLM Agent ready: {self.model} @ {self.base_url}")

        except Exception as e:
            logger.warning(f"LLM Agent setup failed: {e}")
            self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def chat(self, message: str) -> dict:
        """Send a message and get response."""
        if not self._ready or not self.agent:
            return {
                "reply": "LLM Agent 未配置。请设置 DEEPSEEK_API_KEY 后重启。获取免费 Key：https://platform.deepseek.com",
                "tool_calls": [],
                "confidence": 0.0,
            }

        try:
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": message}],
            })

            # Extract reply from messages
            reply = ""
            tool_calls = []
            messages = result.get("messages", [])
            for msg in messages:
                if hasattr(msg, "content") and msg.content:
                    if hasattr(msg, "type") and msg.type == "tool":
                        tool_calls.append({
                            "tool": getattr(msg, "name", "unknown"),
                            "input": str(getattr(msg, "content", ""))[:200],
                        })
                    elif hasattr(msg, "type") and msg.type == "ai":
                        reply = msg.content

            if not reply and messages:
                # Try last AI message
                for msg in reversed(messages):
                    if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                        reply = msg.content
                        break

            if not reply:
                reply = str(messages[-1]) if messages else "抱歉，我暂时无法回答。"

            return {
                "reply": reply,
                "tool_calls": tool_calls,
                "confidence": 0.85 if tool_calls else 0.60,
            }
        except Exception as e:
            logger.error(f"LLM Agent error: {e}")
            return {
                "reply": f"处理出错：{e}。请稍后重试。",
                "tool_calls": [],
                "confidence": 0.0,
            }

    def reset_memory(self):
        """Re-initialize agent to clear conversation state."""
        if self.api_key:
            self._setup()
            logger.info("Agent memory reset")
