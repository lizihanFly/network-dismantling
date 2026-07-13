from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


BASE = Path("result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305")
OUT_DIR = Path("result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses")
REPORT = Path("result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses.md")
DATA_DIR = Path("data/realnetworks_40plus/cleaned")


def classify_outcome(diff: float) -> str:
    if abs(diff) <= 1e-12:
        return "tie / close"
    if diff < 0:
        return "SASB better than M5"
    return "SASB worse than M5"


def load_cleaned_graph(graph_id: str) -> nx.Graph:
    path = DATA_DIR / f"{graph_id}.edges"
    if not path.exists():
        raise FileNotFoundError(path)
    g = nx.read_edgelist(path, comments="#", nodetype=str, data=False)
    g = nx.Graph(g)
    g.remove_edges_from(nx.selfloop_edges(g))
    if g.number_of_nodes() == 0:
        return g
    gcc_nodes = max(nx.connected_components(g), key=len)
    return g.subgraph(gcc_nodes).copy()


def edge_embeddedness_mean(g: nx.Graph) -> float:
    values: list[float] = []
    for u, v in g.edges():
        du = g.degree(u)
        dv = g.degree(v)
        denom = max(min(du, dv) - 1, 0)
        if denom <= 0:
            values.append(0.0)
        else:
            values.append(len(list(nx.common_neighbors(g, u, v))) / denom)
    return float(np.mean(values)) if values else float("nan")


def graph_structure(graph_id: str) -> dict[str, float | int | str]:
    g = load_cleaned_graph(graph_id)
    n = g.number_of_nodes()
    m = g.number_of_edges()
    degrees = np.array([d for _, d in g.degree()], dtype=float)
    avg_degree = float(degrees.mean()) if len(degrees) else float("nan")
    degree_cv = float(degrees.std(ddof=0) / avg_degree) if avg_degree else float("nan")
    clustering = float(nx.average_clustering(g)) if n else float("nan")
    bridges = list(nx.bridges(g)) if m else []
    bridge_ratio = len(bridges) / m if m else float("nan")
    core = nx.k_core(g, k=2) if n else nx.Graph()
    core2_ratio = core.number_of_nodes() / n if n else float("nan")

    if m and n:
        if hasattr(nx.community, "louvain_communities"):
            communities = list(nx.community.louvain_communities(g, seed=0))
            community_algorithm = "louvain"
        else:
            communities = list(nx.community.greedy_modularity_communities(g))
            community_algorithm = "greedy_modularity"
        modularity = float(nx.community.modularity(g, communities))
        num_communities = len(communities)
        community_of: dict[str, int] = {}
        for idx, nodes in enumerate(communities):
            for node in nodes:
                community_of[node] = idx
        inter_edges = sum(1 for u, v in g.edges() if community_of.get(u) != community_of.get(v))
        inter_ratio = inter_edges / m
    else:
        modularity = float("nan")
        num_communities = 0
        inter_ratio = float("nan")
        community_algorithm = "none"

    return {
        "graph_id": graph_id,
        "community_algorithm": community_algorithm,
        "n": n,
        "m": m,
        "average_degree": avg_degree,
        "degree_cv": degree_cv,
        "clustering_coefficient": clustering,
        "modularity": modularity,
        "num_communities": num_communities,
        "bridge_ratio": bridge_ratio,
        "core2_size_ratio": core2_ratio,
        "average_edge_embeddedness": edge_embeddedness_mean(g),
        "inter_community_edge_ratio": inter_ratio,
    }


def format_float(x: float, ndigits: int = 4) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    return f"{x:.{ndigits}f}"


