"""中德税务常量 — 单点维护，calculator.py 和 financial_model.py 共享"""

# === 德国税率 (2026) ===
# 数据来源：德国联邦财政部 (BMF) + 各州 GewSt Hebesatz 均值
# 最后更新：2026-07

KST = 0.15              # Körperschaftsteuer 企业所得税
SOLZ_RATE = 0.055       # Solidaritätszuschlag 团结附加税 (KSt 的 5.5%)
SOLZ = KST * SOLZ_RATE  # = 0.00825

GEWST_BASE = 0.035      # Gewerbesteuer 营业税基础税率 (Steuermesszahl)
AVG_HEBESATZ = 4.00     # 地方稽征率均值 (~400%; 慕尼黑 490 / 法兰克福 460 / 柏林 410)
GEWST = GEWST_BASE * AVG_HEBESATZ  # ≈ 0.14

# 综合税率
COMBINED_CORPORATE_RATE = KST + SOLZ + GEWST  # ≈ 29.825%

# === 预提税 (中德协定) ===
DIV_WHT_DTA = 0.05      # 股息预提税率 (持股 ≥25% 时，协定第10条第2款a项)

# === HGB 合规成本 (年度估算，欧元) ===
HGB_COST = {
    "low": 0,
    "medium": 5000,
    "high": 15000,
    "constituted": 35000,
}

# === 子公司设立成本 (一次性，欧元) ===
SUBSIDIARY_SETUP_COST = 25000
