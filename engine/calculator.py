"""中德关键税务参数对比速算 + PE税负暴露量化"""

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class TaxExposureResult:
    pre_tax_profit_eur: float
    pe_risk_level: str
    withholding_tax_rate: float
    withholding_tax_eur: float
    corporate_tax_rate: float
    corporate_tax_eur: float
    gewst_rate: float
    gewst_eur: float
    total_pe_tax_eur: float
    annual_tax_difference_eur: float
    hgb_compliance_cost_eur: float
    total_annual_exposure_eur: float
    breakdown: dict


class TaxExposureCalculator:
    """PE 构成前后的税务暴露量化计算器

    核心概念澄清：
    - PE 是分支机构 (branch)，不是子公司。PE 构成前，德国对该经营利润无征税权
      （中国就全球所得征税，中德协定第7条第1款：营业利润仅由居民国征税）。
    - PE 构成后，德国就 PE 归属利润征收企业所得税+营业税 (~30%)；
      中国在限额内给予境外税收抵免（中国企业所得税法第23条）。
    - 股息预提税仅适用于子公司利润汇回（协定第10条），PE 分支机构的利润转移
      不涉及股息预提税——这一点纠正了旧版模型的错误。
    """

    def calculate(self, pre_tax_profit_eur: float, pe_risk_level: str,
                  china_cit_rate: float = 0.25,
                  dividend_payout_ratio: float = 0.7) -> TaxExposureResult:
        """计算 PE 构成前后的税负差异

        - pre_tax_profit_eur: 德国 PE 归属的税前利润 (EUR)
        - pe_risk_level: low / medium / high / constituted
        - china_cit_rate: 中国企业所得税税率 (默认25%)
        - dividend_payout_ratio: 不适用于 PE 场景 (保留参数兼容性)
        """
        from engine.tax_constants import (KST, SOLZ_RATE, GEWST, DIV_WHT_DTA, HGB_COST)
        kst_solz = KST * (1 + SOLZ_RATE)
        gewst_rate = GEWST
        total_pe_rate = kst_solz + gewst_rate

        # === PE 前：德国无征税权 ===
        # 营业利润仅由中国征税（协定第7条第1款）
        # 德国税负 = 0（不涉及子公司股息预提税）
        german_tax_before = 0
        china_tax_before = pre_tax_profit_eur * china_cit_rate
        total_tax_before = german_tax_before + china_tax_before

        # === PE 后：德国征 PE 利润税 + 中国抵免 ===
        # 德国侧：KSt + SolZ + GewSt
        kst_eur = pre_tax_profit_eur * kst_solz
        gewst_eur = pre_tax_profit_eur * gewst_rate
        german_tax_after = kst_eur + gewst_eur

        # 中国侧：全球所得征税，境外已纳税额在限额内抵免
        # 抵免限额 = 中国应纳税额 × (境外所得 / 境内境外总所得)
        # 简化：假设德国 PE 利润为全部境外所得，抵免限额 = pre_tax_profit_eur * china_cit_rate
        china_tax_before_credit = pre_tax_profit_eur * china_cit_rate
        credit_limit = china_tax_before_credit
        actual_credit = min(german_tax_after, credit_limit)
        china_tax_after = max(0, china_tax_before_credit - actual_credit)

        total_tax_after = german_tax_after + china_tax_after

        # 合规成本
        compliance = HGB_COST.get(pe_risk_level, 0)

        # 税负差异 = PE 后总税负 - PE 前总税负
        tax_diff = total_tax_after - total_tax_before
        total_exposure = tax_diff + compliance

        return TaxExposureResult(
            pre_tax_profit_eur=pre_tax_profit_eur,
            pe_risk_level=pe_risk_level,
            withholding_tax_rate=DIV_WHT_DTA,
            withholding_tax_eur=0,  # PE 场景不涉及股息预提税
            corporate_tax_rate=round(total_pe_rate * 100, 1),
            corporate_tax_eur=round(german_tax_after, 0),
            gewst_rate=round(gewst_rate * 100, 1),
            gewst_eur=round(gewst_eur, 0),
            total_pe_tax_eur=round(total_tax_after, 0),
            annual_tax_difference_eur=round(tax_diff, 0),
            hgb_compliance_cost_eur=compliance,
            total_annual_exposure_eur=round(total_exposure, 0),
            breakdown={
                "german_kst_solz_eur": round(kst_eur, 0),
                "german_gewst_eur": round(gewst_eur, 0),
                "german_total_eur": round(german_tax_after, 0),
                "china_tax_before_credit_eur": round(china_tax_before_credit, 0),
                "china_foreign_credit_eur": round(actual_credit, 0),
                "china_tax_after_credit_eur": round(china_tax_after, 0),
                "total_tax_before_pe_eur": round(total_tax_before, 0),
                "total_tax_after_pe_eur": round(total_tax_after, 0),
                "effective_pe_rate": round(total_pe_rate * 100, 1),
            },
        )


class TaxParamCalculator:
    def __init__(self):
        with open(DATA_DIR / "tax_params.json", "r", encoding="utf-8") as f:
            self.params = json.load(f)

    def get_categories(self) -> list:
        return [c["name"] for c in self.params["categories"]]

    def get_params_by_category(self, category_name: str) -> list:
        for c in self.params["categories"]:
            if c["name"] == category_name:
                return c["params"]
        return []

    def get_all_params(self) -> list:
        return self.params["categories"]

    def search(self, keyword: str) -> list:
        results = []
        keyword_lower = keyword.lower()
        for cat in self.params["categories"]:
            for p in cat["params"]:
                if (
                    keyword_lower in p["name"].lower()
                    or keyword_lower in p.get("china", "").lower()
                    or keyword_lower in p.get("germany", "").lower()
                ):
                    results.append({"category": cat["name"], **p})
        return results

    def get_disclaimer(self) -> str:
        return self.params["meta"]["disclaimer"]

    def get_update_date(self) -> str:
        return self.params["meta"]["updated"]