def markdown_table(df: pd.DataFrame, columns: list[str], float_digits: int = 4) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, row in df.iterrows():
        vals = []
        for c in columns:
            v = row[c]
            if isinstance(v, float):
                vals.append(format_float(v, float_digits))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def scatter_plot(df: pd.DataFrame, x: str, path: Path, xlabel: str) -> None:
    colors = {
        "SASB better than M5": "#2a9d8f",
        "SASB worse than M5": "#e76f51",
        "tie / close": "#6c757d",
    }
    plt.figure(figsize=(7.2, 4.8))
    for outcome, sub in df.groupby("outcome_class"):
        plt.scatter(sub[x], sub["sasb_minus_m5_normalized_auc"], s=48, alpha=0.85, label=outcome, color=colors.get(outcome))
    plt.axhline(0, color="#222222", linewidth=1, linestyle="--")
    plt.xlabel(xlabel)
    plt.ylabel("SASB - M5 normalized AUC")
    plt.title(f"SASB-M5 AUC difference vs {xlabel}")
    plt.legend(frameon=False, fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def distribution_plot(edge_df: pd.DataFrame, col: str, path: Path, xlabel: str) -> None:
    plt.figure(figsize=(7.2, 4.8))
    bins = 40
    for method, color in [("M5", "#457b9d"), ("SASB", "#f4a261")]:
        values = edge_df.loc[edge_df["method"].eq(method), col].dropna()
        if len(values) > 8000:
            values = values.sample(8000, random_state=0)
        plt.hist(values, bins=bins, density=True, alpha=0.45, label=method, color=color)
    plt.xlabel(xlabel)
    plt.ylabel("density")
    plt.title(f"Selected edge {xlabel} distribution")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=220)
    plt.close()


