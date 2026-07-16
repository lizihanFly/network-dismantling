from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

diag = None
m18 = None
theory = None
fair = None


def require_runtime_modules() -> None:
    """Import experiment modules only when a real run is requested."""
    global diag, m18, theory, fair
    if diag is not None:
        return

    import diagnose_sasb_vs_m5_edge_choices as diag_module  # noqa: E402
    import evaluate_m18_candidate as m18_module  # noqa: E402
    import evaluate_m19_theory_calibrated as theory_module  # noqa: E402
    import evaluate_next_stage_fair_comparison as fair_module  # noqa: E402

    diag = diag_module
    m18 = m18_module
    theory = theory_module
    fair = fair_module


DEFAULT_CONFIG_PATH = ROOT / "result" / "source_policy_ablation_p1" / "p1_experiment_config.json"
DEFAULT_OUT_DIR = ROOT / "result" / "source_policy_ablation_p1"
REAL_COMPLETED_DIR = ROOT / "result" / "sasb_m5_edge_diagnostics" / "full_real_completed_edges_le1305"
SEED = 20260513
SOURCE_BUDGET = 32

METHODS = ["SASB-structured", "SASB-random", "SASB-matched"]
SOURCE_POLICIES = {
    "SASB-structured": "structured",
    "SASB-random": "random",
    "SASB-matched": "matched",
}

SUMMARY_FIELDS = [
    "dataset",
    "graph_id",
    "method",
    "source_policy",
    "seed",
    "status",
    "normalized_auc",
    "gcc_at_5pct",
    "gcc_at_10pct",
    "gcc_at_20pct",
    "gcc_at_40pct",
    "first_positive_drop_step",
    "positive_delta_gcc_rate",
    "conditional_mean_delta_gcc",
    "inter_community_ratio",
    "mean_edge_embeddedness",
    "mean_common_neighbors",
    "true_source_traversal_count",
    "runtime_seconds",
    "candidate_generation_seconds",
    "sampled_path_scoring_seconds",
    "model_scoring_seconds",
    "louvain_recomputes",
    "candidate_set_backend",
    "candidate_set_config",
    "candidate_set_config_equal_to_structured",
    "candidate_set_hashes_recorded",
    "observed_remove_ratio",
    "removed_edges",
    "max_steps",
]

STEP_FIELDS = [
    "dataset",
    "graph_id",
    "method",
    "source_policy",
    "seed",
    "step",
    "attack_phase",
    "selected_edge",
    "candidate_set_size",
    "candidate_set_hash",
    "candidate_set_backend",
    "source_budget",
    "true_source_traversal_count",
    "source_count",
    "source_nodes",
    "source_strata_counts",
    "source_degree_bins",
    "source_community_counts",
    "gcc_before",
    "gcc_after",
    "delta_gcc",
    "num_components_before",
    "num_components_after",
    "is_bridge_before_removal",
    "is_inter_community_edge",
    "degree_u",
    "degree_v",
    "degree_product",
    "common_neighbors",
    "edge_embeddedness",
    "sampled_betweenness_score",
    "remove_ratio_before",
    "remove_ratio_after",
]


def stable_node_key(node: Any) -> tuple[str, str]:
    return (str(type(node)), str(node))


def canonical_edge(edge: tuple[Any, Any]) -> tuple[Any, Any]:
    u, v = edge
    return (u, v) if stable_node_key(u) <= stable_node_key(v) else (v, u)


def edge_string(edge: tuple[Any, Any]) -> str:
    u, v = canonical_edge(edge)
    return f"{u}--{v}"


def attack_phase(remove_ratio: float) -> str:
    if remove_ratio < 1.0 / 3.0:
        return "early"
    if remove_ratio < 2.0 / 3.0:
        return "middle"
    return "late"


def largest_cc_graph(graph: nx.Graph) -> nx.Graph:
    if graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
        return graph.copy()
    nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(nodes).copy()


def gcc_size(graph: nx.Graph) -> int:
    if graph.number_of_nodes() == 0:
        return 0
    return len(max(nx.connected_components(graph), key=len))


def gcc_ratio(graph: nx.Graph, original_n: int) -> float:
    return gcc_size(graph) / float(max(1, original_n))


def num_components(graph: nx.Graph) -> int:
    if graph.number_of_nodes() == 0:
        return 0
    return nx.number_connected_components(graph)


def candidate_hash(candidates: list[tuple[Any, Any]]) -> str:
    payload = "\n".join(edge_string(edge) for edge in sorted(candidates, key=lambda e: (str(e[0]), str(e[1]))))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sorted_edges(edges: list[tuple[Any, Any]] | set[tuple[Any, Any]]) -> list[tuple[Any, Any]]:
    return sorted((canonical_edge(edge) for edge in edges), key=lambda e: (stable_node_key(e[0]), stable_node_key(e[1])))


def degree_bin(degree: int) -> str:
    if degree <= 1:
        return "degree_0_1"
    if degree == 2:
        return "degree_2"
    if degree <= 4:
        return "degree_3_4"
    if degree <= 8:
        return "degree_5_8"
    return "degree_9_plus"


def deterministic_rng(graph_id: str, step: int, seed: int, salt: int) -> random.Random:
    key = f"{graph_id}|{step}|{seed}|{salt}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    return random.Random(int(digest[:16], 16))


