"""PE 税负影响财务模型 — ETR · ROE · 盈亏平衡 · 5年NPV"""

from dataclasses import dataclass

# Tax rates (Germany 2026)
KST = 0.15          # Körperschaftsteuer
SOLZ = 0.055 * KST  # Solidaritätszuschlag
GEWST_BASE = 0.035
AVG_HEBESATZ = 4.0
GEWST = GEWST_BASE * AVG_HEBESATZ  # ≈ 14%
COMBINED_RATE = KST + SOLZ + GEWST  # ≈ 29.825%
DIV_WHT = 0.05      # 中德协定股息预提税率

# HGB compliance annual cost estimates
HGB_COST = {"low": 0, "medium": 5000, "high": 15000, "constituted": 35000}

# Subsidiary setup cost (one-time)
SUBSIDIARY_SETUP = 25000


@dataclass
class FinancialImpactResult:
    """PE 构成后的财务影响分析"""

    # ETR
    etr_before_pe: float        # PE 前有效税率
    etr_after_pe: float         # PE 后有效税率
    etr_delta_pct: float        # ETR 变化 (百分点)

    # ROE
    roe_before_pe: float        # PE 前 ROE
    roe_after_pe: float         # PE 后 ROE
    roe_dilution_pct: float     # ROE 稀释 (百分点)

    # 盈亏平衡
    breakeven_profit_eur: float    # 盈亏平衡德国利润额
    subsidiary_better_above_eur: float  # 超过此金额设子公司更划算

    # 5年 NPV (折现率 8%)
    npv_5yr_tax_pe_before_eur: float
    npv_5yr_tax_pe_after_eur: float
    npv_5yr_difference_eur: float
    npv_roi_if_restructure_eur: float  # 如果花 €25k 重组架构的 NPV 收益

    # 综合建议
    recommendation: str


