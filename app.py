"""PE-Scout: 中德常设机构风险分析助手 — Streamlit 主应用"""

import json
import sys
from pathlib import Path

# Add project root to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from engine.decision_tree import PEEngine
from engine.calculator import TaxParamCalculator
from utils.report import ReportGenerator

st.set_page_config(
    page_title="PE-Scout · 中德常设机构风险分析",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
  /* Brand colors */
  :root {
    --navy: #142F4E;
    --coral: #E94D3A;
    --blue: #5B9AD5;
    --grey-light: #F5F6FA;
  }
  .main-header {
    background: linear-gradient(135deg, #142F4E 0%, #1a3d64 100%);
    color: white;
    padding: 28px 32px;
    border-radius: 12px;
    margin-bottom: 24px;
  }
  .main-header h1 {
    font-size: 28px;
    font-weight: 300;
    margin: 0;
    letter-spacing: 0.5px;
  }
  .main-header p {
    opacity: 0.8;
    margin: 6px 0 0 0;
    font-size: 14px;
  }
  .question-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #142F4E;
    border-radius: 8px;
    padding: 20px 24px;
    margin: 12px 0;
  }
  .question-card h3 {
    color: #142F4E;
    font-size: 16px;
    margin: 0 0 8px 0;
  }
  .question-card .legal-ref {
    font-size: 12px;
    color: #64748b;
    margin-top: 8px;
    font-style: italic;
  }
  .group-header {
    background: #f1f5f9;
    padding: 10px 16px;
    border-radius: 6px;
    margin: 20px 0 8px 0;
    font-weight: 600;
    color: #142F4E;
  }
  .risk-card {
    border-radius: 12px;
    padding: 24px;
    color: white;
    margin: 16px 0;
  }
  .metric-box {
    background: white;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .metric-box .value {
    font-size: 28px;
    font-weight: 700;
    color: #142F4E;
  }
  .metric-box .label {
    font-size: 12px;
    color: #64748b;
    margin-top: 4px;
  }
  .advice-item {
    padding: 8px 0;
    border-bottom: 1px solid #f1f5f9;
  }
  .footer-note {
    text-align: center;
    color: #94a3b8;
    font-size: 12px;
    padding: 24px;
  }
  /* Progress bar */
  div[data-testid="stProgress"] > div > div > div {
    background-color: #142F4E;
    background-image: none;
  }
</style>
""", unsafe_allow_html=True)


def init_session():
    defaults = {
        "page": "welcome",
        "answers": {},
        "current_q": 1,
        "completed": False,
        "result": None,
        "case_loaded": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_assessment():
    st.session_state.answers = {}
    st.session_state.current_q = 1
    st.session_state.completed = False
    st.session_state.result = None
    st.session_state.case_loaded = None


def render_welcome(engine):
    st.markdown('<div class="main-header"><h1>PE-Scout</h1><p>中德常设机构风险分析助手 · Betriebstätten-Risikoanalyse</p></div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("""
        ### 关于本工具
        本工具基于**《中德税收协定》(2014) 第5条**、**OECD 范本注释 (2017)** 和**德国租税通则 (AO) §12-13**，\
        通过 **15 道法律要件问答**，帮助出海德国企业快速评估是否构成德国**常设机构（PE）** 风险。

        ### 为什么 PE 风险至关重要？
        - **PE 构成前**：中国企业仅就来源于德国的特定收入纳税（预提税）
        - **PE 构成后**：德国有权对 PE 归属利润按约 30% 征收企业所得税 + 营业税（GewSt）
        - **合规成本激增**：触发 **HGB §238** 德国商法典账簿记录义务和年报编制义务
        - **历史追溯风险**：PE 认定可追溯至构成之日，产生多年补税+罚息
        """)

        st.info(
            "📋 **评估流程**：约 5-7 分钟完成 15 道法律要件判断 → 即时生成风险报告（含法条引用 + 行动建议）")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("开始风险评估", type="primary", use_container_width=True):
                st.session_state.page = "assessment"
                st.rerun()
        with c2:
            if st.button("加载虚拟案例演示", use_container_width=True):
                st.session_state.page = "cases"
                st.rerun()

    with col2:
        st.markdown("### 评估框架")
        st.markdown("""
        <div style="background:#f8fafc;border-radius:8px;padding:16px;font-size:13px;">
        <b>固定场所型 PE</b>（协定第5条第1-4款）<br>
        <span style="color:#64748b">营业场所 + 固定性 + 持续性 − 辅助豁免</span><br><br>
        <b>工程/安装型 PE</b>（协定第5条第3款）<br>
        <span style="color:#64748b">建筑/安装工程持续 > 12个月</span><br><br>
        <b>代理人型 PE</b>（协定第5条第5-6款）<br>
        <span style="color:#64748b">非独立代理人 + 经常缔约权</span>
        </div>
        """, unsafe_allow_html=True)


def render_assessment(engine):
    st.markdown('<div class="main-header"><h1>PE 风险评估</h1><p>逐项回答法律要件问题，系统自动判定风险等级</p></div>',
                unsafe_allow_html=True)

    if st.button("← 返回首页"):
        reset_assessment()
        st.session_state.page = "welcome"
        st.rerun()

    total_q = engine.get_all_questions_count()
    answered = len(st.session_state.answers)
    progress = answered / total_q
    st.progress(progress, text=f"完成进度：{answered}/{total_q}（{int(progress*100)}%）")

    if st.session_state.completed:
        render_result(engine)
        return

    qid = st.session_state.current_q
    q = engine.get_question(qid)

    if q is None:
        st.session_state.completed = True
        st.session_state.result = engine.evaluate(st.session_state.answers)
        st.rerun()
        return

    group = engine.get_group_for_question(qid)
    if group and (qid == 1 or engine.get_group_for_question(qid - 1) != group or
                  (qid - 1) in st.session_state.answers and engine.get_group_for_question(qid - 1) is None):
        st.markdown(f'<div class="group-header">{group["title"]}</div>', unsafe_allow_html=True)
        with st.expander("查看法律依据", expanded=False):
            st.caption(group["legal_basis"])

    st.markdown(f"""
    <div class="question-card">
      <h3>Q{qid}. {q["text"]}</h3>
      <p style="color:#64748b;font-size:13px;">{q.get("help", "")}</p>
      <p class="legal-ref">{q.get("legal_ref", "")}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("是", type="primary", use_container_width=True, key=f"yes_{qid}"):
            st.session_state.answers[qid] = True
            next_q = engine.get_next_question(qid, True)
            st.session_state.current_q = next_q if next_q else -1
            if next_q is None:
                st.session_state.completed = True
                st.session_state.result = engine.evaluate(st.session_state.answers)
            st.rerun()
    with col2:
        if st.button("否", use_container_width=True, key=f"no_{qid}"):
            st.session_state.answers[qid] = False
            next_q = engine.get_next_question(qid, False)
            st.session_state.current_q = next_q if next_q else -1
            if next_q is None:
                st.session_state.completed = True
                st.session_state.result = engine.evaluate(st.session_state.answers)
            st.rerun()

    st.caption(f"当前第 {answered + 1}/{total_q} 题（部分题目根据回答逻辑跳转）")


def render_result(engine):
    r = st.session_state.result

    st.balloons()

    color_map = {"low": "#22C55E", "medium": "#F59E0B", "high": "#EF4444", "constituted": "#DC2626"}
    st.markdown(f"""
    <div class="risk-card" style="background:{r.risk_color};">
      <h2 style="margin:0;font-weight:300;">分析结果：{r.risk_label}</h2>
      <p style="margin-top:8px;opacity:0.9;">综合风险评分：{r.total_score} 分</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    scores = [
        ("固定场所型PE", r.group_scores.get("fixed_place", 0)),
        ("工程/安装型PE", r.group_scores.get("construction", 0)),
        ("代理人型PE", r.group_scores.get("agent", 0)),
        ("总分", r.total_score),
    ]
    for col, (label, val) in zip([col1, col2, col3, col4], scores):
        with col:
            st.markdown(f"""
            <div class="metric-box">
              <div class="value">{val}</div>
              <div class="label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    tab1, tab2, tab3 = st.tabs(["结论与建议", "法条引用", "答题记录"])

    with tab1:
        st.markdown("### 分析结论")
        st.info(r.summary)
        st.markdown("### 行动建议")
        for i, adv in enumerate(r.advice, 1):
            st.markdown(f"**{i}.** {adv}")

    with tab2:
        st.markdown("### 相关法律依据")
        for ref in r.legal_refs:
            st.markdown(f"- {ref}")

    with tab3:
        with open(Path(__file__).parent / "data" / "rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
        for qid_str in sorted(rules["questions"].keys(), key=int):
            qid = int(qid_str)
            qdata = rules["questions"][qid_str]
            ans = r.answers.get(qid)
            if ans is None:
                continue
            status = "✅ 是" if ans else "❌ 否"
            st.caption(f"**Q{qid}** [{status}] — {qdata['text'][:100]}")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        gen = ReportGenerator(r)
        html = gen.generate_html()
        st.download_button(
            label="下载 HTML 报告",
            data=html,
            file_name=f"PE-Scout_风险报告_{r.risk_level}.html",
            mime="text/html",
            use_container_width=True,
        )
    with col2:
        if st.button("重新评估", use_container_width=True):
            reset_assessment()
            st.session_state.page = "assessment"
            st.rerun()
    with col3:
        if st.button("回到首页", use_container_width=True):
            reset_assessment()
            st.session_state.page = "welcome"
            st.rerun()


def render_tax_params(calc):
    st.markdown('<div class="main-header"><h1>中德税务参数速查</h1><p>关键税制参数对比 · 中国 vs 德国</p></div>',
                unsafe_allow_html=True)

    if st.button("← 返回首页"):
        reset_assessment()
        st.session_state.page = "welcome"
        st.rerun()

    keyword = st.text_input("关键词搜索（如：预提税、折旧、HGB）", placeholder="输入搜索词...")

    if keyword:
        results = calc.search(keyword)
        if results:
            st.markdown(f"找到 **{len(results)}** 条相关结果：")
            for r in results:
                with st.expander(f"{r['name']}（{r['category']}）", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**🇨🇳 中国**")
                        st.markdown(r["china"])
                    with col2:
                        st.markdown(f"**🇩🇪 德国**")
                        st.markdown(r["germany"])
        else:
            st.warning("未找到匹配结果，请尝试其他关键词。")
        st.divider()

    for cat in calc.get_all_params():
        with st.expander(cat["name"], expanded=False):
            for p in cat["params"]:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{p['name']}**")
                    st.markdown(p["china"])
                with col2:
                    st.markdown("&nbsp;")
                    st.markdown(p["germany"])
                st.divider()

    st.caption(calc.get_disclaimer())


def render_cases(engine):
    st.markdown('<div class="main-header"><h1>虚拟案例演示库</h1><p>预设典型出海德国场景，一键加载查看 PE 分析结果</p></div>',
                unsafe_allow_html=True)

    if st.button("← 返回首页"):
        reset_assessment()
        st.session_state.page = "welcome"
        st.rerun()

    st.caption("所有案例均为模拟数据，不涉及任何真实企业信息。")

    cases = engine.get_all_cases()

    for c in cases:
        with st.expander(f"**{c['name']}** — {c['subtitle']}（{c['industry']}）", expanded=False):
            case_data = engine.load_case(c["id"])
            if case_data is None:
                continue

            profile = case_data["profile"]
            st.markdown("#### 企业背景")
            st.markdown(f"""
            - **背景**：{profile['background']}
            - **德国业务活动**：{profile['german_activities']}
            - **德国年收入**：{profile['revenue_eur']}
            - **德国员工数**：{profile['employees_de']}
            """)

            st.markdown(f"#### 分析结论")
            if st.button(f"加载此案例进行完整 PE 分析 →", key=f"load_{c['id']}", type="primary"):
                st.session_state.answers = case_data["answers"]
                st.session_state.completed = True
                st.session_state.result = engine.evaluate(case_data["answers"])
                st.session_state.case_loaded = c["id"]
                st.session_state.page = "assessment"
                st.rerun()

            st.info(f"**裁判分析**：{case_data['analysis']}")


def main():
    init_session()

    with st.sidebar:
        st.markdown("## PE-Scout")
        st.markdown("*中德常设机构风险分析*")
        st.divider()

        pages = {
            "welcome": "🏠 首页",
            "assessment": "🔍 PE 风险评估",
            "tax_params": "📊 中德税务参数速查",
            "cases": "📋 虚拟案例库",
        }

        for page_id, label in pages.items():
            if st.button(label, use_container_width=True,
                         type="primary" if st.session_state.page == page_id else "secondary"):
                if page_id == "assessment" and st.session_state.page != "assessment":
                    reset_assessment()
                st.session_state.page = page_id
                st.rerun()

        st.divider()
        st.caption("基于中德税收协定第5条 + 德国 AO §12-13")
        st.caption("v1.0 · 2026.07")
        st.caption("仅供参考，不构成专业税务意见")

    engine = PEEngine()
    calc = TaxParamCalculator()

    if st.session_state.page == "welcome":
        render_welcome(engine)
    elif st.session_state.page == "assessment":
        render_assessment(engine)
    elif st.session_state.page == "tax_params":
        render_tax_params(calc)
    elif st.session_state.page == "cases":
        render_cases(engine)

    st.markdown('<div class="footer-note">PE-Scout v1.0 · 仅供参考，不构成专业税务意见 · © 2026</div>',
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
