from pathlib import Path
import argparse
import json
import math
import time
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

import community as community_louvain

import evaluate_m18_candidate as m18
import evaluate_m19_theory_calibrated as theory
import evaluate_m19_realworld_40plus as real40
import evaluate_next_stage_fair_comparison as fair


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260513
METHOD_M5 = "M5"
METHOD_SASB = "SASB"
REAL_M5_COMPLETED = ROOT / "result" / "paper_experiments" / "m5_completed_subset" / "m5_completed_subset_per_graph.csv"
DEFAULT_OUT_ROOT = ROOT / "result" / "sasb_m5_edge_diagnostics"


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_csv(path):
    return pd.read_csv(path) if Path(path).exists() else pd.DataFrame()


def method_slug(method):
    return str(method).lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def stable_node_key(node):
    return (str(type(node)), str(node))


def canonical_edge(edge):
    u, v = edge
    return (u, v) if stable_node_key(u) <= stable_node_key(v) else (v, u)


def edge_string(edge):
    u, v = canonical_edge(edge)
    return "{}--{}".format(u, v)


def largest_cc_graph(graph):
    if graph.number_of_nodes() == 0:
        return graph.copy()
    if graph.number_of_edges() == 0:
        return graph.copy()
    nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(nodes).copy()


def gcc_size(graph):
    if graph.number_of_nodes() == 0:
        return 0
    return len(max(nx.connected_components(graph), key=len))


def gcc_ratio(graph, original_n):
    return gcc_size(graph) / float(max(1, original_n))


def num_components(graph):
    if graph.number_of_nodes() == 0:
        return 0
    return nx.number_connected_components(graph)


def attack_phase(remove_ratio):
    if remove_ratio < 1.0 / 3.0:
        return "early"
    if remove_ratio < 2.0 / 3.0:
        return "middle"
    return "late"


def diagnostic_partition(h_graph):
    if h_graph.number_of_edges() == 0:
        return {node: idx for idx, node in enumerate(h_graph.nodes())}
    return community_louvain.best_partition(h_graph, random_state=SEED)


def get_diagnostic_partition(h_graph, step, state, interval):
    interval = max(1, int(interval))
    cached_step = state.get("diagnostic_partition_step")
    cached_partition = state.get("diagnostic_partition")
    cached_nodes = state.get("diagnostic_partition_nodes", set())
    current_nodes = set(h_graph.nodes())
    needs_recompute = (
        cached_partition is None
        or cached_step is None
        or step - cached_step >= interval
        or not current_nodes.issubset(cached_nodes)
    )
    if needs_recompute:
        cached_partition = diagnostic_partition(h_graph)
        state["diagnostic_partition"] = cached_partition
        state["diagnostic_partition_step"] = step
        state["diagnostic_partition_nodes"] = current_nodes
        state["diagnostic_louvain_recomputes"] = state.get("diagnostic_louvain_recomputes", 0) + 1
    return {node: cached_partition[node] for node in h_graph.nodes() if node in cached_partition}


def structural_edge_features(h_graph, edge, partition):
    u, v = canonical_edge(edge)
    degrees = dict(h_graph.degree())
    degree_u = int(degrees.get(u, 0))
    degree_v = int(degrees.get(v, 0))
    neighbors_u = set(h_graph.neighbors(u)) if h_graph.has_node(u) else set()
    neighbors_v = set(h_graph.neighbors(v)) if h_graph.has_node(v) else set()
    common_neighbors = len(neighbors_u & neighbors_v)
    denom = min(max(0, degree_u - 1), max(0, degree_v - 1))
    embeddedness = common_neighbors / float(denom) if denom > 0 else 0.0
    return {
        "edge_u": u,
        "edge_v": v,
        "selected_edge": edge_string((u, v)),
        "degree_u": degree_u,
        "degree_v": degree_v,
        "degree_min": min(degree_u, degree_v),
        "degree_max": max(degree_u, degree_v),
        "degree_product": degree_u * degree_v,
        "common_neighbors": common_neighbors,
        "edge_embeddedness": embeddedness,
        "is_inter_community_edge": int(partition.get(u) != partition.get(v)),
        "community_u": partition.get(u, np.nan),
        "community_v": partition.get(v, np.nan),
    }


def selected_edge_is_bridge(h_graph, edge):
    u, v = canonical_edge(edge)
    if not h_graph.has_edge(u, v):
        return 0
    h_graph.remove_edge(u, v)
    try:
        is_bridge = not nx.has_path(h_graph, u, v)
    finally:
        h_graph.add_edge(u, v)
    return int(is_bridge)


def choose_m5_with_details(h_graph):
    if h_graph.number_of_edges() == 0:
        return None, {}
    betweenness = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
    scores = {canonical_edge(edge): float(score) for edge, score in betweenness.items()}
    rows = [(score, edge) for edge, score in scores.items()]
    rows.sort(key=lambda item: (-item[0], stable_node_key(item[1][0]), stable_node_key(item[1][1])))
    selected = rows[0][1]
    return selected, {
        "full_edge_betweenness_score": scores.get(selected, np.nan),
        "m5_rank_in_full_eb": 1,
        "full_eb_available": 1,
        "sampled_betweenness_score": np.nan,
        "sampled_betweenness_available": 0,
        "candidate_set_size": h_graph.number_of_edges(),
        "sample_sources": np.nan,
        "adaptive_k": np.nan,
    }


