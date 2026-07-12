"""PE 决策树规则引擎 — 基于中德税收协定第5条 + 德国 AO §12-13"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class PEResult:
    risk_level: str
    risk_label: str
    risk_color: str
    risk_icon: str
    total_score: int
    group_scores: dict
    answers: dict
    legal_refs: list
    summary: str
    advice: list


class PEEngine:
    def __init__(self):
        with open(DATA_DIR / "rules.json", "r", encoding="utf-8") as f:
            self.rules = json.load(f)
        with open(DATA_DIR / "legal_basis.json", "r", encoding="utf-8") as f:
            self.legal = json.load(f)

    def get_intro(self) -> dict:
        return {
            "title": self.rules["meta"]["title"],
            "basis": self.rules["meta"]["basis"],
            "total_questions": self.rules["meta"]["total_questions"],
            "groups": [
                {
                    "id": g["id"],
                    "title": g["title"],
                    "desc": g["description"],
                    "count": len(g["questions"]),
                }
                for g in self.rules["groups"].values()
            ],
        }

    def get_question(self, qid: int) -> Optional[dict]:
        q = self.rules["questions"].get(str(qid))
        if q is None:
            return None
        return {
            "id": q["id"],
            "group": q["group"],
            "text": q["text"],
            "help": q.get("help", ""),
            "legal_ref": q.get("legal_ref", ""),
        }

    @staticmethod
    def _get_answer(answers: dict, qid: int) -> bool | None:
        """Get answer by question id, supporting both int and str keys."""
        if qid in answers:
            return answers[qid]
        if str(qid) in answers:
            return answers[str(qid)]
        return None

    def evaluate(self, answers: dict) -> PEResult:
        score = 0
        group_scores = {"fixed_place": 0, "construction": 0, "agent": 0}
        legal_refs = []

        for qid_str, q in self.rules["questions"].items():
            answer = self._get_answer(answers, int(qid_str))
            if answer is True:
                score += q["weight"]
                group_scores[q["group"]] += q["weight"]
                if q["weight"] > 0:
                    legal_refs.append(f"Q{q['id']} — {q['legal_ref']}")
            elif answer is False and q["weight"] < 0:
                pass

        thresholds = self.rules["risk_thresholds"]
        if score >= thresholds["constituted"]["min_score"]:
            level = thresholds["constituted"]
            risk_level = "constituted"
        elif score >= thresholds["high"]["max_score"]:
            level = thresholds["high"]
            risk_level = "high"
        elif score >= thresholds["medium"]["max_score"]:
            level = thresholds["medium"]
            risk_level = "medium"
        else:
            level = thresholds["low"]
            risk_level = "low"

        return PEResult(
            risk_level=risk_level,
            risk_label=level["label"],
            risk_color=level["color"],
            risk_icon=level["icon"],
            total_score=score,
            group_scores=group_scores,
            answers=answers,
            legal_refs=legal_refs,
            summary=level["summary"],
            advice=level["advice"],
        )

    def get_next_question(self, current_qid: int, answer: bool) -> Optional[int]:
        """Determine the next question based on skip logic."""
        q = self.rules["questions"].get(str(current_qid))
        if q is None:
            return None

        if not answer and "if_no_skip_to" in q:
            target = q["if_no_skip_to"]
            if target == "end":
                return None
            return target

        next_id = current_qid + 1
        if str(next_id) in self.rules["questions"]:
            return next_id
        return None

    def get_all_questions_count(self) -> int:
        return self.rules["meta"]["total_questions"]

    def get_group_for_question(self, qid: int) -> Optional[dict]:
        q = self.rules["questions"].get(str(qid))
        if q is None:
            return None
        return self.rules["groups"].get(q["group"])

    def load_case(self, case_id: str) -> Optional[dict]:
        with open(DATA_DIR / "cases.json", "r", encoding="utf-8") as f:
            cases = json.load(f)
        case = cases["cases"].get(case_id)
        if case is None:
            return None
        return {
            "name": case["name"],
            "subtitle": case["subtitle"],
            "industry": case["industry"],
            "profile": case["profile"],
            "answers": case["answers"],
            "expected": case["expected_result"],
            "analysis": case["analysis"],
        }

    def get_all_cases(self) -> list:
        with open(DATA_DIR / "cases.json", "r", encoding="utf-8") as f:
            cases = json.load(f)
        return [
            {"id": cid, "name": c["name"], "subtitle": c["subtitle"], "industry": c["industry"]}
            for cid, c in cases["cases"].items()
        ]
