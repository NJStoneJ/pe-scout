"""PE-Scout v3.0: 中德常设机构风险分析助手 — 黑绿德勤主题 + 对比 + 自由文本 + What-If"""

import json, sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.graph_objects as go

from engine.decision_tree import PEEngine, compute_radar_data
from engine.calculator import TaxParamCalculator, TaxExposureCalculator
from engine.financial_model import FinancialModel
from utils.report import ReportGenerator
from utils.hgb_checklist import get_checklist_for_result
from utils.nlp_extractor import extract_answers, extract_profile, get_extraction_summary
from backend.agents.pe_agent import PEAgent
from backend.knowledge_graph.pe_graph import PEGraphBuilder
from backend.rag.document_store import DocumentStore
from backend.training.feedback_loop import FeedbackCollector

st.set_page_config(page_title="PE-Scout · 中德PE风险分析", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")

# ============================================================
# DELOITTE BLACK+GREEN THEME
# ============================================================
GREEN = "#86BC25"
GREEN_LIGHT = "#A0D939"
GREEN_DIM = "#5A8A1A"
BG = "#0D0D0D"
BG_CARD = "#1A1A1A"
BG_INPUT = "#252525"
TEXT = "#E0E0E0"
TEXT_MUTED = "#999999"
TEXT_DIM = "#666666"
RED = "#FF4444"
ORANGE = "#F59E0B"
YELLOW = "#FFD700"

CSS = f"""
<style>
  .stApp {{ background: {BG}; }}
  section[data-testid="stSidebar"] {{ background: #0A0A0A; }}
  section[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}
  .stButton>button {{
    background: {BG_CARD}; color: {GREEN}; border: 1px solid {GREEN};
    border-radius: 6px; font-family: 'Segoe UI', sans-serif; transition: all 0.2s;
  }}
  .stButton>button:hover {{ background: {GREEN}; color: #000 !important; border-color: {GREEN}; }}
  .main-header {{
    background: linear-gradient(135deg, {GREEN_DIM} 0%, {BG_CARD} 100%);
    border-left: 4px solid {GREEN}; color: {TEXT}; padding: 28px 32px;
    border-radius: 8px; margin-bottom: 24px;
  }}
  .main-header h1 {{ font-size: 28px; font-weight: 400; margin: 0; color: {GREEN_LIGHT}; }}
  .main-header p {{ opacity: 0.8; margin: 6px 0 0 0; font-size: 14px; }}
  .card {{
    background: {BG_CARD}; border: 1px solid #2A2A2A; border-radius: 8px;
    padding: 20px; margin: 10px 0;
  }}
  .card:hover {{ border-color: {GREEN_DIM}; }}
  .question-card {{
    background: {BG_CARD}; border: 1px solid #2A2A2A; border-left: 4px solid {GREEN};
    border-radius: 8px; padding: 20px 24px; margin: 12px 0;
  }}
  .question-card h3 {{ color: {GREEN_LIGHT}; font-size: 16px; margin: 0 0 8px 0; }}
  .question-card .legal-ref {{ font-size: 12px; color: {TEXT_MUTED}; margin-top: 8px; }}
  .group-header {{
    background: #111; padding: 10px 16px; border-radius: 6px;
    margin: 20px 0 8px 0; font-weight: 600; color: {GREEN};
    border-left: 3px solid {GREEN};
  }}
  .risk-badge {{
    border-radius: 8px; padding: 24px; color: white; margin: 16px 0;
  }}
  .metric-box {{
    background: {BG_INPUT}; border-radius: 8px; padding: 16px; text-align: center;
    border: 1px solid #2A2A2A;
  }}
  .metric-box .value {{ font-size: 28px; font-weight: 700; color: {GREEN_LIGHT}; }}
  .metric-box .label {{ font-size: 11px; color: {TEXT_MUTED}; margin-top: 4px; }}
  .big-number {{
    font-size: 48px; font-weight: 700; text-align: center; padding: 16px;
    font-family: 'Segoe UI', sans-serif;
  }}
  .contrast-diff {{ color: {RED}; font-weight: 700; }}
  .contrast-same {{ color: {TEXT_MUTED}; }}
  .cmp-left {{ border-right: 1px solid #2A2A2A; padding-right: 16px; }}
  .cmp-right {{ padding-left: 16px; }}
  .footer-note {{ text-align: center; color: {TEXT_DIM}; font-size: 12px; padding: 24px; }}
  div[data-testid="stProgress"] > div > div > div {{ background: {GREEN}; }}
  div.stSlider > div > div > div > div {{ background: {GREEN}; }}
  .stTextArea textarea {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid #333; }}
  .stTextInput input {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid #333; }}
  .stNumberInput input {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid #333; }}
  .stSelectbox > div > div {{ background: {BG_INPUT}; color: {TEXT}; }}
  .stTabs [data-baseweb="tab-list"] {{ gap: 2px; background: {BG}; }}
  .stTabs [data-baseweb="tab"] {{
    background: {BG_CARD}; color: {TEXT_MUTED}; border-radius: 6px 6px 0 0;
    padding: 10px 16px; border: 1px solid #2A2A2A;
  }}
  .stTabs [aria-selected="true"] {{ background: {GREEN_DIM}; color: white !important; }}
  .stExpander {{ background: {BG_CARD}; border: 1px solid #2A2A2A; border-radius: 8px; }}
  .stExpander:hover {{ border-color: {GREEN_DIM}; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def init_session():
    for k, v in {"page": "welcome", "answers": {}, "answers2": {}, "current_q": 1,
                 "completed": False, "completed2": False, "result": None, "result2": None,
                 "case_loaded": None, "whatif_answers": {}, "free_text": ""}.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_assessment():
    for k in ["answers", "answers2", "current_q", "completed", "completed2",
              "result", "result2", "case_loaded", "whatif_answers", "free_text"]:
        st.session_state[k] = {} if "answers" in k else (False if "completed" in k else (
            None if "result" in k or "case" in k else (1 if k == "current_q" else "")))


def risk_badge_html(label, color, score=None):
    score_str = f"<p style='margin-top:8px;opacity:0.85;'>综合风险评分：{score} 分</p>" if score is not None else ""
    return f"<div class='risk-badge' style='background:{color};'><h2 style='margin:0;font-weight:300;'>{label}</h2>{score_str}</div>"


# ============================================================
# WELCOME
# ============================================================
def render_welcome(engine):
    st.markdown('<div class="main-header"><h1>PE-Scout</h1><p>中德常设机构风险分析助手 v3.0 · Betriebstätten-Risikoanalyse</p></div>',
                unsafe_allow_html=True)
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"""
        <div class="card">
        <h3 style="color:{GREEN_LIGHT};">核心功能</h3>
        <p style="color:{TEXT_MUTED};font-size:14px;">
        基于<strong>《中德税收协定》第5条 + 德国AO §12-13 + BEPS 行动7</strong>，
        提供PE风险<strong>智能识别 → 税负量化 → 合规清单 → What-If推演</strong>全链路分析。
        </p>
        <ul style="color:{TEXT};font-size:13px;line-height:2;">
        <li><strong>自由文本模式</strong> — 粘贴业务描述，AI自动提取法律要件</li>
        <li><strong>15题精准判定</strong> — 三组PE分类 + 四档风险等级</li>
        <li><strong>税负暴露量化</strong> — PE前后税负差异€金额计算</li>
        <li><strong>HGB合规清单</strong> — 按风险等级自动生成德国商法典待办</li>
        <li><strong>六维雷达图</strong> — 风险画像可视化</li>
        <li><strong>双场景对比</strong> — 经营安排调整前后对比分析</li>
        <li><strong>What-If推演</strong> — 拖动关键变量实时看风险变化</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("开始风险评估", type="primary", use_container_width=True, key="btn_start"):
                st.session_state.page = "assessment"; st.rerun()
        with c2:
            if st.button("自由文本输入", use_container_width=True, key="btn_free"):
                st.session_state.page = "free_text"; st.rerun()
        with c3:
            if st.button("加载案例演示", use_container_width=True, key="btn_cases"):
                st.session_state.page = "cases"; st.rerun()
    with col2:
        st.markdown(f"""
        <div class="card">
        <h3 style="color:{GREEN_LIGHT};">评估框架</h3>
        <div style="color:{TEXT};font-size:13px;line-height:2;">
        <p><strong style="color:{GREEN};">固定场所型 PE</strong><br>
        <span style="color:{TEXT_MUTED};">营业场所 + 固定性 + 持续性 − 辅助豁免</span></p>
        <p><strong style="color:{GREEN};">工程/安装型 PE</strong><br>
        <span style="color:{TEXT_MUTED};">建筑/安装工程持续 > 12个月</span></p>
        <p><strong style="color:{GREEN};">代理人型 PE</strong><br>
        <span style="color:{TEXT_MUTED};">非独立代理人 + 经常缔约权</span></p>
        </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="border-left:3px solid {GREEN};">
        <p style="color:{TEXT_MUTED};font-size:12px;margin:0;">
        <strong style="color:{GREEN};">PE构成前：</strong>德国无征税权（协定第7条），仅中国CIT<br>
        <strong style="color:{RED};">PE构成后：</strong>企业所得税 ≈ 30% + HGB合规成本
        </p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# ASSESSMENT (QUESTIONNAIRE)
# ============================================================
def render_assessment(engine):
    st.markdown('<div class="main-header"><h1>PE 风险评估</h1><p>逐项回答15道法律要件问题 · 系统自动判定风险等级</p></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([1, 8])
    with c1:
        if st.button("← 返回首页", key="back_q"):
            reset_assessment(); st.session_state.page = "welcome"; st.rerun()

    if st.session_state.completed:
        render_result(engine, st.session_state.result)
        return

    total_q = engine.get_all_questions_count()
    answered = len(st.session_state.answers)
    st.progress(answered / total_q, text=f"进度：{answered}/{total_q} 题")

    qid = st.session_state.current_q
    q = engine.get_question(qid)
    if q is None:
        st.session_state.completed = True
        st.session_state.result = engine.evaluate(st.session_state.answers)
        st.rerun()
        return

    group = engine.get_group_for_question(qid)
    prev_group = engine.get_group_for_question(qid - 1) if qid > 1 else None
    if group and (qid == 1 or prev_group != group):
        st.markdown(f'<div class="group-header">{group["title"]}</div>', unsafe_allow_html=True)
        with st.expander("法律依据", expanded=False):
            st.caption(group["legal_basis"])

    st.markdown(f"""
    <div class="question-card">
      <h3>Q{qid}. {q["text"]}</h3>
      <p style="color:{TEXT_MUTED};font-size:13px;">{q.get("help", "")}</p>
      <p class="legal-ref">{q.get("legal_ref", "")}</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        if st.button("是 ✓", type="primary", use_container_width=True, key=f"yes_{qid}"):
            st.session_state.answers[qid] = True
            nxt = engine.get_next_question(qid, True)
            st.session_state.current_q = nxt if nxt else -1
            if nxt is None:
                st.session_state.completed = True
                st.session_state.result = engine.evaluate(st.session_state.answers)
            st.rerun()
    with c2:
        if st.button("否 ✗", use_container_width=True, key=f"no_{qid}"):
            st.session_state.answers[qid] = False
            nxt = engine.get_next_question(qid, False)
            st.session_state.current_q = nxt if nxt else -1
            if nxt is None:
                st.session_state.completed = True
                st.session_state.result = engine.evaluate(st.session_state.answers)
            st.rerun()


# ============================================================
# FREE TEXT MODE (E)
# ============================================================
def render_free_text(engine):
    st.markdown('<div class="main-header"><h1>自由文本输入</h1><p>粘贴企业德国业务描述 · AI自动提取PE风险要素</p></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([1, 8])
    with c1:
        if st.button("← 返回首页", key="back_ft"):
            reset_assessment(); st.session_state.page = "welcome"; st.rerun()

    st.markdown(f"""
    <div class="card" style="border-left:3px solid {GREEN};margin-bottom:16px;">
    <p style="color:{TEXT_MUTED};font-size:13px;margin:0;">
    在下方描述贵司在德国的业务活动情况。尽可能包含：<strong style="color:{GREEN};">办公场所类型和租赁期限、
    人员数量和职能、是否签订合同、工程项目的性质和工期、业务活动的核心性质</strong>。
    系统将自动识别15个PE法律要件。
    </p>
    </div>
    """, unsafe_allow_html=True)

    default_text = st.session_state.get("free_text", "")
    text = st.text_area(
        "德国业务活动描述",
        value=default_text,
        placeholder="例如：我司是深圳跨境电商企业，在汉堡租赁了2000平仓库用于存储和发货，租约3年，已运营18个月。仓库有5名当地员工负责分拣打包，不设展示厅，德国消费者不可现场选购。年销售额约800万欧元...",
        height=180,
    )

    col1, col2, col3 = st.columns([2, 1, 4])
    with col1:
        if st.button("🔍 智能提取PE要素", type="primary", use_container_width=True):
            if len(text.strip()) < 30:
                st.warning("请输入至少30字的业务描述")
            else:
                st.session_state.free_text = text
                extracted = extract_answers(text)
                profile = extract_profile(text)
                st.session_state.answers = extracted
                st.session_state.extraction_summary = get_extraction_summary(extracted, profile)
                st.session_state.extraction_done = True
                st.rerun()
    with col2:
        if st.button("清空", use_container_width=True):
            st.session_state.free_text = ""
            st.session_state.answers = {}
            st.session_state.extraction_done = False
            st.rerun()

    if st.session_state.get("extraction_done"):
        st.success(st.session_state.get("extraction_summary", "提取完成"))
        answered = len(st.session_state.answers)
        if answered > 0:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认并查看结果", type="primary", use_container_width=True):
                    st.session_state.completed = True
                    st.session_state.result = engine.evaluate(st.session_state.answers)
                    st.session_state.page = "assessment"
                    st.rerun()
            with c2:
                if st.button("📝 进入逐题补充/修正", use_container_width=True):
                    st.session_state.current_q = 1
                    st.session_state.page = "assessment"
                    st.rerun()
        else:
            st.warning("未能从文本中提取到明确的PE要素，建议使用逐题问答模式。")

    with st.expander("预览已识别的答案", expanded=False):
        if st.session_state.answers:
            with open(Path(__file__).parent / "data" / "rules.json", "r", encoding="utf-8") as f:
                rules = json.load(f)
            for qid, ans in sorted(st.session_state.answers.items()):
                qdata = rules["questions"].get(str(qid))
                if qdata:
                    status = "✅ 是" if ans else "❌ 否"
                    st.caption(f"Q{qid} [{status}] — {qdata['text'][:80]}")


# ============================================================
# RESULT PAGE (with A, B, C, F)
# ============================================================
def render_result(engine, r=None):
    if r is None:
        r = st.session_state.result

    # --- HEADER ---
    st.markdown(risk_badge_html(r.risk_label, r.risk_color, r.total_score), unsafe_allow_html=True)

    # --- TABS ---
    tab_overview, tab_whatif, tab_exposure, tab_compliance, tab_advice, tab_answers = st.tabs([
        "📊 风险全景", "🎮 What-If推演", "💰 税负量化", "📋 HGB合规清单", "📝 建议与法条", "📎 答题记录"
    ])

    # ===== TAB 1: OVERVIEW (Radar + Scores) =====
    with tab_overview:
        col_r, col_s = st.columns([3, 2])
        with col_r:
            radar_data = compute_radar_data(r)
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[d["value"] for d in radar_data["dimensions"]],
                theta=[d["axis"] for d in radar_data["dimensions"]],
                fill='toself', fillcolor=f'rgba(134,188,37,0.20)',
                line=dict(color=GREEN, width=2.5), name='风险画像',
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], showticklabels=False,
                                    gridcolor='#2A2A2A'), angularaxis=dict(gridcolor='#2A2A2A'),
                    bgcolor=BG,
                ), showlegend=False, height=380, margin=dict(l=40, r=40, t=20, b=20),
                paper_bgcolor=BG, font=dict(color=TEXT_MUTED),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_s:
            st.markdown(f"<h4 style='color:{GREEN_LIGHT};'>各维度评分</h4>", unsafe_allow_html=True)
            for label, val, law in [
                ("固定场所型PE", r.group_scores.get("fixed_place", 0), "协定第5条第1-4款"),
                ("工程/安装型PE", r.group_scores.get("construction", 0), "协定第5条第3款"),
                ("代理人型PE", r.group_scores.get("agent", 0), "协定第5条第5-6款"),
            ]:
                bar_c = GREEN if val <= 2 else (YELLOW if val <= 6 else RED)
                pct = min(100, max(5, val / 30 * 100))
                st.markdown(f"**{label}**", help=law)
                st.markdown(f"""
                <div style="background:#252525;border-radius:6px;height:8px;">
                  <div style="background:{bar_c};border-radius:6px;height:8px;width:{pct}%;"></div>
                </div>
                <p style="font-size:11px;color:{TEXT_MUTED};">{val} 分</p>
                """, unsafe_allow_html=True)
            st.divider()
            st.markdown(f"<h4 style='color:{GREEN_LIGHT};'>分析结论</h4>", unsafe_allow_html=True)
            st.info(r.summary)

    # ===== TAB 2: WHAT-IF (F) =====
    with tab_whatif:
        st.markdown('<h4 style="color:' + GREEN_LIGHT + ';">交互式 What-If 推演</h4>', unsafe_allow_html=True)
        st.caption("拖动下方关键变量，实时观察风险评分和雷达图的变化")

        # Initialize whatif from current answers
        if not st.session_state.whatif_answers:
            st.session_state.whatif_answers = dict(r.answers) if r.answers else {}

        wa = st.session_state.whatif_answers

        # Key decision variables
        st.markdown(f"<p style='color:{GREEN};font-weight:600;'>固定场所型PE 关键变量</p>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            wa[1] = st.toggle("Q1: 有固定营业场所", value=wa.get(1, False),
                              help="办公室、工厂、仓库、门店等")
        with c2:
            lease_months = st.slider("场所持续月数（影响Q2+Q3）", 0, 36,
                                     value=12 if wa.get(3, False) else 3,
                                     help="≤6月→Q3为否; >6月→Q3为是")
            wa[2] = lease_months > 1
            wa[3] = lease_months > 6
        with c3:
            wa[6] = st.toggle("Q6: 仅为辅助性活动", value=wa.get(6, False),
                              help="若是→豁免PE; 若否→构成风险")

        st.markdown(f"<p style='color:{GREEN};font-weight:600;margin-top:12px;'>工程型PE 关键变量</p>",
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            wa[8] = st.toggle("Q8: 有建筑/安装工程", value=wa.get(8, False))
        with c2:
            constr_months = st.slider("工程持续月数（影响Q9）", 0, 36,
                                      value=15 if wa.get(9, False) else 6,
                                      help=">12月→Q9为是→构成工程PE")
            wa[9] = constr_months > 12
        with c3:
            wa[10] = st.toggle("Q10: 存在合同拆分风险", value=wa.get(10, False))

        st.markdown(f"<p style='color:{GREEN};font-weight:600;margin-top:12px;'>代理人型PE 关键变量</p>",
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            wa[11] = st.toggle("Q11: 德国有派驻/代理人员", value=wa.get(11, False))
        with c2:
            wa[12] = st.toggle("Q12: 经常以企业名义签合同", value=wa.get(12, False),
                               help="缔约权是代理人PE核心要件")
        with c3:
            wa[13] = st.toggle("Q13: 代理人是独立第三方", value=wa.get(13, False),
                               help="若是→倾向于豁免PE")

        # Live recalculation
        whatif_result = engine.evaluate(wa)
        whatif_radar = compute_radar_data(whatif_result)

        st.divider()
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};'>推演结果</h4>", unsafe_allow_html=True)

        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        with mc1:
            delta = whatif_result.total_score - r.total_score
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            delta_color = RED if delta > 0 else (GREEN if delta < 0 else TEXT_MUTED)
            st.markdown(f"""
            <div class="metric-box">
              <div class="value" style="color:{whatif_result.risk_color};">{whatif_result.total_score}</div>
              <div class="label">推演评分 <span style="color:{delta_color};">({delta_str})</span></div>
            </div>
            """, unsafe_allow_html=True)
        with mc2:
            st.markdown(f"""
            <div class="metric-box">
              <div class="value" style="color:{whatif_result.risk_color};">{whatif_result.risk_label.split('·')[0].strip()}</div>
              <div class="label">推演风险等级</div>
            </div>
            """, unsafe_allow_html=True)
        with mc3:
            tec = TaxExposureCalculator()
            exp_orig = tec.calculate(2000000, r.risk_level)
            exp_new = tec.calculate(2000000, whatif_result.risk_level)
            comp_diff = exp_new.total_annual_exposure_eur - exp_orig.total_annual_exposure_eur
            st.markdown(f"""
            <div class="metric-box">
              <div class="value" style="color:{RED if comp_diff > 0 else GREEN};">{'多缴' if comp_diff > 0 else '节省'} €{abs(comp_diff):,.0f}</div>
              <div class="label">年度税负变化（假设€200万利润）</div>
            </div>
            """, unsafe_allow_html=True)

        # Mini radar for what-if
        with mc4:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatterpolar(
                r=[d["value"] for d in whatif_radar["dimensions"]],
                theta=[d["axis"] for d in whatif_radar["dimensions"]],
                fill='toself', fillcolor=f'rgba(134,188,37,0.20)',
                line=dict(color=GREEN, width=2), name='推演',
            ))
            fig2.update_layout(
                polar=dict(radialaxis=dict(visible=False, range=[0, 100]),
                           angularaxis=dict(gridcolor='#2A2A2A'), bgcolor=BG),
                showlegend=False, height=180, margin=dict(l=10, r=10, t=5, b=5),
                paper_bgcolor=BG,
            )
            st.plotly_chart(fig2, use_container_width=True)
        with mc5:
            if st.button("应用此配置", type="primary", use_container_width=True, key="apply_whatif"):
                st.session_state.answers = dict(wa)
                st.session_state.result = whatif_result
                st.session_state.whatif_answers = {}
                st.rerun()
            if st.button("重置变量", use_container_width=True, key="reset_whatif"):
                st.session_state.whatif_answers = {}
                st.rerun()

    # ===== TAB 3: TAX EXPOSURE (A) =====
    with tab_exposure:
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">PE 税务暴露量化分析</h4>", unsafe_allow_html=True)
        st.caption("基于德国2026年现行税率 · KSt 15% + SolZ 5.5%×KSt + GewSt ≈14%")

        default_profit = {"low": 500000, "medium": 2000000, "high": 5000000, "constituted": 5000000}
        col_in, col_out = st.columns([2, 3])
        with col_in:
            profit = st.number_input("预计德国年税前利润（€）", min_value=50000, max_value=50000000,
                                     value=default_profit.get(r.risk_level, 1000000), step=100000, format="%d")
            payout = st.slider("股息汇回比例", 0.0, 1.0, 0.7, 0.05)
            tec = TaxExposureCalculator()
            exp = tec.calculate(profit, r.risk_level, payout)

        with col_out:
            dcolor = GREEN if exp.total_annual_exposure_eur < 50000 else (
                YELLOW if exp.total_annual_exposure_eur < 200000 else RED)
            st.markdown(f"""
            <div style="text-align:center;padding:24px;background:{r.risk_color};border-radius:10px;color:white;margin-bottom:16px;">
              <p style="font-size:14px;opacity:0.9;margin:0;">PE构成后 · 年度额外税负与合规成本</p>
              <p class="big-number" style="margin:8px 0;color:white;">€{exp.total_annual_exposure_eur:,.0f}</p>
              <p style="font-size:12px;opacity:0.8;margin:0;">税前利润 €{profit:,.0f} · {r.risk_label}</p>
            </div>
            """, unsafe_allow_html=True)

            bd = exp.breakdown
            st.markdown(f"<h5 style='color:{TEXT};'>税负明细对比</h5>", unsafe_allow_html=True)
            bd = exp.breakdown
            st.markdown(f"<h5 style='color:{TEXT};'>双边税负明细对比</h5>", unsafe_allow_html=True)
            st.table({
                "税种/成本项": ["德国企业所得税(KSt+SolZ)", "德国营业税(GewSt ≈14%)",
                              "中国 CIT (境外抵免后)", "HGB合规成本", "双边年度合计"],
                "PE构成前 (€)": ["0", "0", f"{bd.get('total_tax_before_pe_eur', 0):,.0f}", "0",
                              f"{bd.get('total_tax_before_pe_eur', 0):,.0f}"],
                "PE构成后 (€)": [f"{bd['german_kst_solz_eur']:,.0f}", f"{bd['german_gewst_eur']:,.0f}",
                              f"{bd['china_tax_after_credit_eur']:,.0f}", f"{exp.hgb_compliance_cost_eur:,.0f}",
                              f"{exp.total_pe_tax_eur + exp.hgb_compliance_cost_eur:,.0f}"],
                "差异 (€)": [f"+{bd['german_kst_solz_eur']:,.0f}", f"+{bd['german_gewst_eur']:,.0f}",
                          f"{bd['china_tax_after_credit_eur'] - bd.get('total_tax_before_pe_eur', 0):+,.0f}",
                          f"+{exp.hgb_compliance_cost_eur:,.0f}", f"+{exp.total_annual_exposure_eur:,.0f}"],
            })
            st.caption(
                f"PE 后德国侧税率 ≈ {exp.corporate_tax_rate}%"
                f"（KSt+SolZ+GewSt）；中国侧境外税收抵免上限为 CIT {bd.get('china_tax_before_credit_eur', 0):,.0f}€，"
                f"实际抵免 {bd.get('china_foreign_credit_eur', 0):,.0f}€。"
                f"PE 前仅中国 CIT（协定第7条第1款，营业利润由居民国征税）。"
            )

        # --- Financial Model (ETR / ROE / Breakeven / 5yr NPV) ---
        st.divider()
        st.markdown(f"<h5 style='color:{GREEN_LIGHT};'>财务影响模型（Advanced）</h5>", unsafe_allow_html=True)

        model_toggle = st.toggle("启用 5 年 NPV 财务模型", value=False,
                                 help="计算 PE 前后有效税率 (ETR)、ROE 稀释、盈亏平衡点和 5 年累计税负净现值")
        if model_toggle:
            equity = st.number_input("企业全球股东权益（€）", min_value=100000, value=3500000, step=500000,
                                     format="%d", help="用于 ROE 计算")
            growth = st.slider("德国利润年增长率", 0.0, 0.30, 0.05, 0.01, help="用于 5 年 NPV 预测")
            disc = st.slider("折现率 (WACC)", 0.05, 0.20, 0.08, 0.01, help="默认 8%")

            fm = FinancialModel.analyze(
                pretax_profit_eur=profit,
                pe_risk_level=r.risk_level,
                total_equity_global_eur=equity,
                dividend_payout_ratio=payout,
                discount_rate=disc,
                growth_rate=growth,
            )

            # ETR + ROE row
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("PE 前 ETR", f"{fm.etr_before_pe}%", delta=None)
                st.metric("PE 后 ETR", f"{fm.etr_after_pe}%", delta=f"+{fm.etr_delta_pct} pp",
                          delta_color="inverse")
            with c2:
                st.metric("PE 前 ROE", f"{fm.roe_before_pe}%", delta=None)
                st.metric("PE 后 ROE", f"{fm.roe_after_pe}%", delta=f"-{fm.roe_dilution_pct} pp",
                          delta_color="inverse")
            with c3:
                st.markdown(f"""
                <div class="metric-box">
                  <div class="value" style="color:{GREEN_LIGHT};">€{fm.breakeven_profit_eur:,.0f}</div>
                  <div class="label">盈亏平衡利润额</div>
                </div>
                """, unsafe_allow_html=True)
                st.caption("超过此金额设子公司更划算")
            with c4:
                npv_color = RED if fm.npv_5yr_difference_eur > 0 else GREEN
                st.markdown(f"""
                <div class="metric-box">
                  <div class="value" style="color:{npv_color};">€{fm.npv_5yr_difference_eur:,.0f}</div>
                  <div class="label">5 年累计税负差异 (NPV)</div>
                </div>
                """, unsafe_allow_html=True)

            # NPV detail
            c_npv1, c_npv2 = st.columns(2)
            with c_npv1:
                st.metric("PE 前 5 年税负 NPV", f"€{fm.npv_5yr_tax_pe_before_eur:,.0f}")
            with c_npv2:
                st.metric("PE 后 5 年税负 NPV", f"€{fm.npv_5yr_tax_pe_after_eur:,.0f}",
                          delta=f"+€{fm.npv_5yr_difference_eur:,.0f}", delta_color="inverse")

            if fm.npv_roi_if_restructure_eur > 0:
                st.success(f"架构重组（设立子公司）5 年 NPV 收益：**€{fm.npv_roi_if_restructure_eur:,.0f}**")

            st.info(f"**综合建议**：{fm.recommendation}")

    # ===== TAB 4: HGB COMPLIANCE (C) =====
    with tab_compliance:
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">HGB 合规义务清单</h4>", unsafe_allow_html=True)
        checklist = get_checklist_for_result(r)
        st.markdown(f"""
        <div style="background:{checklist['level_color']};border-radius:6px;padding:12px 18px;color:white;margin-bottom:16px;">
          <strong>{checklist['level_label']}</strong>
          <span style="opacity:0.8;font-size:13px;margin-left:12px;">评分 {checklist['total_score']} 分</span>
        </div>
        """, unsafe_allow_html=True)

        priority_labels = {'critical': '紧急', 'high': '高优先', 'medium': '中优先', 'low': '低优先'}
        priority_colors = {'critical': RED, 'high': '#FF6B6B', 'medium': YELLOW, 'low': GREEN}

        for section in checklist["sections"]:
            with st.expander(f"{section['title']}（{len(section['items'])} 项）", expanded=False):
                for item in section["items"]:
                    pc = priority_colors.get(item['priority'], TEXT_MUTED)
                    pl = priority_labels.get(item['priority'], '')
                    st.markdown(f"""
                    <div style="padding:6px 0;border-bottom:1px solid #1A1A1A;">
                      <span style="color:{pc};min-width:50px;font-size:11px;font-weight:600;">[{pl}]</span>
                      <span style="color:{TEXT};font-size:13px;">{item['task']}</span>
                      <span style="color:{TEXT_DIM};font-size:10px;margin-left:8px;">
                        {item['legal']} · ⏱ {item['deadline']}
                      </span>
                    </div>
                    """, unsafe_allow_html=True)

    # ===== TAB 5: ADVICE + LEGAL =====
    with tab_advice:
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">行动建议</h4>", unsafe_allow_html=True)
        for i, adv in enumerate(r.advice, 1):
            st.markdown(f"**{i}.** {adv}")
        st.divider()
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">相关法律依据</h4>", unsafe_allow_html=True)
        for ref in r.legal_refs:
            st.markdown(f"- {ref}")

    # ===== TAB 6: ANSWER LOG =====
    with tab_answers:
        with open(Path(__file__).parent / "data" / "rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
        for qid_str in sorted(rules["questions"].keys(), key=int):
            qid = int(qid_str)
            qdata = rules["questions"][qid_str]
            ans = r.answers.get(qid)
            if ans is None:
                continue
            tag = f'<span style="color:{RED};">是</span>' if ans else f'<span style="color:{GREEN};">否</span>'
            st.markdown(f"**Q{qid}** [{tag}] — {qdata['text'][:100]}", unsafe_allow_html=True)

    # --- BOTTOM ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        gen = ReportGenerator(r)
        html = gen.generate_html()
        st.download_button("下载 HTML 报告", data=html,
                           file_name=f"PE-Scout_风险报告_{r.risk_level}.html",
                           mime="text/html", use_container_width=True)
    with c2:
        if st.button("重新评估", use_container_width=True, key="re_eval"):
            reset_assessment(); st.session_state.page = "assessment"; st.rerun()
    with c3:
        if st.button("回到首页", use_container_width=True, key="home"):
            reset_assessment(); st.session_state.page = "welcome"; st.rerun()


# ============================================================
# COMPARISON MODE (D)
# ============================================================
def render_comparison(engine):
    st.markdown('<div class="main-header"><h1>双场景对比分析</h1><p>经营安排调整前后 · PE风险与税负差异对比</p></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([1, 8])
    with c1:
        if st.button("← 返回首页", key="back_cmp"):
            reset_assessment(); st.session_state.page = "welcome"; st.rerun()

    # Case selectors for both sides
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">场景 A：当前经营安排</h4>", unsafe_allow_html=True)
        cases = engine.get_all_cases()
        case_names = ["自定义（当前评估结果）"] + [f"{c['name']} — {c['subtitle']}" for c in cases]
        left_choice = st.selectbox("选择场景A", case_names, key="left_case")

        if left_choice == "自定义（当前评估结果）":
            if st.session_state.result:
                left_result = st.session_state.result
                st.info(f"使用当前评估结果：{left_result.risk_label}（{left_result.total_score}分）")
            else:
                st.warning("请先在评估页面完成PE分析")
                return
        else:
            idx = case_names.index(left_choice) - 1
            case_data = engine.load_case(cases[idx]["id"])
            left_result = engine.evaluate(case_data["answers"])
            st.info(f"已加载案例：{left_result.risk_label}（{left_result.total_score}分）")

    with col_right:
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">场景 B：调整后经营安排</h4>", unsafe_allow_html=True)
        right_choice = st.selectbox("选择场景B", case_names, key="right_case", index=min(1, len(case_names) - 1))

        if right_choice == "自定义（当前评估结果）":
            if st.session_state.result:
                right_result = st.session_state.result
                st.info(f"使用当前评估结果：{right_result.risk_label}（{right_result.total_score}分）")
            else:
                st.warning("请先在评估页面完成PE分析")
                return
        else:
            idx = case_names.index(right_choice) - 1
            case_data = engine.load_case(cases[idx]["id"])
            right_result = engine.evaluate(case_data["answers"])
            st.info(f"已加载案例：{right_result.risk_label}（{right_result.total_score}分）")

    st.divider()

    # === COMPARISON TABLE ===
    st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">风险对比</h4>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([5, 1, 5])
    with c1:
        st.markdown(risk_badge_html(f"A: {left_result.risk_label}", left_result.risk_color,
                                    left_result.total_score), unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='text-align:center;padding-top:40px;'><h1 style='color:#666;'>vs</h1></div>",
                    unsafe_allow_html=True)
    with c3:
        st.markdown(risk_badge_html(f"B: {right_result.risk_label}", right_result.risk_color,
                                    right_result.total_score), unsafe_allow_html=True)

    # Score comparison
    score_diff = right_result.total_score - left_result.total_score
    diff_color = GREEN if score_diff < 0 else (RED if score_diff > 0 else TEXT_MUTED)
    diff_label = f"降低 {abs(score_diff)} 分" if score_diff < 0 else (
        f"增加 {score_diff} 分" if score_diff > 0 else "无变化")

    st.markdown(f"""
    <div style="text-align:center;padding:12px;background:{BG_CARD};border-radius:8px;">
      <span style="color:{TEXT_MUTED};">风险评分变化：</span>
      <strong style="color:{diff_color};">{diff_label}</strong>
      <span style="color:{TEXT_MUTED};">（{left_result.total_score} → {right_result.total_score}）</span>
    </div>
    """, unsafe_allow_html=True)

    # Tax exposure comparison
    st.divider()
    st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">税负暴露对比（假设€200万利润）</h4>", unsafe_allow_html=True)
    tec = TaxExposureCalculator()
    exp_left = tec.calculate(2000000, left_result.risk_level)
    exp_right = tec.calculate(2000000, right_result.risk_level)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-box">
          <div class="value" style="color:{left_result.risk_color};">€{exp_left.total_annual_exposure_eur:,.0f}</div>
          <div class="label">场景A · 年度额外税负</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        saving = exp_left.total_annual_exposure_eur - exp_right.total_annual_exposure_eur
        st.markdown(f"""
        <div class="metric-box" style="border:2px solid {GREEN if saving > 0 else RED};">
          <div class="value" style="color:{GREEN if saving > 0 else RED};">{'节省' if saving > 0 else '增加'} €{abs(saving):,.0f}</div>
          <div class="label">场景B调整后 · 年度差异</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-box">
          <div class="value" style="color:{right_result.risk_color};">€{exp_right.total_annual_exposure_eur:,.0f}</div>
          <div class="label">场景B · 年度额外税负</div>
        </div>
        """, unsafe_allow_html=True)

    # Radar comparison
    st.divider()
    st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">雷达图叠加对比</h4>", unsafe_allow_html=True)
    radar_left = compute_radar_data(left_result)
    radar_right = compute_radar_data(right_result)

    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Scatterpolar(
        r=[d["value"] for d in radar_left["dimensions"]],
        theta=[d["axis"] for d in radar_left["dimensions"]],
        fill='toself', fillcolor='rgba(255,68,68,0.15)',
        line=dict(color=RED, width=2), name='场景A',
    ))
    fig_cmp.add_trace(go.Scatterpolar(
        r=[d["value"] for d in radar_right["dimensions"]],
        theta=[d["axis"] for d in radar_right["dimensions"]],
        fill='toself', fillcolor='rgba(134,188,37,0.20)',
        line=dict(color=GREEN, width=2), name='场景B',
    ))
    fig_cmp.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], showticklabels=False,
                                    gridcolor='#2A2A2A'),
                   angularaxis=dict(gridcolor='#2A2A2A'), bgcolor=BG),
        showlegend=True, legend=dict(font=dict(color=TEXT)), height=400,
        margin=dict(l=40, r=40, t=20, b=20), paper_bgcolor=BG,
    )
    st.plotly_chart(fig_cmp, use_container_width=True)


