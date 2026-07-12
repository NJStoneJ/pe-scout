"""风险报告生成器"""

import json
from datetime import datetime
from pathlib import Path
from engine.decision_tree import PEResult

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_cases():
    with open(DATA_DIR / "cases.json", "r", encoding="utf-8") as f:
        return json.load(f)


class ReportGenerator:
    def __init__(self, result: PEResult, case_name: str = None):
        self.result = result
        self.case_name = case_name
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    def generate_markdown(self) -> str:
        r = self.result
        lines = []
        lines.append("# PE-Scout 常设机构风险分析报告")
        lines.append("")
        lines.append(f"**生成时间：** {self.generated_at}")
        lines.append(f"**风险等级：** {r.risk_label}")
        lines.append(f"**综合评分：** {r.total_score} 分")
        lines.append(f"**阈值参考：** 低风险≤8 | 中风险≤18 | 高风险<30 | ≥30已构成PE")
        lines.append("")

        lines.append("---")
        lines.append("## 各维度评分")
        group_names = {"fixed_place": "固定场所型PE", "construction": "工程/安装型PE", "agent": "代理人型PE"}
        for gid, gname in group_names.items():
            lines.append(f"- **{gname}：** {r.group_scores.get(gid, 0)} 分")
        lines.append("")

        lines.append("---")
        lines.append("## 结论")
        lines.append(r.summary)
        lines.append("")

        lines.append("## 行动建议")
        for i, advice in enumerate(r.advice, 1):
            lines.append(f"{i}. {advice}")
        lines.append("")

        lines.append("---")
        lines.append("## 相关法律依据")
        for ref in r.legal_refs:
            lines.append(f"- {ref}")
        lines.append("")

        lines.append("---")
        lines.append("## 答题记录")
        with open(DATA_DIR / "rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
        for qid_str in sorted(rules["questions"].keys(), key=int):
            qid = int(qid_str)
            q = rules["questions"][qid_str]
            ans = r.answers.get(qid)
            if ans is None:
                continue
            status = "是" if ans else "否"
            lines.append(f"- **Q{qid}** [{status}] {q['text'][:80]}...")
        lines.append("")

        lines.append("---")
        lines.append("*本报告由 PE-Scout 自动生成，仅供参考，不构成专业税务意见。具体跨境税务规划请咨询中德两地专业税务顾问。*")
        return "\n".join(lines)

    def generate_html(self) -> str:
        r = self.result
        group_names = {"fixed_place": "固定场所型PE", "construction": "工程/安装型PE", "agent": "代理人型PE"}

        score_bar_width = min(max(r.total_score / 40 * 100, 5), 100)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PE-Scout 风险分析报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Calibri, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
  .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
  .header {{ background: #142F4E; color: white; padding: 32px; border-radius: 12px 12px 0 0; }}
  .header h1 {{ font-size: 24px; font-weight: 300; margin-bottom: 8px; }}
  .header .time {{ opacity: 0.7; font-size: 13px; }}
  .risk-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-weight: 600; font-size: 18px; margin: 16px 0; background: {r.risk_color}; color: white; }}
  .score-bar-bg {{ background: #e2e8f0; border-radius: 8px; height: 12px; margin: 12px 0; }}
  .score-bar-fg {{ background: {r.risk_color}; border-radius: 8px; height: 12px; width: {score_bar_width}%; transition: width 0.6s; }}
  .card {{ background: white; border-radius: 12px; padding: 24px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .card h2 {{ font-size: 18px; font-weight: 600; color: #142F4E; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #E94D3A; }}
  .group-scores {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .group-score {{ flex: 1; min-width: 140px; background: #f1f5f9; border-radius: 8px; padding: 12px; text-align: center; }}
  .group-score .score {{ font-size: 24px; font-weight: 700; color: #142F4E; }}
  .group-score .label {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
  .advice-list {{ list-style: none; padding: 0; }}
  .advice-list li {{ padding: 8px 0; border-bottom: 1px solid #f1f5f9; counter-increment: step-counter; }}
  .advice-list li::before {{ content: counter(step-counter); display: inline-block; width: 22px; height: 22px; line-height: 22px; background: #142F4E; color: white; border-radius: 50%; text-align: center; font-size: 12px; margin-right: 10px; }}
  .ref-list {{ list-style: none; padding: 0; }}
  .ref-list li {{ padding: 4px 0; font-size: 13px; color: #475569; }}
  .answer-log {{ font-size: 13px; }}
  .answer-log .q-row {{ padding: 4px 0; border-bottom: 1px solid #f8fafc; }}
  .tag-yes {{ color: #DC2626; font-weight: 600; }}
  .tag-no {{ color: #22C55E; font-weight: 600; }}
  .footer {{ text-align: center; color: #94a3b8; font-size: 12px; padding: 20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>PE-Scout</h1>
    <p>中德常设机构（PE）风险分析报告</p>
    <div class="time">{self.generated_at}</div>
    <div class="risk-badge">{r.risk_label}</div>
    <div class="score-bar-bg"><div class="score-bar-fg"></div></div>
    <p style="margin-top:8px;opacity:0.85">综合评分：{r.total_score} 分（低≤8 | 中≤18 | 高&lt;30 | ≥30已构成PE）</p>
  </div>

  <div class="card">
    <h2>各维度评分</h2>
    <div class="group-scores">
"""
        for gid, gname in group_names.items():
            html += f"""      <div class="group-score">
        <div class="score">{r.group_scores.get(gid, 0)}</div>
        <div class="label">{gname}</div>
      </div>
"""
        html += """    </div>
  </div>

  <div class="card">
    <h2>结论</h2>
    <p>{}</p>
  </div>

  <div class="card">
    <h2>行动建议</h2>
    <ol class="advice-list">
""".format(r.summary)
        for advice in r.advice:
            html += f"      <li>{advice}</li>\n"
        html += """    </ol>
  </div>

  <div class="card">
    <h2>相关法律依据</h2>
    <ul class="ref-list">
"""
        for ref in r.legal_refs:
            html += f"      <li>{ref}</li>\n"
        html += """    </ul>
  </div>

  <div class="card">
    <h2>答题记录</h2>
    <div class="answer-log">
"""
        with open(DATA_DIR / "rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
        for qid_str in sorted(rules["questions"].keys(), key=int):
            qid = int(qid_str)
            q = rules["questions"][qid_str]
            ans = r.answers.get(qid)
            if ans is None:
                continue
            tag = '<span class="tag-yes">是</span>' if ans else '<span class="tag-no">否</span>'
            html += f'      <div class="q-row"><strong>Q{qid}</strong> [{tag}] {q["text"][:90]}...</div>\n'
        html += """    </div>
  </div>

  <div class="footer">
    PE-Scout 自动生成 · 仅供参考，不构成专业税务意见<br>
    具体跨境税务规划请咨询中德两地专业税务顾问
  </div>
</div>
</body>
</html>"""
        return html
