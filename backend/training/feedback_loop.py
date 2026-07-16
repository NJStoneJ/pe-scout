"""RLHF 风格用户反馈收集 — 持续优化PE分析权重"""

import json, logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
FEEDBACK_FILE = Path(__file__).parent.parent.parent / "data" / "feedback_log.json"


class FeedbackCollector:
    """收集用户对PE分析结果的反馈，用于规则权重持续优化"""

    def __init__(self):
        self.feedback_log = self._load_feedback()

    def _load_feedback(self) -> list:
        if FEEDBACK_FILE.exists():
            try:
                with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def record(self, answers: dict, result: dict, user_rating: int,
               comment: str = "", correction: dict = None):
        """记录一条用户反馈"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "answers": {str(k): v for k, v in answers.items()},
            "risk_level": result.get("risk_level", ""),
            "total_score": result.get("total_score", 0),
            "user_rating": user_rating,  # 1-5
            "comment": comment,
            "correction": correction,
        }
        self.feedback_log.append(entry)

        # 每10条保存一次
        if len(self.feedback_log) % 10 == 0:
            self._save()

        logger.info(f"Feedback recorded: rating={user_rating}, risk={result.get('risk_level')}")

    def _save(self):
        try:
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(self.feedback_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save feedback: {e}")

    def get_stats(self) -> dict:
        """分析反馈数据统计"""
        if not self.feedback_log:
            return {"total": 0, "avg_rating": 0, "by_risk": {}}

        ratings = [f["user_rating"] for f in self.feedback_log]
        by_risk = {}
        for f in self.feedback_log:
            rl = f["risk_level"]
            if rl not in by_risk:
                by_risk[rl] = []
            by_risk[rl].append(f["user_rating"])

        return {
            "total": len(self.feedback_log),
            "avg_rating": round(sum(ratings) / len(ratings), 2),
            "by_risk": {k: round(sum(v) / len(v), 2) for k, v in by_risk.items()},
        }

    def export_training_data(self) -> list:
        """导出为RLHF训练格式"""
        return [
            {
                "prompt": f"PE风险分析: {f['answers']}",
                "chosen": f"风险等级: {f['risk_level']}, 评分: {f['total_score']}",
                "reward": f["user_rating"] / 5.0,
            }
            for f in self.feedback_log
        ]