def choose_sasb_with_details(h_graph, step, state, args):
    if h_graph.number_of_edges() == 0:
        return None, {}
    timings = state.setdefault(
        "sasb_timings",
        {
            "candidate_generation_seconds": 0.0,
            "delta_gcc_seconds": 0.0,
            "sampled_path_scoring_seconds": 0.0,
            "model_scoring_seconds": 0.0,
            "total_selection_seconds": 0.0,
        },
    )
    start = time.perf_counter()
    k = theory.adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
    state["last_adaptive_k"] = k
    cand_start = time.perf_counter()
    partition = m18.get_adaptive_stale_partition(
        h_graph,
        step,
        state,
        "sasb",
        max(1, args.louvain_interval),
        max(0.0, args.louvain_drop_threshold),
    )
    candidates, comm, boundary_scores, local_scores, _ = theory.candidate_features(
        h_graph,
        partition,
        k,
        variant="conservative",
        delta_mode="none",
        step=step,
        args=args,
        timings=timings,
    )
    timings["candidate_generation_seconds"] += time.perf_counter() - cand_start
    if not candidates:
        fallback = m18.choose_degree_product_edge(h_graph)
        return fallback, {
            "full_edge_betweenness_score": np.nan,
            "full_eb_available": 0,
            "sampled_betweenness_score": np.nan,
            "sampled_betweenness_available": 0,
            "candidate_set_size": 0,
            "sample_sources": 0,
            "adaptive_k": k,
            "sasb_fallback": 1,
        }

    sample_count = theory.adaptive_sample_count(
        len(candidates),
        args.m_min,
        args.m_max,
        args.confidence_delta,
        args.epsilon,
    )
    boundary_degrees = m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    sources = theory.select_structured_sources(h_graph, partition, boundary_degrees, sample_count, step)

    sample_start = time.perf_counter()
    sampled = theory.sampled_dependencies(h_graph, candidates, sources)
    scale = h_graph.number_of_nodes() / float(max(1, len(sources)))
    be_hat = {edge: scale * sampled.get(edge, 0.0) for edge in candidates}
    timings["sampled_path_scoring_seconds"] += time.perf_counter() - sample_start

    score_start = time.perf_counter()
    scored = [(float(be_hat.get(edge, 0.0)), edge) for edge in candidates]
    scored.sort(key=lambda item: (-item[0], stable_node_key(item[1][0]), stable_node_key(item[1][1])))
    selected = scored[0][1] if scored else None
    timings["model_scoring_seconds"] += time.perf_counter() - score_start
    timings["total_selection_seconds"] += time.perf_counter() - start
    state["sasb_louvain_recomputes"] = state.get("sasb_louvain_recomputes", 0)
    state["last_sample_sources"] = sample_count

    full_score = np.nan
    full_available = 0
    full_rank = np.nan
    if args.compute_sasb_full_eb:
        full = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
        full_scores = {canonical_edge(edge): float(score) for edge, score in full.items()}
        ranked = sorted(
            [(score, edge) for edge, score in full_scores.items()],
            key=lambda item: (-item[0], stable_node_key(item[1][0]), stable_node_key(item[1][1])),
        )
        ranks = {edge: rank + 1 for rank, (_, edge) in enumerate(ranked)}
        full_score = full_scores.get(selected, np.nan)
        full_available = 1
        full_rank = ranks.get(selected, np.nan)

    return selected, {
        "full_edge_betweenness_score": full_score,
        "m5_rank_in_full_eb": full_rank,
        "full_eb_available": full_available,
        "sampled_betweenness_score": be_hat.get(selected, np.nan),
        "sampled_betweenness_available": 1,
        "candidate_set_size": len(candidates),
        "sample_sources": len(sources),
        "adaptive_k": k,
        "sasb_fallback": 0,
    }


