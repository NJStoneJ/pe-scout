"""PE-Scout 自动生成测试用例（AI 辅助生成，满足加分项要求）"""

import json
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.decision_tree import PEEngine
from engine.calculator import TaxParamCalculator
from utils.report import ReportGenerator
from utils.export import export_report_as_html


class TestPEEngine:
    @pytest.fixture
    def engine(self):
        return PEEngine()

    def test_intro(self, engine):
        intro = engine.get_intro()
        assert intro["total_questions"] == 15
        assert len(intro["groups"]) == 3

    def test_get_question_valid(self, engine):
        q = engine.get_question(1)
        assert q is not None
        assert "text" in q
        assert q["id"] == 1

    def test_get_question_invalid(self, engine):
        q = engine.get_question(999)
        assert q is None

    def test_skip_logic_fixed_place_no(self, engine):
        next_q = engine.get_next_question(1, False)
        assert next_q == 8

    def test_skip_logic_construction_no(self, engine):
        next_q = engine.get_next_question(8, False)
        assert next_q == 11

    def test_skip_logic_agent_no_to_end(self, engine):
        next_q = engine.get_next_question(11, False)
        assert next_q is None

    def test_all_no_low_risk(self, engine):
        answers = {i: False for i in range(1, 16)}
        r = engine.evaluate(answers)
        assert r.risk_level == "low"
        assert r.total_score == 0

    def test_all_yes_constituted(self, engine):
        answers = {i: True for i in range(1, 16)}
        r = engine.evaluate(answers)
        assert r.risk_level == "constituted"
        assert r.total_score == 57

    def test_case_1_low_risk(self, engine):
        with open(Path(__file__).parent.parent / "data" / "cases.json", "r", encoding="utf-8") as f:
            case = json.load(f)["cases"]["case_1"]
        r = engine.evaluate(case["answers"])
        assert r.risk_level == "low"

    def test_case_2_constituted(self, engine):
        with open(Path(__file__).parent.parent / "data" / "cases.json", "r", encoding="utf-8") as f:
            case = json.load(f)["cases"]["case_2"]
        r = engine.evaluate(case["answers"])
        assert r.risk_level == "constituted"

    def test_case_3_constituted(self, engine):
        with open(Path(__file__).parent.parent / "data" / "cases.json", "r", encoding="utf-8") as f:
            case = json.load(f)["cases"]["case_3"]
        r = engine.evaluate(case["answers"])
        assert r.risk_level == "constituted"

    def test_case_4_low_risk(self, engine):
        with open(Path(__file__).parent.parent / "data" / "cases.json", "r", encoding="utf-8") as f:
            case = json.load(f)["cases"]["case_4"]
        r = engine.evaluate(case["answers"])
        assert r.risk_level == "low"

    def test_string_keys(self, engine):
        answers = {"1": True, "2": True, "3": True, "4": False, "5": False,
                   "6": False, "8": True, "9": True, "10": False, "11": True, "12": False}
        r = engine.evaluate(answers)
        assert r.risk_level == "constituted"
        assert r.total_score == 43

    def test_get_all_cases(self, engine):
        cases = engine.get_all_cases()
        assert len(cases) == 4

    def test_load_case(self, engine):
        case = engine.load_case("case_1")
        assert case["name"] == "跨境电商仓储配送型"
        assert "answers" in case

    def test_load_invalid_case(self, engine):
        case = engine.load_case("nonexistent")
        assert case is None


class TestTaxParamCalculator:
    @pytest.fixture
    def calc(self):
        return TaxParamCalculator()

    def test_categories(self, calc):
        cats = calc.get_categories()
        assert len(cats) == 5

    def test_get_params_by_category(self, calc):
        params = calc.get_params_by_category("企业所得税")
        assert len(params) > 0

    def test_search_found(self, calc):
        results = calc.search("预提税")
        assert len(results) > 0

    def test_search_not_found(self, calc):
        results = calc.search("火星税")
        assert len(results) == 0

    def test_disclaimer(self, calc):
        assert "不构成专业税务意见" in calc.get_disclaimer()


class TestReportGenerator:
    @pytest.fixture
    def sample_result(self):
        engine = PEEngine()
        return engine.evaluate({1: True, 2: True, 3: True, 4: False, 5: False,
                                6: False, 8: True, 9: True, 10: False, 11: True, 12: False})

    def test_markdown_generation(self, sample_result):
        gen = ReportGenerator(sample_result)
        md = gen.generate_markdown()
        assert "PE-Scout" in md
        assert "已构成 PE" in md

    def test_html_generation(self, sample_result):
        gen = ReportGenerator(sample_result)
        html = gen.generate_html()
        assert "<!DOCTYPE html>" in html
        assert "PE-Scout" in html

    def test_export_html(self, sample_result, tmp_path):
        out = tmp_path / "report.html"
        html = export_report_as_html(sample_result, str(out))
        assert out.exists()
        assert "PE-Scout" in out.read_text(encoding="utf-8")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
