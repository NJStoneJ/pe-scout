"""HGB 合规清单生成器"""

import json
from pathlib import Path
from engine.decision_tree import PEResult

DATA_DIR = Path(__file__).parent.parent / "data"


def load_checklist() -> dict:
    with open(DATA_DIR / "hgb_checklist.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_checklist_for_result(result: PEResult) -> dict:
    """Get HGB compliance checklist based on PE risk level."""
    data = load_checklist()
    level_data = data["levels"].get(result.risk_level, data["levels"]["low"])
    return {
        "level_label": level_data["label"],
        "level_color": level_data["color"],
        "sections": level_data["sections"],
        "risk_level": result.risk_level,
        "total_score": result.total_score,
    }