def simulate_method(dataset, meta, graph0, method, args):
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    max_steps = args.max_steps if args.max_steps > 0 else original_m
    state = {"original_n": original_n}
    rows = []
    curve_rows = [
        {
            "dataset": dataset,
            "graph_id": meta["graph_id"],
            "graph_name": meta.get("graph_name", meta["graph_id"]),
            "graph_type": meta.get("graph_type", "unknown"),
            "community_strength": meta.get("community_strength", "unknown"),
            "method": method,
            "step": 0,
            "removed_edges": 0,
            "remove_ratio": 0.0,
            "gcc_ratio": gcc_ratio(graph, original_n),
            "gcc_size": gcc_size(graph),
        }
    ]
    start = time.perf_counter()
    timed_out = False
    step = 0
    while graph.number_of_edges() > 0 and step < max_steps:
        if step / float(max(1, original_m)) >= args.max_remove_ratio:
            break
        if args.timeout_seconds_per_method > 0 and time.perf_counter() - start > args.timeout_seconds_per_method:
            timed_out = True
            break

        h_graph = largest_cc_graph(graph)
        if h_graph.number_of_edges() == 0:
            break
        partition = get_diagnostic_partition(h_graph, step, state, args.diagnostic_louvain_interval)
        gcc_size_before = gcc_size(graph)
        gcc_ratio_before = gcc_size_before / float(max(1, original_n))
        components_before = num_components(graph)

        if method == METHOD_M5:
            edge, score_details = choose_m5_with_details(h_graph)
        elif method == METHOD_SASB:
            edge, score_details = choose_sasb_with_details(h_graph, step, state, args)
        else:
            raise ValueError("Unknown method: {}".format(method))
        if edge is None or not graph.has_edge(*edge):
            break
        edge = canonical_edge(edge)
        is_selected_bridge = selected_edge_is_bridge(h_graph, edge)
        structural = structural_edge_features(h_graph, edge, partition)

        graph.remove_edge(*edge)
        gcc_size_after = gcc_size(graph)
        gcc_ratio_after = gcc_size_after / float(max(1, original_n))
        components_after = num_components(graph)
        remove_ratio_before = step / float(max(1, original_m))
        remove_ratio_after = (step + 1) / float(max(1, original_m))

        row = {
            "dataset": dataset,
            "graph_id": meta["graph_id"],
            "graph_name": meta.get("graph_name", meta["graph_id"]),
            "graph_type": meta.get("graph_type", "unknown"),
            "community_strength": meta.get("community_strength", "unknown"),
            "method": method,
            "step": step,
            "removed_edges_after_step": step + 1,
            "remove_ratio_before": remove_ratio_before,
            "remove_ratio_after": remove_ratio_after,
            "attack_phase": attack_phase(remove_ratio_before),
            "gcc_before": gcc_ratio_before,
            "gcc_after": gcc_ratio_after,
            "gcc_size_before": gcc_size_before,
            "gcc_size_after": gcc_size_after,
            "delta_gcc": gcc_ratio_before - gcc_ratio_after,
            "num_components_before": components_before,
            "num_components_after": components_after,
            "delta_components": components_after - components_before,
            "is_bridge_before_removal": is_selected_bridge,
            "num_bridges_before": np.nan,
            "current_gcc_nodes": h_graph.number_of_nodes(),
            "current_gcc_edges": h_graph.number_of_edges(),
            "original_nodes": original_n,
            "original_edges": original_m,
        }
        row.update(structural)
        row.update(score_details)
        rows.append(row)
        step += 1
        curve_rows.append(
            {
                "dataset": dataset,
                "graph_id": meta["graph_id"],
                "graph_name": meta.get("graph_name", meta["graph_id"]),
                "graph_type": meta.get("graph_type", "unknown"),
                "community_strength": meta.get("community_strength", "unknown"),
                "method": method,
                "step": step,
                "removed_edges": step,
                "remove_ratio": remove_ratio_after,
                "gcc_ratio": gcc_ratio_after,
                "gcc_size": gcc_size_after,
            }
        )
        if args.progress_interval_steps > 0 and step % args.progress_interval_steps == 0:
            elapsed_so_far = time.perf_counter() - start
            print(
                "progress dataset={} graph={} method={} step={} ratio={} gcc={} elapsed_sec={}".format(
                    dataset,
                    meta["graph_id"],
                    method,
                    step,
                    fmt(remove_ratio_after, 4),
                    fmt(gcc_ratio_after, 4),
                    fmt(elapsed_so_far, 1),
                ),
                flush=True,
            )

    elapsed = time.perf_counter() - start
    status = "timeout" if timed_out else "finished"
    if step >= max_steps and max_steps < original_m:
        status = "max_steps_reached"
    if step / float(max(1, original_m)) >= args.max_remove_ratio and args.max_remove_ratio < 1.0:
        status = "max_remove_ratio_reached"
    step_df = pd.DataFrame(rows)
    curve_df = pd.DataFrame(curve_rows)
    summary = summarize_graph_method(curve_df, step_df, elapsed, status)
    timings = {}
    if method == METHOD_SASB:
        timings = state.get("sasb_timings", {}).copy()
        timings["louvain_recomputes"] = state.get("sasb_louvain_recomputes", 0)
        timings["last_adaptive_k"] = state.get("last_adaptive_k", np.nan)
        timings["last_sample_sources"] = state.get("last_sample_sources", np.nan)
    summary["diagnostic_louvain_recomputes"] = state.get("diagnostic_louvain_recomputes", 0)
    summary["diagnostic_louvain_interval"] = args.diagnostic_louvain_interval
    summary.update(timings)
    return step_df, curve_df, summary


def summarize_graph_method(curve_df, step_df, elapsed, status):
    x = curve_df["remove_ratio"].astype(float).values
    y = curve_df["gcc_ratio"].astype(float).values
    observed = float(x[-1]) if len(x) else 0.0
    auc = float(np.trapz(y, x)) if len(x) else np.nan
    row = {
        "dataset": curve_df["dataset"].iloc[0],
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_name": curve_df["graph_name"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "community_strength": curve_df["community_strength"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "status": status,
        "removed_edges": int(curve_df["removed_edges"].max()),
        "observed_remove_ratio": observed,
        "auc": auc,
        "normalized_auc": auc / observed if observed > 0 else np.nan,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "runtime_seconds": float(elapsed),
    }
    if not step_df.empty:
        row.update(
            {
                "mean_delta_gcc": float(step_df["delta_gcc"].mean()),
                "sum_delta_gcc": float(step_df["delta_gcc"].sum()),
                "bridge_selection_ratio": float(step_df["is_bridge_before_removal"].mean()),
                "inter_community_edge_ratio": float(step_df["is_inter_community_edge"].mean()),
                "mean_common_neighbors": float(step_df["common_neighbors"].mean()),
                "median_common_neighbors": float(step_df["common_neighbors"].median()),
                "mean_edge_embeddedness": float(step_df["edge_embeddedness"].mean()),
                "median_edge_embeddedness": float(step_df["edge_embeddedness"].median()),
                "mean_degree_product": float(step_df["degree_product"].mean()),
            }
        )
    return row


