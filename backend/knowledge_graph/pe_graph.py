"""PE 法律知识图谱构建器 — NetworkX 四层合规推理模型"""

import json, logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class PEGraphBuilder:
    """构建并管理中德PE法律知识图谱"""

    # 德勤绿 + 红/黄/蓝 配色
    COLORS = {
        "treaty": "#86BC25",       # 法律条文 — 德勤绿
        "pe_type": "#142F4E",      # PE类型 — 深蓝
        "condition": "#5B9AD5",    # 触发条件 — 蓝
        "risk": "#E94D3A",         # 风险后果 — 珊瑚红
        "action": "#F59E0B",       # 合规行动 — 琥珀
        "hgb": "#DC2626",          # HGB条款 — 红
        "exemption": "#22C55E",    # 豁免条款 — 绿
        "threshold": "#8B5CF6",    # 时间门槛 — 紫
    }

    def __init__(self):
        self.graph = None
        self._build_graph()

    def _build_graph(self):
        """构建四层PE法律知识图谱"""
        try:
            import networkx as nx
        except ImportError:
            self.graph = self._build_dict_graph()
            return

        self.graph = nx.DiGraph()

        # === Layer 1: 法律条文（Treaty） ===
        self.graph.add_node("treaty_art5", label="中德税收协定\n第5条", layer=0,
                            type="treaty", color=self.COLORS["treaty"], size=35)
        self.graph.add_node("ao_12", label="德国 AO §12\n常设机构定义", layer=0,
                            type="treaty", color=self.COLORS["treaty"], size=30)
        self.graph.add_node("ao_13", label="德国 AO §13\n常设代理人", layer=0,
                            type="treaty", color=self.COLORS["treaty"], size=28)
        self.graph.add_node("beps_7", label="BEPS 行动7\n反PE规避", layer=0,
                            type="treaty", color=self.COLORS["treaty"], size=28)
        self.graph.add_node("hgb_238", label="HGB §238\n簿记义务", layer=0,
                            type="treaty", color=self.COLORS["hgb"], size=32)

        # === Layer 2: PE类型 ===
        self.graph.add_node("pe_fixed", label="固定场所型 PE\n第5条第1-4款", layer=1,
                            type="pe_type", color=self.COLORS["pe_type"], size=30)
        self.graph.add_node("pe_construction", label="工程/安装型 PE\n第5条第3款", layer=1,
                            type="pe_type", color=self.COLORS["pe_type"], size=28)
        self.graph.add_node("pe_agent", label="代理人型 PE\n第5条第5-6款", layer=1,
                            type="pe_type", color=self.COLORS["pe_type"], size=28)

        # PE类型 ← 法律条文
        self.graph.add_edge("treaty_art5", "pe_fixed", relation="定义")
        self.graph.add_edge("treaty_art5", "pe_construction", relation="定义")
        self.graph.add_edge("treaty_art5", "pe_agent", relation="定义")
        self.graph.add_edge("ao_12", "pe_fixed", relation="国内法补充")
        self.graph.add_edge("ao_13", "pe_agent", relation="国内法补充")
        self.graph.add_edge("beps_7", "pe_agent", relation="降低认定门槛")
        self.graph.add_edge("beps_7", "pe_fixed", relation="反碎片化")

        # === Layer 2b: 关键时间门槛 ===
        self.graph.add_node("threshold_6m", label="6个月\n固定场所门槛", layer=1,
                            type="threshold", color=self.COLORS["threshold"], size=22)
        self.graph.add_node("threshold_12m", label="12个月\n工程PE门槛", layer=1,
                            type="threshold", color=self.COLORS["threshold"], size=24)
        self.graph.add_edge("pe_fixed", "threshold_6m", relation="持续>6月构成")
        self.graph.add_edge("pe_construction", "threshold_12m", relation="持续>12月构成")

        # === Layer 3: 触发条件 ===
        conditions_fixed = [
            ("cond_place", "固定营业场所\n(Q1)", 8),
            ("cond_control", "企业支配权\n(Q2)", 6),
            ("cond_duration", "持续>6个月\n(Q3)", 7),
            ("cond_storage", "纯仓储豁免\n(Q4)", -5),
            ("cond_procure", "纯采购豁免\n(Q5)", -4),
            ("cond_prep", "准备辅助豁免\n(Q6)", -5),
            ("cond_fragment", "反碎片化规则\n(Q7)", 8),
        ]
        for cid, clabel, _ in conditions_fixed:
            self.graph.add_node(cid, label=clabel, layer=2, type="condition",
                                color=self.COLORS["exemption"] if "豁免" in clabel else self.COLORS["condition"],
                                size=18)
            self.graph.add_edge("pe_fixed", cid, relation="要件")

        conditions_construction = [
            ("cond_site", "建筑/安装工程\n(Q8)", 6),
            ("cond_12m", "持续>12个月\n(Q9)", 10),
            ("cond_split", "合同拆分风险\n(Q10)", 6),
        ]
        for cid, clabel, _ in conditions_construction:
            self.graph.add_node(cid, label=clabel, layer=2, type="condition",
                                color=self.COLORS["condition"], size=18)
            self.graph.add_edge("pe_construction", cid, relation="要件")

        conditions_agent = [
            ("cond_person", "德国有派驻人员\n(Q11)", 6),
            ("cond_sign", "经常行使缔约权\n(Q12)", 10),
            ("cond_independent", "独立代理人豁免\n(Q13)", -8),
            ("cond_exclusive", "≥90%业务单一\n(Q14)", 7),
            ("cond_office", "代理人办公场所\n(Q15)", 5),
        ]
        for cid, clabel, _ in conditions_agent:
            self.graph.add_node(cid, label=clabel, layer=2, type="condition",
                                color=self.COLORS["exemption"] if "豁免" in clabel else self.COLORS["condition"],
                                size=18)
            self.graph.add_edge("pe_agent", cid, relation="要件")

        # === Layer 4: 风险后果 ===
        risks = [
            ("risk_low", "低风险\n德国无征税权(协定第7条)", "low"),
            ("risk_medium", "中风险\n建议专业评估", "medium"),
            ("risk_high", "高风险\n需紧急行动", "high"),
            ("risk_constituted", "已构成PE\n企业所得税≈30%\n+HGB合规", "constituted"),
        ]
        for rid, rlabel, rlevel in risks:
            self.graph.add_node(rid, label=rlabel, layer=3, type="risk",
                                color=self.COLORS["risk"], size=22)
            # Semantic edges: positive-weight conditions → higher risk levels;
            # negative-weight (exemption) conditions → low risk
            for cid, _, cweight in conditions_fixed + conditions_construction + conditions_agent:
                if cweight > 0 and rlevel in ("medium", "high", "constituted"):
                    self.graph.add_edge(cid, rid, relation="触发")
                elif cweight <= 0 and rlevel == "low":
                    self.graph.add_edge(cid, rid, relation="豁免")

        # === Layer 5: 合规行动 ===
        actions = [
            ("act_register", "税务登记 + 增值税号"),
            ("act_books", "建立HGB §238账簿"),
            ("act_audit", "年报编制 §242"),
            ("act_aoa", "AOA利润归属分析"),
            ("act_ongoing", "持续申报义务"),
        ]
        for aid, alabel in actions:
            self.graph.add_node(aid, label=alabel, layer=4, type="action",
                                color=self.COLORS["action"], size=20)
            for rid, _, _ in risks:
                if rid == "risk_constituted":
                    self.graph.add_edge(rid, aid, relation="触发")

        # HGB → 合规行动
        self.graph.add_edge("hgb_238", "act_books", relation="法定要求")
        self.graph.add_edge("hgb_238", "act_audit", relation="法定要求")

        logger.info(f"Knowledge graph built: {self.graph.number_of_nodes()} nodes, "
                    f"{self.graph.number_of_edges()} edges")

    def _build_dict_graph(self):
        """NetworkX不可用时的备选字典图"""
        return None

    def export_graph(self) -> dict:
        """导出为前端可视化格式（PyVis兼容）"""
        if self.graph is None:
            return {"nodes": [], "edges": []}

        try:
            import networkx as nx
            nodes = []
            for nid, data in self.graph.nodes(data=True):
                nodes.append({
                    "id": nid,
                    "label": data.get("label", nid),
                    "layer": data.get("layer", 0),
                    "type": data.get("type", ""),
                    "color": data.get("color", "#666"),
                    "size": data.get("size", 10),
                })

            edges = []
            for src, dst, data in self.graph.edges(data=True):
                edges.append({
                    "source": src,
                    "target": dst,
                    "relation": data.get("relation", ""),
                })

            return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"nodes": [], "edges": []}

    def find_paths(self, node_type: str = "all", max_depth: int = 2) -> list:
        """查找知识图谱路径"""
        if self.graph is None:
            return []

        try:
            import networkx as nx
            paths = []
            for src in self.graph.nodes():
                src_data = self.graph.nodes[src]
                if node_type != "all" and src_data.get("type") != node_type:
                    continue
                try:
                    for dst in self.graph.nodes():
                        if src == dst:
                            continue
                        for path in nx.all_simple_paths(self.graph, src, dst, cutoff=max_depth):
                            path_labels = [self.graph.nodes[n].get("label", n) for n in path]
                            paths.append({"nodes": path, "labels": path_labels, "length": len(path)})
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
            return paths[:50]
        except Exception:
            return []

    def compliance_chain(self, risk_level: str = "constituted") -> list:
        """四层合规推理链：法条→PE类型→触发条件→风险→行动"""
        if self.graph is None:
            return [{"layer": i, "label": f"Layer {i}", "items": []} for i in range(5)]

        chain = [
            {"layer": 0, "name": "法律依据", "items": []},
            {"layer": 1, "name": "PE分类", "items": []},
            {"layer": 2, "name": "触发条件/豁免", "items": []},
            {"layer": 3, "name": "风险后果", "items": []},
            {"layer": 4, "name": "合规行动", "items": []},
        ]

        for nid, data in self.graph.nodes(data=True):
            layer = data.get("layer", -1)
            if 0 <= layer <= 4:
                chain[layer]["items"].append({
                    "id": nid,
                    "label": data.get("label", nid),
                    "type": data.get("type", ""),
                    "color": data.get("color", "#666"),
                })

        return chain

    def get_subgraph_for_result(self, risk_level: str, group_scores: dict) -> dict:
        """根据PE分析结果，高亮当前判定路径"""
        graph_data = self.export_graph()

        # 标记高亮节点
        highlighted = set()

        # 固定场所PE路径
        if group_scores.get("fixed_place", 0) > 0:
            highlighted.update(["pe_fixed", "threshold_6m",
                               "cond_place", "cond_control", "cond_duration"])
            if group_scores.get("fixed_place", 0) >= 6:
                highlighted.add("risk_medium")

        # 工程PE路径
        if group_scores.get("construction", 0) > 0:
            highlighted.update(["pe_construction", "threshold_12m",
                               "cond_site", "cond_12m"])
            if group_scores.get("construction", 0) >= 10:
                highlighted.add("risk_constituted")

        # 代理人PE路径
        if group_scores.get("agent", 0) > 0:
            highlighted.update(["pe_agent", "cond_person", "cond_sign", "cond_exclusive"])
            if group_scores.get("agent", 0) >= 10:
                highlighted.add("risk_constituted")

        # 标记豁免节点
        if group_scores.get("fixed_place", 0) <= 3:
            highlighted.update(["cond_storage", "cond_procure", "cond_prep"])

        # 高亮风险节点
        risk_map = {"low": "risk_low", "medium": "risk_medium",
                     "high": "risk_high", "constituted": "risk_constituted"}
        highlighted.add(risk_map.get(risk_level, "risk_low"))

        # 更新节点高亮状态
        for node in graph_data["nodes"]:
            node["highlighted"] = node["id"] in highlighted
            if node["highlighted"]:
                node["size"] = node.get("size", 10) * 1.5

        return graph_data