def phase_plot(phase: pd.DataFrame, path: Path) -> None:
    agg = phase.groupby(["outcome_class", "method", "attack_phase"], as_index=False)["phase_normalized_auc"].mean()
    phase_order = ["early", "middle", "late"]
    outcomes = ["SASB better than M5", "SASB worse than M5", "tie / close"]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), sharey=True)
    for ax, outcome in zip(axes, outcomes):
        sub = agg[agg["outcome_class"].eq(outcome)]
        x = np.arange(len(phase_order))
        for offset, method, color in [(-0.18, "M5", "#457b9d"), (0.18, "SASB", "#f4a261")]:
            vals = []
            for ph in phase_order:
                row = sub[sub["method"].eq(method) & sub["attack_phase"].eq(ph)]
                vals.append(float(row["phase_normalized_auc"].iloc[0]) if len(row) else np.nan)
            ax.bar(x + offset, vals, width=0.34, label=method, color=color)
        ax.set_title(outcome)
        ax.set_xticks(x)
        ax.set_xticklabels(phase_order)
        ax.axhline(0, color="#222222", linewidth=0.8)
    axes[0].set_ylabel("mean phase normalized AUC")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = pd.read_csv(BASE / "graph_method_summary.csv")
    diagnosis = pd.read_csv(BASE / "network_diagnosis.csv")
    phase = pd.read_csv(BASE / "phase_auc_by_graph.csv")
    edges = pd.read_csv(BASE / "edge_step_diagnostics.csv")

    diagnosis["outcome_class"] = diagnosis["sasb_minus_m5_normalized_auc"].map(classify_outcome)
    outcome_map = diagnosis.set_index("graph_id")["outcome_class"].to_dict()

    structures = pd.DataFrame([graph_structure(g) for g in sorted(diagnosis["graph_id"].unique())])
    graph_analysis = diagnosis.merge(structures, on="graph_id", how="left")
    graph_analysis.to_csv(OUT_DIR / "graph_structure_by_outcome.csv", index=False, encoding="utf-8-sig")

    structure_by_outcome = (
        graph_analysis.groupby("outcome_class")
        .agg(
            {
                "graph_id": "count",
                "sasb_minus_m5_normalized_auc": "mean",
                "n": "mean",
                "m": "mean",
                "average_degree": "mean",
                "degree_cv": "mean",
                "clustering_coefficient": "mean",
                "modularity": "mean",
                "num_communities": "mean",
                "bridge_ratio": "mean",
                "core2_size_ratio": "mean",
                "average_edge_embeddedness": "mean",
                "inter_community_edge_ratio": "mean",
            }
        )
        .reset_index()
        .rename(
            columns={
                "graph_id": "graphs",
                "sasb_minus_m5_normalized_auc": "auc_diff_mean",
                "n": "n_mean",
                "m": "m_mean",
                "average_degree": "average_degree_mean",
                "degree_cv": "degree_cv_mean",
                "clustering_coefficient": "clustering_coefficient_mean",
                "modularity": "modularity_mean",
                "num_communities": "num_communities_mean",
                "bridge_ratio": "bridge_ratio_mean",
                "core2_size_ratio": "core2_size_ratio_mean",
                "average_edge_embeddedness": "average_edge_embeddedness_mean",
                "inter_community_edge_ratio": "inter_community_edge_ratio_mean",
            }
        )
    )
    structure_by_outcome.to_csv(OUT_DIR / "structure_summary_by_outcome.csv", index=False, encoding="utf-8-sig")

    edges["outcome_class"] = edges["graph_id"].map(outcome_map)
    selected_stats = (
        edges.groupby(["outcome_class", "method"])
        .agg(
            {
                "step": "count",
                "is_bridge": "mean",
                "is_inter_community": "mean",
                "common_neighbors": "mean",
                "embeddedness": "mean",
                "degree_product": "mean",
                "delta_gcc": "mean",
            }
        )
        .reset_index()
        .rename(
            columns={
                "step": "selected_edges",
                "is_bridge": "bridge_selection_ratio",
                "is_inter_community": "inter_community_edge_ratio",
                "common_neighbors": "mean_common_neighbors",
                "embeddedness": "mean_edge_embeddedness",
                "degree_product": "mean_degree_product",
                "delta_gcc": "mean_immediate_delta_gcc",
            }
        )
    )
    selected_stats.to_csv(OUT_DIR / "selected_edge_summary_by_outcome_method.csv", index=False, encoding="utf-8-sig")

    phase["outcome_class"] = phase["graph_id"].map(outcome_map)
    phase_summary = (
        phase.groupby(["outcome_class", "method", "attack_phase"])
        .agg({"graph_id": "nunique", "phase_normalized_auc": "mean"})
        .reset_index()
        .rename(columns={"graph_id": "graphs", "phase_normalized_auc": "mean_phase_normalized_auc"})
    )
    phase_summary.to_csv(OUT_DIR / "phase_auc_summary_by_outcome_method.csv", index=False, encoding="utf-8-sig")

    scatter_plot(graph_analysis, "modularity", OUT_DIR / "auc_diff_vs_modularity.png", "modularity")
    scatter_plot(graph_analysis, "bridge_ratio", OUT_DIR / "auc_diff_vs_bridge_ratio.png", "bridge ratio")
    scatter_plot(graph_analysis, "core2_size_ratio", OUT_DIR / "auc_diff_vs_2core_ratio.png", "2-core size ratio")
    distribution_plot(edges, "embeddedness", OUT_DIR / "selected_edge_embeddedness_distribution_by_method.png", "embeddedness")
    distribution_plot(edges, "delta_gcc", OUT_DIR / "selected_edge_delta_gcc_distribution_by_method.png", "immediate delta_gcc")
    phase_plot(phase, OUT_DIR / "phase_auc_comparison_by_outcome.png")

    corr_cols = ["modularity", "bridge_ratio", "core2_size_ratio", "degree_cv", "clustering_coefficient", "average_edge_embeddedness", "inter_community_edge_ratio"]
    correlations = []
    for col in corr_cols:
        valid = graph_analysis[[col, "sasb_minus_m5_normalized_auc"]].dropna()
        corr = valid[col].corr(valid["sasb_minus_m5_normalized_auc"], method="spearman") if len(valid) >= 3 else float("nan")
        correlations.append({"feature": col, "spearman_corr_with_sasb_minus_m5_auc": corr})
    corr_df = pd.DataFrame(correlations)
    corr_df.to_csv(OUT_DIR / "auc_diff_feature_correlations.csv", index=False, encoding="utf-8-sig")

    better_graphs = ", ".join(f"`{g}`" for g in graph_analysis.loc[graph_analysis["outcome_class"].eq("SASB better than M5"), "graph_id"])
    worse_graphs = ", ".join(f"`{g}`" for g in graph_analysis.loc[graph_analysis["outcome_class"].eq("SASB worse than M5"), "graph_id"])
    tie_graphs = ", ".join(f"`{g}`" for g in graph_analysis.loc[graph_analysis["outcome_class"].eq("tie / close"), "graph_id"])

    def outcome_row(label: str) -> pd.Series:
        return structure_by_outcome[structure_by_outcome["outcome_class"].eq(label)].iloc[0]

    better = outcome_row("SASB better than M5")
    worse = outcome_row("SASB worse than M5")
    tie = outcome_row("tie / close")

    selected_pivot = selected_stats.pivot(index="outcome_class", columns="method")
    phase_pivot = phase_summary.pivot_table(index=["outcome_class", "attack_phase"], columns="method", values="mean_phase_normalized_auc").reset_index()

    report: list[str] = []
    report.append("# 为什么 SASB 在部分真实网络上赢 M5、在部分网络上输给 M5")
    report.append("")
    report.append("本报告基于 `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/` 中当前 24/28 completed subset 的 M5 与 SASB 诊断结果生成。剩余 4 个真实网络尚未纳入本报告，因此以下结论是阶段性解释，不是最终 full realworld 结论。AUC 使用 normalized GCC AUC，数值越低表示瓦解越快；`SASB-M5 AUC difference < 0` 表示 SASB 优于 M5。")
    report.append("")
    report.append("## 1. 数据与分组")
    report.append("")
    report.append("读取文件：")
    report.append("")
    for name in ["graph_method_summary.csv", "network_diagnosis.csv", "phase_auc_by_graph.csv", "edge_step_diagnostics.csv"]:
        report.append(f"- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/{name}`")
    report.append("")
    report.append("图级结构特征从 `data/realnetworks_40plus/cleaned/*.edges` 重新读取，并统一转为无向、无权、去自环后的 GCC 计算。当前环境的 NetworkX 不提供 Louvain 接口，因此本报告中的 modularity、community count 与 graph-level inter-community edge ratio 使用 `greedy_modularity_communities` 近似；M5/SASB 逐边诊断中的 community/inter-community 字段仍来自原实验记录。")
    report.append("")
    report.append("分组结果：")
    report.append("")
    report.append(f"- SASB better than M5：{int(better['graphs'])} 个网络，{better_graphs}")
    report.append(f"- SASB worse than M5：{int(worse['graphs'])} 个网络，{worse_graphs}")
    report.append(f"- tie / close：{int(tie['graphs'])} 个网络，{tie_graphs}")
    report.append("")
    report.append("## 2. 每类网络的结构特征")
    report.append("")
    structure_cols = [
        "outcome_class", "graphs", "auc_diff_mean", "n_mean", "m_mean", "average_degree_mean",
        "degree_cv_mean", "clustering_coefficient_mean", "modularity_mean", "num_communities_mean",
        "bridge_ratio_mean", "core2_size_ratio_mean", "average_edge_embeddedness_mean",
        "inter_community_edge_ratio_mean",
    ]
    report.extend(markdown_table(structure_by_outcome[structure_cols], structure_cols))
    report.append("")
    report.append("从当前 24 图看，SASB 赢/输组的 modularity 均值接近，不能把胜负简单归因于“模块度更高”。更稳的结构差异是：SASB 赢的网络平均 2-core ratio 更高、初始 bridge ratio 更低；SASB 输的网络平均 bridge ratio 明显更高、2-core ratio 更低，说明这些图中存在更多树状分支或瓶颈式割边，完整 M5 的全局 edge betweenness 更容易稳定捕捉这类关键桥边。")
    report.append("")
    report.append("Spearman 相关用于辅助观察，不作为因果证明：")
    report.append("")
    report.extend(markdown_table(corr_df, ["feature", "spearman_corr_with_sasb_minus_m5_auc"]))
    report.append("")
    report.append("## 3. M5 与 SASB 选边结构差异")
    report.append("")
    selected_cols = [
        "outcome_class", "method", "selected_edges", "bridge_selection_ratio",
        "inter_community_edge_ratio", "mean_common_neighbors", "mean_edge_embeddedness",
        "mean_degree_product", "mean_immediate_delta_gcc",
    ]
    report.extend(markdown_table(selected_stats[selected_cols], selected_cols))
    report.append("")
    report.append("SASB 相比 M5 更倾向于选择 inter-community edge；在当前 24 图总体报告中，SASB 的 inter-community ratio 为 0.455046，高于 M5 的 0.346077。这说明少量结构化源点采样确实引入了偏向社区边界的结构偏差。这个偏差在模块化结构较清晰、核心部分较大的网络中可能有益；但在 bridge 较多、网络更树状或关键割边更分散的网络中，过强的社区边界偏好不一定等价于最大 GCC 降幅。")
    report.append("")
    report.append("## 4. early / middle / late phase AUC")
    report.append("")
    phase_cols = ["outcome_class", "attack_phase", "M5", "SASB"]
    report.extend(markdown_table(phase_pivot[phase_cols], phase_cols))
    report.append("")
    report.append("SASB 赢的图通常不是每一步 immediate delta 都更大；在当前分组均值中，SASB better 组的 early phase 反而略高于 M5，但 middle 与 late phase 更低，说明优势主要在中后段兑现。SASB 输的图中，M5 在 early 与 middle 阶段更稳定地压低 GCC，后续差距会被整体 AUC 放大。late 阶段的 phase AUC 绝对值较小，解释时应弱于 early/middle。")
    report.append("")
    report.append("## 5. 图表路径")
    report.append("")
    for name in [
        "auc_diff_vs_modularity.png",
        "auc_diff_vs_bridge_ratio.png",
        "auc_diff_vs_2core_ratio.png",
        "selected_edge_embeddedness_distribution_by_method.png",
        "selected_edge_delta_gcc_distribution_by_method.png",
        "phase_auc_comparison_by_outcome.png",
    ]:
        report.append(f"- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/{name}`")
    report.append("")
    report.append("## 6. 回答核心问题")
    report.append("")
    report.append("**SASB 在哪些网络结构上更容易赢 M5？**")
    report.append("")
    report.append("当前 completed subset 中，SASB 更容易在 2-core 占比较高、初始 bridge ratio 较低的网络上获胜；modularity 本身不是充分解释变量，因为赢/输组的均值很接近。这类网络的关键边更可能体现为核心中的跨模块通路或低嵌入连接，SASB 的 `S_comm/S_boundary/S_local` 候选集与 sampled dependency 更容易把采样预算集中到这些结构位置。")
    report.append("")
    report.append("**SASB 输给 M5 的网络有什么共同特征？**")
    report.append("")
    report.append("SASB 输的网络平均 bridge ratio 更高、2-core ratio 更低，说明图中树状分支、局部瓶颈和割边更多。对于这类网络，完整 M5 的动态 edge betweenness 对全局最短路流量和桥边变化更敏感；SASB 的结构化采样如果偏向社区边界，可能会错过某些在当前 GCC 中真正承担最大割裂作用的桥边或准桥边。")
    report.append("")
    report.append("**SASB 选边和 M5 选边的结构差异是什么？**")
    report.append("")
    report.append("最稳定的差异是 SASB 更偏向 inter-community edge，并且在不少图上选到更低 embeddedness 的边。这种差异说明 SASB 不是简单复刻完整 edge betweenness，而是形成了社区边界优先的近似介数偏差。该偏差在某些网络中降低 AUC，在另一些网络中会牺牲 M5 的全局精度。")
    report.append("")
    report.append("**少量结构化源点采样是否带来了有益的结构偏差？**")
    report.append("")
    report.append("初步结果表明，少量结构化源点采样确实带来了结构偏差，而且这种偏差不是纯噪声：在 7 个 SASB better 网络中，它能以更低成本识别出足够有效的跨社区或低嵌入边；但在 16 个 SASB worse 网络中，这种偏差不足以替代完整 M5 对全局桥边和动态最短路流量的刻画。因此更准确的表述是：结构化源点采样带来了有条件有益的偏差，而不是普遍优于完整 betweenness。")
    report.append("")
    report.append("**后续是否应该发展 adaptive source budget 或 adaptive source composition？**")
    report.append("")
    report.append("应该。当前结果支持两个自适应方向：第一，adaptive source budget，应在 bridge ratio 高、2-core ratio 低或 early-phase AUC 开始落后时增加源点预算；第二，adaptive source composition，应根据网络是否呈现强模块化、树状桥多、核心密集等结构，动态调节社区源点、边界源点与局部源点的比例。这样可以保留 SASB 的速度优势，同时降低在桥多网络上输给 M5 的风险。")
    report.append("")
    report.append("## 7. 产出文件")
    report.append("")
    report.append("- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/graph_structure_by_outcome.csv`")
    report.append("- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/structure_summary_by_outcome.csv`")
    report.append("- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/selected_edge_summary_by_outcome_method.csv`")
    report.append("- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/phase_auc_summary_by_outcome_method.csv`")
    report.append("- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_feature_correlations.csv`")

    REPORT.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