def run_path(out_dir, dataset, graph_id, method):
    root = out_dir / "runs" / dataset / str(graph_id) / method_slug(method)
    return root / "edge_steps.csv", root / "curve.csv", root / "summary.csv"


def run_one(out_dir, dataset, meta, graph, method, args):
    steps_path, curve_path, summary_path = run_path(out_dir, dataset, meta["graph_id"], method)
    if steps_path.exists() and curve_path.exists() and summary_path.exists() and not args.overwrite_runs:
        return pd.read_csv(steps_path), pd.read_csv(curve_path), pd.read_csv(summary_path).iloc[0].to_dict(), "cached"
    step_df, curve_df, summary = simulate_method(dataset, meta, graph, method, args)
    write_csv(step_df, steps_path)
    write_csv(curve_df, curve_path)
    write_csv(pd.DataFrame([summary]), summary_path)
    return step_df, curve_df, summary, "ran"


def completed_real_graph_ids():
    per = read_csv(REAL_M5_COMPLETED)
    if per.empty:
        return []
    m5 = per[(per["method_label"] == "M5") & (per["status"] == "finished")].copy()
    m5["observed_remove_ratio"] = pd.to_numeric(m5["observed_remove_ratio"], errors="coerce")
    return sorted(m5[m5["observed_remove_ratio"] >= 0.999999]["graph_id"].dropna().unique())


def fallback_real_metadata(graph_ids):
    per = read_csv(REAL_M5_COMPLETED)
    if per.empty:
        return pd.DataFrame()
    base = per[per["graph_id"].isin(graph_ids)].drop_duplicates("graph_id").copy()
    metadata_path = ROOT / "data" / "realnetworks_40plus" / "metadata" / "real_networks_metadata.csv"
    metadata = read_csv(metadata_path)
    if not metadata.empty:
        keep_cols = [col for col in metadata.columns if col not in base.columns or col == "graph_id"]
        base = base.merge(metadata[keep_cols], on="graph_id", how="left")
    if "cleaned_file" not in base.columns:
        base["cleaned_file"] = base["graph_id"].map(
            lambda graph_id: str(Path("data") / "realnetworks_40plus" / "cleaned" / "{}.edges".format(graph_id))
        )
    for col in ["graph_name", "network_name"]:
        if col not in base.columns:
            base[col] = base["graph_id"]
    if "graph_type" not in base.columns:
        if "network_type" in base.columns:
            base["graph_type"] = base["network_type"]
        else:
            base["graph_type"] = "unknown"
    if "community_strength" not in base.columns:
        base["community_strength"] = "realworld"
    order = {graph_id: idx for idx, graph_id in enumerate(graph_ids)}
    base["_order"] = base["graph_id"].map(order)
    return base.sort_values("_order").drop(columns=["_order"])


def load_real_graph_from_meta(meta):
    cleaned = meta.get("cleaned_file", "")
    path = ROOT / cleaned if cleaned else ROOT / "data" / "realnetworks_40plus" / "cleaned" / "{}.edges".format(meta["graph_id"])
    if not path.exists():
        path = ROOT / "data" / "realnetworks_40plus" / "cleaned" / "{}.edges".format(meta["graph_id"])
    return real40.load_cleaned_graph(path)


def select_graphs(args):
    selected = []
    datasets = {part.strip() for part in args.datasets.split(",") if part.strip()}
    graph_filter = set(part.strip() for part in args.graph_ids.split(",") if part.strip())
    if "synthetic45" in datasets:
        groups = fair.load_synthetic_groups(max_graphs=args.max_synthetic)
        for graph_id, group in groups:
            if graph_filter and graph_id not in graph_filter:
                continue
            selected.append(("synthetic45", fair.synthetic_meta(group), fair.reconstruct_synthetic_graph(group)))
    if "realworld_completed" in datasets:
        graph_ids = completed_real_graph_ids()
        if graph_filter:
            graph_ids = [gid for gid in graph_ids if gid in graph_filter]
        if args.max_real > 0:
            graph_ids = graph_ids[: args.max_real]
        try:
            metadata = fair.load_real_metadata(graph_ids=graph_ids)
            loader = fair.load_real_graph
        except FileNotFoundError:
            metadata = fallback_real_metadata(graph_ids)
            loader = load_real_graph_from_meta
        for _, row in metadata.iterrows():
            meta = row.to_dict()
            graph = loader(meta)
            if args.real_max_nodes > 0 and graph.number_of_nodes() > args.real_max_nodes:
                continue
            if args.real_max_edges > 0 and graph.number_of_edges() > args.real_max_edges:
                continue
            selected.append(("realworld_completed", meta, graph))
    return selected


def collect_run_outputs(out_dir):
    step_frames = []
    curve_frames = []
    summary_frames = []
    for path in sorted((out_dir / "runs").glob("*/*/*/edge_steps.csv")):
        step_frames.append(pd.read_csv(path))
    for path in sorted((out_dir / "runs").glob("*/*/*/curve.csv")):
        curve_frames.append(pd.read_csv(path))
    for path in sorted((out_dir / "runs").glob("*/*/*/summary.csv")):
        summary_frames.append(pd.read_csv(path))
    steps = pd.concat(step_frames, ignore_index=True, sort=False) if step_frames else pd.DataFrame()
    curves = pd.concat(curve_frames, ignore_index=True, sort=False) if curve_frames else pd.DataFrame()
    summaries = pd.concat(summary_frames, ignore_index=True, sort=False) if summary_frames else pd.DataFrame()
    return steps, curves, summaries


