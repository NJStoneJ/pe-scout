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
    """PE 构成前后的税务暴露量化计算器"""

    def calculate(self, pre_tax_profit_eur: float, pe_risk_level: str,
                  dividend_payout_ratio: float = 0.7) -> TaxExposureResult:
        """计算 PE 构成前后的税负差异"""
        from engine.tax_constants import (KST, SOLZ_RATE, GEWST, DIV_WHT_DTA, HGB_COST)
        gewst_rate = GEWST
        kst_solz = KST * (1 + SOLZ_RATE)
        total_pe_rate = kst_solz + gewst_rate

        # PE 前：仅股息预提税（德国来源利润汇回中国）
        wt_eur = pre_tax_profit_eur * dividend_payout_ratio * DIV_WHT_DTA

        # PE 后：德国企业所得税 + 营业税 + 预提税（剩余利润汇回）
        kst_eur = pre_tax_profit_eur * kst_solz
        gewst_eur = pre_tax_profit_eur * gewst_rate
        after_tax_profit = pre_tax_profit_eur - kst_eur - gewst_eur
        div_wt_eur = after_tax_profit * dividend_payout_ratio * DIV_WHT_DTA
        total_pe_eur = kst_eur + gewst_eur + div_wt_eur

        # 合规成本
        compliance = HGB_COST.get(pe_risk_level, 0)

        # 总差异
        tax_diff = total_pe_eur - wt_eur
        total_exposure = tax_diff + compliance

        return TaxExposureResult(
            pre_tax_profit_eur=pre_tax_profit_eur,
            pe_risk_level=pe_risk_level,
            withholding_tax_rate=DIV_WHT_DTA,
            withholding_tax_eur=round(wt_eur, 0),
            corporate_tax_rate=round(total_pe_rate * 100, 1),
            corporate_tax_eur=round(total_pe_eur, 0),
            gewst_rate=round(gewst_rate * 100, 1),
            gewst_eur=round(gewst_eur, 0),
            total_pe_tax_eur=round(total_pe_eur, 0),
            annual_tax_difference_eur=round(tax_diff, 0),
            hgb_compliance_cost_eur=compliance,
            total_annual_exposure_eur=round(total_exposure, 0),
            breakdown={
                "kst_solz_eur": round(kst_eur, 0),
                "gewst_eur": round(gewst_eur, 0),
                "div_wt_after_pe_eur": round(div_wt_eur, 0),
                "div_wt_before_pe_eur": round(wt_eur, 0),
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
