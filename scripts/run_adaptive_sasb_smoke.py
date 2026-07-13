from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_m18_candidate as m18  # noqa: E402
import evaluate_m19_realworld_40plus as real40  # noqa: E402
import evaluate_m19_theory_calibrated as theory  # noqa: E402


DIAG_DIR = ROOT / "result" / "sasb_m5_edge_diagnostics" / "full_real_completed_edges_le1305"
WHY_DIR = ROOT / "result" / "sasb_m5_edge_diagnostics" / "why_sasb_wins_or_loses"
REPORT_PATH = ROOT / "result" / "sasb_m5_edge_diagnostics" / "adaptive_sasb_smoke_report.md"
DATA_DIR = ROOT / "data" / "realnetworks_40plus" / "cleaned"
SEED = 20260707

METHODS = ["SASB-k32", "SASB-k64", "Adaptive-SASB"]

SMOKE_GRAPHS = [
    "football",
    "bio_diseasome",
    "bio_celegansneural",
    "soc_wiki_vote",
    "ca_csphd",
    "bio_grid_mouse",
    "rt_twitter_copen",
    "inf_power",
]


def canonical_edge(edge):
    u, v = edge
    return (u, v) if u <= v else (v, u)


def top_edges(scores: dict[tuple[int, int], float], k: int) -> list[tuple[int, int]]:
    ranked = sorted(scores.items(), key=lambda item: (-float(item[1]), item[0][0], item[0][1]))
    return [edge for edge, _ in ranked[: max(0, k)]]


def largest_cc_subgraph(graph: nx.Graph) -> nx.Graph:
    if graph.number_of_nodes() == 0:
        return graph.copy()
    nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(nodes).copy()


def gcc_size(graph: nx.Graph) -> int:
    if graph.number_of_nodes() == 0:
        return 0
    return len(max(nx.connected_components(graph), key=len))


def selected_edge_is_bridge(h_graph: nx.Graph, edge: tuple[int, int]) -> int:
    u, v = canonical_edge(edge)
    if not h_graph.has_edge(u, v):
        return 0
    h_graph.remove_edge(u, v)
    try:
        return int(not nx.has_path(h_graph, u, v))
    finally:
        h_graph.add_edge(u, v)


def core2_ratio(h_graph: nx.Graph) -> float:
    if h_graph.number_of_nodes() == 0:
        return 0.0
    if h_graph.number_of_edges() == 0:
        return 0.0
    core = nx.k_core(h_graph, k=2)
    return core.number_of_nodes() / float(max(1, h_graph.number_of_nodes()))


def bridge_ratio(h_graph: nx.Graph) -> float:
    m = h_graph.number_of_edges()
    if m == 0:
        return 0.0
    return sum(1 for _ in nx.bridges(h_graph)) / float(m)


def node_add(selected: list[int], labels: dict[int, str], node: int, label: str, limit: int) -> None:
    if len(selected) >= limit:
        return
    if node not in labels:
        selected.append(node)
        labels[node] = label