def phase_auc(curve_df):
    rows = []
    intervals = [("early", 0.0, 1.0 / 3.0), ("middle", 1.0 / 3.0, 2.0 / 3.0), ("late", 2.0 / 3.0, 1.0)]
    for (dataset, graph_id, method), group in curve_df.groupby(["dataset", "graph_id", "method"]):
        group = group.sort_values("remove_ratio")
        x = group["remove_ratio"].astype(float).values
        y = group["gcc_ratio"].astype(float).values
        if len(x) < 2:
            continue
        observed = float(x[-1])
        for phase, start, end in intervals:
            upper = min(end, observed)
            if upper <= start:
                rows.append(
                    {
                        "dataset": dataset,
                        "graph_id": graph_id,
                        "method": method,
                        "attack_phase": phase,
                        "phase_start": start,
                        "phase_end": upper,
                        "phase_observed_width": 0.0,
                        "phase_auc": np.nan,
                        "phase_normalized_auc": np.nan,
                    }
                )
                continue
            inner_x = x[(x > start) & (x < upper)]
            grid = np.unique(np.concatenate([[start], inner_x, [upper]]))
            vals = np.interp(grid, x, y)
            auc = float(np.trapz(vals, grid))
            rows.append(
                {
                    "dataset": dataset,
                    "graph_id": graph_id,
                    "method": method,
                    "attack_phase": phase,
                    "phase_start": start,
                    "phase_end": upper,
                    "phase_observed_width": upper - start,
                    "phase_auc": auc,
                    "phase_normalized_auc": auc / (upper - start),
                }
            )
    return pd.DataFrame(rows)


def structure_summary(step_df):
    if step_df.empty:
        return pd.DataFrame()
    grouped = step_df.groupby(["dataset", "method", "attack_phase"])
    out = grouped.agg(
        {
            "step": "count",
            "delta_gcc": ["mean", "median"],
            "is_bridge_before_removal": "mean",
            "is_inter_community_edge": "mean",
            "common_neighbors": ["mean", "median"],
            "edge_embeddedness": ["mean", "median"],
            "degree_product": ["mean", "median"],
        }
    ).reset_index()
    out.columns = [
        "dataset",
        "method",
        "attack_phase",
        "steps",
        "mean_delta_gcc",
        "median_delta_gcc",
        "bridge_selection_ratio",
        "inter_community_edge_ratio",
        "mean_common_neighbors",
        "median_common_neighbors",
        "mean_edge_embeddedness",
        "median_edge_embeddedness",
        "mean_degree_product",
        "median_degree_product",
    ]
    return out


def diagnose_row(group):
    by = {row["method"]: row for _, row in group.iterrows()}
    if METHOD_M5 not in by or METHOD_SASB not in by:
        return None
    m5 = by[METHOD_M5]
    sasb = by[METHOD_SASB]
    diff = float(sasb["normalized_auc"]) - float(m5["normalized_auc"])
    reasons = []
    if diff < -1e-12:
        outcome = "SASB_better"
        if sasb.get("bridge_selection_ratio", 0) > m5.get("bridge_selection_ratio", 0):
            reasons.append("SASB 更频繁选择 bridge")
        if sasb.get("mean_edge_embeddedness", 0) < m5.get("mean_edge_embeddedness", 0):
            reasons.append("SASB 更偏向低 embeddedness 边")
        if sasb.get("mean_delta_gcc", 0) > m5.get("mean_delta_gcc", 0):
            reasons.append("SASB 所选边带来更大的平均 GCC drop")
    elif diff > 1e-12:
        outcome = "SASB_worse"
        if sasb.get("bridge_selection_ratio", 0) < m5.get("bridge_selection_ratio", 0):
            reasons.append("SASB 选择 bridge 的比例更低")
        if sasb.get("mean_delta_gcc", 0) < m5.get("mean_delta_gcc", 0):
            reasons.append("SASB 所选边平均 GCC drop 更小")
        if sasb.get("mean_common_neighbors", 0) > m5.get("mean_common_neighbors", 0):
            reasons.append("SASB 所选边局部嵌入更强")
    else:
        outcome = "tie"
    if not reasons:
        reasons.append("当前记录的单一结构指标不足以解释 AUC 差异")
    return {
        "dataset": m5["dataset"],
        "graph_id": m5["graph_id"],
        "graph_name": m5.get("graph_name", m5["graph_id"]),
        "graph_type": m5.get("graph_type", "unknown"),
        "community_strength": m5.get("community_strength", "unknown"),
        "sasb_minus_m5_normalized_auc": diff,
        "outcome": outcome,
        "m5_auc": m5["normalized_auc"],
        "sasb_auc": sasb["normalized_auc"],
        "m5_mean_delta_gcc": m5.get("mean_delta_gcc", np.nan),
        "sasb_mean_delta_gcc": sasb.get("mean_delta_gcc", np.nan),
        "m5_bridge_ratio": m5.get("bridge_selection_ratio", np.nan),
        "sasb_bridge_ratio": sasb.get("bridge_selection_ratio", np.nan),
        "m5_inter_community_ratio": m5.get("inter_community_edge_ratio", np.nan),
        "sasb_inter_community_ratio": sasb.get("inter_community_edge_ratio", np.nan),
        "m5_mean_common_neighbors": m5.get("mean_common_neighbors", np.nan),
        "sasb_mean_common_neighbors": sasb.get("mean_common_neighbors", np.nan),
        "m5_mean_embeddedness": m5.get("mean_edge_embeddedness", np.nan),
        "sasb_mean_embeddedness": sasb.get("mean_edge_embeddedness", np.nan),
        "diagnosis": "; ".join(reasons),
    }