class FinancialModel:
    """PE 税负影响财务模型"""

    @staticmethod
    def analyze(
        pretax_profit_eur: float,
        pe_risk_level: str,
        total_equity_global_eur: float = 3_500_000,
        dividend_payout_ratio: float = 0.7,
        discount_rate: float = 0.08,
        growth_rate: float = 0.05,
    ) -> FinancialImpactResult:
        """运行完整财务影响分析"""

        # === 1. ETR 计算 ===
        wt_only = pretax_profit_eur * dividend_payout_ratio * DIV_WHT
        etr_before = wt_only / pretax_profit_eur if pretax_profit_eur > 0 else 0

        kst_solz = pretax_profit_eur * (KST + SOLZ)
        gewst = pretax_profit_eur * GEWST
        after_tax = pretax_profit_eur - kst_solz - gewst
        div_wt_after = after_tax * dividend_payout_ratio * DIV_WHT
        total_pe_tax = kst_solz + gewst + div_wt_after
        etr_after = total_pe_tax / pretax_profit_eur if pretax_profit_eur > 0 else 0

        # === 2. ROE 影响 ===
        net_profit_before = pretax_profit_eur - wt_only
        net_profit_after = after_tax - div_wt_after
        hgb_cost = HGB_COST.get(pe_risk_level, 0)
        net_profit_after_net = net_profit_after - hgb_cost

        roe_before = net_profit_before / total_equity_global_eur if total_equity_global_eur > 0 else 0
        roe_after = net_profit_after_net / total_equity_global_eur if total_equity_global_eur > 0 else 0

        # === 3. 盈亏平衡分析 ===
        # 设子公司: 一次性设立成本 SUBSIDIARY_SETUP, 但法人独立 → 只有 KSt+GewSt, 无 PE 争议
        # PE 成本: 每年 HGB_COMPLIANCE + 法律风险溢价
        annual_pe_overhead = hgb_cost + (pretax_profit_eur * 0.02)  # 2% risk premium
        breakeven = SUBSIDIARY_SETUP / (COMBINED_RATE - DIV_WHT) if (COMBINED_RATE - DIV_WHT) > 0 else float('inf')
        subsidiary_better = breakeven * 2  # rough threshold

        # === 4. 5年 NPV ===
        cashflows_before = []
        cashflows_after = []
        for year in range(5):
            profit_y = pretax_profit_eur * ((1 + growth_rate) ** year)
            wt_y = profit_y * dividend_payout_ratio * DIV_WHT
            cashflows_before.append(wt_y)

            kst_y = profit_y * (KST + SOLZ)
            gewst_y = profit_y * GEWST
            at_y = profit_y - kst_y - gewst_y
            dw_y = at_y * dividend_payout_ratio * DIV_WHT
            total_y = kst_y + gewst_y + dw_y + hgb_cost
            cashflows_after.append(total_y)

        def npv(cashflows, rate):
            return sum(cf / ((1 + rate) ** (i + 1)) for i, cf in enumerate(cashflows))

        npv_before = npv(cashflows_before, discount_rate)
        npv_after = npv(cashflows_after, discount_rate)
        npv_diff = npv_after - npv_before

        # 重组收益: 投入 SUBSIDIARY_SETUP, 之后每年按 subsidiary 税率
        subsidiary_annual_tax = pretax_profit_eur * (KST + SOLZ + GEWST)
        subsidiary_annual_wt = (pretax_profit_eur - subsidiary_annual_tax) * dividend_payout_ratio * DIV_WHT
        subsidiary_annual_total = subsidiary_annual_tax + subsidiary_annual_wt
        subsidiary_cashflows = []
        for year in range(5):
            profit_y = pretax_profit_eur * ((1 + growth_rate) ** year)
            kst_y = profit_y * (KST + SOLZ)
            gewst_y = profit_y * GEWST
            at_y = profit_y - kst_y - gewst_y
            dw_y = at_y * dividend_payout_ratio * DIV_WHT
            subsidiary_cashflows.append(kst_y + gewst_y + dw_y)

        npv_subsidiary = npv(subsidiary_cashflows, discount_rate)
        npv_restructure_benefit = npv_after - npv_subsidiary - SUBSIDIARY_SETUP

        # === 5. 综合建议 ===
        if pe_risk_level in ("low",):
            recommendation = (
                f"当前 PE 风险较低（{pretax_profit_eur:,.0f}€利润），维持现有经营安排即可。"
                f"每年合规成本仅 {hgb_cost:,}€。无需设立子公司。"
            )
        elif pe_risk_level == "medium":
            recommendation = (
                f"PE 风险中等。建议评估：设立德国子公司一次性成本 {SUBSIDIARY_SETUP:,}€，"
                f"但可消除 PE 不确定性。若德国利润超过 {subsidiary_better:,.0f}€，设子公司更划算。"
            )
        elif pe_risk_level == "high":
            recommendation = (
                f"PE 风险较高，强烈建议进行架构重组。5 年累计额外税负 NPV ≈ {npv_diff:,.0f}€。"
                f"设立子公司（{SUBSIDIARY_SETUP:,}€一次性成本）可在 {breakeven:,.0f}€ 利润时收回。"
            )
        else:  # constituted
            recommendation = (
                f"PE 已构成。5 年累计税负 NPV ≈ {npv_after:,.0f}€（vs PE 前 {npv_before:,.0f}€）。"
                f"建议立即履行 HGB 合规义务（年成本约 {hgb_cost:,}€），"
                f"同时评估：将 PE 转换为子公司可节约 {npv_restructure_benefit:,.0f}€（5年 NPV）。"
            )

        return FinancialImpactResult(
            etr_before_pe=round(etr_before * 100, 1),
            etr_after_pe=round(etr_after * 100, 1),
            etr_delta_pct=round((etr_after - etr_before) * 100, 1),
            roe_before_pe=round(roe_before * 100, 2),
            roe_after_pe=round(roe_after * 100, 2),
            roe_dilution_pct=round((roe_before - roe_after) * 100, 2),
            breakeven_profit_eur=round(breakeven, 0),
            subsidiary_better_above_eur=round(subsidiary_better, 0),
            npv_5yr_tax_pe_before_eur=round(npv_before, 0),
            npv_5yr_tax_pe_after_eur=round(npv_after, 0),
            npv_5yr_difference_eur=round(npv_diff, 0),
            npv_roi_if_restructure_eur=round(npv_restructure_benefit, 0),
            recommendation=recommendation,
        )
