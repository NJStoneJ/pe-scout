# PE-Scout · 中德常设机构风险分析助手

基于 **LLM Agent + RAG + 知识图谱** 的智能税务合规平台，专为中国企业出海德国场景设计的常设机构（PE）风险分析工具。

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)](https://streamlit.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 快速启动

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 http://localhost:8501

（可选）启动 FastAPI 后端：

```bash
uvicorn backend.main:app --port 8000
# API文档: http://localhost:8000/docs
```

---

## 核心功能

### 智能 PE 风险分析

| 功能 | 说明 |
|------|------|
| **自由文本输入** | 粘贴企业德国业务描述，NLP 自动提取 15 个法律要件，秒级出结果 |
| **逐题问答评估** | 15 道法律要件判断，动态跳转逻辑，四档风险等级输出 |
| **双场景对比** | 经营安排调整前后，左右分栏对比 PE 风险、税负、雷达图 |
| **What-If 推演** | 9 个关键变量滑块/开关，实时联动风险评分和雷达图 |

### AI 能力矩阵

| 功能 | 技术实现 | 说明 |
|------|---------|------|
| **AI 咨询 Agent** | 10 种意图分类 + 规则引擎 + 内置知识库 | 自然语言 PE 问答，置信度评分，建议后续操作 |
| **法律知识图谱** | NetworkX 构建，PyVis 交互可视化 | 34 个节点 / 91 条边，五层四维合规推理模型 |
| **法律文档语义检索** | ChromaDB 向量存储 + 关键词回退检索 | 70+ 法律文档片段索引，覆盖中德协定全文 / AO / BEPS / HGB |
| **用户反馈循环** | RLHF 风格反馈收集器 | 评分记录、统计分析、训练数据导出 |

### 财税专业能力

| 功能 | 说明 |
|------|------|
| **PE 构成风险判定** | 固定场所型（第 5 条第 1-4 款）/ 工程安装型（第 3 款）/ 代理人型（第 5-6 款） |
| **税负暴露量化** | KSt 15% + SolZ + GewSt ≈14% + 预提税 + HGB 合规成本 = 年度 € 金额 |
| **HGB 合规清单** | 按风险等级自动生成德国商法典合规待办（法条引用 + 优先级 + 截止期限） |
| **六维风险雷达图** | 固定场所 / 工程安装 / 代理人 PE / 合规负担 / 财务暴露 / 政策不确定性 |
| **中德税务参数速查** | 企业所得税 / 增值税 / 个税 / HGB 差异 / PE 判定差异，关键词搜索 |
| **虚拟案例库** | 跨境电商仓储 / 光伏安装工程 / 律所代理人 / IT 驻场服务，全风险梯度覆盖 |

---

## 技术架构

```
pe-scout/
├── app.py                          # Streamlit 主入口（9 页面）
├── engine/
│   ├── decision_tree.py            # PE 规则引擎（15 题决策树）
│   └── calculator.py               # 税务暴露量化计算器
├── backend/
│   ├── main.py                     # FastAPI 应用（lifespan 管理）
│   ├── api/
│   │   ├── pe_analysis.py          # PE 分析 API
│   │   ├── chat.py                 # Agent 对话 API
│   │   ├── rag.py                  # RAG 检索 API
│   │   └── knowledge.py            # 知识图谱 API
│   ├── agents/
│   │   └── pe_agent.py             # PE 咨询 Agent（10 意图 + 知识库）
│   ├── rag/
│   │   └── document_store.py       # ChromaDB 向量存储 + 关键词回退
│   ├── knowledge_graph/
│   │   └── pe_graph.py             # NetworkX 知识图谱（5 层合规推理）
│   └── training/
│       └── feedback_loop.py        # RLHF 用户反馈收集器
├── data/
│   ├── rules.json                  # 15 题 PE 规则配置
│   ├── cases.json                  # 4 个虚拟案例
│   ├── tax_params.json             # 中德税务参数对比库（5 大类 25 组）
│   ├── legal_basis.json            # 法律条文引用库（10 部法律文件）
│   └── hgb_checklist.json          # HGB 合规清单（4 等级自动化）
├── utils/
│   ├── nlp_extractor.py            # 自由文本 PE 要素提取器
│   ├── report.py                   # HTML 风险报告生成器
│   ├── hgb_checklist.py            # HGB 合规清单加载器
│   └── export.py                   # 报告导出工具
├── tests/
│   └── test_engine.py              # 34 个自动化测试用例
└── requirements.txt
```

### 四层合规推理模型

```
Layer 0: 法律依据 → Layer 1: PE 分类 → Layer 2: 触发条件/豁免 → Layer 3: 风险后果 → Layer 4: 合规行动
    ↑                   ↑                    ↑                    ↑                 ↑
 中德协定第5条      固定场所型PE       固定营业场所(Q1)        低风险          税务登记
 AO §12-13         工程/安装型PE       企业支配权(Q2)         中风险          HGB §238 账簿
 BEPS 行动7         代理人型PE         持续>6月(Q3)           高风险          年报编制 §242
 HGB §238-263                          纯仓储豁免(Q4)        已构成PE        AOA利润归属
 欧盟最低税指令                         持续>12月(Q9)                         持续申报义务
                                       经常缔约权(Q12)
```

---

## 法律依据

| 法律文件 | 条款 | 适用范围 |
|---------|------|---------|
| 《中德税收协定》(2014) | 第 5 条第 1-6 款 | PE 定义、类型、豁免、门槛 |
| 德国租税通则 (AO) | §12 常设机构、§13 常设代理人 | 德国国内法 PE 补充定义 |
| OECD 税收协定范本注释 (2017) | 第 5 条注释 | PE 判定实务指引 |
| BEPS 行动计划 7 最终报告 (2015) | 防止人为规避 PE | 代理人门槛降低、反碎片化、合同拆分 |
| 德国商法典 (HGB) | §238 簿记义务、§242 年报编制、§253 计价 | PE 构成后合规义务 |
| 欧盟最低税指令 | 2022/2523 | 支柱二 GloBE 规则 EU 实施 |

---

## 评价标准对照（德勤竞赛 100 分制）

| 评价维度 | 权重 | PE-Scout 对应能力 |
|---------|------|------------------|
| 财税场景价值与创新性 | 25% | 中德 PE 风险分析 + HGB 合规清单 + 六维雷达 + 税负 € 量化 |
| AI Coding 融合度与协同质量 | 25% | Claude Code 全流程驱动，86% AI 代码占比，12 次关键交互日志 |
| 技术实现与用户体验 | 25% | Streamlit + FastAPI 双架构，9 页面，Agent + RAG + KG 三引擎 |
| 过程文档与演示表现 | 25% | 10 页方案 PPT + 12 次 AI 协作日志 + 34 个自动化测试 |
| 加分项 | +5 | Streamlit Cloud 可部署公网 + AI 自动生成测试用例 + 财税知识图谱 |

---

## 测试

```bash
pytest tests/test_engine.py -v
# 34 passed — 规则引擎、税负计算、雷达图、HGB清单、RAG文档、Agent、反馈收集
```

---

## 免责声明

本工具仅供初步风险评估参考，**不构成专业税务意见**。
所有案例数据均为自行构造的模拟数据，不涉及任何真实企业信息。
具体跨境税务规划请咨询中德两地专业税务顾问。

---

## License

MIT © 2026 PE-Scout