def network_diagnosis(summary_df):
    rows = []
    if summary_df.empty:
        return pd.DataFrame()
    for _, group in summary_df.groupby(["dataset", "graph_id"]):
        row = diagnose_row(group)
        if row is not None:
            rows.append(row)
    return pd.DataFrame(rows)


def boxplot_metric(step_df, metric, path, title, ylabel):
    if step_df.empty or metric not in step_df.columns:
        return
    labels = []
    values = []
    for (dataset, method), group in step_df.groupby(["dataset", "method"]):
        series = pd.to_numeric(group[metric], errors="coerce").dropna()
        if len(series) == 0:
            continue
        labels.append("{}\n{}".format(dataset.replace("_", " "), method))
        values.append(series.values)
    if not values:
        return
    fig, ax = plt.subplots(figsize=(max(7, len(values) * 1.4), 4.8))
    ax.boxplot(values, labels=labels, showfliers=False)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def bar_metric(summary, metric, path, title, ylabel):
    if summary.empty or metric not in summary.columns:
        return
    labels = []
    values = []
    for _, row in summary.iterrows():
        labels.append("{}\n{}\n{}".format(row["dataset"].replace("_", " "), row["method"], row["attack_phase"]))
        values.append(float(row[metric]))
    fig, ax = plt.subplots(figsize=(max(8, len(values) * 0.55), 4.8))
    ax.bar(range(len(values)), values)
    ax.set_xticks(range(len(values)))
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def phase_auc_plot(phase_df, path):
    if phase_df.empty:
        return
    summary = (
        phase_df.groupby(["dataset", "method", "attack_phase"])["phase_normalized_auc"]
        .mean()
        .reset_index()
    )
    phases = ["early", "middle", "late"]
    labels = []
    values = []
    for (dataset, method), group in summary.groupby(["dataset", "method"]):
        row = {r["attack_phase"]: r["phase_normalized_auc"] for _, r in group.iterrows()}
        labels.append("{}\n{}".format(dataset.replace("_", " "), method))
        values.append([row.get(phase, np.nan) for phase in phases])
    if not values:
        return
    x = np.arange(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.2), 4.8))
    for idx, phase in enumerate(phases):
        ax.bar(x + (idx - 1) * width, [row[idx] for row in values], width, label=phase)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Mean phase normalized AUC")
    ax.set_title("Early / middle / late phase AUC")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_plots(out_dir, steps, struct, phase_df):
    plot_dir = out_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    boxplot_metric(
        steps,
        "delta_gcc",
        plot_dir / "selected_edge_delta_gcc_distribution.png",
        "M5 vs SASB selected-edge delta GCC distribution",
        "GCC ratio drop after selected edge removal",
    )
    bar_metric(
        struct,
        "bridge_selection_ratio",
        plot_dir / "bridge_selection_ratio_by_phase.png",
        "M5 vs SASB bridge selection ratio",
        "Bridge selection ratio",
    )
    bar_metric(
        struct,
        "inter_community_edge_ratio",
        plot_dir / "inter_community_edge_ratio_by_phase.png",
        "M5 vs SASB inter-community edge ratio",
        "Inter-community edge ratio",
    )
    boxplot_metric(
        steps,
        "common_neighbors",
        plot_dir / "selected_edge_common_neighbors_distribution.png",
        "Selected-edge common-neighbor distribution",
        "Common neighbors",
    )
    boxplot_metric(
        steps,
        "edge_embeddedness",
        plot_dir / "selected_edge_embeddedness_distribution.png",
        "Selected-edge embeddedness distribution",
        "Edge embeddedness",
    )
    phase_auc_plot(phase_df, plot_dir / "phase_auc_comparison.png")


def fmt(value, digits=4):
    if value is None or pd.isna(value):
        return "-"
    return ("{:." + str(digits) + "f}").format(float(value))