def current_mixed_sources(
    h_graph: nx.Graph,
    partition: dict[int, int],
    boundary: dict[int, float],
    limit: int,
    step: int,
) -> tuple[list[int], dict[int, str]]:
    limit = max(1, int(limit))
    degrees = dict(h_graph.degree())
    selected: list[int] = []
    labels: dict[int, str] = {}

    for node, _ in sorted(boundary.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), item[0])):
        node_add(selected, labels, node, "boundary", limit)
        if len(selected) >= max(1, limit * 2 // 5):
            break

    for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], item[0])):
        node_add(selected, labels, node, "degree", limit)
        if len(selected) >= max(1, limit * 7 // 10):
            break

    if partition:
        communities: dict[int, list[int]] = {}
        for node, community_id in partition.items():
            communities.setdefault(community_id, []).append(node)
        community_rows = sorted(communities.values(), key=lambda nodes: (-len(nodes), min(nodes)))
        for nodes in community_rows:
            representative = max(nodes, key=lambda node: (degrees.get(node, 0), boundary.get(node, 0), -node))
            node_add(selected, labels, representative, "community", limit)
            if len(selected) >= max(1, limit * 9 // 10):
                break

    rng = random.Random(SEED + 7919 + step)
    nodes = list(h_graph.nodes())
    rng.shuffle(nodes)
    for node in nodes:
        node_add(selected, labels, node, "random_fill", limit)
        if len(selected) >= limit:
            break
    return selected[:limit], labels


def adaptive_sources(
    h_graph: nx.Graph,
    partition: dict[int, int],
    boundary: dict[int, float],
    limit: int,
    step: int,
) -> tuple[list[int], dict[int, str]]:
    limit = max(1, int(limit))
    degrees = dict(h_graph.degree())
    selected: list[int] = []
    labels: dict[int, str] = {}

    bridges = list(nx.bridges(h_graph))
    bridge_nodes: dict[int, int] = {}
    for u, v in bridges:
        bridge_nodes[u] = bridge_nodes.get(u, 0) + 1
        bridge_nodes[v] = bridge_nodes.get(v, 0) + 1
    for node, _ in sorted(bridge_nodes.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), item[0])):
        node_add(selected, labels, node, "bridge_neighbor", limit)
        if len(selected) >= max(1, int(math.ceil(limit * 0.30))):
            break

    core_nodes = set(nx.k_core(h_graph, k=2).nodes()) if h_graph.number_of_edges() else set()
    core_boundary_scores: dict[int, int] = {}
    if core_nodes:
        for node in core_nodes:
            outside = sum(1 for nbr in h_graph.neighbors(node) if nbr not in core_nodes)
            if outside:
                core_boundary_scores[node] = outside
        if not core_boundary_scores:
            for node in core_nodes:
                core_boundary_scores[node] = degrees.get(node, 0)
    for node, _ in sorted(core_boundary_scores.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), item[0])):
        node_add(selected, labels, node, "core2_boundary", limit)
        if len(selected) >= max(1, int(math.ceil(limit * 0.55))):
            break

    for node, _ in sorted(boundary.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), item[0])):
        node_add(selected, labels, node, "community_boundary", limit)
        if len(selected) >= max(1, int(math.ceil(limit * 0.75))):
            break

    for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], item[0])):
        node_add(selected, labels, node, "degree", limit)
        if len(selected) >= max(1, int(math.ceil(limit * 0.90))):
            break

    rng = random.Random(SEED + 104729 + step)
    nodes = list(h_graph.nodes())
    rng.shuffle(nodes)
    for node in nodes:
        node_add(selected, labels, node, "random_fill", limit)
        if len(selected) >= limit:
            break
    return selected[:limit], labels


def method_policy(method: str, h_graph: nx.Graph) -> tuple[int, int, str, float, float]:
    br = bridge_ratio(h_graph)
    c2 = core2_ratio(h_graph)
    if method == "SASB-k32":
        return 32, 32, "current_mixed", br, c2
    if method == "SASB-k64":
        return 64, 64, "current_mixed", br, c2
    if br >= 0.15 or c2 <= 0.75:
        return 64, 64, "bridge_core_adaptive", br, c2
    return 32, 32, "current_mixed", br, c2


