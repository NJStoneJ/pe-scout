# PE-Scout：中德常设机构风险分析助手

基于中德税收协定第5条 + 德国 AO §12-13 + OECD BEPS 行动计划7 的常设机构（PE）风险分析 Web 工具。

## 快速启动

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器自动打开 http://localhost:8501

## 功能模块

- **PE 风险评估**：15道法律要件问答 → 三组PE分类判定 → 四档风险等级 + 法条引用 + 行动建议
- **中德税务参数速查**：五大类别（企业所得税/增值税/个税/HGB差异/PE判定）双边对比
- **虚拟案例库**：4个预设典型出海德国场景，一键加载演示

## 项目结构

```
pe-scout/
├── app.py                 # Streamlit 主入口
├── engine/
│   ├── decision_tree.py   # PE 规则引擎
│   └── calculator.py      # 税务参数速算
├── data/
│   ├── rules.json         # 15题规则配置
│   ├── cases.json         # 4个虚拟案例
│   ├── tax_params.json    # 中德税务参数对比库
│   └── legal_basis.json   # 法律条文引用库
├── utils/
│   ├── report.py          # HTML 报告生成
│   └── export.py          # 报告导出
├── tests/
│   └── test_engine.py     # 24个自动化测试用例
└── requirements.txt
```

## 法律依据

- 《中德税收协定》(2014) 第5条
- 德国租税通则 (AO) §12-13
- OECD 税收协定范本及注释 (2017)
- BEPS 行动计划7 (2015)

## 免责声明

本工具仅供初步风险评估参考，不构成专业税务意见。
具体跨境税务规划请咨询中德两地专业税务顾问。