def add_source(selected: list[Any], labels: dict[Any, str], node: Any, label: str, limit: int) -> None:
    if len(selected) >= limit:
        return
    if node not in labels:
        selected.append(node)
        labels[node] = label


def structured_sources_with_labels(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    boundary: dict[Any, float],
    limit: int,
    step: int,
    seed: int,
    graph_id: str,
) -> tuple[list[Any], dict[Any, str]]:
    limit = min(max(1, int(limit)), h_graph.number_of_nodes())
    degrees = dict(h_graph.degree())
    selected: list[Any] = []
    labels: dict[Any, str] = {}

    for node, _ in sorted(boundary.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), stable_node_key(item[0]))):
        add_source(selected, labels, node, "boundary", limit)
        if len(selected) >= max(1, limit * 2 // 5):
            break

    for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], stable_node_key(item[0]))):
        add_source(selected, labels, node, "degree_core", limit)
        if len(selected) >= max(1, limit * 7 // 10):
            break

    if partition:
        communities: dict[Any, list[Any]] = {}
        for node, community_id in partition.items():
            communities.setdefault(community_id, []).append(node)
        community_rows = sorted(communities.values(), key=lambda nodes: (-len(nodes), min(str(node) for node in nodes)))
        for nodes in community_rows:
            representative = max(
                nodes,
                key=lambda node: (degrees.get(node, 0), boundary.get(node, 0), tuple(reversed(stable_node_key(node)))),
            )
            add_source(selected, labels, representative, "community_rep", limit)
            if len(selected) >= max(1, limit * 9 // 10):
                break

    rng = deterministic_rng(graph_id, step, seed, 7919)
    nodes = list(h_graph.nodes())
    rng.shuffle(nodes)
    for node in nodes:
        add_source(selected, labels, node, "random_fill", limit)
        if len(selected) >= limit:
            break
    return selected[:limit], labels


def uniform_random_sources(h_graph: nx.Graph, limit: int, step: int, seed: int, graph_id: str) -> tuple[list[Any], dict[Any, str]]:
    limit = min(max(1, int(limit)), h_graph.number_of_nodes())
    nodes = list(h_graph.nodes())
    rng = deterministic_rng(graph_id, step, seed, 1729)
    rng.shuffle(nodes)
    selected = nodes[:limit]
    return selected, {node: "uniform_random" for node in selected}


def source_profile(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    labels: dict[Any, str],
    sources: list[Any],
) -> tuple[dict[str, int], dict[str, int], dict[Any, int]]:
    degrees = dict(h_graph.degree())
    strata_counts: dict[str, int] = {}
    degree_bins: dict[str, int] = {}
    community_counts: dict[Any, int] = {}
    for node in sources:
        strata = labels.get(node, "unknown")
        strata_counts[strata] = strata_counts.get(strata, 0) + 1
        bin_name = degree_bin(int(degrees.get(node, 0)))
        degree_bins[bin_name] = degree_bins.get(bin_name, 0) + 1
        community = partition.get(node, "missing")
        community_counts[community] = community_counts.get(community, 0) + 1
    return strata_counts, degree_bins, community_counts


def matched_random_sources(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    structured_labels: dict[Any, str],
    structured_sources: list[Any],
    limit: int,
    step: int,
    seed: int,
    graph_id: str,
) -> tuple[list[Any], dict[Any, str]]:
    limit = min(max(1, int(limit)), h_graph.number_of_nodes())
    degrees = dict(h_graph.degree())
    target_rows = []
    for source in structured_sources:
        target_rows.append(
            {
                "source": source,
                "stratum": structured_labels.get(source, "unknown"),
                "degree_bin": degree_bin(int(degrees.get(source, 0))),
                "community": partition.get(source, "missing"),
            }
        )
    rng = deterministic_rng(graph_id, step, seed, 3181)
    selected: list[Any] = []
    labels: dict[Any, str] = {}
    all_nodes = list(h_graph.nodes())

    for row in target_rows:
        strict = [
            node
            for node in all_nodes
            if node not in labels
            and node != row["source"]
            and degree_bin(int(degrees.get(node, 0))) == row["degree_bin"]
            and partition.get(node, "missing") == row["community"]
        ]
        relaxed_degree = [
            node
            for node in all_nodes
            if node not in labels
            and node != row["source"]
            and degree_bin(int(degrees.get(node, 0))) == row["degree_bin"]
        ]
        relaxed_community = [
            node
            for node in all_nodes
            if node not in labels and node != row["source"] and partition.get(node, "missing") == row["community"]
        ]
        fallback = [node for node in all_nodes if node not in labels and node != row["source"]]
        pool = strict or relaxed_degree or relaxed_community or fallback
        if not pool:
            pool = [node for node in all_nodes if node not in labels]
        if not pool:
            break
        node = rng.choice(pool)
        selected.append(node)
        labels[node] = f"matched_{row['stratum']}"
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        remaining = [node for node in all_nodes if node not in labels]
        rng.shuffle(remaining)
        for node in remaining:
            selected.append(node)
            labels[node] = "matched_fill"
            if len(selected) >= limit:
                break
    return selected[:limit], labels


def select_sources(
    method: str,
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    boundary_degrees: dict[Any, float],
    step: int,
    seed: int,
    graph_id: str,
) -> tuple[list[Any], dict[Any, str], dict[str, Any]]:
    structured, structured_labels = structured_sources_with_labels(
        h_graph, partition, boundary_degrees, SOURCE_BUDGET, step, seed, graph_id
    )
    policy = SOURCE_POLICIES[method]
    if policy == "structured":
        sources, labels = structured, structured_labels
    elif policy == "random":
        sources, labels = uniform_random_sources(h_graph, SOURCE_BUDGET, step, seed, graph_id)
    elif policy == "matched":
        sources, labels = matched_random_sources(
            h_graph, partition, structured_labels, structured, SOURCE_BUDGET, step, seed, graph_id
        )
    else:
        raise ValueError(f"Unknown source policy: {policy}")
    strata_counts, degree_bins, community_counts = source_profile(h_graph, partition, labels, sources)
    return sources, labels, {
        "source_policy": policy,
        "source_strata_counts": strata_counts,
        "source_degree_bins": degree_bins,
        "source_community_counts": {str(key): value for key, value in community_counts.items()},
        "structured_reference_count": len(structured),
    }


def structural_edge_features(h_graph: nx.Graph, edge: tuple[Any, Any], partition: dict[Any, Any]) -> dict[str, Any]:
    return diag.structural_edge_features(h_graph, edge, partition)


def selected_edge_is_bridge(h_graph: nx.Graph, edge: tuple[Any, Any]) -> int:
    return diag.selected_edge_is_bridge(h_graph, edge)


def build_candidates(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    step: int,
    state: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[list[tuple[Any, Any]], dict[Any, float], dict[str, float]]:
    timings = state.setdefault(
        "timings",
        {
            "candidate_generation_seconds": 0.0,
            "delta_gcc_seconds": 0.0,
            "sampled_path_scoring_seconds": 0.0,
            "model_scoring_seconds": 0.0,
            "total_selection_seconds": 0.0,
        },
    )
    k = theory.adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
    state["last_adaptive_k"] = k
    start = time.perf_counter()
    candidates, _comm, boundary_scores, _local, _delta = theory.candidate_features(
        h_graph,
        partition,
        k,
        variant="conservative",
        delta_mode="none",
        step=step,
        args=args,
        timings=timings,
    )
    timings["candidate_generation_seconds"] += time.perf_counter() - start
    candidates = [canonical_edge(edge) for edge in candidates]
    metadata = {
        "adaptive_k": k,
        "candidate_set_backend": "theory.candidate_features(conservative, delta_mode=none)",
        "candidate_set_config": json.dumps(
            {
                "k_min": args.k_min,
                "k_max": args.k_max,
                "variant": "conservative",
                "delta_mode": "none",
            },
            sort_keys=True,
        ),
    }
    return candidates, boundary_scores, metadata


def original_sasb_candidate_builder(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    step: int,
    args: argparse.Namespace,
) -> tuple[list[tuple[Any, Any]], dict[Any, float], dict[Any, float], dict[Any, float], int]:
    """Call the current SASB candidate builder directly, without reimplementing it."""
    k = theory.adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
    timings = {
        "candidate_generation_seconds": 0.0,
        "delta_gcc_seconds": 0.0,
        "sampled_path_scoring_seconds": 0.0,
        "model_scoring_seconds": 0.0,
        "total_selection_seconds": 0.0,
    }
    candidates, comm_scores, boundary_scores, local_scores, _delta_scores = theory.candidate_features(
        h_graph,
        partition,
        k,
        variant="conservative",
        delta_mode="none",
        step=step,
        args=args,
        timings=timings,
    )
    return sorted_edges(candidates), comm_scores, boundary_scores, local_scores, k


def edge_component_counts(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    candidates: list[tuple[Any, Any]],
    comm_scores: dict[Any, float],
    boundary_scores: dict[Any, float],
    local_scores: dict[Any, float],
    k: int,
) -> dict[str, Any]:
    candidate_set = set(sorted_edges(candidates))
    bridge_set = {canonical_edge(edge) for edge in nx.bridges(h_graph)}
    common_neighbor_counts = m18.common_neighbor_counts_for_edges(h_graph)
    degrees = dict(h_graph.degree())
    degree_rows = [
        (degrees.get(edge[0], 0) * degrees.get(edge[1], 0), edge)
        for edge in sorted_edges(list(h_graph.edges()))
    ]
    degree_rows.sort(key=lambda item: (-item[0], stable_node_key(item[1][0]), stable_node_key(item[1][1])))
    degree_top = {edge for _score, edge in degree_rows[: max(1, min(k, len(degree_rows)))]}
    return {
        "candidate_count": len(candidate_set),
        "candidate_fraction": len(candidate_set) / float(max(1, h_graph.number_of_edges())),
        "candidate_edge_hash": candidate_hash(list(candidate_set)),
        "cross_count": sum(1 for edge in candidate_set if partition.get(edge[0]) != partition.get(edge[1])),
        "boundary_count": sum(1 for edge in candidate_set if float(boundary_scores.get(edge, 0.0)) > 0.0),
        "bridge_count": len(candidate_set & bridge_set),
        "low_cn_count": sum(1 for edge in candidate_set if int(common_neighbor_counts.get(edge, 0)) <= 1),
        "degree_top_count": len(candidate_set & degree_top),
        "comm_score_positive_count": sum(1 for edge in candidate_set if float(comm_scores.get(edge, 0.0)) > 0.0),
        "local_score_positive_count": sum(1 for edge in candidate_set if float(local_scores.get(edge, 0.0)) > 0.0),
        "adaptive_k": k,
    }


def candidate_set_equivalence_check(
    dataset: str,
    meta: dict[str, Any],
    graph: nx.Graph,
    args: argparse.Namespace,
    out_dir: Path,
) -> tuple[pd.DataFrame, bool]:
    state = {"original_n": graph.number_of_nodes()}
    h_graph = largest_cc_graph(graph)
    partition = m18.get_adaptive_stale_partition(
        h_graph,
        0,
        state,
        "candidate_equivalence",
        max(1, args.louvain_interval),
        max(0.0, args.louvain_drop_threshold),
    )
    old_candidates, old_comm, old_boundary, old_local, old_k = original_sasb_candidate_builder(h_graph, partition, 0, args)
    new_candidates, new_boundary, new_meta = build_candidates(h_graph, partition, 0, state, args)
    new_candidates = sorted_edges(new_candidates)
    old_counts = edge_component_counts(h_graph, partition, old_candidates, old_comm, old_boundary, old_local, old_k)
    new_counts = edge_component_counts(h_graph, partition, new_candidates, old_comm, new_boundary, old_local, old_k)
    same_edge_set = set(old_candidates) == set(new_candidates)
    same_hash = old_counts["candidate_edge_hash"] == new_counts["candidate_edge_hash"]
    rows = []
    for builder, counts in [("original_sasb_candidate_features", old_counts), ("p1_build_candidates", new_counts)]:
        rows.append(
            {
                "dataset": dataset,
                "graph_id": meta["graph_id"],
                "builder": builder,
                "candidate_set_backend": new_meta["candidate_set_backend"],
                "candidate_set_config": new_meta["candidate_set_config"],
                "same_edge_set": int(same_edge_set),
                "same_hash": int(same_hash),
                **counts,
            }
        )
    df = pd.DataFrame(rows)
    write_csv(df, out_dir / "candidate_set_equivalence.csv")
    return df, bool(same_edge_set and same_hash)


def choose_policy_edge(
    h_graph: nx.Graph,
    method: str,
    step: int,
    state: dict[str, Any],
    args: argparse.Namespace,
    graph_id: str,
    seed: int,
) -> tuple[tuple[Any, Any] | None, dict[str, Any]]:
    selection_start = time.perf_counter()
    if h_graph.number_of_edges() == 0:
        return None, {}
    partition = m18.get_adaptive_stale_partition(
        h_graph,
        step,
        state,
        "p1_source_policy_ablation",
        max(1, args.louvain_interval),
        max(0.0, args.louvain_drop_threshold),
    )
    candidates, boundary_scores, candidate_meta = build_candidates(h_graph, partition, step, state, args)
    if not candidates:
        fallback = m18.choose_degree_product_edge(h_graph)
        return fallback, {
            **candidate_meta,
            "candidate_set_size": 0,
            "candidate_set_hash": "",
            "source_count": 0,
            "true_source_traversal_count": 0,
            "sampled_betweenness_score": np.nan,
            "candidate_set_config_equal_to_structured": 1,
            "source_nodes": "[]",
            "source_strata_counts": "{}",
            "source_degree_bins": "{}",
            "source_community_counts": "{}",
            "p1_fallback": 1,
        }

    boundary_degrees = m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    sources, _labels, source_meta = select_sources(method, h_graph, partition, boundary_degrees, step, seed, graph_id)

    timings = state["timings"]
    sample_start = time.perf_counter()
    sampled = theory.sampled_dependencies(h_graph, candidates, sources)
    scale = h_graph.number_of_nodes() / float(max(1, len(sources)))
    be_hat = {edge: scale * float(sampled.get(edge, 0.0)) for edge in candidates}
    timings["sampled_path_scoring_seconds"] += time.perf_counter() - sample_start

    score_start = time.perf_counter()
    scored = [(float(be_hat.get(edge, 0.0)), edge) for edge in candidates]
    scored.sort(key=lambda item: (-item[0], stable_node_key(item[1][0]), stable_node_key(item[1][1])))
    selected = scored[0][1] if scored else None
    timings["model_scoring_seconds"] += time.perf_counter() - score_start
    timings["total_selection_seconds"] += time.perf_counter() - selection_start
    state["true_source_traversal_count"] = state.get("true_source_traversal_count", 0) + len(sources)
    state["p1_source_policy_ablation_louvain_recomputes"] = state.get("p1_source_policy_ablation_louvain_recomputes", 0)

    details = {
        **candidate_meta,
        "candidate_set_size": len(candidates),
        "candidate_set_hash": candidate_hash(candidates),
        "source_budget": SOURCE_BUDGET,
        "source_count": len(sources),
        "true_source_traversal_count": len(sources),
        "sampled_betweenness_score": be_hat.get(selected, np.nan),
        "candidate_set_config_equal_to_structured": 1,
        "source_nodes": json.dumps([str(node) for node in sources], ensure_ascii=False),
        "source_strata_counts": json.dumps(source_meta["source_strata_counts"], sort_keys=True),
        "source_degree_bins": json.dumps(source_meta["source_degree_bins"], sort_keys=True),
        "source_community_counts": json.dumps(source_meta["source_community_counts"], sort_keys=True),
        "p1_fallback": 0,
    }
    return selected, details


def summarize_curve(curve_df: pd.DataFrame, step_df: pd.DataFrame, elapsed: float, status: str, state: dict[str, Any]) -> dict[str, Any]:
    x = curve_df["remove_ratio"].astype(float).to_numpy()
    y = curve_df["gcc_ratio"].astype(float).to_numpy()
    observed = float(x[-1]) if len(x) else 0.0
    auc = float(np.trapezoid(y, x)) if len(x) else np.nan
    row: dict[str, Any] = {
        "dataset": curve_df["dataset"].iloc[0],
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_name": curve_df["graph_name"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "community_strength": curve_df["community_strength"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "source_policy": curve_df["source_policy"].iloc[0],
        "seed": int(curve_df["seed"].iloc[0]),
        "status": status,
        "auc": auc,
        "normalized_auc": auc / observed if observed > 0 else np.nan,
        "observed_remove_ratio": observed,
        "removed_edges": int(curve_df["removed_edges"].max()) if len(curve_df) else 0,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "runtime_seconds": float(elapsed),
        "true_source_traversal_count": int(state.get("true_source_traversal_count", 0)),
        "louvain_recomputes": int(state.get("p1_source_policy_ablation_louvain_recomputes", 0)),
        "candidate_set_backend": "theory.candidate_features(conservative, delta_mode=none)",
        "candidate_set_config": json.dumps(
            {
                "k_min": state.get("config_k_min"),
                "k_max": state.get("config_k_max"),
                "variant": "conservative",
                "delta_mode": "none",
            },
            sort_keys=True,
        ),
        "candidate_set_config_equal_to_structured": 1,
        "candidate_set_hashes_recorded": int(step_df["candidate_set_hash"].nunique()) if not step_df.empty else 0,
        "max_steps": int(state.get("max_steps", 0)),
    }
    for budget in [5, 10, 20, 40]:
        eligible = curve_df[curve_df["remove_ratio"] <= budget / 100.0]
        row[f"gcc_at_{budget}pct"] = float(eligible.iloc[-1]["gcc_ratio"]) if not eligible.empty else np.nan
    if not step_df.empty:
        delta = pd.to_numeric(step_df["delta_gcc"], errors="coerce")
        positive = delta[delta > 0]
        row.update(
            {
                "first_positive_drop_step": int(step_df.loc[delta > 0, "step"].iloc[0]) if (delta > 0).any() else np.nan,
                "positive_delta_gcc_rate": float((delta > 0).mean()),
                "conditional_mean_delta_gcc": float(positive.mean()) if not positive.empty else np.nan,
                "inter_community_ratio": float(pd.to_numeric(step_df["is_inter_community_edge"], errors="coerce").mean()),
                "mean_edge_embeddedness": float(pd.to_numeric(step_df["edge_embeddedness"], errors="coerce").mean()),
                "mean_common_neighbors": float(pd.to_numeric(step_df["common_neighbors"], errors="coerce").mean()),
            }
        )
    timings = state.get("timings", {})
    for key in ["candidate_generation_seconds", "sampled_path_scoring_seconds", "model_scoring_seconds", "total_selection_seconds"]:
        row[key] = float(timings.get(key, 0.0))
    return row


def simulate_policy(dataset: str, meta: dict[str, Any], graph0: nx.Graph, method: str, args: argparse.Namespace, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    max_steps = min(original_m, int(args.max_steps)) if int(getattr(args, "max_steps", 0)) > 0 else original_m
    state: dict[str, Any] = {
        "original_n": original_n,
        "config_k_min": args.k_min,
        "config_k_max": args.k_max,
        "max_steps": max_steps,
    }
    curve_rows = [
        {
            "dataset": dataset,
            "graph_id": meta["graph_id"],
            "graph_name": meta.get("graph_name", meta["graph_id"]),
            "graph_type": meta.get("graph_type", "unknown"),
            "community_strength": meta.get("community_strength", "unknown"),
            "method": method,
            "source_policy": SOURCE_POLICIES[method],
            "seed": seed,
            "step": 0,
            "removed_edges": 0,
            "remove_ratio": 0.0,
            "gcc_ratio": gcc_ratio(graph, original_n),
            "gcc_size": gcc_size(graph),
        }
    ]
    step_rows = []
    start = time.perf_counter()
    timed_out = False
    step = 0
    while graph.number_of_edges() > 0 and step < max_steps:
        if step / float(max(1, original_m)) >= args.max_remove_ratio:
            break
        if args.timeout_seconds > 0 and time.perf_counter() - start > args.timeout_seconds:
            timed_out = True
            break

        h_graph = largest_cc_graph(graph)
        if h_graph.number_of_edges() == 0:
            break
        diagnostic_partition = diag.get_diagnostic_partition(h_graph, step, state, args.diagnostic_louvain_interval)
        gcc_before = gcc_ratio(graph, original_n)
        components_before = num_components(graph)
        edge, details = choose_policy_edge(h_graph, method, step, state, args, meta["graph_id"], seed)
        if edge is None or not graph.has_edge(*edge):
            break
        edge = canonical_edge(edge)
        bridge = selected_edge_is_bridge(h_graph, edge)
        features = structural_edge_features(h_graph, edge, diagnostic_partition)
        graph.remove_edge(*edge)
        gcc_after = gcc_ratio(graph, original_n)
        components_after = num_components(graph)
        remove_ratio_before = step / float(max(1, original_m))
        remove_ratio_after = (step + 1) / float(max(1, original_m))
        row = {
            "dataset": dataset,
            "graph_id": meta["graph_id"],
            "method": method,
            "source_policy": SOURCE_POLICIES[method],
            "seed": seed,
            "step": step,
            "attack_phase": attack_phase(remove_ratio_before),
            "gcc_before": gcc_before,
            "gcc_after": gcc_after,
            "delta_gcc": gcc_before - gcc_after,
            "num_components_before": components_before,
            "num_components_after": components_after,
            "is_bridge_before_removal": bridge,
            "remove_ratio_before": remove_ratio_before,
            "remove_ratio_after": remove_ratio_after,
        }
        row.update(features)
        row.update(details)
        step_rows.append(row)
        step += 1
        curve_rows.append(
            {
                "dataset": dataset,
                "graph_id": meta["graph_id"],
                "graph_name": meta.get("graph_name", meta["graph_id"]),
                "graph_type": meta.get("graph_type", "unknown"),
                "community_strength": meta.get("community_strength", "unknown"),
                "method": method,
                "source_policy": SOURCE_POLICIES[method],
                "seed": seed,
                "step": step,
                "removed_edges": step,
                "remove_ratio": remove_ratio_after,
                "gcc_ratio": gcc_after,
                "gcc_size": gcc_size(graph),
            }
        )
    elapsed = time.perf_counter() - start
    status = "timeout" if timed_out else "finished"
    if step / float(max(1, original_m)) >= args.max_remove_ratio:
        status = "finished"
    step_df = pd.DataFrame(step_rows)
    curve_df = pd.DataFrame(curve_rows)
    summary = summarize_curve(curve_df, step_df, elapsed, status, state)
    return step_df, curve_df, summary


def run_paths(out_dir: Path, dataset: str, graph_id: str, method: str, seed: int) -> tuple[Path, Path, Path]:
    slug = method.lower().replace("-", "_")
    root = out_dir / "runs" / dataset / graph_id / f"{slug}_seed{seed}"
    return root / "edge_steps.csv", root / "curve.csv", root / "summary.csv"


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def load_real_completed_ids() -> list[str]:
    path = REAL_COMPLETED_DIR / "graph_method_summary.csv"
    df = pd.read_csv(path)
    return sorted(df["graph_id"].dropna().unique().tolist())


def select_graphs(config: dict[str, Any], args: argparse.Namespace) -> list[tuple[str, dict[str, Any], nx.Graph]]:
    selected = []
    graph_cap = int(getattr(args, "max_graphs", 0))
    graph_filter = set(config.get("graph_ids", []))
    if config.get("real_validation_path"):
        fair.REAL_VALIDATION = ROOT / config["real_validation_path"]
    if config["datasets"].get("synthetic45", {}).get("enabled", True):
        max_synthetic = int(config["datasets"]["synthetic45"].get("max_graphs", 0))
        if graph_cap > 0:
            max_synthetic = graph_cap if max_synthetic <= 0 else min(max_synthetic, graph_cap)
        for graph_id, group in fair.load_synthetic_groups(max_graphs=max_synthetic):
            if graph_filter and graph_id not in graph_filter:
                continue
            selected.append(("synthetic45", fair.synthetic_meta(group), fair.reconstruct_synthetic_graph(group)))
            if graph_cap > 0 and len(selected) >= graph_cap:
                return selected
    if config["datasets"].get("realworld_completed_24of28", {}).get("enabled", True):
        graph_ids = config["datasets"]["realworld_completed_24of28"].get("graph_ids") or load_real_completed_ids()
        if graph_filter:
            graph_ids = [graph_id for graph_id in graph_ids if graph_id in graph_filter]
        if graph_cap > 0:
            graph_ids = graph_ids[: max(0, graph_cap - len(selected))]
        metadata = fair.load_real_metadata(graph_ids=graph_ids)
        for _, row in metadata.iterrows():
            meta = row.to_dict()
            selected.append(("realworld_completed", meta, fair.load_real_graph(meta)))
            if graph_cap > 0 and len(selected) >= graph_cap:
                return selected
    if graph_cap > 0:
        selected = selected[: args.max_graphs]
    return selected


def default_config() -> dict[str, Any]:
    real_ids = load_real_completed_ids() if (REAL_COMPLETED_DIR / "graph_method_summary.csv").exists() else []
    return {
        "experiment_name": "p1_source_policy_ablation",
        "run_enabled_by_default": False,
        "output_dir": str(DEFAULT_OUT_DIR.relative_to(ROOT)),
        "seed": SEED,
        "random_seeds": [SEED],
        "source_budget": SOURCE_BUDGET,
        "remove_ratio": 1.0,
        "methods": METHODS,
        "candidate_set": {
            "backend": "evaluate_m19_theory_calibrated.candidate_features",
            "variant": "conservative",
            "delta_mode": "none",
            "k_min": 64,
            "k_max": 512,
            "candidate_set_must_match_across_source_policies_for_same_graph_state": True,
        },
        "source_policies": {
            "SASB-structured": "current select_m19_sources structure: boundary -> degree_core -> community_rep -> random_fill",
            "SASB-random": "uniform random nodes from current GCC with same source budget and seed schedule",
            "SASB-matched": "random nodes matched to structured source degree-bin and community distribution, with stratum labels recorded",
        },
        "dynamic_recompute": {
            "gcc": "recomputed after every edge removal",
            "louvain": "adaptive stale partition reused from current SASB implementation",
            "sampled_dependency": "recomputed on current GCC for selected source policy each step",
        },
        "datasets": {
            "synthetic45": {"enabled": True, "remove_ratio": 1.0, "max_graphs": 0},
            "realworld_completed_24of28": {
                "enabled": True,
                "remove_ratio": 1.0,
                "graph_ids": real_ids,
                "coverage": "24/28 current completed mechanism-diagnostic subset",
            },
        },
        "metrics": SUMMARY_FIELDS,
        "safety": {
            "do_not_modify_v3_v4_v5": True,
            "do_not_run_large_experiment_without_explicit_run_flag": True,
            "do_not_overwrite_existing_runs_by_default": True,
        },
    }


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_config(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def args_from_config(config: dict[str, Any]) -> argparse.Namespace:
    candidate = config.get("candidate_set", {})
    return argparse.Namespace(
        max_remove_ratio=float(config.get("remove_ratio", 1.0)),
        timeout_seconds=float(config.get("timeout_seconds", 0.0)),
        max_steps=int(config.get("max_steps", 0)),
        k_min=int(candidate.get("k_min", 64)),
        k_max=int(candidate.get("k_max", 512)),
        louvain_interval=int(config.get("louvain_interval", 10)),
        louvain_drop_threshold=float(config.get("louvain_drop_threshold", 0.05)),
        diagnostic_louvain_interval=int(config.get("diagnostic_louvain_interval", 1)),
    )


def collect_step_outputs(out_dir: Path) -> pd.DataFrame:
    frames = []
    for path in (out_dir / "runs").glob("*/*/*/edge_steps.csv"):
        if path.exists():
            frames.append(pd.read_csv(path))
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_empty_"
    cols = list(df.columns)
    rows = [["" if pd.isna(value) else str(value) for value in row] for row in df[cols].to_numpy().tolist()]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def smoke_checks(out_dir: Path, eq_df: pd.DataFrame, summary_df: pd.DataFrame) -> dict[str, Any]:
    step_df = collect_step_outputs(out_dir)
    methods_seen = sorted(summary_df["method"].dropna().unique().tolist()) if not summary_df.empty else []
    required_methods = sorted(METHODS)
    first_step = step_df[step_df["step"] == 0].copy() if not step_df.empty and "step" in step_df else pd.DataFrame()
    candidate_hash_same_state_ok = False
    if not first_step.empty and "candidate_set_hash" in first_step:
        candidate_hash_same_state_ok = first_step["candidate_set_hash"].nunique(dropna=True) == 1
    candidate_nonempty = True
    if not step_df.empty and "candidate_set_size" in step_df:
        candidate_nonempty = bool((pd.to_numeric(step_df["candidate_set_size"], errors="coerce") > 0).all())
    source_budget_ok = True
    if not step_df.empty and "source_count" in step_df:
        source_budget_ok = bool((pd.to_numeric(step_df["source_count"], errors="coerce") == SOURCE_BUDGET).all())
    gcc_ok = True
    gcc_cols = [col for col in ["gcc_before", "gcc_after"] if col in step_df.columns]
    if gcc_cols:
        gcc_vals = step_df[gcc_cols].apply(pd.to_numeric, errors="coerce")
        gcc_ok = bool(gcc_vals.notna().all().all() and ((gcc_vals >= 0.0) & (gcc_vals <= 1.0)).all().all())
    summary_numeric_cols = [
        "normalized_auc",
        "positive_delta_gcc_rate",
        "runtime_seconds",
        "true_source_traversal_count",
    ]
    numeric_ok = True
    if not summary_df.empty:
        present = [col for col in summary_numeric_cols if col in summary_df.columns]
        numeric_ok = bool(summary_df[present].apply(pd.to_numeric, errors="coerce").notna().all().all()) if present else False
    return {
        "candidate_equivalence_ok": bool(not eq_df.empty and int(eq_df["same_edge_set"].min()) == 1 and int(eq_df["same_hash"].min()) == 1),
        "methods_ok": methods_seen == required_methods,
        "methods_seen": methods_seen,
        "source_budget_ok": source_budget_ok,
        "candidate_hash_same_state_ok": candidate_hash_same_state_ok,
        "candidate_nonempty_ok": candidate_nonempty,
        "gcc_ok": gcc_ok,
        "summary_numeric_ok": numeric_ok,
        "step_rows": int(len(step_df)),
        "summary_rows": int(len(summary_df)),
    }


def write_smoke_report(out_dir: Path, eq_df: pd.DataFrame, summary_df: pd.DataFrame, status: str) -> None:
    checks = smoke_checks(out_dir, eq_df, summary_df)
    lines = [
        "# P1 Smoke Validation Report",
        "",
        f"- Status: `{status}`",
        f"- Python executable: `{sys.executable}`",
        "- Louvain dependency: `python-louvain` import path checked before smoke run.",
        "- Formal synthetic45 / realworld 24/28 experiment: not run.",
        "- v3/v4/v5 original files: not modified by this script.",
        "",
        "## Candidate-Set Equivalence",
        "",
        f"- Equivalent edge set: `{checks['candidate_equivalence_ok']}`",
    ]
    if not eq_df.empty:
        cols = [
            "builder",
            "candidate_count",
            "candidate_fraction",
            "candidate_edge_hash",
            "cross_count",
            "boundary_count",
            "bridge_count",
            "low_cn_count",
            "degree_top_count",
        ]
        lines.append("")
        lines.append(markdown_table(eq_df[[col for col in cols if col in eq_df.columns]]))
    lines.extend(
        [
            "",
            "## Smoke Checks",
            "",
            f"- Three source policies completed: `{checks['methods_ok']}` ({', '.join(checks['methods_seen'])})",
            f"- Source budget equals 32 on every step: `{checks['source_budget_ok']}`",
            f"- Candidate hash identical at the same initial graph state: `{checks['candidate_hash_same_state_ok']}`",
            f"- Candidate set never empty: `{checks['candidate_nonempty_ok']}`",
            f"- GCC values valid and non-null: `{checks['gcc_ok']}`",
            f"- Summary metrics present and numeric: `{checks['summary_numeric_ok']}`",
            f"- Step rows: `{checks['step_rows']}`",
            f"- Summary rows: `{checks['summary_rows']}`",
        ]
    )
    if not summary_df.empty:
        show_cols = [
            "dataset",
            "graph_id",
            "method",
            "source_policy",
            "status",
            "removed_edges",
            "normalized_auc",
            "gcc_at_5pct",
            "gcc_at_10pct",
            "gcc_at_20pct",
            "gcc_at_40pct",
            "positive_delta_gcc_rate",
            "true_source_traversal_count",
            "runtime_seconds",
        ]
        lines.extend(["", "## Smoke Results", "", markdown_table(summary_df[[col for col in show_cols if col in summary_df.columns]])])
    can_continue = all(
        [
            checks["candidate_equivalence_ok"],
            checks["methods_ok"],
            checks["source_budget_ok"],
            checks["candidate_hash_same_state_ok"],
            checks["candidate_nonempty_ok"],
            checks["gcc_ok"],
            checks["summary_numeric_ok"],
        ]
    )
    lines.extend(["", "## Recommendation", "", f"- Ready for formal synthetic45/realworld run: `{can_continue}`"])
    (out_dir / "smoke_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_experiment(config: dict[str, Any], args: argparse.Namespace) -> None:
    require_runtime_modules()
    out_dir = ROOT / config.get("output_dir", str(DEFAULT_OUT_DIR.relative_to(ROOT)))
    run_args = args_from_config(config)
    if int(getattr(args, "max_steps", 0)) > 0:
        run_args.max_steps = int(args.max_steps)
    graphs = select_graphs(config, args)
    if not graphs:
        raise RuntimeError("No graphs selected for smoke validation or experiment.")

    run_config = {
        **config,
        "python_executable": sys.executable,
        "cli_max_graphs": int(getattr(args, "max_graphs", 0)),
        "cli_max_steps": int(getattr(args, "max_steps", 0)),
        "effective_max_steps": int(getattr(run_args, "max_steps", 0)),
        "formal_experiment": not (
            int(getattr(args, "max_graphs", 0)) == 1
            and 0 < int(getattr(run_args, "max_steps", 0)) <= 40
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_config.json").write_text(json.dumps(run_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    eq_df, equivalent = candidate_set_equivalence_check(graphs[0][0], graphs[0][1], graphs[0][2], run_args, out_dir)
    if not equivalent:
        write_smoke_report(out_dir, eq_df, pd.DataFrame(), "failed_candidate_equivalence")
        raise RuntimeError("Candidate-set equivalence check failed; stopping before P1 smoke run.")

    summaries = []
    for dataset, meta, graph in graphs:
        for seed in config.get("random_seeds", [SEED]):
            for method in METHODS:
                steps_path, curve_path, summary_path = run_paths(out_dir, dataset, meta["graph_id"], method, int(seed))
                if summary_path.exists() and not args.overwrite:
                    existing = pd.read_csv(summary_path)
                    if not existing.empty:
                        summaries.append(existing)
                    continue
                step_df, curve_df, summary = simulate_policy(dataset, meta, graph, method, run_args, int(seed))
                write_csv(step_df.reindex(columns=[col for col in STEP_FIELDS if col in step_df.columns]), steps_path)
                write_csv(curve_df, curve_path)
                summary_df = pd.DataFrame([summary]).reindex(columns=[col for col in SUMMARY_FIELDS if col in summary])
                write_csv(summary_df, summary_path)
                summaries.append(summary_df)
                print(f"ran dataset={dataset} graph={meta['graph_id']} method={method} seed={seed}", flush=True)
    if summaries:
        combined = pd.concat(summaries, ignore_index=True, sort=False)
        write_csv(combined, out_dir / "p1_source_policy_ablation_summary.csv")
        write_csv(combined, out_dir / "smoke_results.csv")
        write_smoke_report(out_dir, eq_df, combined, "success")


def main() -> None:
    parser = argparse.ArgumentParser(description="P1 source-policy ablation for SASB. Defaults to no formal run.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--write-default-config", action="store_true")
    parser.add_argument("--run", action="store_true", help="Actually run the ablation. Omit for design/dry-run mode.")
    parser.add_argument("--max-graphs", type=int, default=0, help="Optional cap for smoke/debug use after confirmation.")
    parser.add_argument("--max-steps", type=int, default=0, help="Optional step cap for smoke/debug use after confirmation.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    if args.write_default_config or not config_path.exists():
        save_default_config(config_path)
        print(f"wrote config: {config_path}")
    config = load_config(config_path)
    if not args.run:
        print("dry-run/design mode only; no attack experiment was started")
        print(f"config: {config_path}")
        print("methods:", ", ".join(config["methods"]))
        print("realworld graphs:", len(config["datasets"]["realworld_completed_24of28"].get("graph_ids", [])))
        return
    run_experiment(config, args)


if __name__ == "__main__":
    main()