def select_edge(
    h_graph: nx.Graph,
    method: str,
    step: int,
    state: dict,
) -> tuple[tuple[int, int] | None, dict]:
    if h_graph.number_of_edges() == 0:
        return None, {}

    timings = state.setdefault(
        "timings",
        {
            "candidate_generation_seconds": 0.0,
            "sampled_path_scoring_seconds": 0.0,
            "model_scoring_seconds": 0.0,
            "total_selection_seconds": 0.0,
        },
    )
    start = time.perf_counter()
    k, sample_count, source_mode, br, c2 = method_policy(method, h_graph)

    cand_start = time.perf_counter()
    partition = m18.get_adaptive_stale_partition(
        h_graph,
        step,
        state,
        method.lower().replace("-", "_"),
        interval=10,
        drop_threshold=0.05,
    )
    args = argparse.Namespace(
        recall_plus_random_fraction=0.05,
        recall_plus_candidate_multiplier=2.0,
        recall_plus_max_candidates=512,
    )
    candidates, comm, boundary_scores, local_scores, _ = theory.candidate_features(
        h_graph,
        partition,
        k,
        variant="conservative",
        delta_mode="none",
        step=step,
        args=args,
        timings={"delta_gcc_seconds": 0.0},
    )
    timings["candidate_generation_seconds"] += time.perf_counter() - cand_start
    if not candidates:
        degrees = dict(h_graph.degree())
        ranked = sorted(h_graph.edges(), key=lambda e: (-(degrees[e[0]] * degrees[e[1]]), canonical_edge(e)))
        return canonical_edge(ranked[0]), {"fallback": 1}

    boundary = m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    if source_mode == "bridge_core_adaptive":
        sources, source_labels = adaptive_sources(h_graph, partition, boundary, sample_count, step)
    else:
        sources, source_labels = current_mixed_sources(h_graph, partition, boundary, sample_count, step)

    sample_start = time.perf_counter()
    sampled = theory.sampled_dependencies(h_graph, candidates, sources)
    scale = h_graph.number_of_nodes() / float(max(1, len(sources)))
    be_hat = {edge: scale * sampled.get(edge, 0.0) for edge in candidates}
    timings["sampled_path_scoring_seconds"] += time.perf_counter() - sample_start

    score_start = time.perf_counter()
    scored = [(float(be_hat.get(edge, 0.0)), edge) for edge in candidates]
    scored.sort(key=lambda item: (-item[0], item[1][0], item[1][1]))
    timings["model_scoring_seconds"] += time.perf_counter() - score_start
    timings["total_selection_seconds"] += time.perf_counter() - start

    counts: dict[str, int] = {}
    for source in sources:
        label = source_labels.get(source, "unknown")
        counts[label] = counts.get(label, 0) + 1
    selected = scored[0][1] if scored else None
    return selected, {
        "fallback": 0,
        "candidate_set_size": len(candidates),
        "k": k,
        "sample_sources": len(sources),
        "source_mode": source_mode,
        "current_bridge_ratio": br,
        "current_core2_ratio": c2,
        **{f"source_{key}": value for key, value in counts.items()},
    }


def edge_features(h_graph: nx.Graph, edge: tuple[int, int], partition: dict[int, int] | None) -> dict:
    u, v = canonical_edge(edge)
    common = len(list(nx.common_neighbors(h_graph, u, v))) if h_graph.has_edge(u, v) else 0
    du = h_graph.degree(u)
    dv = h_graph.degree(v)
    denom = max(1, min(du, dv) - 1)
    return {
        "degree_product": du * dv,
        "common_neighbors": common,
        "embeddedness": common / float(denom),
        "is_inter_community": int(bool(partition) and partition.get(u) != partition.get(v)),
        "is_bridge": selected_edge_is_bridge(h_graph, edge),
    }


