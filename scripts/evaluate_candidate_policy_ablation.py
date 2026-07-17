from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evaluate_source_policy_ablation as p1  # noqa: E402


OUT_DIR = ROOT / "result" / "candidate_policy_ablation_p2"
CONFIG_PATH = OUT_DIR / "p2_experiment_config.json"
P1_REAL_VALIDATION = ROOT / "result" / "source_policy_ablation_p1" / "formal_realworld_validation" / "graph_validation_summary.csv"
SEED = 20260513
SOURCE_BUDGET = 32

METHODS = [
    "SASB-candidate",
    "Random-size-matched-candidate",
    "Structure-matched-candidate",
]
CANDIDATE_POLICIES = {
    "SASB-candidate": "sasb",
    "Random-size-matched-candidate": "random_size_matched",
    "Structure-matched-candidate": "structure_matched",
}
CORE_COMPARISONS = [
    ("SASB-candidate", "Structure-matched-candidate"),
    ("SASB-candidate", "Random-size-matched-candidate"),
    ("Structure-matched-candidate", "Random-size-matched-candidate"),
]
PRIMARY = "normalized_auc"
SECONDARY = ["gcc_at_5pct", "gcc_at_10pct", "gcc_at_20pct", "gcc_at_40pct"]
MECHANISM = [
    "first_positive_drop_step",
    "positive_delta_gcc_rate",
    "conditional_mean_delta_gcc",
    "inter_community_ratio",
    "mean_edge_embeddedness",
    "mean_common_neighbors",
]
COST = [
    "runtime_seconds",
    "true_source_traversal_count",
    "candidate_generation_seconds",
    "sampled_path_scoring_seconds",
    "model_scoring_seconds",
    "louvain_recomputes",
]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def stable_edge_sort(edge: tuple[Any, Any]) -> tuple[tuple[str, str], tuple[str, str]]:
    edge = p1.canonical_edge(edge)
    return p1.stable_node_key(edge[0]), p1.stable_node_key(edge[1])


def deterministic_rng(graph_id: str, step: int, seed: int, salt: int, policy: str) -> random.Random:
    payload = f"p2|{graph_id}|{step}|{seed}|{salt}|{policy}".encode("utf-8")
    return random.Random(int(hashlib.sha256(payload).hexdigest()[:16], 16))


def distribution(counter: Counter[str]) -> dict[str, float]:
    total = sum(counter.values())
    if total <= 0:
        return {}
    return {key: counter[key] / total for key in sorted(counter)}


def l1_distribution_distance(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    return float(sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys))


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def degree_product_bin(value: int) -> str:
    if value <= 4:
        return "dp_0_4"
    if value <= 16:
        return "dp_5_16"
    if value <= 64:
        return "dp_17_64"
    if value <= 256:
        return "dp_65_256"
    return "dp_257_plus"


def common_neighbor_bin(value: int) -> str:
    if value <= 0:
        return "cn_0"
    if value == 1:
        return "cn_1"
    if value <= 3:
        return "cn_2_3"
    if value <= 8:
        return "cn_4_8"
    return "cn_9_plus"


def feature_counter(rows: list[dict[str, Any]], key: str) -> Counter[str]:
    return Counter(str(row.get(key, "missing")) for row in rows)


