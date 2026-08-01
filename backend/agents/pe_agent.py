"""PE-Scout 智能 Agent — LLM + 规则引擎双引擎驱动"""

import re, json, os, logging
from pathlib import Path
import config  # auto-load .env
from engine.decision_tree import PEEngine
from engine.calculator import TaxExposureCalculator
from utils.nlp_extractor import extract_answers, extract_profile

logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parent.parent.parent / "data"


class PEAgent:
    """税务PE咨询Agent — LLM优先，规则引擎兜底"""

    def __init__(self):
        self.engine = PEEngine()
        self.tec = TaxExposureCalculator()
        self.llm_agent = None

        # Try to initialize LLM agent
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if api_key:
            try:
                from backend.agents.llm_agent import LLMPEAgent
                self.llm_agent = LLMPEAgent(api_key=api_key)
                logger.info("PEAgent: LLM mode enabled (DeepSeek)")
            except Exception as e:
                logger.warning(f"PEAgent: LLM init failed ({e}), using rule-based mode")

        # 预定义意图模式（LLM 不可用时的回退）
        self.intents = {
            "pe_analysis": [
                r"分析.*风险|风险.*分析|评估.*PE|PE.*风险|会.*构成.*PE|会.*构成.*常设|有.*PE.*风险|常设机构.*风险",
                r"帮我.*分析|帮我.*看.*风险|判断.*是否|是否.*构成|会不会.*PE",
            ],
            "pe_type": [
                r"什么是.*固定场所|什么是.*工程.*PE|什么是.*代理人.*PE|固定场所.*什么意思|代理人.*什么意思",
                r"三种.*PE|PE.*分类|PE.*类型|PE.*种类",
            ],
            "threshold": [
                r"12.*月.*门槛|6.*月.*门槛|多少.*月|多长时间|持续多久|时间.*门槛|时间.*要件",
                r"工程.*12.*月|场所.*6.*月",
            ],
            "treaty_article": [
                r"第5条.*规定|协定.*第5|中德协定.*内容|双边协定.*PE|税收协定.*PE",
                r"协定.*原文|条文.*规定|法律.*依据|法律.*条文",
            ],
            "hgb_compliance": [
                r"HGB.*义务|合规.*清单|账簿.*义务|年报.*义务|德国.*商法典.*义务",
                r"PE.*后.*做什么|构成.*后.*怎么|构成.*后.*义务|PE.*后.*义务",
            ],
            "tax_calculation": [
                r"税负.*多少|要交.*多少.*税|税.*多少|额外.*税|多.*交.*税",
                r"税.*计算|计算.*税|税率.*多少|成本.*多少",
            ],
            "preparatory_auxiliary": [
                r"准备性|辅助性|豁免|不构成.*PE|例外.*情况|什么.*不构成",
                r"存储.*豁免|采购.*豁免|信息.*收集.*豁免",
            ],
            "beps_action7": [
                r"BEPS|反碎片|合同.*拆分|行动.*7|行动.*计划.*7",
                r"避税.*PE|规避.*PE|人为.*规避",
            ],
            "ao_vs_treaty": [
                r"德国.*国内法|AO.*12|AO.*13|国内法.*PE|双边协定.*国内法",
                r"协定.*国内法.*不同|国内.*国际.*区别",
            ],
        }

        # 知识库回答模板
        self.knowledge = self._build_knowledge()

    def _build_knowledge(self) -> dict:
        return {
            "pe_type": (
                "根据《中德税收协定》第5条，常设机构（PE）分为三种类型：\n\n"
                "**1. 固定场所型 PE（第5条第1-4款）**\n"
                "- 要件：固定营业场所 + 企业支配权 + 持续>6个月 + 从事非辅助性营业活动\n"
                "- 典型例子：办公室、工厂、仓库（非纯仓储）、门店\n"
                "- 豁免：纯仓储/展示/交付/采购/信息收集/其他准备辅助活动\n\n"
                "**2. 工程/安装型 PE（第5条第3款）**\n"
                "- 要件：建筑工地、建造、装配或安装工程持续>12个月\n"
                "- 注意：停工期间（含天气、资金原因）计入工期\n"
                "- 合同拆分反避税：多个关联合同合并计算工期\n\n"
                "**3. 代理人型 PE（第5条第5-6款）**\n"
                "- 要件：非独立代理人 + 经常以企业名义签订合同\n"
                "- 豁免：独立代理人（代理多家、自负盈亏）\n"
                "- BEPS后：'经常缔约'门槛降低，≥90%业务为单一企业即丧失独立性"
            ),
            "threshold": (
                "中德PE协定中的关键时间门槛：\n\n"
                "- **固定场所型PE**：实务参考门槛为**6个月**。非临时性场所，持续>6月→满足'永久性'要件\n"
                "- **工程/安装型PE**：**12个月**（协定第5条第3款明文规定）\n"
                "  - 工期计算从工程开始日（含准备活动）至工程完成/永久放弃日\n"
                "  - 季节性停工、因天气停工、因资金不足停工期间**均计入工期**\n"
                "- **重要**：德国国内法 AO §12 建筑工程PE门槛为6个月，但**双边协定优先适用**12个月\n"
                "- **服务PE**：中德协定无独立服务PE条款，但特定驻场服务可能通过固定场所PE条款被认定"
            ),
            "treaty_article": (
                "《中德税收协定》(2014) 第5条 常设机构 核心内容：\n\n"
                "**第1款**：PE基本定义——企业进行全部或部分营业的固定营业场所\n"
                "**第2款**：PE列举——管理场所、分支机构、办事处、工厂、作业场所、矿场/油井/采石场等\n"
                "**第3款**：工程型PE——建筑/装配/安装工程持续>12个月\n"
                "**第4款**：豁免清单——(a)仓储/交付设施 (b)库存保存 (c)委托加工库存 (d)采购/信息收集 (e)其他准备辅助活动\n"
                "**第5款**：代理人PE——非独立代理人有权并经常以企业名义签合同\n"
                "**第6款**：独立代理人豁免——经纪人/佣金代理人/其他独立代理人按常规经营业务不构成PE"
            ),
            "preparatory_auxiliary": (
                "协定第5条第4款的准备性/辅助性豁免分析：\n\n"
                "**判断标准**（OECD范本注释第5条§58-60）：\n"
                "- 活动是否构成企业**核心业务**的一部分？\n"
                "- 活动是否**直接产生收入**？\n"
                "- 活动在人员、资产规模上是否**显著**？\n\n"
                "**安全港**（几乎确定豁免）：\n"
                "- 纯仓储、纯交付货物（不进行销售谈判）\n"
                "- 纯采购办事处（不向第三方销售）\n"
                "- 纯广告/市场调研/信息收集\n\n"
                "**危险区**（可能不豁免）：\n"
                "- 仓库同时设展示厅、接受订单、议价→超出辅助性\n"
                "- 采购办事处兼做销售支持\n"
                "- 售后服务包含维修收入\n\n"
                "**反碎片化规则（BEPS行动7）**：\n"
                "- 多处辅助场所组合构成整体营业→合并认定为PE\n"
                "- 紧密关联方分别从事的辅助活动→合并审查"
            ),
            "beps_action7": (
                "BEPS 行动计划7（防止人为规避常设机构）——对PE协定的三大改革：\n\n"
                "**1. 代理人PE门槛降低**\n"
                "- 原文：'有权以企业名义签订合同'\n"
                "- 修改：扩展为'在订立合同过程中起主要作用，且企业通常不对合同进行实质性修改'\n"
                "- 影响：佣金代理商、分销商等更容易被认定为PE\n\n"
                "**2. 准备性/辅助性豁免收紧（反碎片化）**\n"
                "- 新增反碎片化规则：多处关联场所组合活动不豁免\n"
                "- 紧密关联企业分别从事的活动合并审查\n"
                "- 为企业或关联方提供的活动不豁免\n\n"
                "**3. 合同拆分反避税**\n"
                "- 同一项目多个关联合同→合并计算工期\n"
                "- 防止人为将>12月工程拆分为多个≤12月合同"
            ),
            "ao_vs_treaty": (
                "德国国内法 AO vs 中德双边协定——PE定义的关键差异：\n\n"
                "| 维度 | 德国 AO | 中德协定 |\n"
                "|------|---------|----------|\n"
                "| 工程PE门槛 | **6个月** (§12) | **12个月** (第5.3条) |\n"
                "| 代理人PE | §13 常设代理人 | 第5.5-6条（更详细） |\n"
                "| PE豁免 | 基本相同 | 基本相同 |\n"
                "| 适用优先级 | 国内法补缺 | **双边协定优先** |\n\n"
                "**实践影响**：中德协定12个月门槛优先于AO 6个月，但在纯国内情形下AO适用。双边协定的PE条款一般比国内法更优惠（'条约优先'Treaty override原则）。"
            ),
        }

    def process_message(self, message: str, context: dict = None,
                        history: list = None) -> dict:
        """处理用户消息 — LLM优先，规则引擎兜底"""

        # 0. Try LLM Agent first
        if self.llm_agent and self.llm_agent.is_ready:
            result = self.llm_agent.chat(message)
            if result["confidence"] > 0.5:
                return {
                    "reply": result["reply"],
                    "suggested_actions": [
                        {"action": "chat_continue", "label": "继续提问"},
                        {"action": "view_result", "label": "查看完整PE分析报告"},
                    ],
                    "extracted_facts": {
                        "intent": "llm_agent",
                        "pe_answers": 0,
                        "tool_calls": result.get("tool_calls", []),
                    },
                    "confidence": result["confidence"],
                }

        # 1. 意图识别（规则引擎兜底）
        intent, confidence = self._classify_intent(message)

        # 2. 如果涉及PE分析，提取PE要素
        extracted = {}
        if intent in ("pe_analysis", None):
            extracted = extract_answers(message)
            if extracted:
                profile = extract_profile(message)
                extracted["_profile"] = profile

        # 3. 生成回复
        if intent and intent in self.knowledge:
            reply = self.knowledge[intent]
            confidence = max(confidence, 0.85)
        elif intent == "pe_analysis":
            reply = self._analyze_pe_reply(extracted, message)
            confidence = max(confidence, 0.75 if extracted else 0.4)
        elif intent == "tax_calculation":
            reply = self._tax_reply(extracted, message)
            confidence = max(confidence, 0.70)
        elif intent == "hgb_compliance":
            reply = self._hgb_reply(context)
            confidence = max(confidence, 0.80)
        else:
            reply = self._fallback_reply(message)
            confidence = 0.30

        # 4. 建议后续操作
        suggested = self._suggest_actions(intent, extracted)

        return {
            "reply": reply,
            "suggested_actions": suggested,
            "extracted_facts": {"intent": intent, "pe_answers": len(extracted) if extracted else 0},
            "confidence": confidence,
        }

    def _classify_intent(self, message: str) -> tuple:
        for intent, patterns in self.intents.items():
            for pat in patterns:
                if re.search(pat, message):
                    return intent, 0.80
        return None, 0.0

    def _analyze_pe_reply(self, extracted: dict, message: str) -> str:
        if not extracted:
            return (
                "我暂时无法从您的描述中准确识别PE风险要素。\n\n"
                "请尝试更具体地描述：\n"
                "- 在德国是否有固定营业场所（办公室/仓库/工厂等）？租的还是自有的？持续多久了？\n"
                "- 是否有人员在德国开展业务？是否代表公司签合同？\n"
                "- 是否有建筑安装工程项目？工期多长？\n\n"
                "或者您可以直接在「逐题问答」页面逐项回答15道法律要件判断。"
            )

        result = self.engine.evaluate(extracted)
        profile = extracted.pop("_profile", {})

        lines = [f"根据您的描述，我已完成PE风险初步分析：\n"]
        lines.append(f"**风险等级：{result.risk_label}**")
        lines.append(f"**风险评分：{result.total_score} 分**\n")
        lines.append(f"**分析概要**：{result.summary}\n")
        lines.append("**最关键的3个风险因素**：")
        for ref in result.legal_refs[:3]:
            lines.append(f"- {ref}")
        lines.append(f"\n建议您切换到「PE风险评估」页面查看完整雷达图和税负量化结果。")
        return "\n".join(lines)

    def _tax_reply(self, extracted: dict, message: str) -> str:
        lines = ["关于PE税负，以典型场景（假设€200万年利润，中国CIT 25%）为例：\n"]
        lines.append("**PE构成前后双边税负对比（协定第7条 + 中国企业所得税法第23条）：**")
        lines.append("- PE前：德国无征税权（协定第7条第1款），仅中国CIT ≈ €500,000/年")
        lines.append("- PE后：德国KSt+SolZ+GewSt≈30% = €600,000，中国CIT €500,000 − 境外抵免≈€100,000")
        lines.append("- **年度净增税负 ≈ €200,000/年 + HGB合规成本**\n")
        lines.append("实际金额取决于您的德国利润规模和具体业务结构。请在「税负量化」页面输入具体数字查看精确计算。")
        return "\n".join(lines)

    def _hgb_reply(self, context: dict) -> str:
        risk = context.get("risk_level", "constituted") if context else "constituted"
        lines = ["PE构成后触发的主要HGB合规义务：\n"]
        lines.append("**第一优先级（立即）：**")
        lines.append("1. HGB §238 — 建立德国账簿体系（GoB原则）")
        lines.append("2. AO §137-139 — 向德国税务机关登记PE")
        lines.append("3. UStG §18 — 申请德国增值税号\n")
        lines.append("**第二优先级（1-3个月）：**")
        lines.append("4. HGB §242 — 编制首年年度财务报表")
        lines.append("5. 开设德国银行账户 + 建立存货/固定资产台账")
        lines.append("6. AOA利润归属分析\n")
        lines.append("完整清单请查看「HGB合规清单」页面。")
        return "\n".join(lines)

    def _fallback_reply(self, message: str) -> str:
        return (
            "感谢您的提问。我目前专注于以下方面的PE分析：\n\n"
            "- PE风险评估（固定场所/工程/代理人三种类型）\n"
            "- 中德税收协定第5条条文解读\n"
            "- PE时间门槛（6/12个月）\n"
            "- 准备性辅助性活动豁免\n"
            "- BEPS行动7反避税规则\n"
            "- PE构成后税负量化\n"
            "- HGB合规义务\n\n"
            "请重新描述您的问题，或从建议问题中选择一个。"
        )

    def _suggest_actions(self, intent: str, extracted: dict) -> list:
        suggestions = []
        if intent == "pe_analysis" and extracted:
            suggestions.append({"action": "view_result", "label": "查看完整PE分析报告"})
            suggestions.append({"action": "whatif", "label": "进行 What-If 推演调整变量"})
        if intent in ("hgb_compliance", "pe_analysis"):
            suggestions.append({"action": "checklist", "label": "查看HGB合规义务清单"})
        if intent in ("tax_calculation", "pe_analysis"):
            suggestions.append({"action": "exposure", "label": "查看税负暴露量化分析"})
        suggestions.append({"action": "chat_continue", "label": "继续提问其他PE相关问题"})
        return suggestions
