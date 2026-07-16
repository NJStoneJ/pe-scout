"""PE Analysis API — 规则引擎 + 税负量化 + HGB合规"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from engine.decision_tree import PEEngine, compute_radar_data
from engine.calculator import TaxExposureCalculator
from utils.hgb_checklist import get_checklist_for_result
from utils.report import ReportGenerator

router = APIRouter()


class PEAnalysisRequest(BaseModel):
    answers: dict[int, bool]
    profit_eur: Optional[float] = None
    payout_ratio: Optional[float] = 0.7


class PEAnalysisResponse(BaseModel):
    risk_level: str
    risk_label: str
    risk_color: str
    total_score: int
    group_scores: dict
    legal_refs: list
    summary: str
    advice: list
    radar: dict
    exposure: Optional[dict] = None
    checklist: Optional[dict] = None


@router.post("/analyze", response_model=PEAnalysisResponse)
async def analyze_pe(req: PEAnalysisRequest):
    engine = PEEngine()
    result = engine.evaluate(req.answers)
    radar = compute_radar_data(result)

    exposure = None
    if req.profit_eur:
        tec = TaxExposureCalculator()
        exp = tec.calculate(req.profit_eur, result.risk_level, req.payout_ratio or 0.7)
        exposure = {
            "pre_tax_profit_eur": exp.pre_tax_profit_eur,
            "withholding_tax_eur": exp.withholding_tax_eur,
            "total_pe_tax_eur": exp.total_pe_tax_eur,
            "annual_tax_difference_eur": exp.annual_tax_difference_eur,
            "hgb_compliance_cost_eur": exp.hgb_compliance_cost_eur,
            "total_annual_exposure_eur": exp.total_annual_exposure_eur,
            "corporate_tax_rate": exp.corporate_tax_rate,
            "breakdown": exp.breakdown,
        }

    cl = get_checklist_for_result(result)

    return PEAnalysisResponse(
        risk_level=result.risk_level,
        risk_label=result.risk_label,
        risk_color=result.risk_color,
        total_score=result.total_score,
        group_scores=result.group_scores,
        legal_refs=result.legal_refs,
        summary=result.summary,
        advice=result.advice,
        radar=radar,
        exposure=exposure,
        checklist={"level_label": cl["level_label"], "level_color": cl["level_color"],
                   "sections": cl["sections"]},
    )


@router.get("/cases")
async def get_cases():
    engine = PEEngine()
    return {"cases": engine.get_all_cases()}


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    engine = PEEngine()
    case = engine.load_case(case_id)
    if not case:
        raise HTTPException(404)
    return case