# ============================================================
# TAX PARAMS + CASES (unchanged logic, new theme)
# ============================================================
def render_tax_params(calc):
    st.markdown('<div class="main-header"><h1>中德税务参数速查</h1><p>关键税制参数对比 · 中国 vs 德国</p></div>',
                unsafe_allow_html=True)
    if st.button("← 返回首页", key="back_tp"):
        reset_assessment(); st.session_state.page = "welcome"; st.rerun()

    keyword = st.text_input("关键词搜索", placeholder="如：预提税、折旧、HGB、增值税...")
    if keyword:
        results = calc.search(keyword)
        if results:
            st.markdown(f"找到 **{len(results)}** 条：")
            for r_item in results:
                with st.expander(f"{r_item['name']}（{r_item['category']}）", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1: st.markdown(f"**🇨🇳 中国**"); st.markdown(r_item["china"])
                    with c2: st.markdown(f"**🇩🇪 德国**"); st.markdown(r_item["germany"])
        else:
            st.warning("未找到匹配结果")
        st.divider()

    for cat in calc.get_all_params():
        with st.expander(cat["name"], expanded=False):
            for p in cat["params"]:
                c1, c2 = st.columns(2)
                with c1: st.markdown(f"**{p['name']}**"); st.markdown(p["china"])
                with c2: st.markdown(""); st.markdown(p["germany"])
                st.divider()
    st.caption(calc.get_disclaimer())


def render_cases(engine):
    st.markdown('<div class="main-header"><h1>虚拟案例演示库</h1><p>4个预设典型出海德国场景 · 一键加载完整PE分析</p></div>',
                unsafe_allow_html=True)
    if st.button("← 返回首页", key="back_cs"):
        reset_assessment(); st.session_state.page = "welcome"; st.rerun()
    st.caption("所有案例均为模拟数据，不涉及任何真实企业信息。")

    cases = engine.get_all_cases()
    for c in cases:
        with st.expander(f"{c['name']} — {c['subtitle']}（{c['industry']}）", expanded=False):
            case_data = engine.load_case(c["id"])
            if not case_data: continue
            p = case_data["profile"]
            st.markdown(f"""
            <div class="card">
            <strong>背景：</strong>{p['background']}<br>
            <strong>德国业务：</strong>{p['german_activities']}<br>
            <strong>年收入：</strong>{p['revenue_eur']} · <strong>员工：</strong>{p['employees_de']}人
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"加载案例 → {c['name']}", key=f"load_{c['id']}", type="primary"):
                st.session_state.answers = case_data["answers"]
                st.session_state.completed = True
                st.session_state.result = engine.evaluate(case_data["answers"])
                st.session_state.case_loaded = c["id"]
                st.session_state.page = "assessment"
                st.rerun()
            st.info(f"**分析**：{case_data['analysis']}")


# ============================================================
# MAIN
# ============================================================
# ============================================================
# CHAT AGENT PAGE
# ============================================================
def render_chat_agent():
    st.markdown('<div class="main-header"><h1>AI 税务咨询 Agent</h1><p>DeepSeek LLM + 规则引擎 + RAG 法律检索 · 三引擎驱动</p></div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns([1, 8])
    with c1:
        if st.button("← 返回首页", key="back_chat"):
            reset_assessment(); st.session_state.page = "welcome"; st.rerun()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "agent" not in st.session_state:
        try:
            st.session_state.agent = PEAgent()
        except Exception as e:
            st.session_state.agent = None
            st.error(f"⚠️ 分析 Agent 初始化失败：{e}。请检查依赖或环境变量后刷新页面。")
    if "feedback_collector" not in st.session_state:
        st.session_state.feedback_collector = FeedbackCollector()

    agent = st.session_state.agent
    if agent is None:
        st.warning("⚠️ 当前无法加载分析引擎，对话功能已停用；其余页面不受影响。")
        return

    # LLM status badge
    llm_available = agent.llm_agent is not None and agent.llm_agent.is_ready
    badge_color = GREEN if llm_available else ORANGE
    badge_text = "LLM 已连接 · DeepSeek" if llm_available else "规则引擎模式（设置 DEEPSEEK_API_KEY 开启 LLM）"
    st.markdown(f"""
    <div style="background:{badge_color};border-radius:6px;padding:6px 14px;margin-bottom:12px;
                display:inline-block;color:white;font-size:12px;font-weight:600;">
    {badge_text}
    </div>
    """, unsafe_allow_html=True)

    # Suggested questions
    llm_note = ('当前使用 <strong style="color:' + GREEN + ';">DeepSeek LLM</strong> 进行智能推理。') if llm_available else ''
    st.markdown(f"""
    <div class="card" style="border-left:3px solid {GREEN};margin-bottom:16px;">
    <p style="color:{TEXT_MUTED};font-size:13px;margin:0;">
    我可以回答中德PE相关的法律要件、时间门槛、豁免条款、HGB义务、税负计算等问题。
    试试下面的建议问题，或输入您自己的问题。{llm_note}
    </p>
    </div>
    """, unsafe_allow_html=True)

    suggestions = [
        "如果我的德国仓库除了存储还增加了展示功能，会构成PE吗？",
        "工程停工3个月还算在12个月工期里吗？",
        "什么是反碎片化规则（BEPS行动7）？",
        "PE构成后触发哪些HGB合规义务？",
        "德国国内法AO的PE定义和双边协定有什么不同？",
    ]

    cols = st.columns(len(suggestions))
    for i, sug in enumerate(suggestions):
        with cols[i]:
            if st.button(sug[:40] + "...", key=f"sug_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": sug})
                try:
                    resp = agent.process_message(sug)
                    st.session_state.chat_history.append({"role": "assistant", "content": resp["reply"],
                                                           "confidence": resp["confidence"],
                                                           "suggested": resp["suggested_actions"],
                                                           "tool_calls": resp.get("extracted_facts", {}).get("tool_calls", [])})
                except Exception as e:
                    st.error(f"⚠️ 处理消息时出错：{e}")
                st.rerun()

    st.divider()

    # Clear chat button
    if st.button("🗑 清空对话", key="clear_chat"):
        st.session_state.chat_history = []
        if agent.llm_agent:
            agent.llm_agent.reset_memory()
        st.rerun()

    # Chat display
    for i, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])
                if msg.get("confidence", 0) > 0:
                    st.caption(f"置信度: {msg['confidence']:.0%}")
                if msg.get("tool_calls"):
                    with st.expander("查看工具调用", expanded=False):
                        for tc in msg["tool_calls"]:
                            st.caption(f"🔧 {tc['tool']}: {tc['input'][:120]}")
                if msg.get("suggested"):
                    for act in msg["suggested"]:
                        st.button(f"→ {act['label']}", key=f"act_{i}_{act['action']}", use_container_width=False)

    # Input
    user_input = st.chat_input("输入您的中德PE相关问题..." + (" (LLM 推理模式)" if llm_available else ""))
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        try:
            resp = agent.process_message(user_input)
            st.session_state.chat_history.append({"role": "assistant", "content": resp["reply"],
                                                   "confidence": resp["confidence"],
                                                   "suggested": resp["suggested_actions"],
                                                   "tool_calls": resp.get("extracted_facts", {}).get("tool_calls", [])})
        except Exception as e:
            st.error(f"⚠️ 处理消息时出错：{e}")
        st.rerun()


# ============================================================
# KNOWLEDGE GRAPH PAGE
# ============================================================
def render_knowledge_graph():
    st.markdown('<div class="main-header"><h1>PE 法律知识图谱</h1><p>中德PE四层合规推理模型 · 交互式可视化</p></div>',
                unsafe_allow_html=True)
    if st.button("← 返回首页", key="back_kg"):
        reset_assessment(); st.session_state.page = "welcome"; st.rerun()

    if "kg_builder" not in st.session_state:
        with st.spinner("构建知识图谱..."):
            st.session_state.kg_builder = PEGraphBuilder()

    kg = st.session_state.kg_builder

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};'>四层合规推理结构</h4>", unsafe_allow_html=True)

        chain = kg.compliance_chain("constituted")
        for layer in chain:
            with st.expander(f"Layer {layer['layer']}: {layer['name']}（{len(layer['items'])} 个节点）",
                             expanded=layer['layer'] <= 1):
                for item in layer["items"]:
                    st.markdown(f"""
                    <span style="display:inline-block;width:12px;height:12px;background:{item['color']};
                    border-radius:50%;margin-right:6px;"></span>
                    <span style="color:{TEXT};font-size:13px;">{item['label'].replace(chr(10), ' → ')}</span>
                    """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};'>图谱统计</h4>", unsafe_allow_html=True)
        graph_data = kg.export_graph()
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        st.markdown(f"""
        <div class="metric-box">
          <div class="value">{len(nodes)}</div>
          <div class="label">知识节点</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-box">
          <div class="value">{len(edges)}</div>
          <div class="label">关联边</div>
        </div>
        """, unsafe_allow_html=True)

        # Legend
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};margin-top:12px;'>图例</h4>", unsafe_allow_html=True)
        legend = [
            ("法律条文/协定", "#86BC25"),
            ("PE类型", "#142F4E"),
            ("触发条件/豁免", "#5B9AD5"),
            ("风险后果", "#E94D3A"),
            ("合规行动", "#F59E0B"),
            ("HGB条款", "#DC2626"),
            ("时间门槛", "#8B5CF6"),
        ]
        for label, color in legend:
            st.markdown(f"""
            <span style="display:inline-block;width:10px;height:10px;background:{color};
            border-radius:50%;margin-right:6px;"></span>
            <span style="color:{TEXT};font-size:12px;">{label}</span>
            """, unsafe_allow_html=True)

    # Interactive graph visualization
    st.divider()
    st.markdown(f"<h4 style='color:{GREEN_LIGHT};\">交互式知识图谱</h4>", unsafe_allow_html=True)
    st.caption("节点可拖拽 · 滚轮缩放 · 点击查看详情")

    # Build PyVis HTML
    try:
        import networkx as nx
        from pyvis.network import Network

        net = Network(height="550px", width="100%", bgcolor=BG, font_color=TEXT)
        net.repulsion(node_distance=150, spring_length=200, damping=0.85)

        for node in graph_data["nodes"]:
            net.add_node(node["id"], label=node["label"].replace("\n", " "),
                         color=node.get("color", "#666"),
                         size=node.get("size", 10),
                         title=node["label"].replace("\n", "<br>"))

        for edge in graph_data["edges"]:
            net.add_edge(edge["source"], edge["target"],
                         title=edge.get("relation", ""),
                         color={"color": "#555555", "opacity": 0.5})

        html = net.generate_html()
        # Inject dark background
        html = html.replace("background-color: rgba(200,200,200,1);",
                           f"background-color: {BG};")
        st.components.v1.html(html, height=580, scrolling=False)
    except ImportError:
        st.warning("PyVis not installed. Install with: pip install pyvis")
        st.caption("显示简化版图谱：")
        for edge in graph_data["edges"][:30]:
            st.caption(f"{edge['source']} --[{edge.get('relation','')}]--> {edge['target']}")

    # If result is available, show highlighted subgraph
    if st.session_state.result:
        st.divider()
        st.markdown(f"<h4 style='color:{GREEN_LIGHT};'>当前判定路径高亮</h4>", unsafe_allow_html=True)

        subgraph = kg.get_subgraph_for_result(
            st.session_state.result.risk_level,
            st.session_state.result.group_scores
        )
        highlighted_nodes = [n for n in subgraph["nodes"] if n.get("highlighted")]
        st.markdown(f"高亮节点：{len(highlighted_nodes)}/{len(subgraph['nodes'])}")
        for node in highlighted_nodes:
            st.markdown(f"""
            <span style="display:inline-block;width:10px;height:10px;background:{node['color']};
            border-radius:50%;margin-right:6px;"></span>
            <span style="color:{TEXT};font-size:12px;">{node['label'].replace(chr(10), ' → ')}</span>
            """, unsafe_allow_html=True)


# ============================================================
# RAG SEARCH PAGE
# ============================================================
def render_rag_search():
    st.markdown('<div class="main-header"><h1>法律文档语义检索</h1><p>中德税法全文本地检索 · 基于关键词匹配</p></div>',
                unsafe_allow_html=True)
    if st.button("← 返回首页", key="back_rag"):
        reset_assessment(); st.session_state.page = "welcome"; st.rerun()

    if "doc_store" not in st.session_state:
        with st.spinner("加载文档索引..."):
            import asyncio
            ds = DocumentStore()
            asyncio.run(ds.initialize())
            st.session_state.doc_store = ds

    ds = st.session_state.doc_store
    if not ds._initialized:
        ds._initialized = True

    st.markdown(f"""
    <div class="card" style="border-left:3px solid {GREEN};">
    <p style="color:{TEXT_MUTED};font-size:13px;margin:0;">
    已索引 <strong style="color:{GREEN};">{len(ds.documents)}</strong> 个法律文档片段，覆盖：
    中德税收协定第5条全文 · OECD范本注释 · 德国AO §12-13 · BEPS行动7 · HGB合规条款 · 15个PE法律要件
    </p>
    </div>
    """, unsafe_allow_html=True)

    query = st.text_input("搜索法律条文", placeholder="例如：12个月门槛、准备性辅助性豁免、代理人缔约权...",
                          key="rag_query_main")

    if query:
        with st.spinner("检索中..."):
            results = ds.search(query, top_k=8)

        if results:
            st.markdown(f"找到 **{len(results)}** 条相关结果：")
            for i, r in enumerate(results):
                score_color = GREEN if r["score"] > 0.5 else (YELLOW if r["score"] > 0.2 else TEXT_MUTED)
                with st.expander(f"[{r['score']:.0%}] {r['content'][:80]}...  ({r['source']})",
                                 expanded=i < 3):
                    st.markdown(r["content"])
                    st.caption(f"来源: {r['source']} · 类型: {r['type']} · 相关度: {r['score']:.0%}")
        else:
            st.warning("未找到相关结果，请尝试其他关键词。")

    st.divider()
    st.markdown(f"<h4 style='color:{GREEN_LIGHT};'>文档来源</h4>", unsafe_allow_html=True)
    sources = [
        "中德税收协定 (2014) 第5条第1-6款",
        "德国租税通则 (AO) §12 常设机构定义",
        "德国租税通则 (AO) §13 常设代理人",
        "OECD 税收协定范本注释 (2017) 第5条",
        "BEPS 行动计划7最终报告 (2015)",
        "德国商法典 (HGB) §238-263 账簿+年报",
        "欧盟最低税指令 2022/2523 支柱二",
    ]
    for src in sources:
        st.markdown(f"- {src}")


def main():
    init_session()

    with st.sidebar:
        st.markdown(f"<h2 style='color:{GREEN};font-weight:400;'>PE-Scout</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:{TEXT_MUTED};font-size:12px;'>中德常设机构风险分析 v4.0</p>", unsafe_allow_html=True)
        st.divider()

        pages = {
            "welcome": "🏠 首页",
            "free_text": "📝 自由文本输入",
            "assessment": "🔍 逐题问答评估",
            "comparison": "⚖️ 双场景对比",
            "chat_agent": "🤖 AI 咨询 Agent",
            "knowledge_graph": "🕸️ 法律知识图谱",
            "rag_search": "🔎 条文语义检索",
            "tax_params": "📊 中德税务参数速查",
            "cases": "📋 虚拟案例库",
        }
        for page_id, label in pages.items():
            if st.button(label, use_container_width=True,
                         type="primary" if st.session_state.page == page_id else "secondary",
                         key=f"nav_{page_id}"):
                if page_id in ("assessment", "free_text") and st.session_state.page != page_id:
                    reset_assessment()
                st.session_state.page = page_id
                st.rerun()

        st.divider()
        st.caption(f"中德税收协定第5条 + 德国AO §12-13")
        st.caption(f"v4.0 · Agent+RAG+KG · 2026.07")
        st.caption("仅供参考，不构成专业税务意见")

    engine = PEEngine()
    calc = TaxParamCalculator()

    page = st.session_state.page
    if page == "welcome": render_welcome(engine)
    elif page == "free_text": render_free_text(engine)
    elif page == "assessment": render_assessment(engine)
    elif page == "comparison": render_comparison(engine)
    elif page == "chat_agent": render_chat_agent()
    elif page == "knowledge_graph": render_knowledge_graph()
    elif page == "rag_search": render_rag_search()
    elif page == "tax_params": render_tax_params(calc)
    elif page == "cases": render_cases(engine)

    st.markdown(f'<div class="footer-note">PE-Scout v4.0 · Agent+RAG+Knowledge Graph · © 2026</div>',
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