def to_markdown_table(df, max_rows=30):
    if df.empty:
        return "暂无数据。"
    d = df.head(max_rows).copy()
    lines = [
        "| " + " | ".join(map(str, d.columns)) + " |",
        "|" + "|".join("---" for _ in d.columns) + "|",
    ]
    for _, row in d.iterrows():
        vals = []
        for col in d.columns:
            value = row[col]
            if isinstance(value, float):
                vals.append(fmt(value, 6))
            else:
                vals.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_report(out_dir, args, steps, curves, summaries, struct, phase_df, diagnosis):
    plot_dir = out_dir / "plots"
    if summaries.empty:
        method_summary = pd.DataFrame()
    else:
        rows = []
        for (dataset, method), group in summaries.groupby(["dataset", "method"]):
            rows.append(
                {
                    "dataset": dataset,
                    "method": method,
                    "graphs": group["graph_id"].nunique(),
                    "finished": int((group["status"] == "finished").sum()),
                    "mean_auc": group["normalized_auc"].mean(),
                    "mean_runtime_seconds": group["runtime_seconds"].mean(),
                    "mean_delta_gcc": group.get("mean_delta_gcc", pd.Series(dtype=float)).mean(),
                    "bridge_ratio": group.get("bridge_selection_ratio", pd.Series(dtype=float)).mean(),
                    "inter_ratio": group.get("inter_community_edge_ratio", pd.Series(dtype=float)).mean(),
                    "common_neighbors": group.get("mean_common_neighbors", pd.Series(dtype=float)).mean(),
                    "embeddedness": group.get("mean_edge_embeddedness", pd.Series(dtype=float)).mean(),
                }
            )
        method_summary = pd.DataFrame(rows)
    outcome_counts = (
        diagnosis.groupby(["dataset", "outcome"]).size().reset_index(name="graphs")
        if not diagnosis.empty
        else pd.DataFrame()
    )
    incomplete = summaries[summaries["status"] != "finished"] if not summaries.empty else pd.DataFrame()
    lines = [
        "# SASB vs M5 选边机制诊断报告",
        "",
        "## 1. 诊断目的",
        "",
        "本诊断固定主方法为 `M19-sampled-BE-fast / SASB`，不引入新算法。脚本逐步重跑 M5 dynamic edge betweenness 与 SASB，在同一批网络上记录每一步被选边的结构特征，用于分析少量结构化源点近似边介数为何可能更适合网络瓦解。",
        "",
        "## 2. 方法口径",
        "",
        "- M5：每一步在当前 GCC 上计算完整 `nx.edge_betweenness_centrality(..., normalized=True, weight=None)`，选择最高边。",
        "- SASB：使用 `S_comm/S_boundary/S_local` 三类结构候选集，不使用 `Delta_GCC`，最终按 sampled dependency / sampled betweenness 排序。",
        "- 诊断特征：每一步在当前 GCC 上计算 bridge 标记、Louvain 社区间边、端点度、度乘积、共同邻居、embeddedness、GCC drop 与组件数变化。",
        "- AUC 越低表示瓦解越快。early/middle/late 按边移除比例 `[0,1/3)`, `[1/3,2/3)`, `[2/3,1]` 划分。",
        "",
        "## 3. 运行设置",
        "",
        f"- 数据集参数：`{args.datasets}`。",
        f"- `max_remove_ratio={args.max_remove_ratio}`，`max_steps={args.max_steps}`，`timeout_seconds_per_method={args.timeout_seconds_per_method}`。",
        f"- SASB 参数：`k_min={args.k_min}`，`k_max={args.k_max}`，`m_min={args.m_min}`，`m_max={args.m_max}`，`epsilon={args.epsilon}`，`confidence_delta={args.confidence_delta}`。",
        f"- 输出目录：`{out_dir.relative_to(ROOT)}`。",
        "",
        "## 4. 总体统计",
        "",
        to_markdown_table(method_summary),
        "",
        "## 5. SASB 优于或弱于 M5 的网络诊断",
        "",
        to_markdown_table(outcome_counts),
        "",
        to_markdown_table(
            diagnosis[
                [
                    "dataset",
                    "graph_id",
                    "graph_type",
                    "community_strength",
                    "outcome",
                    "sasb_minus_m5_normalized_auc",
                    "diagnosis",
                ]
            ]
            if not diagnosis.empty
            else diagnosis
        ),
        "",
        "## 6. 图表路径",
        "",
        f"- selected edge delta_gcc 分布：`{(plot_dir / 'selected_edge_delta_gcc_distribution.png').relative_to(ROOT)}`",
        f"- bridge selection ratio：`{(plot_dir / 'bridge_selection_ratio_by_phase.png').relative_to(ROOT)}`",
        f"- inter-community edge ratio：`{(plot_dir / 'inter_community_edge_ratio_by_phase.png').relative_to(ROOT)}`",
        f"- common-neighbor 分布：`{(plot_dir / 'selected_edge_common_neighbors_distribution.png').relative_to(ROOT)}`",
        f"- embeddedness 分布：`{(plot_dir / 'selected_edge_embeddedness_distribution.png').relative_to(ROOT)}`",
        f"- early/middle/late AUC：`{(plot_dir / 'phase_auc_comparison.png').relative_to(ROOT)}`",
        "",
        "## 7. 机制解释",
        "",
    ]
    if diagnosis.empty:
        lines.extend(
            [
                "当前还没有同时包含 M5 与 SASB 的完整网络对照，因此不能回答机制问题。请扩大运行范围后重新生成报告。",
            ]
        )
    else:
        better = diagnosis[diagnosis["outcome"] == "SASB_better"]
        worse = diagnosis[diagnosis["outcome"] == "SASB_worse"]
        lines.extend(
            [
                f"- 当前结果中，SASB 优于 M5 的网络数为 `{len(better)}`，弱于 M5 的网络数为 `{len(worse)}`。如果本次是限步或限比例诊断，这个结论只适用于已观察攻击前缀。",
                "- 当 SASB 更好时，优先检查它是否更频繁选择 bridge、低 embeddedness、低 common-neighbor 或带来更大 immediate GCC drop 的边。如果这些指标同步增强，可以将少量源点采样解释为一种有益的结构偏差，而不是简单估计误差。",
                "- 当 SASB 更弱时，通常需要检查候选集是否遗漏 M5 高介数边、采样排序是否偏离、或 SASB 是否选择了更局部嵌入的边而没有产生足够 GCC drop。",
                "- 本报告只依据已落盘诊断 CSV 自动生成；若 full realworld completed subset 尚未跑完，不应外推为最终论文结论。",
            ]
        )
    if not incomplete.empty:
        lines.extend(
            [
                "",
                "## 8. 未完成或前缀运行",
                "",
                "以下方法-网络未达到完整 finished 状态，相关结果只能作为前缀诊断：",
                "",
                to_markdown_table(incomplete[["dataset", "graph_id", "method", "status", "observed_remove_ratio", "removed_edges"]]),
            ]
        )
    (out_dir / "mechanism_diagnostic_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_required_alias_columns(steps):
    if steps.empty:
        return steps
    aliases = {
        "edge_u": "selected_edge_u",
        "edge_v": "selected_edge_v",
        "num_components_before": "components_before",
        "num_components_after": "components_after",
        "is_bridge_before_removal": "is_bridge",
        "is_inter_community_edge": "is_inter_community",
        "edge_embeddedness": "embeddedness",
        "full_edge_betweenness_score": "full_edge_betweenness",
        "sampled_betweenness_score": "sampled_betweenness",
    }
    steps = steps.copy()
    for source, target in aliases.items():
        if source in steps.columns and target not in steps.columns:
            steps[target] = steps[source]
    return steps


def finalize_outputs(out_dir, args):
    steps, curves, summaries = collect_run_outputs(out_dir)
    steps = add_required_alias_columns(steps)
    write_csv(steps, out_dir / "edge_step_diagnostics.csv")
    write_csv(curves, out_dir / "attack_curves.csv")
    write_csv(summaries, out_dir / "graph_method_summary.csv")
    struct = structure_summary(steps)
    phase_df = phase_auc(curves)
    diagnosis = network_diagnosis(summaries)
    write_csv(struct, out_dir / "structure_summary_by_phase.csv")
    write_csv(phase_df, out_dir / "phase_auc_by_graph.csv")
    write_csv(diagnosis, out_dir / "network_diagnosis.csv")
    make_plots(out_dir, steps, struct, phase_df)
    write_report(out_dir, args, steps, curves, summaries, struct, phase_df, diagnosis)


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnose selected-edge mechanisms for M5 vs SASB.")
    parser.add_argument("--datasets", default="synthetic45,realworld_completed")
    parser.add_argument("--graph-ids", default="", help="Optional comma-separated graph ids.")
    parser.add_argument("--max-synthetic", type=int, default=45)
    parser.add_argument("--max-real", type=int, default=0, help="0 means all completed realworld graphs.")
    parser.add_argument("--max-remove-ratio", type=float, default=1.0)
    parser.add_argument("--max-steps", type=int, default=0, help="0 means no explicit step cap.")
    parser.add_argument("--timeout-seconds-per-method", type=float, default=0.0)
    parser.add_argument("--compute-sasb-full-eb", action="store_true")
    parser.add_argument("--overwrite-runs", action="store_true")
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--real-max-nodes", type=int, default=0, help="0 means no real-network node cap.")
    parser.add_argument("--real-max-edges", type=int, default=0, help="0 means no real-network edge cap.")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--k-min", type=int, default=64)
    parser.add_argument("--k-max", type=int, default=512)
    parser.add_argument("--m-min", type=int, default=16)
    parser.add_argument("--m-max", type=int, default=128)
    parser.add_argument("--confidence-delta", type=float, default=0.05)
    parser.add_argument("--epsilon", type=float, default=0.10)
    parser.add_argument("--louvain-interval", type=int, default=10)
    parser.add_argument("--louvain-drop-threshold", type=float, default=0.05)
    parser.add_argument("--diagnostic-louvain-interval", type=int, default=1)
    parser.add_argument("--progress-interval-steps", type=int, default=250)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = DEFAULT_OUT_ROOT / "diagnostic_{}".format(stamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": str(Path(__file__).resolve().relative_to(ROOT)),
        "m5_implementation": "scripts/evaluate_heuristic_attacks.py::choose_betweenness_edge",
        "sasb_implementation": "scripts/evaluate_m19_theory_calibrated.py::METHOD_THEORY_FAST_NO_DELTA plus candidate_features(delta_mode='none')",
        "args": vars(args),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.aggregate_only:
        finalize_outputs(out_dir, args)
        print("aggregated existing diagnostic outputs in {}".format(out_dir), flush=True)
        return
    graphs = select_graphs(args)
    if not graphs:
        raise RuntimeError("No graphs selected.")
    run_rows = []
    for dataset, meta, graph in graphs:
        for method in [METHOD_M5, METHOD_SASB]:
            step_df, curve_df, summary, source = run_one(out_dir, dataset, meta, graph, method, args)
            run_rows.append(
                {
                    "dataset": dataset,
                    "graph_id": meta["graph_id"],
                    "method": method,
                    "status": summary.get("status"),
                    "source": source,
                    "removed_edges": summary.get("removed_edges"),
                    "observed_remove_ratio": summary.get("observed_remove_ratio"),
                    "runtime_seconds": summary.get("runtime_seconds"),
                }
            )
            print(
                "{} {} {} {} removed={} ratio={}".format(
                    dataset,
                    meta["graph_id"],
                    method,
                    summary.get("status"),
                    summary.get("removed_edges"),
                    fmt(summary.get("observed_remove_ratio"), 4),
                ),
                flush=True,
            )
    write_csv(pd.DataFrame(run_rows), out_dir / "run_status.csv")
    finalize_outputs(out_dir, args)
    print("diagnostic outputs written to {}".format(out_dir), flush=True)


if __name__ == "__main__":
    main()