def feature_distribution(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    return distribution(feature_counter(rows, key))


def candidate_feature_difference(reference: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, float]:
    keys = [
        "is_inter_community_edge",
        "is_boundary_edge",
        "is_bridge_edge",
        "is_low_common_neighbor_edge",
        "degree_product_bin",
        "common_neighbor_bin",
    ]
    diffs = {f"{key}_l1": l1_distribution_distance(feature_distribution(reference, key), feature_distribution(selected, key)) for key in keys}
    diffs["mean_l1"] = float(np.mean(list(diffs.values()))) if diffs else np.nan
    return diffs


def edge_feature_rows(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    boundary_scores: dict[Any, float],
) -> dict[tuple[Any, Any], dict[str, Any]]:
    bridge_set = {p1.canonical_edge(edge) for edge in nx.bridges(h_graph)}
    cn = p1.m18.common_neighbor_counts_for_edges(h_graph)
    degrees = dict(h_graph.degree())
    rows: dict[tuple[Any, Any], dict[str, Any]] = {}
    for edge in p1.sorted_edges(list(h_graph.edges())):
        u, v = edge
        common_neighbors = int(cn.get(edge, 0))
        degree_product = int(degrees.get(u, 0) * degrees.get(v, 0))
        boundary_value = float(boundary_scores.get(edge, boundary_scores.get((v, u), 0.0)))
        rows[edge] = {
            "edge": edge,
            "is_inter_community_edge": int(partition.get(u) != partition.get(v)),
            "is_boundary_edge": int(boundary_value > 0.0),
            "is_bridge_edge": int(edge in bridge_set),
            "is_low_common_neighbor_edge": int(common_neighbors <= 1),
            "degree_product": degree_product,
            "common_neighbors": common_neighbors,
            "degree_product_bin": degree_product_bin(degree_product),
            "common_neighbor_bin": common_neighbor_bin(common_neighbors),
        }
    return rows


def summarize_candidate_rows(rows: list[dict[str, Any]], total_edges: int) -> dict[str, Any]:
    if not rows:
        return {
            "candidate_count": 0,
            "candidate_fraction": 0.0,
            "candidate_inter_community_ratio": np.nan,
            "candidate_boundary_ratio": np.nan,
            "candidate_bridge_ratio": np.nan,
            "candidate_low_cn_ratio": np.nan,
            "candidate_degree_product_distribution": "{}",
            "candidate_common_neighbor_distribution": "{}",
            "candidate_mean_common_neighbors": np.nan,
            "candidate_mean_degree_product": np.nan,
        }
    return {
        "candidate_count": len(rows),
        "candidate_fraction": len(rows) / float(max(1, total_edges)),
        "candidate_inter_community_ratio": float(np.mean([row["is_inter_community_edge"] for row in rows])),
        "candidate_boundary_ratio": float(np.mean([row["is_boundary_edge"] for row in rows])),
        "candidate_bridge_ratio": float(np.mean([row["is_bridge_edge"] for row in rows])),
        "candidate_low_cn_ratio": float(np.mean([row["is_low_common_neighbor_edge"] for row in rows])),
        "candidate_degree_product_distribution": json_dumps(feature_distribution(rows, "degree_product_bin")),
        "candidate_common_neighbor_distribution": json_dumps(feature_distribution(rows, "common_neighbor_bin")),
        "candidate_mean_common_neighbors": float(np.mean([row["common_neighbors"] for row in rows])),
        "candidate_mean_degree_product": float(np.mean([row["degree_product"] for row in rows])),
    }


def sasb_candidates(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    step: int,
    state: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[list[tuple[Any, Any]], dict[Any, float], dict[str, Any]]:
    k = p1.theory.adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
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
    start = time.perf_counter()
    candidates, _comm, boundary_scores, _local, _delta = p1.theory.candidate_features(
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
    state["last_adaptive_k"] = k
    config = {
        "backend": "evaluate_m19_theory_calibrated.candidate_features",
        "variant": "conservative",
        "delta_mode": "none",
        "k_min": args.k_min,
        "k_max": args.k_max,
    }
    return p1.sorted_edges(candidates), boundary_scores, {"adaptive_k": k, "candidate_config": json_dumps(config)}


def random_size_matched_candidates(
    all_edges: list[tuple[Any, Any]],
    count: int,
    graph_id: str,
    step: int,
    seed: int,
) -> tuple[list[tuple[Any, Any]], dict[str, Any]]:
    rng = deterministic_rng(graph_id, step, seed, 4241, "random_size_matched")
    pool = list(all_edges)
    rng.shuffle(pool)
    selected = p1.sorted_edges(pool[: min(count, len(pool))])
    return selected, {
        "match_mode_counts": {"random_size_matched": len(selected)},
        "strict_match_count": 0,
        "degree_only_match_count": 0,
        "community_only_match_count": 0,
        "fallback_count": 0,
        "fallback_reason_counts": {},
    }


def structure_matched_candidates(
    all_edges: list[tuple[Any, Any]],
    sasb_edges: list[tuple[Any, Any]],
    feature_map: dict[tuple[Any, Any], dict[str, Any]],
    graph_id: str,
    step: int,
    seed: int,
) -> tuple[list[tuple[Any, Any]], dict[str, Any]]:
    rng = deterministic_rng(graph_id, step, seed, 8677, "structure_matched")
    remaining = set(all_edges)
    selected: list[tuple[Any, Any]] = []
    mode_counts: Counter[str] = Counter()
    fallback_reasons: Counter[str] = Counter()
    target_rows = [feature_map[edge] for edge in sasb_edges if edge in feature_map]

    for target in target_rows:
        if not remaining:
            fallback_reasons["no_remaining_edges"] += 1
            break

        def available(predicate: Any) -> list[tuple[Any, Any]]:
            return [edge for edge in remaining if predicate(feature_map[edge])]

        strict = available(
            lambda row: row["is_inter_community_edge"] == target["is_inter_community_edge"]
            and row["is_boundary_edge"] == target["is_boundary_edge"]
            and row["is_bridge_edge"] == target["is_bridge_edge"]
            and row["is_low_common_neighbor_edge"] == target["is_low_common_neighbor_edge"]
            and row["degree_product_bin"] == target["degree_product_bin"]
            and row["common_neighbor_bin"] == target["common_neighbor_bin"]
        )
        degree_only = available(
            lambda row: row["degree_product_bin"] == target["degree_product_bin"]
            and row["common_neighbor_bin"] == target["common_neighbor_bin"]
        )
        community_only = available(
            lambda row: row["is_inter_community_edge"] == target["is_inter_community_edge"]
            and row["is_boundary_edge"] == target["is_boundary_edge"]
        )
        fallback = list(remaining)

        if strict:
            pool = strict
            mode = "strict"
        elif degree_only:
            pool = degree_only
            mode = "degree_only"
            fallback_reasons["no_strict_match"] += 1
        elif community_only:
            pool = community_only
            mode = "community_only"
            fallback_reasons["no_strict_or_degree_match"] += 1
        else:
            pool = fallback
            mode = "fallback"
            fallback_reasons["no_strict_degree_or_community_match"] += 1

        edge = rng.choice(pool)
        remaining.remove(edge)
        selected.append(edge)
        mode_counts[mode] += 1

    return p1.sorted_edges(selected), {
        "match_mode_counts": dict(mode_counts),
        "strict_match_count": int(mode_counts.get("strict", 0)),
        "degree_only_match_count": int(mode_counts.get("degree_only", 0)),
        "community_only_match_count": int(mode_counts.get("community_only", 0)),
        "fallback_count": int(mode_counts.get("fallback", 0)),
        "fallback_reason_counts": dict(fallback_reasons),
    }


def build_policy_candidates(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    method: str,
    step: int,
    state: dict[str, Any],
    args: argparse.Namespace,
    graph_id: str,
    seed: int,
) -> tuple[list[tuple[Any, Any]], dict[Any, float], dict[str, Any]]:
    sasb, boundary_scores, sasb_meta = sasb_candidates(h_graph, partition, step, state, args)
    all_edges = p1.sorted_edges(list(h_graph.edges()))
    feature_map = edge_feature_rows(h_graph, partition, boundary_scores)
    sasb_rows = [feature_map[edge] for edge in sasb if edge in feature_map]
    policy = CANDIDATE_POLICIES[method]

    start = time.perf_counter()
    if policy == "sasb":
        candidates = sasb
        match_meta = {
            "match_mode_counts": {"sasb_builder": len(candidates)},
            "strict_match_count": 0,
            "degree_only_match_count": 0,
            "community_only_match_count": 0,
            "fallback_count": 0,
            "fallback_reason_counts": {},
        }
        backend = "sasb_candidate_builder"
    elif policy == "random_size_matched":
        candidates, match_meta = random_size_matched_candidates(all_edges, len(sasb), graph_id, step, seed)
        backend = "uniform_random_edges_size_matched_to_sasb"
    elif policy == "structure_matched":
        candidates, match_meta = structure_matched_candidates(all_edges, sasb, feature_map, graph_id, step, seed)
        backend = "random_edges_structure_matched_to_sasb"
    else:
        raise ValueError(f"Unknown candidate policy: {policy}")
    state["timings"]["candidate_generation_seconds"] += time.perf_counter() - start

    selected_rows = [feature_map[edge] for edge in candidates if edge in feature_map]
    feature_diff = candidate_feature_difference(sasb_rows, selected_rows)
    summary = summarize_candidate_rows(selected_rows, h_graph.number_of_edges())
    meta = {
        **sasb_meta,
        **summary,
        "candidate_backend": backend,
        "candidate_policy": policy,
        "candidate_hash": p1.candidate_hash(candidates),
        "sasb_candidate_count_reference": len(sasb),
        "sasb_candidate_hash_reference": p1.candidate_hash(sasb),
        "match_mode_counts": json_dumps(match_meta["match_mode_counts"]),
        "strict_match_count": int(match_meta["strict_match_count"]),
        "degree_only_match_count": int(match_meta["degree_only_match_count"]),
        "community_only_match_count": int(match_meta["community_only_match_count"]),
        "fallback_count": int(match_meta["fallback_count"]),
        "fallback_reason": json_dumps(match_meta["fallback_reason_counts"]),
        "matched_feature_difference": float(feature_diff["mean_l1"]),
        "matched_feature_difference_detail": json_dumps(feature_diff),
        "candidate_count_equal_to_sasb": int(len(candidates) == len(sasb)),
    }
    return candidates, boundary_scores, meta


def select_fixed_sources(
    h_graph: nx.Graph,
    partition: dict[Any, Any],
    step: int,
    seed: int,
    graph_id: str,
) -> tuple[list[Any], dict[Any, str], dict[str, Any]]:
    boundary_degrees = p1.m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    sources, labels = p1.structured_sources_with_labels(
        h_graph, partition, boundary_degrees, SOURCE_BUDGET, step, seed, graph_id
    )
    strata_counts, degree_bins, community_counts = p1.source_profile(h_graph, partition, labels, sources)
    return sources, labels, {
        "source_policy": "SASB-structured",
        "source_count": len(sources),
        "source_nodes": json.dumps([str(node) for node in sources], ensure_ascii=False),
        "source_node_hash": hashlib.sha256(
            "\n".join(str(node) for node in sources).encode("utf-8")
        ).hexdigest(),
        "source_strata_counts": json_dumps(strata_counts),
        "source_degree_bins": json_dumps(degree_bins),
        "source_community_counts": json_dumps({str(key): value for key, value in community_counts.items()}),
    }


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
    partition = p1.m18.get_adaptive_stale_partition(
        h_graph,
        step,
        state,
        "p2_candidate_policy_ablation",
        max(1, args.louvain_interval),
        max(0.0, args.louvain_drop_threshold),
    )
    sources, _labels, source_meta = select_fixed_sources(h_graph, partition, step, seed, graph_id)
    candidates, _boundary_scores, candidate_meta = build_policy_candidates(
        h_graph, partition, method, step, state, args, graph_id, seed
    )

    if not candidates:
        fallback = p1.m18.choose_degree_product_edge(h_graph)
        return fallback, {
            **source_meta,
            **candidate_meta,
            "selected_edge": p1.edge_string(fallback) if fallback is not None else "",
            "source_budget": SOURCE_BUDGET,
            "true_source_traversal_count": len(sources),
            "sampled_betweenness_score": np.nan,
            "p2_degree_product_fallback": 1,
        }

    timings = state["timings"]
    sample_start = time.perf_counter()
    sampled = p1.theory.sampled_dependencies(h_graph, candidates, sources)
    scale = h_graph.number_of_nodes() / float(max(1, len(sources)))
    be_hat = {edge: scale * float(sampled.get(edge, 0.0)) for edge in candidates}
    timings["sampled_path_scoring_seconds"] += time.perf_counter() - sample_start

    score_start = time.perf_counter()
    scored = [(float(be_hat.get(edge, 0.0)), edge) for edge in candidates]
    scored.sort(key=lambda item: (-item[0], *stable_edge_sort(item[1])))
    selected = scored[0][1] if scored else None
    timings["model_scoring_seconds"] += time.perf_counter() - score_start
    timings["total_selection_seconds"] += time.perf_counter() - selection_start
    state["true_source_traversal_count"] = state.get("true_source_traversal_count", 0) + len(sources)
    return selected, {
        **source_meta,
        **candidate_meta,
        "selected_edge": p1.edge_string(selected) if selected is not None else "",
        "source_budget": SOURCE_BUDGET,
        "true_source_traversal_count": len(sources),
        "sampled_betweenness_score": be_hat.get(selected, np.nan),
        "p2_degree_product_fallback": 0,
    }


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
        "candidate_policy": curve_df["candidate_policy"].iloc[0],
        "source_policy": "SASB-structured",
        "seed": int(curve_df["seed"].iloc[0]),
        "status": status,
        "auc": auc,
        "normalized_auc": auc / observed if observed > 0 else np.nan,
        "observed_remove_ratio": observed,
        "removed_edges": int(curve_df["removed_edges"].max()) if len(curve_df) else 0,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "runtime_seconds": float(elapsed),
        "true_source_traversal_count": int(state.get("true_source_traversal_count", 0)),
        "louvain_recomputes": int(state.get("p2_candidate_policy_ablation_louvain_recomputes", 0)),
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
                "source_count_min": float(pd.to_numeric(step_df["source_count"], errors="coerce").min()),
                "source_count_max": float(pd.to_numeric(step_df["source_count"], errors="coerce").max()),
                "source_count_mean": float(pd.to_numeric(step_df["source_count"], errors="coerce").mean()),
                "source_count_median": float(pd.to_numeric(step_df["source_count"], errors="coerce").median()),
                "candidate_count_mean": float(pd.to_numeric(step_df["candidate_count"], errors="coerce").mean()),
                "candidate_fraction_mean": float(pd.to_numeric(step_df["candidate_fraction"], errors="coerce").mean()),
                "candidate_match_difference_mean": float(pd.to_numeric(step_df["matched_feature_difference"], errors="coerce").mean()),
                "strict_match_count_total": int(pd.to_numeric(step_df["strict_match_count"], errors="coerce").sum()),
                "degree_only_match_count_total": int(pd.to_numeric(step_df["degree_only_match_count"], errors="coerce").sum()),
                "community_only_match_count_total": int(pd.to_numeric(step_df["community_only_match_count"], errors="coerce").sum()),
                "fallback_count_total": int(pd.to_numeric(step_df["fallback_count"], errors="coerce").sum()),
                "p2_degree_product_fallback_count": int(pd.to_numeric(step_df["p2_degree_product_fallback"], errors="coerce").sum()),
                "initial_source_nodes": step_df.iloc[0]["source_nodes"],
                "initial_source_node_hash": step_df.iloc[0]["source_node_hash"],
                "initial_candidate_count": int(pd.to_numeric(step_df["candidate_count"], errors="coerce").iloc[0]),
                "initial_candidate_hash": step_df.iloc[0]["candidate_hash"],
            }
        )
    timings = state.get("timings", {})
    for key in ["candidate_generation_seconds", "sampled_path_scoring_seconds", "model_scoring_seconds", "total_selection_seconds"]:
        row[key] = float(timings.get(key, 0.0))
    return row


def simulate_policy(
    dataset: str,
    meta: dict[str, Any],
    graph0: nx.Graph,
    method: str,
    args: argparse.Namespace,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    max_steps = min(original_m, int(args.max_steps)) if int(getattr(args, "max_steps", 0)) > 0 else original_m
    state: dict[str, Any] = {
        "original_n": original_n,
        "max_steps": max_steps,
        "timings": {
            "candidate_generation_seconds": 0.0,
            "delta_gcc_seconds": 0.0,
            "sampled_path_scoring_seconds": 0.0,
            "model_scoring_seconds": 0.0,
            "total_selection_seconds": 0.0,
        },
    }
    curve_rows = [
        {
            "dataset": dataset,
            "graph_id": meta["graph_id"],
            "graph_name": meta.get("graph_name", meta["graph_id"]),
            "graph_type": meta.get("graph_type", "unknown"),
            "community_strength": meta.get("community_strength", "unknown"),
            "method": method,
            "candidate_policy": CANDIDATE_POLICIES[method],
            "source_policy": "SASB-structured",
            "seed": seed,
            "step": 0,
            "removed_edges": 0,
            "remove_ratio": 0.0,
            "gcc_ratio": p1.gcc_ratio(graph, original_n),
            "gcc_size": p1.gcc_size(graph),
        }
    ]
    step_rows: list[dict[str, Any]] = []
    start = time.perf_counter()
    timed_out = False
    step = 0
    while graph.number_of_edges() > 0 and step < max_steps:
        if step / float(max(1, original_m)) >= args.max_remove_ratio:
            break
        if args.timeout_seconds > 0 and time.perf_counter() - start > args.timeout_seconds:
            timed_out = True
            break
        h_graph = p1.largest_cc_graph(graph)
        if h_graph.number_of_edges() == 0:
            break
        diagnostic_partition = p1.diag.get_diagnostic_partition(h_graph, step, state, args.diagnostic_louvain_interval)
        gcc_before = p1.gcc_ratio(graph, original_n)
        components_before = p1.num_components(graph)
        edge, details = choose_policy_edge(h_graph, method, step, state, args, meta["graph_id"], seed)
        if edge is None or not graph.has_edge(*edge):
            break
        edge = p1.canonical_edge(edge)
        bridge = p1.selected_edge_is_bridge(h_graph, edge)
        features = p1.structural_edge_features(h_graph, edge, diagnostic_partition)
        graph.remove_edge(*edge)
        gcc_after = p1.gcc_ratio(graph, original_n)
        remove_ratio_before = step / float(max(1, original_m))
        remove_ratio_after = (step + 1) / float(max(1, original_m))
        row = {
            "dataset": dataset,
            "graph_id": meta["graph_id"],
            "method": method,
            "candidate_policy": CANDIDATE_POLICIES[method],
            "source_policy": "SASB-structured",
            "seed": seed,
            "step": step,
            "attack_phase": p1.attack_phase(remove_ratio_before),
            "gcc_before": gcc_before,
            "gcc_after": gcc_after,
            "delta_gcc": gcc_before - gcc_after,
            "num_components_before": components_before,
            "num_components_after": p1.num_components(graph),
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
                "candidate_policy": CANDIDATE_POLICIES[method],
                "source_policy": "SASB-structured",
                "seed": seed,
                "step": step,
                "removed_edges": step,
                "remove_ratio": remove_ratio_after,
                "gcc_ratio": gcc_after,
                "gcc_size": p1.gcc_size(graph),
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


def load_real_completed_ids() -> list[str]:
    path = ROOT / "result" / "sasb_m5_edge_diagnostics" / "full_real_completed_edges_le1305" / "graph_method_summary.csv"
    if path.exists():
        df = pd.read_csv(path)
        return sorted(df["graph_id"].dropna().unique().tolist())
    p1_config = ROOT / "result" / "source_policy_ablation_p1" / "formal_run_config.json"
    if p1_config.exists():
        config = json.loads(p1_config.read_text(encoding="utf-8"))
        return config["datasets"]["realworld_completed_24of28"]["graph_ids"]
    return []


def default_config() -> dict[str, Any]:
    real_ids = load_real_completed_ids()
    return {
        "experiment_name": "p2_candidate_policy_ablation",
        "output_dir": str(OUT_DIR.relative_to(ROOT)),
        "seed": SEED,
        "random_seeds": [SEED],
        "source_policy": "SASB-structured",
        "source_budget": SOURCE_BUDGET,
        "actual_source_count_rule": "min(32, current GCC node count)",
        "remove_ratio": 1.0,
        "methods": METHODS,
        "candidate_policies": {
            "SASB-candidate": {
                "backend": "evaluate_m19_theory_calibrated.candidate_features",
                "variant": "conservative",
                "delta_mode": "none",
                "k_min": 64,
                "k_max": 512,
            },
            "Random-size-matched-candidate": "uniform random candidate edges from current GCC, count matched to SASB candidate count",
            "Structure-matched-candidate": "random candidate edges from current GCC, count and structural distributions matched to SASB candidate set",
        },
        "datasets": {
            "synthetic45": {"enabled": True, "remove_ratio": 1.0, "max_graphs": 0},
            "realworld_completed_24of28": {
                "enabled": True,
                "remove_ratio": 1.0,
                "graph_ids": real_ids,
                "coverage": "24/28 current completed subset",
            },
        },
        "real_validation_path": str(P1_REAL_VALIDATION.relative_to(ROOT)).replace("\\", "/") if P1_REAL_VALIDATION.exists() else "",
        "louvain_interval": 10,
        "louvain_drop_threshold": 0.05,
        "diagnostic_louvain_interval": 1,
        "max_steps": 0,
        "timeout_seconds": 0,
        "fixed_variables": [
            "source_policy",
            "source_budget_upper_bound",
            "seed",
            "network_data",
            "dynamic_gcc_measurement",
            "louvain_policy",
            "sampled_dependency",
            "edge_score_sorting",
            "tie_breaking",
            "auc_calculation",
            "remove_ratio",
        ],
        "interpretation_rule": "SASB-candidate must outperform Structure-matched-candidate to support independent candidate-rule bias.",
    }


def save_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_config(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def args_from_config(config: dict[str, Any]) -> argparse.Namespace:
    sasb = config["candidate_policies"]["SASB-candidate"]
    return argparse.Namespace(
        max_remove_ratio=float(config.get("remove_ratio", 1.0)),
        timeout_seconds=float(config.get("timeout_seconds", 0.0)),
        max_steps=int(config.get("max_steps", 0)),
        k_min=int(sasb.get("k_min", 64)),
        k_max=int(sasb.get("k_max", 512)),
        louvain_interval=int(config.get("louvain_interval", 10)),
        louvain_drop_threshold=float(config.get("louvain_drop_threshold", 0.05)),
        diagnostic_louvain_interval=int(config.get("diagnostic_louvain_interval", 1)),
    )


def select_graphs(config: dict[str, Any], cli_args: argparse.Namespace) -> list[tuple[str, dict[str, Any], nx.Graph]]:
    selected: list[tuple[str, dict[str, Any], nx.Graph]] = []
    graph_cap = int(getattr(cli_args, "max_graphs", 0))
    graph_filter = set(getattr(cli_args, "graph_id", []) or [])
    if config.get("real_validation_path"):
        p1.fair.REAL_VALIDATION = ROOT / config["real_validation_path"]
    if config["datasets"].get("synthetic45", {}).get("enabled", True):
        max_synthetic = int(config["datasets"]["synthetic45"].get("max_graphs", 0))
        if graph_cap > 0:
            max_synthetic = graph_cap if max_synthetic <= 0 else min(max_synthetic, graph_cap)
        for graph_id, group in p1.fair.load_synthetic_groups(max_graphs=max_synthetic):
            if graph_filter and graph_id not in graph_filter:
                continue
            selected.append(("synthetic45", p1.fair.synthetic_meta(group), p1.fair.reconstruct_synthetic_graph(group)))
            if graph_cap > 0 and len(selected) >= graph_cap:
                return selected
    if config["datasets"].get("realworld_completed_24of28", {}).get("enabled", True):
        graph_ids = config["datasets"]["realworld_completed_24of28"].get("graph_ids") or load_real_completed_ids()
        if graph_filter:
            graph_ids = [graph_id for graph_id in graph_ids if graph_id in graph_filter]
        if graph_cap > 0:
            graph_ids = graph_ids[: max(0, graph_cap - len(selected))]
        if graph_ids:
            metadata = p1.fair.load_real_metadata(graph_ids=graph_ids)
            for _, row in metadata.iterrows():
                meta = row.to_dict()
                selected.append(("realworld_completed", meta, p1.fair.load_real_graph(meta)))
                if graph_cap > 0 and len(selected) >= graph_cap:
                    return selected
    return selected


def collect_summaries(out_dir: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in (out_dir / "runs").glob("*/*/*/summary.csv")]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def collect_steps(out_dir: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in (out_dir / "runs").glob("*/*/*/edge_steps.csv")]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def mean_ci(values: pd.Series) -> dict[str, float]:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    n = int(len(vals))
    mean = float(vals.mean()) if n else np.nan
    sd = float(vals.std(ddof=1)) if n > 1 else 0.0 if n == 1 else np.nan
    margin = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0 if n == 1 else np.nan
    return {"n": n, "mean": mean, "std": sd, "ci95_low": mean - margin, "ci95_high": mean + margin}


def build_paired(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metrics = [PRIMARY, *SECONDARY, *MECHANISM, *COST]
    for (dataset, graph_id, seed), group in summary.groupby(["dataset", "graph_id", "seed"], sort=True):
        by_method = group.set_index("method")
        for left, right in CORE_COMPARISONS:
            if left not in by_method.index or right not in by_method.index:
                continue
            row: dict[str, Any] = {
                "dataset": dataset,
                "dataset_label": "realworld24" if dataset == "realworld_completed" else dataset,
                "graph_id": graph_id,
                "seed": seed,
                "comparison": f"{left} minus {right}",
                "left_method": left,
                "right_method": right,
            }
            for metric in metrics:
                if metric in by_method.columns:
                    left_value = by_method.loc[left, metric]
                    right_value = by_method.loc[right, metric]
                    row[f"{metric}_left"] = left_value
                    row[f"{metric}_right"] = right_value
                    row[f"{metric}_diff"] = left_value - right_value
            diff = row.get(f"{PRIMARY}_diff", np.nan)
            row["left_better"] = int(pd.notna(diff) and diff < -1e-9)
            row["right_better"] = int(pd.notna(diff) and diff > 1e-9)
            row["tie"] = int(pd.notna(diff) and abs(diff) <= 1e-9)
            rows.append(row)
    return pd.DataFrame(rows)


def build_effects(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dataset, comparison), group in paired.groupby(["dataset", "comparison"], sort=True):
        diffs = pd.to_numeric(group[f"{PRIMARY}_diff"], errors="coerce").dropna()
        rows.append(
            {
                "dataset": dataset,
                "dataset_label": group["dataset_label"].iloc[0],
                "comparison": comparison,
                "metric": PRIMARY,
                **mean_ci(diffs),
                "left_wins": int((diffs < -1e-9).sum()),
                "right_wins": int((diffs > 1e-9).sum()),
                "ties": int((diffs.abs() <= 1e-9).sum()),
                "direction_note": "negative mean means left method has lower normalized GCC-AUC",
            }
        )
    return pd.DataFrame(rows)


def metric_summary(summary: pd.DataFrame, metrics: list[str], kind: str) -> pd.DataFrame:
    rows = []
    for (dataset, method), group in summary.groupby(["dataset", "method"], sort=True):
        for metric in metrics:
            if metric in group.columns:
                rows.append(
                    {
                        "summary_kind": kind,
                        "dataset": dataset,
                        "dataset_label": "realworld24" if dataset == "realworld_completed" else dataset,
                        "method": method,
                        "metric": metric,
                        **mean_ci(group[metric]),
                    }
                )
    return pd.DataFrame(rows)


def build_candidate_match_quality(summary: pd.DataFrame, steps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if steps.empty:
        return pd.DataFrame()
    numeric_cols = [
        "candidate_count",
        "candidate_fraction",
        "candidate_inter_community_ratio",
        "candidate_boundary_ratio",
        "candidate_bridge_ratio",
        "candidate_low_cn_ratio",
        "matched_feature_difference",
        "strict_match_count",
        "degree_only_match_count",
        "community_only_match_count",
        "fallback_count",
    ]
    for col in numeric_cols:
        if col in steps.columns:
            steps[col] = pd.to_numeric(steps[col], errors="coerce")
    for (dataset, graph_id, method, seed), group in steps.groupby(["dataset", "graph_id", "method", "seed"], sort=True):
        first = group.sort_values("step").iloc[0]
        rows.append(
            {
                "dataset": dataset,
                "dataset_label": "realworld24" if dataset == "realworld_completed" else dataset,
                "graph_id": graph_id,
                "method": method,
                "candidate_policy": first["candidate_policy"],
                "seed": seed,
                "steps": int(len(group)),
                "initial_candidate_count": int(first["candidate_count"]),
                "candidate_count_mean": float(group["candidate_count"].mean()),
                "candidate_fraction_mean": float(group["candidate_fraction"].mean()),
                "inter_community_ratio_mean": float(group["candidate_inter_community_ratio"].mean()),
                "boundary_ratio_mean": float(group["candidate_boundary_ratio"].mean()),
                "bridge_ratio_mean": float(group["candidate_bridge_ratio"].mean()),
                "low_cn_ratio_mean": float(group["candidate_low_cn_ratio"].mean()),
                "matched_feature_difference_mean": float(group["matched_feature_difference"].mean()),
                "strict_match_count": int(group["strict_match_count"].sum()),
                "degree_only_match_count": int(group["degree_only_match_count"].sum()),
                "community_only_match_count": int(group["community_only_match_count"].sum()),
                "fallback_count": int(group["fallback_count"].sum()),
                "initial_candidate_hash": first["candidate_hash"],
                "initial_source_node_hash": first["source_node_hash"],
            }
        )
    return pd.DataFrame(rows)


def build_source_count_summary(summary: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "dataset",
        "graph_id",
        "method",
        "candidate_policy",
        "seed",
        "removed_edges",
        "source_count_min",
        "source_count_max",
        "source_count_mean",
        "source_count_median",
        "true_source_traversal_count",
    ]
    return summary[[col for col in cols if col in summary.columns]].copy()


def plot_outputs(summary: pd.DataFrame, paired: pd.DataFrame, out_dir: Path) -> None:
    plots = out_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    order = METHODS
    for dataset, group in summary.groupby("dataset", sort=True):
        data = [pd.to_numeric(group[group["method"].eq(method)][PRIMARY], errors="coerce").dropna().to_numpy() for method in order]
        plt.figure(figsize=(8, 4.5))
        plt.boxplot(data, tick_labels=[m.replace("-candidate", "").replace("-matched", "") for m in order], showmeans=True)
        plt.ylabel("normalized GCC-AUC (lower is better)")
        plt.title(f"P2 {dataset}: AUC by candidate policy")
        plt.tight_layout()
        plt.savefig(plots / f"{dataset}_candidate_policy_auc_boxplot.png", dpi=200)
        plt.close()
    core = paired[paired["comparison"].eq("SASB-candidate minus Structure-matched-candidate")]
    for dataset, group in core.groupby("dataset", sort=True):
        plot_df = group.sort_values(f"{PRIMARY}_diff")
        plt.figure(figsize=(10, max(4, 0.18 * len(plot_df))))
        colors = ["#2f6f4e" if value < 0 else "#a64242" if value > 0 else "#777777" for value in plot_df[f"{PRIMARY}_diff"]]
        plt.barh(plot_df["graph_id"], plot_df[f"{PRIMARY}_diff"], color=colors)
        plt.axvline(0, color="black", linewidth=0.8)
        plt.xlabel("SASB - structure-matched normalized GCC-AUC")
        plt.title(f"P2 {dataset}: core paired candidate effect")
        plt.tight_layout()
        plt.savefig(plots / f"{dataset}_sasb_minus_structure_matched_auc_diff.png", dpi=200)
        plt.close()


def build_report(summary: pd.DataFrame, paired: pd.DataFrame, effects: pd.DataFrame, match_quality: pd.DataFrame, cost: pd.DataFrame) -> str:
    lines = [
        "# P2 Candidate-Set Ablation Exploratory Report",
        "",
        "## Research Question",
        "",
        "With source policy, source budget upper bound, seed, and dynamic GCC workflow fixed, does the SASB candidate-edge set provide an independent beneficial structural bias?",
        "",
        "The core comparison is `SASB-candidate` versus `Structure-matched-candidate`; comparing only against size-matched random candidates is insufficient.",
        "",
        "## Run Integrity",
        "",
        f"- summary rows: `{len(summary)}`.",
        f"- all finished: `{bool(summary['status'].eq('finished').all()) if not summary.empty else False}`.",
        f"- datasets: `{json_dumps(summary.groupby('dataset').size().to_dict()) if not summary.empty else '{}'}`.",
        f"- methods: `{', '.join(sorted(summary['method'].dropna().unique())) if not summary.empty else ''}`.",
        f"- failed or non-finished runs: `{int((~summary['status'].eq('finished')).sum()) if not summary.empty else 0}`.",
        "",
        "## Main Result: normalized GCC-AUC",
        "",
    ]
    for dataset in sorted(summary["dataset"].unique()):
        lines.append(f"### {dataset}")
        for method in METHODS:
            vals = pd.to_numeric(summary[(summary["dataset"].eq(dataset)) & (summary["method"].eq(method))][PRIMARY], errors="coerce")
            s = mean_ci(vals)
            lines.append(f"- `{method}` mean AUC: `{s['mean']:.6f}` (n={s['n']}).")
        core = effects[(effects["dataset"].eq(dataset)) & (effects["comparison"].eq("SASB-candidate minus Structure-matched-candidate"))]
        if not core.empty:
            row = core.iloc[0]
            supports = bool(row["mean"] < 0 and row["ci95_high"] < 0 and row["left_wins"] > row["right_wins"])
            lines.append(
                "- Core SASB-minus-structure-matched diff: `{:.6f}`, 95% descriptive CI `[{:.6f}, {:.6f}]`, wins/losses/ties `{}/{}/{}`; supports candidate-rule H1: `{}`.".format(
                    row["mean"],
                    row["ci95_low"],
                    row["ci95_high"],
                    int(row["left_wins"]),
                    int(row["right_wins"]),
                    int(row["ties"]),
                    supports,
                )
            )
        lines.append("")
    lines.extend(["## Paired Difference Summary", ""])
    for _, row in effects.sort_values(["dataset", "comparison"]).iterrows():
        lines.append(
            "- `{}` `{}`: mean `{:.6f}`, 95% descriptive CI `[{:.6f}, {:.6f}]`, wins/losses/ties `{}/{}/{}`.".format(
                row["dataset"],
                row["comparison"],
                row["mean"],
                row["ci95_low"],
                row["ci95_high"],
                int(row["left_wins"]),
                int(row["right_wins"]),
                int(row["ties"]),
            )
        )
    lines.extend(["## Candidate Match Quality", ""])
    for dataset, group in match_quality.groupby("dataset", sort=True):
        sm = group[group["method"].eq("Structure-matched-candidate")]
        if sm.empty:
            continue
        lines.append(
            "- `{}` structure-matched mean feature L1 difference `{:.6f}`, strict matches `{}`, degree-only `{}`, community-only `{}`, fallback `{}`.".format(
                dataset,
                float(pd.to_numeric(sm["matched_feature_difference_mean"], errors="coerce").mean()),
                int(pd.to_numeric(sm["strict_match_count"], errors="coerce").sum()),
                int(pd.to_numeric(sm["degree_only_match_count"], errors="coerce").sum()),
                int(pd.to_numeric(sm["community_only_match_count"], errors="coerce").sum()),
                int(pd.to_numeric(sm["fallback_count"], errors="coerce").sum()),
            )
        )
    lines.append("- Match quality is measured on the coarse structural features used by P2 matching; exact edge-set equality is not claimed.")
    lines.extend(["", "## Source Count", ""])
    for dataset in sorted(summary["dataset"].unique()):
        lines.append(f"### {dataset}")
        for method in METHODS:
            group = summary[(summary["dataset"].eq(dataset)) & (summary["method"].eq(method))]
            if group.empty:
                continue
            lines.append(
                "- `{}` actual source_count min/max/mean = `{:.1f}` / `{:.1f}` / `{:.3f}`; true source traversal mean `{:.1f}`.".format(
                    method,
                    float(pd.to_numeric(group["source_count_min"], errors="coerce").min()),
                    float(pd.to_numeric(group["source_count_max"], errors="coerce").max()),
                    float(pd.to_numeric(group["source_count_mean"], errors="coerce").mean()),
                    float(pd.to_numeric(group["true_source_traversal_count"], errors="coerce").mean()),
                )
            )
        lines.append("")
    lines.extend(["## Mechanism Metrics", ""])
    for dataset in sorted(summary["dataset"].unique()):
        lines.append(f"### {dataset}")
        for metric in MECHANISM:
            values = []
            for method in METHODS:
                group = summary[(summary["dataset"].eq(dataset)) & (summary["method"].eq(method))]
                values.append(f"{method}={pd.to_numeric(group[metric], errors='coerce').mean():.6f}")
            lines.append(f"- `{metric}` mean: " + ", ".join(values) + ".")
        lines.append("")
    lines.extend(["", "## Cost", ""])
    for dataset in sorted(summary["dataset"].unique()):
        lines.append(f"### {dataset}")
        for method in METHODS:
            row = cost[(cost["dataset"].eq(dataset)) & (cost["method"].eq(method)) & (cost["metric"].eq("runtime_seconds"))]
            trav = cost[(cost["dataset"].eq(dataset)) & (cost["method"].eq(method)) & (cost["metric"].eq("true_source_traversal_count"))]
            if not row.empty and not trav.empty:
                lines.append(f"- `{method}` runtime mean `{row.iloc[0]['mean']:.3f}s`, source traversal mean `{trav.iloc[0]['mean']:.1f}`.")
        lines.append("")
    lines.extend(
        [
            "## Scientific Interpretation Rules",
            "",
            "- If SASB-candidate beats both random-size-matched and structure-matched candidates, this supports an independent candidate selection contribution.",
            "- If SASB-candidate beats random-size-matched but is close to structure-matched, candidate structural composition may matter more than the exact SASB scoring rule.",
            "- If all three are close, no stable independent candidate-set advantage is observed under this protocol.",
            "- If random-size-matched is better, the current SASB candidate rule may introduce an unfavorable structural bias.",
            "",
            "## What This Experiment Cannot Claim",
            "",
            "- It cannot claim universal effectiveness from code completion.",
            "- It cannot prove candidate bias as the only mechanism.",
            "- It cannot claim source-policy bias, because source policy is fixed here.",
            "- It does not require candidate hashes to remain identical after dynamic trajectories diverge.",
        ]
    )
    return "\n".join(lines) + "\n"


def analyze_outputs(out_dir: Path, formal: bool) -> dict[str, Any]:
    summary = collect_summaries(out_dir)
    if summary.empty:
        return {"summary_rows": 0}
    for col in [PRIMARY, *SECONDARY, *MECHANISM, *COST]:
        if col in summary.columns:
            summary[col] = pd.to_numeric(summary[col], errors="coerce")
    steps = collect_steps(out_dir)
    paired = build_paired(summary)
    effects = build_effects(paired)
    match_quality = build_candidate_match_quality(summary, steps)
    source_counts = build_source_count_summary(summary)
    cost = metric_summary(summary, COST, "cost_summary")
    write_csv(summary, out_dir / ("formal_results.csv" if formal else "smoke_results.csv"))
    if formal:
        write_csv(paired, out_dir / "paired_comparisons.csv")
        write_csv(effects, out_dir / "effect_sizes.csv")
        write_csv(match_quality, out_dir / "candidate_match_quality.csv")
        write_csv(source_counts, out_dir / "source_count_summary.csv")
        write_csv(cost, out_dir / "cost_summary.csv")
        plot_outputs(summary, paired, out_dir)
        (out_dir / "formal_experiment_report.md").write_text(
            build_report(summary, paired, effects, match_quality, cost),
            encoding="utf-8",
        )
    return {
        "summary_rows": int(len(summary)),
        "paired_rows": int(len(paired)),
        "effect_rows": int(len(effects)),
        "match_quality_rows": int(len(match_quality)),
        "all_finished": bool(summary["status"].eq("finished").all()),
    }


def smoke_checks(out_dir: Path) -> dict[str, Any]:
    summary = collect_summaries(out_dir)
    steps = collect_steps(out_dir)
    checks: dict[str, Any] = {
        "summary_rows": int(len(summary)),
        "step_rows": int(len(steps)),
        "methods_ok": False,
        "source_policy_identical": False,
        "initial_source_nodes_identical": False,
        "initial_candidate_counts_equal": False,
        "candidate_nonempty": False,
        "source_count_valid": False,
        "metrics_valid": False,
        "no_degree_product_fallback": False,
        "match_fields_recorded": False,
        "match_quality_numeric": False,
        "passed": False,
    }
    if summary.empty or steps.empty:
        return checks
    checks["methods_ok"] = sorted(summary["method"].dropna().unique().tolist()) == sorted(METHODS)
    checks["source_policy_identical"] = summary["source_policy"].nunique(dropna=True) == 1 and summary["source_policy"].iloc[0] == "SASB-structured"
    first = steps[pd.to_numeric(steps["step"], errors="coerce").eq(0)].copy()
    checks["initial_source_nodes_identical"] = first["source_node_hash"].nunique(dropna=True) == 1
    checks["initial_candidate_counts_equal"] = pd.to_numeric(first["candidate_count"], errors="coerce").nunique(dropna=True) == 1
    checks["candidate_nonempty"] = bool((pd.to_numeric(steps["candidate_count"], errors="coerce") > 0).all())
    source_count = pd.to_numeric(steps["source_count"], errors="coerce")
    checks["source_count_valid"] = bool(source_count.notna().all() and (source_count > 0).all() and (source_count <= SOURCE_BUDGET).all())
    metric_cols = ["normalized_auc", "runtime_seconds", "positive_delta_gcc_rate"]
    checks["metrics_valid"] = bool(summary[metric_cols].apply(pd.to_numeric, errors="coerce").notna().all().all())
    checks["no_degree_product_fallback"] = bool(pd.to_numeric(steps["p2_degree_product_fallback"], errors="coerce").sum() == 0)
    needed = ["match_mode_counts", "fallback_reason", "strict_match_count", "degree_only_match_count", "community_only_match_count", "fallback_count"]
    checks["match_fields_recorded"] = all(col in steps.columns for col in needed)
    checks["match_quality_numeric"] = bool(pd.to_numeric(steps["matched_feature_difference"], errors="coerce").notna().all())
    checks["passed"] = all(
        checks[key]
        for key in [
            "methods_ok",
            "source_policy_identical",
            "initial_source_nodes_identical",
            "initial_candidate_counts_equal",
            "candidate_nonempty",
            "source_count_valid",
            "metrics_valid",
            "no_degree_product_fallback",
            "match_fields_recorded",
            "match_quality_numeric",
        ]
    )
    return checks


def write_smoke_report(out_dir: Path) -> dict[str, Any]:
    checks = smoke_checks(out_dir)
    lines = [
        "# P2 Candidate-Set Ablation Smoke Validation Report",
        "",
        f"- Smoke passed: `{checks['passed']}`.",
        f"- Summary rows: `{checks['summary_rows']}`.",
        f"- Step rows: `{checks['step_rows']}`.",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        if key not in {"summary_rows", "step_rows"}:
            lines.append(f"- `{key}`: `{value}`.")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This smoke test validates implementation and measurement plumbing only. It is not evidence that any candidate policy is scientifically effective.",
        ]
    )
    (out_dir / "smoke_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checks


def run_experiment(config: dict[str, Any], cli_args: argparse.Namespace) -> dict[str, Any]:
    p1.require_runtime_modules()
    out_dir = ROOT / config.get("output_dir", str(OUT_DIR.relative_to(ROOT)))
    run_args = args_from_config(config)
    if int(getattr(cli_args, "max_steps", 0)) > 0:
        run_args.max_steps = int(cli_args.max_steps)
    graphs = select_graphs(config, cli_args)
    if not graphs:
        raise RuntimeError("No graphs selected for P2.")
    formal = not (int(getattr(cli_args, "max_graphs", 0)) == 1 and 0 < int(getattr(run_args, "max_steps", 0)) <= 40)
    run_config = {
        **config,
        "python_executable": sys.executable,
        "cli_max_graphs": int(getattr(cli_args, "max_graphs", 0)),
        "cli_max_steps": int(getattr(cli_args, "max_steps", 0)),
        "effective_max_steps": int(getattr(run_args, "max_steps", 0)),
        "formal_experiment": formal,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_config.json").write_text(json.dumps(run_config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summaries = []
    for dataset, meta, graph in graphs:
        for seed in config.get("random_seeds", [SEED]):
            for method in METHODS:
                step_path, curve_path, summary_path = run_paths(out_dir, dataset, meta["graph_id"], method, int(seed))
                if summary_path.exists() and not cli_args.overwrite:
                    existing = pd.read_csv(summary_path)
                    if not existing.empty:
                        summaries.append(existing)
                    continue
                step_df, curve_df, summary = simulate_policy(dataset, meta, graph, method, run_args, int(seed))
                write_csv(step_df, step_path)
                write_csv(curve_df, curve_path)
                summary_df = pd.DataFrame([summary])
                write_csv(summary_df, summary_path)
                summaries.append(summary_df)
                print(f"ran dataset={dataset} graph={meta['graph_id']} method={method} seed={seed}", flush=True)
    if summaries:
        write_csv(pd.concat(summaries, ignore_index=True, sort=False), out_dir / "p2_candidate_policy_ablation_summary.csv")
    manifest = analyze_outputs(out_dir, formal=formal)
    if not formal:
        checks = write_smoke_report(out_dir)
        manifest.update(checks)
    (out_dir / ("formal_manifest.json" if formal else "smoke_manifest.json")).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="P2 candidate-set ablation for SASB. Defaults to dry-run/design mode.")
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--write-default-config", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--max-graphs", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--graph-id", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    if args.write_default_config or not config_path.exists():
        save_default_config(config_path)
        print(f"wrote config: {config_path}")
    config = load_config(config_path)
    if not args.run:
        print("dry-run/design mode only; no P2 attack experiment was started")
        print(f"config: {config_path}")
        print("methods:", ", ".join(config["methods"]))
        print("realworld graphs:", len(config["datasets"]["realworld_completed_24of28"].get("graph_ids", [])))
        return
    manifest = run_experiment(config, args)
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