def simulate(graph0: nx.Graph, graph_id: str, method: str, max_remove_ratio: float = 1.0, max_steps: int = 0) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    limit_steps = max_steps if max_steps > 0 else original_m
    state: dict = {}
    rows = []
    curves = [{"graph_id": graph_id, "method": method, "step": 0, "remove_ratio": 0.0, "gcc_ratio": gcc_size(graph) / float(max(1, original_n))}]
    start = time.perf_counter()
    step = 0
    while graph.number_of_edges() > 0 and step < limit_steps:
        if step / float(max(1, original_m)) >= max_remove_ratio:
            break
        h_graph = largest_cc_subgraph(graph)
        if h_graph.number_of_edges() == 0:
            break
        partition = m18.m17.louvain_partition(h_graph)
        gcc_before = gcc_size(graph) / float(max(1, original_n))
        edge, details = select_edge(h_graph, method, step, state)
        if edge is None or not graph.has_edge(*edge):
            break
        features = edge_features(h_graph, edge, partition)
        graph.remove_edge(*edge)
        gcc_after = gcc_size(graph) / float(max(1, original_n))
        remove_ratio_after = (step + 1) / float(max(1, original_m))
        phase = "early" if remove_ratio_after < 1 / 3 else "middle" if remove_ratio_after < 2 / 3 else "late"
        rows.append(
            {
                "graph_id": graph_id,
                "method": method,
                "step": step,
                "remove_ratio_after": remove_ratio_after,
                "attack_phase": phase,
                "edge_u": edge[0],
                "edge_v": edge[1],
                "gcc_before": gcc_before,
                "gcc_after": gcc_after,
                "delta_gcc": gcc_before - gcc_after,
                **features,
                **details,
            }
        )
        curves.append({"graph_id": graph_id, "method": method, "step": step + 1, "remove_ratio": remove_ratio_after, "gcc_ratio": gcc_after})
        step += 1

    elapsed = time.perf_counter() - start
    curve_df = pd.DataFrame(curves)
    x = curve_df["remove_ratio"].astype(float).values
    y = curve_df["gcc_ratio"].astype(float).values
    auc = float(np.trapz(y, x)) if len(x) else np.nan
    observed = float(x[-1]) if len(x) else 0.0
    normalized_auc = auc / observed if observed > 0 else np.nan
    step_df = pd.DataFrame(rows)
    summary = {
        "graph_id": graph_id,
        "method": method,
        "status": "finished",
        "removed_edges": step,
        "observed_remove_ratio": observed,
        "auc": auc,
        "normalized_auc": normalized_auc,
        "runtime_seconds": elapsed,
        "candidate_generation_seconds": state.get("timings", {}).get("candidate_generation_seconds", 0.0),
        "sampled_path_scoring_seconds": state.get("timings", {}).get("sampled_path_scoring_seconds", 0.0),
        "model_scoring_seconds": state.get("timings", {}).get("model_scoring_seconds", 0.0),
        "total_selection_seconds": state.get("timings", {}).get("total_selection_seconds", 0.0),
        "mean_k": step_df["k"].mean() if "k" in step_df else np.nan,
        "mean_sample_sources": step_df["sample_sources"].mean() if "sample_sources" in step_df else np.nan,
        "bridge_core_adaptive_step_ratio": float((step_df.get("source_mode", pd.Series(dtype=str)) == "bridge_core_adaptive").mean()) if len(step_df) else np.nan,
        "bridge_selection_ratio_full": step_df["is_bridge"].mean() if "is_bridge" in step_df else np.nan,
        "early_bridge_selection_ratio": step_df.loc[step_df["attack_phase"].eq("early"), "is_bridge"].mean() if len(step_df) else np.nan,
        "middle_bridge_selection_ratio": step_df.loc[step_df["attack_phase"].eq("middle"), "is_bridge"].mean() if len(step_df) else np.nan,
        "late_bridge_selection_ratio": step_df.loc[step_df["attack_phase"].eq("late"), "is_bridge"].mean() if len(step_df) else np.nan,
        "mean_delta_gcc": step_df["delta_gcc"].mean() if "delta_gcc" in step_df else np.nan,
        "mean_embeddedness": step_df["embeddedness"].mean() if "embeddedness" in step_df else np.nan,
        "inter_community_edge_ratio": step_df["is_inter_community"].mean() if "is_inter_community" in step_df else np.nan,
    }
    source_cols = [
        c
        for c in step_df.columns
        if c.startswith("source_") and c != "source_mode" and pd.api.types.is_numeric_dtype(step_df[c])
    ]
    for col in source_cols:
        summary[f"mean_{col}"] = step_df[col].fillna(0).mean()
        summary[f"ratio_{col}"] = step_df[col].fillna(0).sum() / float(max(1, step_df["sample_sources"].fillna(0).sum()))
    return step_df, curve_df, summary


def choose_smoke_graphs() -> pd.DataFrame:
    graph_struct = pd.read_csv(WHY_DIR / "graph_structure_by_outcome.csv")
    selected = graph_struct[graph_struct["graph_id"].isin(SMOKE_GRAPHS)].copy()
    selected["selection_reason"] = selected["graph_id"].map(
        {
            "football": "SASB better; low bridge, core2=1, small social graph",
            "bio_diseasome": "SASB better; moderate bridge, modular biological graph",
            "bio_celegansneural": "SASB better; very low bridge, high 2-core",
            "soc_wiki_vote": "SASB better; medium scale, moderate core2",
            "ca_csphd": "SASB worse; extremely high bridge, very low 2-core",
            "bio_grid_mouse": "SASB worse; high bridge, low 2-core",
            "rt_twitter_copen": "SASB worse; high bridge, low 2-core, medium scale",
            "inf_power": "SASB worse; large infrastructure graph, high bridge pressure",
        }
    )
    return selected.sort_values(["outcome_class", "graph_id"])


