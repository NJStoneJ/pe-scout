"""报告导出工具"""

from pathlib import Path
from engine.decision_tree import PEResult
from utils.report import ReportGenerator


def export_report_as_html(result: PEResult, output_path: str = None) -> str:
    gen = ReportGenerator(result)
    html = gen.generate_html()
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
    return html
