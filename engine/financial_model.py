"""PE 税负影响财务模型 — ETR · ROE · 盈亏平衡 · 5年NPV"""

from dataclasses import dataclass
from engine.tax_constants import (
    KST, SOLZ, GEWST, COMBINED_CORPORATE_RATE as COMBINED_RATE,
    DIV_WHT_DTA as DIV_WHT, HGB_COST, SUBSIDIARY_SETUP_COST as SUBSIDIARY_SETUP
)


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
        china_cit_rate: float = 0.25,
        discount_rate: float = 0.08,
        growth_rate: float = 0.05,
    ) -> FinancialImpactResult:
        """运行完整财务影响分析

        PE 税负原理：
        - PE前：德国对该经营利润无征税权（协定第7条），仅中国征 CIT
        - PE后：德国征 PE 利润税 (~30%)，中国征 CIT 并给予境外税收抵免
        """

        # === 1. ETR 计算 ===
        # PE 前：德国无税 + 中国 CIT
        china_tax_before = pretax_profit_eur * china_cit_rate
        total_tax_before = china_tax_before
        etr_before = total_tax_before / pretax_profit_eur if pretax_profit_eur > 0 else 0

        # PE 后：德国 KSt+GewSt + 中国 CIT 扣减免税额
        german_tax = pretax_profit_eur * (KST + SOLZ + GEWST)
        credit_limit = pretax_profit_eur * china_cit_rate
        actual_credit = min(german_tax, credit_limit)
        china_tax_after = max(0, china_tax_before - actual_credit)
        total_tax_after = german_tax + china_tax_after
        etr_after = total_tax_after / pretax_profit_eur if pretax_profit_eur > 0 else 0

        # === 2. ROE 影响 ===
        hgb_cost = HGB_COST.get(pe_risk_level, 0)
        net_profit_before = pretax_profit_eur - total_tax_before
        net_profit_after = pretax_profit_eur - total_tax_after - hgb_cost

        roe_before = net_profit_before / total_equity_global_eur if total_equity_global_eur > 0 else 0
        roe_after = net_profit_after / total_equity_global_eur if total_equity_global_eur > 0 else 0

        # === 3. 盈亏平衡分析 ===
        breakeven = SUBSIDIARY_SETUP / (GEWST + 0.01) if GEWST > 0 else float('inf')
        subsidiary_better = breakeven * 3

        # === 4. 5年 NPV ===
        cashflows_before = []  # PE前: 只有中国 CIT
        cashflows_after = []   # PE后: 德国税 + 中国税(抵免后) + HGB

        for year in range(5):
            profit_y = pretax_profit_eur * ((1 + growth_rate) ** year)
            # PE前
            cf_before = profit_y * china_cit_rate
            cashflows_before.append(cf_before)
            # PE后: 德国税 + 中国税(抵免后) + 合规成本
            ger_tax_y = profit_y * (KST + SOLZ + GEWST)
            credit_y = min(ger_tax_y, profit_y * china_cit_rate)
            chn_tax_y = max(0, profit_y * china_cit_rate - credit_y)
            cashflows_after.append(ger_tax_y + chn_tax_y + hgb_cost)

        def npv(cashflows, rate):
            return sum(cf / ((1 + rate) ** (i + 1)) for i, cf in enumerate(cashflows))

        npv_before = npv(cashflows_before, discount_rate)
        npv_after = npv(cashflows_after, discount_rate)
        npv_diff = npv_after - npv_before

        # 子公司场景: 德国子公司在德国缴税 + 股息预提税汇回中国
        subsidiary_cashflows = []
        for year in range(5):
            profit_y = pretax_profit_eur * ((1 + growth_rate) ** year)
            ger_sub_tax = profit_y * (KST + SOLZ + GEWST)
            after_tax_profit = profit_y - ger_sub_tax
            div_wt = after_tax_profit * 0.7 * DIV_WHT  # 股息汇回
            subsidiary_cashflows.append(ger_sub_tax + div_wt)

        npv_subsidiary = npv(subsidiary_cashflows, discount_rate)
        npv_restructure_benefit = npv_after - npv_subsidiary - SUBSIDIARY_SETUP

        # === 5. 综合建议 ===
        if pe_risk_level in ("low",):
            recommendation = (
                f"当前 PE 风险较低（{pretax_profit_eur:,.0f}€利润），无德国纳税义务。"
                f"HGB 合规成本仅 {hgb_cost:,}€/年。建议维持现有安排，定期复查。"
            )
        elif pe_risk_level == "medium":
            recommendation = (
                f"PE 风险中等。建议委托中德税务顾问进行正式 PE 评估。如果后续业务扩大，"
                f"提前规划架构（PE vs 子公司）可避免被动局面。当前无需立即行动。"
            )
        elif pe_risk_level == "high":
            recommendation = (
                f"PE 风险较高。PE 构成将触发德国税负约 €{german_tax:,.0f}/年"
                f"（中方境外抵免后净增约 €{total_tax_after - total_tax_before:,.0f}/年）。"
                f"设立子公司一次性成本 €{SUBSIDIARY_SETUP:,}，可在约 {subsidiary_better:,.0f}€ 利润时收回。"
            )
        else:  # constituted
            recommendation = (
                f"PE 已构成。双边总有效税率 {etr_after*100:.1f}%（德国 {KST*100+SOLZ*100+GEWST*100:.0f}%"
                f" + 中方 CIT {china_cit_rate*100:.0f}% 减境外抵免）。"
                f"5 年累计税负 NPV €{npv_after:,.0f}（vs 无 PE 情景 €{npv_before:,.0f}）。"
                f"建议：立即履行 HGB 合规义务（年成本约 €{hgb_cost:,}），"
                f"同时评估转子公司方案（5年 NPV 收益约 €{npv_restructure_benefit:,.0f}）。"
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
