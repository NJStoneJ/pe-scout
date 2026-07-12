"""中德关键税务参数对比速算"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


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