def corrected_bridge_diagnostics(edge_steps: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    full = (
        edge_steps.groupby(["graph_id", "method"])["is_bridge"]
        .mean()
        .unstack()
        .reset_index()
        .rename(columns={"M5": "m5_full_bridge_ratio", "SASB": "sasb_full_bridge_ratio"})
    )
    full["full_ratio_diff"] = full["sasb_full_bridge_ratio"] - full["m5_full_bridge_ratio"]
    phase = (
        edge_steps.groupby(["graph_id", "method", "attack_phase"])["is_bridge"]
        .mean()
        .reset_index()
        .pivot_table(index=["graph_id", "attack_phase"], columns="method", values="is_bridge")
        .reset_index()
        .rename(columns={"M5": "m5_phase_bridge_ratio", "SASB": "sasb_phase_bridge_ratio"})
    )
    phase["phase_ratio_diff"] = phase["sasb_phase_bridge_ratio"] - phase["m5_phase_bridge_ratio"]
    return full, phase


def plot_curves(curves: pd.DataFrame, out_dir: Path) -> None:
    for graph_id, group in curves.groupby("graph_id"):
        plt.figure(figsize=(6.4, 4.2))
        for method, sub in group.groupby("method"):
            plt.plot(sub["remove_ratio"], sub["gcc_ratio"], label=method, linewidth=1.5)
        plt.xlabel("removed edge ratio")
        plt.ylabel("GCC ratio")
        plt.title(graph_id)
        plt.legend(frameon=False, fontsize=8)
        plt.tight_layout()
        plt.savefig(out_dir / "plots" / f"{graph_id}_gcc_curves.png", dpi=180)
        plt.close()


def write_report(
    out_dir: Path,
    selected: pd.DataFrame,
    summary: pd.DataFrame,
    bridge_full: pd.DataFrame,
    bridge_phase: pd.DataFrame,
    max_remove_ratio: float,
    max_steps: int,
) -> None:
    m5 = pd.read_csv(DIAG_DIR / "graph_method_summary.csv")
    m5 = m5[m5["method"].eq("M5")][["graph_id", "normalized_auc", "runtime_seconds"]].rename(
        columns={"normalized_auc": "m5_auc", "runtime_seconds": "m5_runtime_seconds"}
    )
    sasb_old = pd.read_csv(DIAG_DIR / "network_diagnosis.csv")[["graph_id", "outcome", "sasb_minus_m5_normalized_auc"]]
    merged = summary.merge(m5, on="graph_id", how="left").merge(sasb_old, on="graph_id", how="left")
    merged["speedup_vs_m5"] = merged["m5_runtime_seconds"] / merged["runtime_seconds"]
    merged["auc_minus_m5"] = merged["normalized_auc"] - merged["m5_auc"]
    merged.to_csv(out_dir / "summary_with_m5_baseline.csv", index=False, encoding="utf-8-sig")

    pivot = merged.pivot_table(index="graph_id", columns="method", values="normalized_auc").reset_index()
    pivot = pivot.merge(sasb_old, on="graph_id", how="left")
    pivot["adaptive_minus_k32"] = pivot["Adaptive-SASB"] - pivot["SASB-k32"]
    pivot["adaptive_minus_k64"] = pivot["Adaptive-SASB"] - pivot["SASB-k64"]
    better_group = pivot[pivot["outcome"].eq("SASB_better")]
    worse_group = pivot[pivot["outcome"].eq("SASB_worse")]

    method_summary = merged.groupby("method", as_index=False).agg(
        {
            "normalized_auc": "mean",
            "runtime_seconds": "mean",
            "speedup_vs_m5": "mean",
            "mean_k": "mean",
            "mean_sample_sources": "mean",
            "bridge_core_adaptive_step_ratio": "mean",
        }
    )

    source_cols = [c for c in merged.columns if c.startswith("ratio_source_")]
    source_summary = merged.groupby("method", as_index=False)[source_cols].mean() if source_cols else pd.DataFrame()
    method_summary.to_csv(out_dir / "method_average_summary.csv", index=False, encoding="utf-8-sig")
    source_summary.to_csv(out_dir / "source_composition_summary.csv", index=False, encoding="utf-8-sig")
    pivot.to_csv(out_dir / "adaptive_vs_fixed_auc_delta.csv", index=False, encoding="utf-8-sig")

    def md_table(df: pd.DataFrame, cols: list[str], digits: int = 6) -> list[str]:
        rows = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
        for _, row in df.iterrows():
            vals = []
            for col in cols:
                val = row.get(col, "")
                if isinstance(val, float):
                    vals.append(f"{val:.{digits}f}")
                else:
                    vals.append(str(val))
            rows.append("| " + " | ".join(vals) + " |")
        return rows

    lines = [
        "# Adaptive-SASB smoke test 报告",
        "",
        f"输出目录：`{out_dir.relative_to(ROOT).as_posix()}`",
        "",
        "本实验只在当前 24/28 completed subset 中选出的 8 个真实网络上做 smoke test；不修改当前 running queue，不覆盖既有结果。三种方法均沿用 sampled-BE ranking，区别在于候选/源点预算和源点组成。",
        "",
        "评价口径：本次运行为 prefix smoke，`max_steps={}`，`max_remove_ratio={}`。因此下文 AUC 是 observed prefix 上的 normalized AUC，不能与 100% edge-removal full AUC 直接混用。".format(max_steps, max_remove_ratio),
        "",
        "## 1. bridge_selection_ratio 字段核验与统计修复",
        "",
        "`edge_step_diagnostics.csv` 中 `is_bridge` / `is_bridge_before_removal` 的语义是：被选中的边在删除前是否为当前 GCC 中的 bridge。字段本身是有效的。",
        "",
        "但当前诊断是 100% edge removal。对任意从连通图删到无边图的完整删除序列，bridge 删除次数等于最终连通分量增加量，即约为 `n-1`，因此全程平均 bridge selection ratio 是 order-invariant 的，M5 与 SASB 会完全一样。这不是选边行为相同，而是全程统计口径失去区分度。",
        "",
        "修复后的统计口径：保留全程 bridge ratio 作为一致性检查，但主要使用 early/middle/late phase bridge ratio 观察选边偏差。",
        "",
        "全程 bridge ratio 差异检查：",
        "",
    ]
    lines.extend(md_table(bridge_full[["graph_id", "m5_full_bridge_ratio", "sasb_full_bridge_ratio", "full_ratio_diff"]].head(8), ["graph_id", "m5_full_bridge_ratio", "sasb_full_bridge_ratio", "full_ratio_diff"]))
    lines.extend(
        [
            "",
            "分阶段 bridge ratio 文件：`{}/bridge_selection_corrected_by_phase.csv`。".format(out_dir.relative_to(ROOT).as_posix()),
            "",
            "## 2. smoke-test 网络选择",
            "",
        ]
    )
    lines.extend(md_table(selected[["graph_id", "outcome_class", "bridge_ratio", "core2_size_ratio", "m", "selection_reason"]], ["graph_id", "outcome_class", "bridge_ratio", "core2_size_ratio", "m", "selection_reason"], digits=4))
    lines.extend(["", "## 3. 每个网络的 AUC、runtime、speedup", ""])
    lines.extend(md_table(merged[["graph_id", "outcome", "method", "normalized_auc", "runtime_seconds", "speedup_vs_m5", "mean_k", "mean_sample_sources", "bridge_core_adaptive_step_ratio"]], ["graph_id", "outcome", "method", "normalized_auc", "runtime_seconds", "speedup_vs_m5", "mean_k", "mean_sample_sources", "bridge_core_adaptive_step_ratio"], digits=4))
    lines.extend(["", "## 4. 方法平均表现", ""])
    lines.extend(md_table(method_summary, list(method_summary.columns), digits=4))
    lines.extend(["", "## 5. source composition 实际比例", ""])
    if not source_summary.empty:
        lines.extend(md_table(source_summary, list(source_summary.columns), digits=4))
    lines.extend(["", "## 6. Adaptive-SASB 是否改善 worse 组、是否损害 better 组", ""])
    lines.append(
        "- SASB worse 组：Adaptive-SASB 相比 SASB-k32 的 mean AUC delta = `{:.6f}`，小于 0 表示改善。".format(
            float(worse_group["adaptive_minus_k32"].mean()) if len(worse_group) else np.nan
        )
    )
    lines.append(
        "- SASB better 组：Adaptive-SASB 相比 SASB-k32 的 mean AUC delta = `{:.6f}`，大于 0 表示损害。".format(
            float(better_group["adaptive_minus_k32"].mean()) if len(better_group) else np.nan
        )
    )
    lines.append(
        "- SASB worse 组逐图改善数：`{}/{}`。".format(
            int((worse_group["adaptive_minus_k32"] < 0).sum()) if len(worse_group) else 0,
            len(worse_group),
        )
    )
    lines.append(
        "- SASB better 组逐图未损害数：`{}/{}`。".format(
            int((better_group["adaptive_minus_k32"] <= 0).sum()) if len(better_group) else 0,
            len(better_group),
        )
    )
    lines.extend(
        [
            "",
            "解释边界：这是 8 图 smoke test，不是最终结论。Adaptive 规则如果在 worse 组降低 AUC，同时在 better 组不明显升高 AUC，才说明值得扩展到 24 图或完整 28 图。",
            "",
            "## 7. 输出文件",
            "",
            f"- `{(out_dir / 'per_graph_method_summary.csv').relative_to(ROOT).as_posix()}`",
            f"- `{(out_dir / 'summary_with_m5_baseline.csv').relative_to(ROOT).as_posix()}`",
            f"- `{(out_dir / 'source_composition_summary.csv').relative_to(ROOT).as_posix()}`",
            f"- `{(out_dir / 'adaptive_vs_fixed_auc_delta.csv').relative_to(ROOT).as_posix()}`",
            f"- `{(out_dir / 'plots').relative_to(ROOT).as_posix()}/`",
            "",
            "原始逐边过程文件 `edge_steps.csv` 与逐步曲线 `curves.csv` 仅在本地结果目录保留，不作为 GitHub curated update 的重点内容。",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-remove-ratio", type=float, default=1.0)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--graph-ids", default=",".join(SMOKE_GRAPHS))
    parser.add_argument("--out-dir", default="")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "result" / "sasb_m5_edge_diagnostics" / f"adaptive_sasb_smoke_{timestamp}"
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    if out_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {out_dir}")
    (out_dir / "plots").mkdir(parents=True, exist_ok=False)

    graph_ids = [g.strip() for g in args.graph_ids.split(",") if g.strip()]
    selected = choose_smoke_graphs()
    selected = selected[selected["graph_id"].isin(graph_ids)].copy()
    selected.to_csv(out_dir / "selected_smoke_graphs.csv", index=False, encoding="utf-8-sig")

    original_steps = pd.read_csv(DIAG_DIR / "edge_step_diagnostics.csv", usecols=["graph_id", "method", "attack_phase", "is_bridge"])
    bridge_full, bridge_phase = corrected_bridge_diagnostics(original_steps)
    bridge_full.to_csv(out_dir / "bridge_selection_full_order_invariant_check.csv", index=False, encoding="utf-8-sig")
    bridge_phase.to_csv(out_dir / "bridge_selection_corrected_by_phase.csv", index=False, encoding="utf-8-sig")

    all_steps = []
    all_curves = []
    summaries = []
    for graph_id in graph_ids:
        path = DATA_DIR / f"{graph_id}.edges"
        graph = real40.load_cleaned_graph(path)
        for method in METHODS:
            print(f"running {graph_id} {method}", flush=True)
            step_df, curve_df, summary = simulate(graph, graph_id, method, max_remove_ratio=args.max_remove_ratio, max_steps=args.max_steps)
            all_steps.append(step_df)
            all_curves.append(curve_df)
            summaries.append(summary)
            pd.DataFrame([summary]).to_csv(out_dir / f"{graph_id}_{method}_summary.csv", index=False, encoding="utf-8-sig")

    steps = pd.concat(all_steps, ignore_index=True, sort=False)
    curves = pd.concat(all_curves, ignore_index=True, sort=False)
    summary_df = pd.DataFrame(summaries)
    steps.to_csv(out_dir / "edge_steps.csv", index=False, encoding="utf-8-sig")
    curves.to_csv(out_dir / "curves.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(out_dir / "per_graph_method_summary.csv", index=False, encoding="utf-8-sig")
    (out_dir / "run_config.json").write_text(
        json.dumps({"graph_ids": graph_ids, "methods": METHODS, "max_remove_ratio": args.max_remove_ratio, "max_steps": args.max_steps}, indent=2),
        encoding="utf-8",
    )
    plot_curves(curves, out_dir)
    write_report(out_dir, selected, summary_df, bridge_full, bridge_phase, args.max_remove_ratio, args.max_steps)
    print(f"Wrote {REPORT_PATH}", flush=True)
    print(f"Outputs in {out_dir}", flush=True)


if __name__ == "__main__":
    main()
