from pathlib import Path
from collections import deque
import argparse
import json
import math
import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from scipy.stats import kendalltau, spearmanr

import evaluate_m18_candidate as m18
import evaluate_m19_next_stage_validation as m19val
import evaluate_next_stage_fair_comparison as fair


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260513
OUT_DIR = ROOT / "result" / "next_stage_fair_comparison"

METHOD_ORIGINAL = "M19-original"
METHOD_THEORY_LEGACY = "M19-theory"
METHOD_THEORY_CONSERVATIVE = "M19-theory-conservative"
METHOD_THEORY_GAP_STOP = "M19-theory-gap-stop"
METHOD_THEORY_RECALL_PLUS = "M19-theory-recall-plus"
METHOD_THEORY_FAST_NO_DELTA_LEGACY = "M19-theory-fast-no-delta"
METHOD_THEORY_FAST_NO_DELTA = "M19-sampled-BE-fast"
METHOD_THEORY_FULL_DELTA = "theory-full-delta"
METHOD_THEORY_NO_DELTA = "theory-no-delta"
METHOD_THEORY_BRIDGE_DELTA_ONLY = "theory-bridge-delta-only"
METHOD_THEORY_LOCAL_TOP_DELTA_ONLY = "theory-local-top-delta-only"
METHOD_THEORY = METHOD_THEORY_CONSERVATIVE
METHOD_BE = "M19-BE"
METHOD_CALIBRATED = "M19-calibrated"

BASELINE_METHODS = [
    fair.METHOD_M5,
    fair.METHOD_M7,
    fair.METHOD_M12,
    fair.METHOD_M19,
    fair.METHOD_M19_NO_BRIDGE,
]
COMPARISON_METHODS = [
    METHOD_ORIGINAL,
    fair.METHOD_M19_NO_BRIDGE,
    METHOD_THEORY_CONSERVATIVE,
    METHOD_THEORY_GAP_STOP,
    METHOD_THEORY_RECALL_PLUS,
    METHOD_THEORY_FAST_NO_DELTA,
    METHOD_THEORY_FULL_DELTA,
    METHOD_THEORY_NO_DELTA,
    METHOD_THEORY_BRIDGE_DELTA_ONLY,
    METHOD_THEORY_LOCAL_TOP_DELTA_ONLY,
    METHOD_CALIBRATED,
    fair.METHOD_M5,
    fair.METHOD_M7,
    fair.METHOD_M12,
]
LABELS = {
    METHOD_ORIGINAL: "M19-original",
    METHOD_THEORY_LEGACY: "M19-theory-conservative",
    METHOD_THEORY_CONSERVATIVE: "M19-theory-conservative",
    METHOD_THEORY_GAP_STOP: "M19-theory-gap-stop",
    METHOD_THEORY_RECALL_PLUS: "M19-theory-recall-plus",
    METHOD_THEORY_FAST_NO_DELTA_LEGACY: "M19-sampled-BE-fast",
    METHOD_THEORY_FAST_NO_DELTA: "M19-sampled-BE-fast",
    METHOD_THEORY_FULL_DELTA: "theory-full-delta",
    METHOD_THEORY_NO_DELTA: "theory-no-delta",
    METHOD_THEORY_BRIDGE_DELTA_ONLY: "theory-bridge-delta-only",
    METHOD_THEORY_LOCAL_TOP_DELTA_ONLY: "theory-local-top-delta-only",
    METHOD_BE: "M19-BE",
    METHOD_CALIBRATED: "M19-calibrated",
    fair.METHOD_M19_NO_BRIDGE: "M19-no-bridge",
    fair.METHOD_M5: "M5",
    fair.METHOD_M7: "M7",
    fair.METHOD_M12: "M12",
}


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def canonical_edge(edge):
    u, v = edge
    return (u, v) if u <= v else (v, u)


def top_edges(scores, limit):
    rows = [(score, edge) for edge, score in scores.items()]
    rows.sort(key=lambda item: (-item[0], item[1]))
    return [edge for _, edge in rows[: max(0, limit)]]


def normalize_dict(scores):
    if not scores:
        return {}
    maximum = max(scores.values())
    if maximum <= 0:
        return {edge: 0.0 for edge in scores}
    return {edge: value / maximum for edge, value in scores.items()}


def canonical_method(method):
    if method == METHOD_THEORY_LEGACY:
        return METHOD_THEORY_CONSERVATIVE
    if method == METHOD_THEORY_FAST_NO_DELTA_LEGACY:
        return METHOD_THEORY_FAST_NO_DELTA
    return method


def method_candidate_variant(method):
    if method == METHOD_THEORY_RECALL_PLUS:
        return "recall_plus"
    return "conservative"


def method_delta_mode(method):
    if method in {METHOD_THEORY_FAST_NO_DELTA, METHOD_THEORY_NO_DELTA}:
        return "none"
    if method == METHOD_THEORY_BRIDGE_DELTA_ONLY:
        return "bridge"
    if method == METHOD_THEORY_LOCAL_TOP_DELTA_ONLY:
        return "local_top"
    return "full"


def method_uses_theory_sampling(method):
    return method in {
        METHOD_THEORY_CONSERVATIVE,
        METHOD_THEORY_RECALL_PLUS,
        METHOD_THEORY_FAST_NO_DELTA,
        METHOD_THEORY_FULL_DELTA,
        METHOD_THEORY_NO_DELTA,
        METHOD_THEORY_BRIDGE_DELTA_ONLY,
        METHOD_THEORY_LOCAL_TOP_DELTA_ONLY,
    }


def method_uses_candidate_v2_cache(method):
    return method in {
        METHOD_THEORY_CONSERVATIVE,
        METHOD_THEORY_RECALL_PLUS,
        METHOD_THEORY_FAST_NO_DELTA,
        METHOD_THEORY_FULL_DELTA,
        METHOD_THEORY_NO_DELTA,
        METHOD_THEORY_BRIDGE_DELTA_ONLY,
        METHOD_THEORY_LOCAL_TOP_DELTA_ONLY,
    }


def method_candidate_backend(method):
    if method == METHOD_THEORY_FAST_NO_DELTA:
        return "candidate_v3_no_delta_timing"
    if method_uses_candidate_v2_cache(method):
        return "candidate_v2"
    return ""


def adaptive_k(num_nodes, num_edges, k_min, k_max):
    if num_edges <= 0:
        return k_min
    value = int(math.ceil(math.sqrt(num_edges) * math.log(max(3, num_nodes))))
    return min(k_max, max(k_min, value))


def adaptive_sample_count(candidate_count, m_min, m_max, delta, epsilon):
    c = max(1, candidate_count)
    if epsilon <= 0:
        return m_max
    estimate = int(math.ceil(math.log(2.0 * c / max(delta, 1e-12)) / (2.0 * epsilon * epsilon)))
    return min(m_max, max(m_min, estimate))


def largest_component_after_removal(h_graph, edge):
    if not h_graph.has_edge(*edge):
        return h_graph.number_of_nodes()
    h_graph.remove_edge(*edge)
    if h_graph.number_of_nodes() == 0:
        size = 0
    elif h_graph.number_of_edges() == 0:
        size = 1
    else:
        size = len(max(nx.connected_components(h_graph), key=len))
    h_graph.add_edge(*edge)
    return size


def delta_gcc_scores(h_graph, limit=None, edges=None):
    n = max(1, h_graph.number_of_nodes())
    rows = []
    edge_iter = edges if edges is not None else list(h_graph.edges())
    for edge in list(edge_iter):
        edge = canonical_edge(edge)
        if not h_graph.has_edge(*edge):
            continue
        after = largest_component_after_removal(h_graph, edge)
        rows.append(((n - after) / float(n), edge))
    rows.sort(key=lambda item: (-item[0], item[1]))
    if limit is not None:
        rows = rows[: max(0, limit)]
    return {edge: score for score, edge in rows}


def random_candidate_edges(h_graph, count, step, salt=0):
    if count <= 0:
        return []
    edges = [canonical_edge(edge) for edge in h_graph.edges()]
    if not edges:
        return []
    rng = np.random.RandomState(SEED + 104729 * (step + 1) + salt)
    order = rng.permutation(len(edges))
    return [edges[int(idx)] for idx in order[: min(count, len(edges))]]


def delta_candidates_for_mode(h_graph, local, k, mode):
    if mode == "none":
        return {}
    if mode == "bridge":
        bridges = list(nx.bridges(h_graph))
        return delta_gcc_scores(h_graph, limit=k, edges=bridges)
    if mode == "local_top":
        local_edges = top_edges(local, k)
        return delta_gcc_scores(h_graph, limit=k, edges=local_edges)
    return delta_gcc_scores(h_graph, limit=k)


def candidate_features(h_graph, partition, k, variant="conservative", delta_mode="full", step=0, args=None, timings=None):
    comm = m18.score_m19_community_edges(h_graph, partition)
    boundary = m18.score_m19_boundary_priority_edges(h_graph, partition)
    local, degree = m18.score_local_and_degree_edges(h_graph)
    delta_start = time.perf_counter()
    delta = delta_candidates_for_mode(h_graph, local, k, delta_mode)
    if timings is not None:
        timings["delta_gcc_seconds"] += time.perf_counter() - delta_start
    intra_local = {}
    if partition:
        intra_local = {
            edge: score
            for edge, score in local.items()
            if edge[0] in partition and edge[1] in partition and partition[edge[0]] == partition[edge[1]]
        }

    candidates = set()
    candidates.update(top_edges(comm, k))
    candidates.update(top_edges(boundary, k))
    candidates.update(top_edges(local, k))
    candidates.update(delta.keys())
    random_edges = []
    if variant == "recall_plus":
        candidates.update(top_edges(degree, k))
        candidates.update(top_edges(intra_local, k))
        random_count = max(1, int(math.ceil(k * max(0.0, getattr(args, "recall_plus_random_fraction", 0.05)))))
        random_edges = random_candidate_edges(h_graph, random_count, step, salt=17)
        candidates.update(random_edges)
    if not candidates:
        return [], {}, {}, {}, {}

    priority = {}
    for edge in candidates:
        base_priority = max(comm.get(edge, 0.0), boundary.get(edge, 0.0), local.get(edge, 0.0), delta.get(edge, 0.0))
        if variant == "recall_plus":
            base_priority = max(
                base_priority,
                degree.get(edge, 0.0),
                intra_local.get(edge, 0.0),
                1e-12 if edge in random_edges else 0.0,
            )
        priority[edge] = base_priority
    limit = k
    if variant == "recall_plus":
        multiplier = max(1.0, float(getattr(args, "recall_plus_candidate_multiplier", 2.0)))
        limit = min(max(k, int(math.ceil(k * multiplier))), int(getattr(args, "recall_plus_max_candidates", 512)))
    candidates = top_edges(priority, limit)
    return candidates, comm, boundary, local, delta


def select_structured_sources(h_graph, partition, boundary, limit, step):
    args = argparse.Namespace(m19_sample_sources=limit)
    return m18.select_m19_sources(h_graph, partition, boundary, args, step)


def sampled_dependencies(h_graph, candidate_edges, sources):
    return m18.sampled_candidate_edge_dependencies(h_graph, candidate_edges, sources)


def sampled_dependencies_by_source_batch(h_graph, candidate_edges, sources, adjacency=None):
    candidate_set = {canonical_edge(edge) for edge in candidate_edges}
    if adjacency is None:
        adjacency = {node: tuple(h_graph.neighbors(node)) for node in h_graph.nodes()}
    rows = []
    for source in sources:
        dependency_scores = {edge: 0.0 for edge in candidate_set}
        stack = []
        predecessors = {}
        sigma = {source: 1.0}
        distance = {source: 0}
        queue = deque([source])
        while queue:
            v = queue.popleft()
            stack.append(v)
            sigma_v = sigma[v]
            next_distance = distance[v] + 1
            for w in adjacency[v]:
                if w not in distance:
                    queue.append(w)
                    distance[w] = next_distance
                if distance[w] == next_distance:
                    sigma[w] = sigma.get(w, 0.0) + sigma_v
                    predecessors.setdefault(w, []).append(v)

        delta = {}
        while stack:
            w = stack.pop()
            sigma_w = sigma.get(w, 0.0)
            if sigma_w == 0:
                continue
            coeff = (1.0 + delta.get(w, 0.0)) / sigma_w
            for v in predecessors.get(w, ()):
                contribution = sigma[v] * coeff
                edge = (v, w) if v < w else (w, v)
                if edge in dependency_scores:
                    dependency_scores[edge] += contribution
                delta[v] = delta.get(v, 0.0) + contribution
        rows.append(dependency_scores)
    return rows


def top_two_mean_edges(mean_scores):
    rows = [(score, edge) for edge, score in mean_scores.items()]
    rows.sort(key=lambda item: (-item[0], item[1]))
    if not rows:
        return None, None, 0.0, 0.0
    top_score, top_edge = rows[0]
    second_score = rows[1][0] if len(rows) > 1 else 0.0
    second_edge = rows[1][1] if len(rows) > 1 else None
    return top_edge, second_edge, float(top_score), float(second_score)


def choose_gap_stop_edge(h_graph, candidates, partition, boundary_scores, step, state, args):
    boundary = m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    max_sources = max(1, int(args.gap_max_sources))
    min_sources = min(max_sources, max(1, int(args.gap_min_sources)))
    batch_size = max(1, int(args.gap_batch_size))
    patience_required = max(1, int(args.gap_patience))
    gap_delta = max(float(args.gap_delta), 1e-12)

    sources = select_structured_sources(h_graph, partition, boundary, max_sources, step)
    raw_accum = {edge: 0.0 for edge in candidates}
    norm_accum = {edge: 0.0 for edge in candidates}
    adjacency = {node: tuple(h_graph.neighbors(node)) for node in h_graph.nodes()}
    consecutive_ok = 0
    actual_sources = 0
    final_gap = 0.0
    final_radius = math.inf
    top_norm_edge = None
    second_norm_edge = None
    stopped_reason = "mmax"
    gap_certified = False

    for batch_start in range(0, len(sources), batch_size):
        batch = sources[batch_start : batch_start + batch_size]
        for sampled in sampled_dependencies_by_source_batch(h_graph, candidates, batch, adjacency=adjacency):
            actual_sources += 1
            source_max = max((sampled.get(edge, 0.0) for edge in candidates), default=0.0)
            for edge in candidates:
                value = float(sampled.get(edge, 0.0))
                raw_accum[edge] += value
                if source_max > 0:
                    norm_accum[edge] += value / source_max

        if actual_sources < min_sources:
            continue

        mean_scores = {edge: norm_accum[edge] / float(actual_sources) for edge in candidates}
        top_norm_edge, second_norm_edge, top_score, second_score = top_two_mean_edges(mean_scores)
        final_gap = top_score - second_score
        final_radius = math.sqrt(math.log(2.0 * max(1, len(candidates)) / gap_delta) / (2.0 * actual_sources))
        if final_gap > 2.0 * final_radius:
            consecutive_ok += 1
        else:
            consecutive_ok = 0
        if consecutive_ok >= patience_required:
            stopped_reason = "gap_certified"
            gap_certified = True
            break

    if top_norm_edge is None:
        mean_scores = {edge: norm_accum[edge] / float(max(1, actual_sources)) for edge in candidates}
        top_norm_edge, second_norm_edge, top_score, second_score = top_two_mean_edges(mean_scores)
        final_gap = top_score - second_score
        final_radius = math.sqrt(
            math.log(2.0 * max(1, len(candidates)) / gap_delta) / (2.0 * max(1, actual_sources))
        )

    raw_ranked = sorted(((raw_accum.get(edge, 0.0), edge) for edge in candidates), key=lambda item: (-item[0], item[1]))
    top_raw_edge = raw_ranked[0][1] if raw_ranked else None
    agree = bool(top_norm_edge == top_raw_edge)
    hit_mmax = actual_sources >= max_sources
    if hit_mmax and not gap_certified:
        stopped_reason = "mmax"

    stats = {
        "method": METHOD_THEORY_GAP_STOP,
        "step": step,
        "current_nodes": h_graph.number_of_nodes(),
        "current_edges": h_graph.number_of_edges(),
        "candidate_set_size": len(candidates),
        "adaptive_k": state.get("last_adaptive_k", np.nan),
        "actual_sample_sources": int(actual_sources),
        "stopped_reason": stopped_reason,
        "final_gap": float(final_gap),
        "confidence_radius": float(final_radius),
        "gap_certified": int(gap_certified),
        "hit_mmax": int(hit_mmax),
        "top_norm_edge": str(top_norm_edge),
        "second_norm_edge": str(second_norm_edge),
        "top_raw_edge": str(top_raw_edge),
        "top_edge_raw_norm_agree": int(agree),
        "dependency_backend": "batched_v3",
    }
    state.setdefault("gap_sampling_stats", []).append(stats)
    return top_norm_edge


def build_candidate_matrix(h_graph, candidates, sampled_scores, comm, boundary, local, delta):
    boundary_local = {edge: max(boundary.get(edge, 0.0), local.get(edge, 0.0)) for edge in candidates}
    norm_sampled = normalize_dict({edge: sampled_scores.get(edge, 0.0) for edge in candidates})
    norm_comm = normalize_dict({edge: comm.get(edge, 0.0) for edge in candidates})
    norm_boundary_local = normalize_dict(boundary_local)
    norm_delta = normalize_dict({edge: delta.get(edge, 0.0) for edge in candidates})
    rows = []
    for edge in candidates:
        rows.append(
            [
                norm_sampled.get(edge, 0.0),
                norm_comm.get(edge, 0.0),
                norm_boundary_local.get(edge, 0.0),
                norm_delta.get(edge, 0.0),
            ]
        )
    return np.array(rows, dtype=float)


def choose_theory_or_calibrated_edge(graph, step, state, args, weights=None):
    h_graph = m18.m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    start = time.perf_counter()
    timings = state.setdefault(
        "theory_timings",
        {
            "candidate_generation_seconds": 0.0,
            "delta_gcc_seconds": 0.0,
            "sampled_path_scoring_seconds": 0.0,
            "model_scoring_seconds": 0.0,
            "total_selection_seconds": 0.0,
        },
    )

    method = state.get("active_method", METHOD_THEORY_CONSERVATIVE)
    k = adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
    state["last_adaptive_k"] = k
    cand_start = time.perf_counter()
    partition = m18.get_adaptive_stale_partition(
        h_graph,
        step,
        state,
        "m19_theory",
        max(1, args.louvain_interval),
        max(0.0, args.louvain_drop_threshold),
    )
    candidates, comm, boundary_scores, local, delta = candidate_features(
        h_graph,
        partition,
        k,
        variant=method_candidate_variant(method),
        delta_mode=method_delta_mode(method),
        step=step,
        args=args,
        timings=timings,
    )
    timings["candidate_generation_seconds"] += time.perf_counter() - cand_start
    if not candidates:
        return m18.choose_degree_product_edge(h_graph)

    if method == METHOD_THEORY_GAP_STOP:
        sample_start = time.perf_counter()
        edge = choose_gap_stop_edge(h_graph, candidates, partition, boundary_scores, step, state, args)
        timings["sampled_path_scoring_seconds"] += time.perf_counter() - sample_start
        timings["total_selection_seconds"] += time.perf_counter() - start
        state["last_sample_sources"] = state.get("gap_sampling_stats", [{}])[-1].get("actual_sample_sources", np.nan)
        state["theory_louvain_recomputes"] = state.get("m19_theory_louvain_recomputes", 0)
        return edge

    sample_count = adaptive_sample_count(len(candidates), args.m_min, args.m_max, args.confidence_delta, args.epsilon)
    boundary = m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    sources = select_structured_sources(h_graph, partition, boundary, sample_count, step)

    sample_start = time.perf_counter()
    sampled = sampled_dependencies(h_graph, candidates, sources)
    scale = h_graph.number_of_nodes() / float(max(1, len(sources)))
    be_hat = {edge: scale * sampled.get(edge, 0.0) for edge in candidates}
    timings["sampled_path_scoring_seconds"] += time.perf_counter() - sample_start

    score_start = time.perf_counter()
    if weights is None:
        scored = [(be_hat.get(edge, 0.0), edge) for edge in candidates]
    else:
        matrix = build_candidate_matrix(h_graph, candidates, sampled, comm, boundary_scores, local, delta)
        values = matrix.dot(np.array(weights, dtype=float))
        scored = [(float(value), edge) for value, edge in zip(values, candidates)]
    scored.sort(key=lambda item: (-item[0], item[1]))
    timings["model_scoring_seconds"] += time.perf_counter() - score_start
    timings["total_selection_seconds"] += time.perf_counter() - start
    state["last_sample_sources"] = sample_count
    state["theory_louvain_recomputes"] = state.get("m19_theory_louvain_recomputes", 0)
    return scored[0][1] if scored else None


def gcc_ratio(graph, original_n):
    if original_n <= 0 or graph.number_of_nodes() == 0:
        return 0.0
    if graph.number_of_edges() == 0:
        return 1.0 / float(original_n)
    return len(max(nx.connected_components(graph), key=len)) / float(original_n)


def first_ratio(curve_df, threshold):
    hit = curve_df[curve_df["gcc_ratio"] <= threshold]
    return np.nan if hit.empty else float(hit["remove_ratio"].iloc[0])


def curve_row(dataset, meta, method, step, original_m, ratio):
    return {
        "dataset": dataset,
        "graph_id": meta["graph_id"],
        "graph_name": meta.get("graph_name", meta["graph_id"]),
        "graph_type": meta.get("graph_type", "unknown"),
        "community_strength": meta.get("community_strength", "unknown"),
        "method": method,
        "method_label": LABELS.get(method, method),
        "removed_edges": step,
        "remove_ratio": step / float(max(1, original_m)),
        "gcc_ratio": ratio,
    }


def summarize_curve(curve_df, elapsed, status, timings):
    x = curve_df["remove_ratio"].values
    y = curve_df["gcc_ratio"].values
    observed = float(x[-1]) if len(x) else 0.0
    auc = float(np.trapz(y, x)) if len(x) else np.nan
    row = {
        "dataset": curve_df["dataset"].iloc[0],
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_name": curve_df["graph_name"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "community_strength": curve_df["community_strength"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "method_label": curve_df["method_label"].iloc[0],
        "status": status,
        "auc": auc,
        "normalized_auc": auc / observed if observed > 0 else np.nan,
        "observed_remove_ratio": observed,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "runtime_seconds": float(elapsed),
        "removed_edges": int(curve_df["removed_edges"].max()) if len(curve_df) else 0,
        "remove_ratio_gcc_le_0.5": first_ratio(curve_df, 0.5),
        "remove_ratio_gcc_le_0.2": first_ratio(curve_df, 0.2),
        "remove_ratio_gcc_le_0.1": first_ratio(curve_df, 0.1),
    }
    row.update(timings)
    total_selection = float(row.get("total_selection_seconds", 0.0) or 0.0)
    if total_selection > 0:
        row["delta_gcc_runtime_ratio"] = float(row.get("delta_gcc_seconds", 0.0) or 0.0) / total_selection
        row["sampled_path_runtime_ratio"] = float(row.get("sampled_path_scoring_seconds", 0.0) or 0.0) / total_selection
    else:
        row["delta_gcc_runtime_ratio"] = np.nan
        row["sampled_path_runtime_ratio"] = np.nan
    return row


def simulate_attack(dataset, meta, graph0, method, args, weights=None):
    method = canonical_method(method)
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    rows = [curve_row(dataset, meta, method, 0, original_m, gcc_ratio(graph, original_n))]
    state = {"original_n": original_n, "active_method": method}
    step = 0
    start = time.perf_counter()
    timed_out = False
    while graph.number_of_edges() > 0 and step / float(max(1, original_m)) < args.max_remove_ratio:
        if args.timeout_seconds > 0 and time.perf_counter() - start > args.timeout_seconds:
            timed_out = True
            break
        if method_uses_theory_sampling(method):
            edge = choose_theory_or_calibrated_edge(graph, step, state, args, weights=None)
        elif method == METHOD_THEORY_GAP_STOP:
            edge = choose_theory_or_calibrated_edge(graph, step, state, args, weights=None)
        elif method == METHOD_CALIBRATED:
            edge = choose_theory_or_calibrated_edge(graph, step, state, args, weights=weights)
        else:
            raise ValueError("Unsupported new method: {}".format(method))
        if edge is None or not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
        rows.append(curve_row(dataset, meta, method, step, original_m, gcc_ratio(graph, original_n)))
    elapsed = time.perf_counter() - start
    timings = state.get("theory_timings", {}).copy()
    timings["louvain_recomputes"] = state.get("m19_theory_louvain_recomputes", 0)
    timings["last_adaptive_k"] = state.get("last_adaptive_k", np.nan)
    timings["last_sample_sources"] = state.get("last_sample_sources", np.nan)
    backend = method_candidate_backend(method)
    if backend:
        timings["candidate_backend"] = backend
    gap_stats = pd.DataFrame(state.get("gap_sampling_stats", []))
    if not gap_stats.empty:
        timings["avg_actual_sample_sources"] = gap_stats["actual_sample_sources"].mean()
        timings["median_actual_sample_sources"] = gap_stats["actual_sample_sources"].median()
        timings["max_actual_sample_sources"] = gap_stats["actual_sample_sources"].max()
        timings["gap_stop_rate"] = gap_stats["gap_certified"].mean()
        timings["mean_final_gap"] = gap_stats["final_gap"].mean()
        timings["mean_confidence_radius"] = gap_stats["confidence_radius"].mean()
        timings["num_gap_certified_steps"] = int(gap_stats["gap_certified"].sum())
        timings["num_mmax_steps"] = int(gap_stats["hit_mmax"].sum())
        timings["top_edge_raw_norm_agree_rate"] = gap_stats["top_edge_raw_norm_agree"].mean()
    curve_df = pd.DataFrame(rows)
    if not gap_stats.empty:
        for key, value in {
            "dataset": dataset,
            "graph_id": meta["graph_id"],
            "graph_name": meta.get("graph_name", meta["graph_id"]),
            "graph_type": meta.get("graph_type", "unknown"),
            "community_strength": meta.get("community_strength", "unknown"),
            "method": method,
            "method_label": LABELS.get(method, method),
        }.items():
            gap_stats[key] = value
    return curve_df, summarize_curve(curve_df, elapsed, "timeout" if timed_out else "finished", timings), gap_stats


def load_baseline_results():
    per = pd.read_csv(OUT_DIR / "next_stage_per_graph_results.csv")
    curves = pd.read_csv(OUT_DIR / "next_stage_attack_curves.csv")
    keep = per[per["method"].isin(BASELINE_METHODS)].copy()
    keep["method"] = keep["method"].replace({fair.METHOD_M19: METHOD_ORIGINAL})
    keep["method_label"] = keep["method"].map(lambda m: LABELS.get(m, m))
    curves = curves[curves["method"].isin(BASELINE_METHODS)].copy()
    curves["method"] = curves["method"].replace({fair.METHOD_M19: METHOD_ORIGINAL})
    curves["method_label"] = curves["method"].map(lambda m: LABELS.get(m, m))
    return keep, curves


def calibration_xy_for_groups(groups, args):
    rows_x = []
    rows_y = []
    for graph_id, group in groups:
        graph = fair.reconstruct_synthetic_graph(group)
        h_graph = m18.m17.largest_cc_subgraph(graph)
        if h_graph.number_of_edges() == 0:
            continue
        partition = m18.m17.louvain_partition(h_graph)
        k = adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
        candidates, comm, boundary_scores, local, delta = candidate_features(h_graph, partition, k)
        if not candidates:
            continue
        sample_count = adaptive_sample_count(len(candidates), args.m_min, args.m_max, args.confidence_delta, args.epsilon)
        boundary = m18.m17.boundary_degrees(h_graph, partition)
        sources = select_structured_sources(h_graph, partition, boundary, sample_count, 0)
        sampled = sampled_dependencies(h_graph, candidates, sources)
        x = build_candidate_matrix(h_graph, candidates, sampled, comm, boundary_scores, local, delta)
        eb = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
        y_scores = {canonical_edge(edge): score for edge, score in eb.items()}
        y = np.array([y_scores.get(edge, 0.0) for edge in candidates], dtype=float)
        y_max = y.max()
        if y_max > 0:
            y = y / y_max
        rows_x.append(x)
        rows_y.append(y)
    if not rows_x:
        return np.empty((0, 4)), np.empty((0,))
    return np.vstack(rows_x), np.concatenate(rows_y)


def mse_for_weights(x, y, weights):
    if x.size == 0 or y.size == 0:
        return np.nan
    pred = x.dot(np.array(weights, dtype=float))
    return float(np.mean((pred - y) ** 2))


def train_calibrated_weights(args):
    total = args.train_graphs + args.validation_graphs + args.test_graphs
    groups = fair.load_synthetic_groups(max_graphs=total)
    train_groups = groups[: args.train_graphs]
    val_groups = groups[args.train_graphs : args.train_graphs + args.validation_graphs]
    test_groups = groups[args.train_graphs + args.validation_graphs : total]
    split_rows = []
    for split_name, split_groups in [("train", train_groups), ("validation", val_groups), ("test", test_groups)]:
        for graph_id, group in split_groups:
            meta = fair.synthetic_meta(group)
            split_rows.append(
                {
                    "split": split_name,
                    "dataset": "synthetic",
                    "graph_id": graph_id,
                    "graph_type": meta.get("graph_type", "unknown"),
                    "community_strength": meta.get("community_strength", "unknown"),
                }
            )
    split_df = pd.DataFrame(split_rows)
    write_csv(split_df, OUT_DIR / "m19_calibration_split_networks.csv")

    x_all, y_all = calibration_xy_for_groups(train_groups, args)
    if x_all.size == 0:
        weights = np.array([5.0, 2.0, 1.0, 0.5], dtype=float)
        status = "fallback_manual_no_training_rows"
    else:
        lam = max(0.0, args.l2)
        if lam > 0:
            x_aug = np.vstack([x_all, math.sqrt(lam) * np.eye(4)])
            y_aug = np.concatenate([y_all, np.zeros(4)])
        else:
            x_aug = x_all
            y_aug = y_all
        weights, _ = nnls(x_aug, y_aug)
        if weights.sum() <= 0:
            weights = np.array([5.0, 2.0, 1.0, 0.5], dtype=float)
            status = "fallback_manual_zero_solution"
        else:
            status = "trained_nnls_l2"
    x_val, y_val = calibration_xy_for_groups(val_groups, args)
    x_test, y_test = calibration_xy_for_groups(test_groups, args)
    train_mse = mse_for_weights(x_all, y_all, weights)
    validation_mse = mse_for_weights(x_val, y_val, weights)
    test_mse = mse_for_weights(x_test, y_test, weights)
    weight_df = pd.DataFrame(
        [
            {"feature": "sampled_dependency", "theta": weights[0], "manual_m19_weight": 5.0},
            {"feature": "community_bottleneck", "theta": weights[1], "manual_m19_weight": 2.0},
            {"feature": "boundary_local", "theta": weights[2], "manual_m19_weight": 1.0},
            {"feature": "delta_gcc", "theta": weights[3], "manual_m19_weight": 0.5},
        ]
    )
    weight_df["theta_normalized_sum1"] = weight_df["theta"] / weight_df["theta"].sum() if weight_df["theta"].sum() > 0 else np.nan
    weight_df["status"] = status
    weight_df["train_graphs"] = args.train_graphs
    weight_df["validation_graphs"] = args.validation_graphs
    weight_df["test_graphs"] = args.test_graphs
    weight_df["train_networks"] = ",".join([graph_id for graph_id, _ in train_groups])
    weight_df["validation_networks"] = ",".join([graph_id for graph_id, _ in val_groups])
    weight_df["test_networks"] = ",".join([graph_id for graph_id, _ in test_groups])
    weight_df["l2"] = args.l2
    weight_df["train_mse"] = train_mse
    weight_df["validation_mse"] = validation_mse
    weight_df["test_mse"] = test_mse
    write_csv(weight_df, OUT_DIR / "m19_calibrated_weights.csv")
    return weights, weight_df


def run_new_methods(args, weights, stage):
    run_root = OUT_DIR / ("m19_theory_smoke_runs" if stage == "smoke" else "m19_theory_runs")
    summaries = []
    curves = []
    sampling_stats = []
    datasets = [part.strip() for part in args.datasets.split(",") if part.strip()]
    if "synthetic" in datasets:
        for graph_id, group in fair.load_synthetic_groups(max_graphs=args.max_synthetic):
            meta = fair.synthetic_meta(group)
            graph = fair.reconstruct_synthetic_graph(group)
            synthetic_methods = [
                METHOD_THEORY_CONSERVATIVE,
                METHOD_THEORY_GAP_STOP,
                METHOD_THEORY_RECALL_PLUS,
                METHOD_THEORY_FAST_NO_DELTA,
                METHOD_THEORY_FULL_DELTA,
                METHOD_THEORY_NO_DELTA,
                METHOD_THEORY_BRIDGE_DELTA_ONLY,
                METHOD_THEORY_LOCAL_TOP_DELTA_ONLY,
                METHOD_CALIBRATED,
            ]
            for method in synthetic_methods:
                root = run_root / "synthetic" / graph_id
                root.mkdir(parents=True, exist_ok=True)
                summary_path = root / "{}_summary.csv".format(fair.method_slug(method))
                curve_path = root / "{}_curve.csv".format(fair.method_slug(method))
                sampling_path = root / "{}_sampling.csv".format(fair.method_slug(method))
                if method == METHOD_THEORY_CONSERVATIVE and not summary_path.exists():
                    legacy_summary = root / "{}_summary.csv".format(fair.method_slug(METHOD_THEORY_LEGACY))
                    legacy_curve = root / "{}_curve.csv".format(fair.method_slug(METHOD_THEORY_LEGACY))
                    if legacy_summary.exists() and legacy_curve.exists() and not args.overwrite_runs:
                        summary_path = legacy_summary
                        curve_path = legacy_curve
                if method == METHOD_THEORY_FAST_NO_DELTA and not summary_path.exists():
                    legacy_summary = root / "{}_summary.csv".format(fair.method_slug(METHOD_THEORY_FAST_NO_DELTA_LEGACY))
                    legacy_curve = root / "{}_curve.csv".format(fair.method_slug(METHOD_THEORY_FAST_NO_DELTA_LEGACY))
                    legacy_sampling = root / "{}_sampling.csv".format(fair.method_slug(METHOD_THEORY_FAST_NO_DELTA_LEGACY))
                    if legacy_summary.exists() and legacy_curve.exists() and not args.overwrite_runs:
                        summary_path = legacy_summary
                        curve_path = legacy_curve
                        sampling_path = legacy_sampling
                cache_valid = summary_path.exists() and curve_path.exists() and not args.overwrite_runs
                if cache_valid and method == METHOD_THEORY_GAP_STOP:
                    if not sampling_path.exists():
                        cache_valid = False
                    else:
                        cached_sampling = pd.read_csv(sampling_path)
                        cache_valid = (
                            "dependency_backend" in cached_sampling.columns
                            and set(cached_sampling["dependency_backend"].dropna()) == {"batched_v3"}
                        )
                if cache_valid and method_uses_candidate_v2_cache(method):
                    cached_summary = pd.read_csv(summary_path)
                    expected_backend = method_candidate_backend(method)
                    cache_valid = (
                        "candidate_backend" in cached_summary.columns
                        and set(cached_summary["candidate_backend"].dropna()) == {expected_backend}
                    )
                if cache_valid:
                    summary = pd.read_csv(summary_path)
                    curve = pd.read_csv(curve_path)
                    sampling = pd.read_csv(sampling_path) if sampling_path.exists() else pd.DataFrame()
                    if "method" in summary.columns:
                        summary["method"] = summary["method"].map(canonical_method)
                        summary["method_label"] = summary["method"].map(lambda m: LABELS.get(m, m))
                    if "method" in curve.columns:
                        curve["method"] = curve["method"].map(canonical_method)
                        curve["method_label"] = curve["method"].map(lambda m: LABELS.get(m, m))
                else:
                    curve, summary_row, sampling = simulate_attack("synthetic", meta, graph, method, args, weights=weights)
                    summary = pd.DataFrame([summary_row])
                    write_csv(summary, summary_path)
                    write_csv(curve, curve_path)
                    if not sampling.empty:
                        write_csv(sampling, sampling_path)
                summaries.append(summary)
                curves.append(curve)
                if not sampling.empty:
                    sampling_stats.append(sampling)
                print("synthetic {} {} {}".format(graph_id, method, summary["status"].iloc[0]), flush=True)
    if "realworld_m5_subset" in datasets:
        base = pd.read_csv(OUT_DIR / "next_stage_per_graph_results.csv")
        graph_ids = list(base[(base["dataset"] == "realworld") & (base["method"] == fair.METHOD_M5)]["graph_id"].drop_duplicates())
        if args.max_real > 0:
            graph_ids = graph_ids[: args.max_real]
        metadata = fair.load_real_metadata(graph_ids=graph_ids)
        for _, row in metadata.iterrows():
            meta = row.to_dict()
            graph = fair.load_real_graph(meta)
            real_methods = [
                METHOD_THEORY_CONSERVATIVE,
                METHOD_THEORY_FAST_NO_DELTA,
                METHOD_CALIBRATED,
                METHOD_THEORY_RECALL_PLUS,
            ]
            for method in real_methods:
                root = run_root / "realworld" / meta["graph_id"]
                root.mkdir(parents=True, exist_ok=True)
                summary_path = root / "{}_summary.csv".format(fair.method_slug(method))
                curve_path = root / "{}_curve.csv".format(fair.method_slug(method))
                sampling_path = root / "{}_sampling.csv".format(fair.method_slug(method))
                if method == METHOD_THEORY_CONSERVATIVE and not summary_path.exists():
                    legacy_summary = root / "{}_summary.csv".format(fair.method_slug(METHOD_THEORY_LEGACY))
                    legacy_curve = root / "{}_curve.csv".format(fair.method_slug(METHOD_THEORY_LEGACY))
                    if legacy_summary.exists() and legacy_curve.exists() and not args.overwrite_runs:
                        summary_path = legacy_summary
                        curve_path = legacy_curve
                if method == METHOD_THEORY_FAST_NO_DELTA and not summary_path.exists():
                    legacy_summary = root / "{}_summary.csv".format(fair.method_slug(METHOD_THEORY_FAST_NO_DELTA_LEGACY))
                    legacy_curve = root / "{}_curve.csv".format(fair.method_slug(METHOD_THEORY_FAST_NO_DELTA_LEGACY))
                    legacy_sampling = root / "{}_sampling.csv".format(fair.method_slug(METHOD_THEORY_FAST_NO_DELTA_LEGACY))
                    if legacy_summary.exists() and legacy_curve.exists() and not args.overwrite_runs:
                        summary_path = legacy_summary
                        curve_path = legacy_curve
                        sampling_path = legacy_sampling
                cache_valid = summary_path.exists() and curve_path.exists() and not args.overwrite_runs
                if cache_valid and method == METHOD_THEORY_GAP_STOP:
                    if not sampling_path.exists():
                        cache_valid = False
                    else:
                        cached_sampling = pd.read_csv(sampling_path)
                        cache_valid = (
                            "dependency_backend" in cached_sampling.columns
                            and set(cached_sampling["dependency_backend"].dropna()) == {"batched_v3"}
                        )
                if cache_valid and method_uses_candidate_v2_cache(method):
                    cached_summary = pd.read_csv(summary_path)
                    expected_backend = method_candidate_backend(method)
                    cache_valid = (
                        "candidate_backend" in cached_summary.columns
                        and set(cached_summary["candidate_backend"].dropna()) == {expected_backend}
                    )
                if cache_valid:
                    summary = pd.read_csv(summary_path)
                    curve = pd.read_csv(curve_path)
                    sampling = pd.read_csv(sampling_path) if sampling_path.exists() else pd.DataFrame()
                    if "method" in summary.columns:
                        summary["method"] = summary["method"].map(canonical_method)
                        summary["method_label"] = summary["method"].map(lambda m: LABELS.get(m, m))
                    if "method" in curve.columns:
                        curve["method"] = curve["method"].map(canonical_method)
                        curve["method_label"] = curve["method"].map(lambda m: LABELS.get(m, m))
                else:
                    curve, summary_row, sampling = simulate_attack("realworld", meta, graph, method, args, weights=weights)
                    summary = pd.DataFrame([summary_row])
                    write_csv(summary, summary_path)
                    write_csv(curve, curve_path)
                    if not sampling.empty:
                        write_csv(sampling, sampling_path)
                summaries.append(summary)
                curves.append(curve)
                if not sampling.empty:
                    sampling_stats.append(sampling)
                print("realworld {} {} {}".format(meta["graph_id"], method, summary["status"].iloc[0]), flush=True)
    return (
        pd.concat(summaries, ignore_index=True, sort=False) if summaries else pd.DataFrame(),
        pd.concat(curves, ignore_index=True, sort=False) if curves else pd.DataFrame(),
        pd.concat(sampling_stats, ignore_index=True, sort=False) if sampling_stats else pd.DataFrame(),
    )


def collect_new_runs(include_smoke=True):
    roots = []
    if include_smoke:
        roots.append(OUT_DIR / "m19_theory_smoke_runs")
    roots.append(OUT_DIR / "m19_theory_runs")
    summaries = []
    curves = []
    sampling_stats = []
    for root in roots:
        if not root.exists():
            continue
        for summary_path in sorted(root.glob("*/*/*_summary.csv")):
            try:
                summary = pd.read_csv(summary_path)
            except pd.errors.EmptyDataError:
                continue
            if summary.empty:
                continue
            if "method" in summary.columns:
                summary["method"] = summary["method"].map(canonical_method)
                summary["method_label"] = summary["method"].map(lambda m: LABELS.get(m, m))
            summaries.append(summary)
            curve_path = summary_path.with_name(summary_path.name.replace("_summary.csv", "_curve.csv"))
            if curve_path.exists():
                try:
                    curve = pd.read_csv(curve_path)
                    if not curve.empty:
                        if "method" in curve.columns:
                            curve["method"] = curve["method"].map(canonical_method)
                            curve["method_label"] = curve["method"].map(lambda m: LABELS.get(m, m))
                        curves.append(curve)
                except pd.errors.EmptyDataError:
                    pass
            sampling_path = summary_path.with_name(summary_path.name.replace("_summary.csv", "_sampling.csv"))
            if sampling_path.exists():
                try:
                    sampling = pd.read_csv(sampling_path)
                    if not sampling.empty:
                        if "method" in sampling.columns:
                            sampling["method"] = sampling["method"].map(canonical_method)
                            sampling["method_label"] = sampling["method"].map(lambda m: LABELS.get(m, m))
                        sampling_stats.append(sampling)
                except pd.errors.EmptyDataError:
                    pass
    return (
        pd.concat(summaries, ignore_index=True, sort=False) if summaries else pd.DataFrame(),
        pd.concat(curves, ignore_index=True, sort=False) if curves else pd.DataFrame(),
        pd.concat(sampling_stats, ignore_index=True, sort=False) if sampling_stats else pd.DataFrame(),
    )


def write_gap_stop_outputs(per, summary, sampling_stats):
    methods = [
        METHOD_ORIGINAL,
        fair.METHOD_M19_NO_BRIDGE,
        METHOD_THEORY_CONSERVATIVE,
        METHOD_THEORY_GAP_STOP,
        METHOD_THEORY_RECALL_PLUS,
        METHOD_THEORY_FAST_NO_DELTA,
        METHOD_CALIBRATED,
        fair.METHOD_M5,
        fair.METHOD_M7,
        fair.METHOD_M12,
    ]
    gap_per = per[per["method"].isin(methods)].copy()
    gap_per["method_label"] = gap_per["method"].map(lambda m: LABELS.get(m, m))
    preferred_cols = [
        "dataset",
        "graph_id",
        "graph_name",
        "graph_type",
        "community_strength",
        "method",
        "method_label",
        "status",
        "normalized_auc",
        "final_gcc_ratio",
        "runtime_seconds",
        "removed_edges",
        "observed_remove_ratio",
        "avg_actual_sample_sources",
        "median_actual_sample_sources",
        "max_actual_sample_sources",
        "gap_stop_rate",
        "mean_final_gap",
        "mean_confidence_radius",
        "num_gap_certified_steps",
        "num_mmax_steps",
        "top_edge_raw_norm_agree_rate",
    ]
    ordered_cols = [col for col in preferred_cols if col in gap_per.columns] + [
        col for col in gap_per.columns if col not in preferred_cols
    ]
    gap_per = gap_per[ordered_cols]

    gap_summary = summary[
        (summary["comparison_scope"].isin(["all_available", "new_variant_common_subset"]))
        & (summary["method"].isin(methods))
    ].copy()
    gap_summary["method_label"] = gap_summary["method"].map(lambda m: LABELS.get(m, m))

    gap_sampling = sampling_stats.copy()
    if not gap_sampling.empty:
        gap_sampling["method"] = gap_sampling["method"].map(canonical_method)
        gap_sampling = gap_sampling[gap_sampling["method"] == METHOD_THEORY_GAP_STOP].copy()
        if "dependency_backend" in gap_sampling.columns:
            gap_sampling = gap_sampling[gap_sampling["dependency_backend"] == "batched_v3"].copy()
        gap_sampling["method_label"] = gap_sampling["method"].map(lambda m: LABELS.get(m, m))
        stat_cols = [
            "dataset",
            "graph_id",
            "graph_name",
            "graph_type",
            "community_strength",
            "method",
            "method_label",
            "step",
            "current_nodes",
            "current_edges",
            "candidate_set_size",
            "adaptive_k",
            "actual_sample_sources",
            "stopped_reason",
            "final_gap",
            "confidence_radius",
            "gap_certified",
            "hit_mmax",
            "top_norm_edge",
            "second_norm_edge",
            "top_raw_edge",
            "top_edge_raw_norm_agree",
            "dependency_backend",
        ]
        gap_sampling = gap_sampling[[col for col in stat_cols if col in gap_sampling.columns]]

    write_csv(gap_summary, OUT_DIR / "m19_gap_stop_comparison_summary.csv")
    write_csv(gap_per, OUT_DIR / "m19_gap_stop_per_graph.csv")
    write_csv(gap_sampling, OUT_DIR / "m19_gap_stop_sampling_stats.csv")
    return gap_per, gap_summary, gap_sampling


def attach_recall_metrics(frame):
    recall_path = OUT_DIR / "m19_candidate_recall_summary.csv"
    if not recall_path.exists() or frame.empty:
        return frame
    recall = pd.read_csv(recall_path)
    if recall.empty or "method" not in recall.columns:
        return frame
    recall = recall[recall["dataset"].isin(["synthetic", "realworld"])].copy()
    if recall.empty:
        return frame
    recall["method"] = recall["method"].map(canonical_method)
    cols = [
        "dataset",
        "method",
        "mean_top1_recall",
        "mean_top5_recall",
        "mean_top10_recall",
        "mean_candidate_set_size",
        "mean_spearman",
        "mean_kendall",
        "candidate_miss_top1_count",
        "ranking_error_top1_count",
    ]
    return frame.merge(recall[[col for col in cols if col in recall.columns]], on=["dataset", "method"], how="left")


def write_recall_plus_delta_outputs(per, summary):
    recall_methods = [
        METHOD_ORIGINAL,
        fair.METHOD_M19_NO_BRIDGE,
        METHOD_THEORY_CONSERVATIVE,
        METHOD_THEORY_GAP_STOP,
        METHOD_THEORY_RECALL_PLUS,
        METHOD_THEORY_FAST_NO_DELTA,
        fair.METHOD_M5,
        fair.METHOD_M7,
        fair.METHOD_M12,
    ]
    delta_methods = [
        METHOD_THEORY_FAST_NO_DELTA,
        METHOD_THEORY_FULL_DELTA,
        METHOD_THEORY_NO_DELTA,
        METHOD_THEORY_BRIDGE_DELTA_ONLY,
        METHOD_THEORY_LOCAL_TOP_DELTA_ONLY,
    ]
    recall_summary = summary[
        (summary["comparison_scope"] == "all_available")
        & (summary["dataset"] == "synthetic")
        & (summary["method"].isin(recall_methods))
    ].copy()
    delta_summary = summary[
        (summary["comparison_scope"] == "all_available")
        & (summary["dataset"] == "synthetic")
        & (summary["method"].isin(delta_methods + [METHOD_THEORY_CONSERVATIVE]))
    ].copy()
    recall_summary = attach_recall_metrics(recall_summary)
    delta_summary = attach_recall_metrics(delta_summary)
    recall_per = per[per["method"].isin(recall_methods)].copy()
    delta_per = per[per["method"].isin(delta_methods + [METHOD_THEORY_CONSERVATIVE])].copy()
    write_csv(recall_summary, OUT_DIR / "m19_recall_plus_comparison_summary.csv")
    write_csv(recall_per, OUT_DIR / "m19_recall_plus_per_graph.csv")
    write_csv(delta_summary, OUT_DIR / "m19_delta_gcc_ablation_summary.csv")
    write_csv(delta_per, OUT_DIR / "m19_delta_gcc_ablation_per_graph.csv")
    return recall_summary, delta_summary


def write_fast_no_delta_outputs(per, summary):
    methods = [
        fair.METHOD_M5,
        fair.METHOD_M7,
        fair.METHOD_M12,
        METHOD_ORIGINAL,
        fair.METHOD_M19_NO_BRIDGE,
        METHOD_THEORY_CONSERVATIVE,
        METHOD_THEORY_FAST_NO_DELTA,
        METHOD_CALIBRATED,
    ]
    fast_summary = summary[
        (
            ((summary["comparison_scope"] == "all_available") & (summary["dataset"] == "synthetic"))
            | ((summary["comparison_scope"] == "new_variant_common_subset") & (summary["dataset"] == "realworld"))
        )
        & (summary["method"].isin(methods))
    ].copy()
    fast_summary = attach_recall_metrics(fast_summary)
    fast_per = per[per["method"].isin(methods)].copy()
    write_csv(fast_summary, OUT_DIR / "m19_fast_no_delta_comparison_summary.csv")
    write_csv(fast_per, OUT_DIR / "m19_fast_no_delta_per_graph.csv")
    plot_fast_no_delta_auc_runtime(fast_summary, OUT_DIR / "m19_fast_no_delta_auc_runtime.png")
    return fast_summary


def aggregate_outputs(args, weight_df):
    base_per, base_curves = load_baseline_results()
    new_per, new_curves, sampling_stats = collect_new_runs(include_smoke=True)
    per = pd.concat([base_per, new_per], ignore_index=True, sort=False) if not new_per.empty else base_per
    if "method" in per.columns:
        per["method"] = per["method"].map(canonical_method)
        per["method_label"] = per["method"].map(lambda m: LABELS.get(m, m))
    per = per[per["method"].isin(COMPARISON_METHODS)].copy()
    per = per.drop_duplicates(["dataset", "graph_id", "method"], keep="last")

    rows = []

    def append_summary(scope, frame):
        finished = frame[frame["status"].fillna("finished") == "finished"].copy()
        if finished.empty:
            return
        finished["rank_in_scope"] = np.nan
        for (_, graph_id), group in finished.groupby(["dataset", "graph_id"], sort=False):
            finished.loc[group.index, "rank_in_scope"] = group["normalized_auc"].rank(method="min", ascending=True)
        for (dataset, method), group in finished.groupby(["dataset", "method"], sort=False):
            def compare_against(reference_method):
                wins = losses = ties = 0
                diffs = []
                for graph_id, graph_group in finished[finished["dataset"] == dataset].groupby("graph_id", sort=False):
                    by = {row["method"]: row for _, row in graph_group.iterrows()}
                    if method not in by or reference_method not in by:
                        continue
                    diff = float(by[method]["normalized_auc"]) - float(by[reference_method]["normalized_auc"])
                    diffs.append(diff)
                    if abs(diff) <= 1e-12:
                        ties += 1
                    elif diff < 0:
                        wins += 1
                    else:
                        losses += 1
                return wins, losses, ties, diffs

            wins, losses, ties, diffs = compare_against(METHOD_ORIGINAL)
            wins_m5, losses_m5, ties_m5, diffs_m5 = compare_against(fair.METHOD_M5)
            rows.append(
                {
                    "comparison_scope": scope,
                    "dataset": dataset,
                    "method": method,
                    "method_label": LABELS.get(method, method),
                    "num_graphs": group["graph_id"].nunique(),
                    "mean_normalized_auc": group["normalized_auc"].mean(),
                    "median_normalized_auc": group["normalized_auc"].median(),
                    "mean_final_gcc_ratio": group["final_gcc_ratio"].mean(),
                    "total_runtime_seconds": group["runtime_seconds"].sum(),
                    "mean_runtime_seconds": group["runtime_seconds"].mean(),
                    "mean_rank": group["rank_in_scope"].mean(),
                    "wins_vs_m19_original": wins,
                    "losses_vs_m19_original": losses,
                    "ties_vs_m19_original": ties,
                    "mean_auc_diff_vs_m19_original": float(np.mean(diffs)) if diffs else np.nan,
                    "wins_vs_m5": wins_m5,
                    "losses_vs_m5": losses_m5,
                    "ties_vs_m5": ties_m5,
                    "mean_auc_diff_vs_m5": float(np.mean(diffs_m5)) if diffs_m5 else np.nan,
                    "delta_gcc_runtime_ratio": group["delta_gcc_runtime_ratio"].mean()
                    if "delta_gcc_runtime_ratio" in group.columns
                    else np.nan,
                    "sampled_path_runtime_ratio": group["sampled_path_runtime_ratio"].mean()
                    if "sampled_path_runtime_ratio" in group.columns
                    else np.nan,
                }
            )

    append_summary("all_available", per)
    for dataset, df in per.groupby("dataset", sort=False):
        theory_graphs = set(df[df["method"] == METHOD_THEORY_CONSERVATIVE]["graph_id"])
        gap_graphs = set(df[df["method"] == METHOD_THEORY_GAP_STOP]["graph_id"])
        fast_graphs = set(df[df["method"] == METHOD_THEORY_FAST_NO_DELTA]["graph_id"])
        calibrated_graphs = set(df[df["method"] == METHOD_CALIBRATED]["graph_id"])
        common_graphs = theory_graphs & calibrated_graphs
        if gap_graphs:
            common_graphs = common_graphs & gap_graphs
        if fast_graphs:
            common_graphs = common_graphs & fast_graphs
        if not common_graphs:
            continue
        append_summary(
            "new_variant_common_subset",
            df[df["graph_id"].isin(common_graphs)].copy(),
        )
    split_path = OUT_DIR / "m19_calibration_split_networks.csv"
    if split_path.exists():
        split_df = pd.read_csv(split_path)
        test_graphs = set(split_df[(split_df["dataset"] == "synthetic") & (split_df["split"] == "test")]["graph_id"])
        if test_graphs:
            append_summary(
                "calibration_test_subset",
                per[(per["dataset"] == "synthetic") & (per["graph_id"].isin(test_graphs))].copy(),
            )
    summary = pd.DataFrame(rows).sort_values(["comparison_scope", "dataset", "mean_normalized_auc"])
    write_csv(per, OUT_DIR / "m19_theory_comparison_per_graph.csv")
    write_csv(summary, OUT_DIR / "m19_theory_comparison_summary.csv")
    gap_per, gap_summary, gap_sampling = write_gap_stop_outputs(per, summary, sampling_stats)
    recall_plus_summary, delta_ablation_summary = write_recall_plus_delta_outputs(per, summary)
    fast_no_delta_summary = write_fast_no_delta_outputs(per, summary)

    loss_rows = []
    for (dataset, graph_id), group in per.groupby(["dataset", "graph_id"], sort=False):
        by = {row["method"]: row for _, row in group.iterrows()}
        original = by.get(METHOD_ORIGINAL)
        for method in [METHOD_THEORY_CONSERVATIVE, METHOD_THEORY_GAP_STOP, METHOD_THEORY_FAST_NO_DELTA, METHOD_CALIBRATED]:
            if original is None or method not in by:
                continue
            diff = float(by[method]["normalized_auc"]) - float(original["normalized_auc"])
            if diff > 0:
                loss_rows.append(
                    {
                        "dataset": dataset,
                        "graph_id": graph_id,
                        "method": method,
                        "original_auc": float(original["normalized_auc"]),
                        "variant_auc": float(by[method]["normalized_auc"]),
                        "auc_diff_variant_minus_original": diff,
                    }
                )
    loss_df = pd.DataFrame(loss_rows)
    write_csv(loss_df, OUT_DIR / "m19_theory_loss_cases.csv")

    plot_auc_runtime(summary[summary["comparison_scope"] == "all_available"], OUT_DIR / "m19_theory_vs_original_auc_runtime.png")
    plot_gap_stop_auc_runtime(gap_summary, OUT_DIR / "m19_gap_stop_auc_runtime.png")
    plot_gap_stop_sampling_distribution(gap_sampling, OUT_DIR / "m19_gap_stop_sampling_distribution.png")
    write_parameter_report(args, weight_df, summary, loss_df)
    update_stage_report(
        summary,
        weight_df,
        loss_df,
        gap_summary=gap_summary,
        gap_sampling=gap_sampling,
        recall_plus_summary=recall_plus_summary,
        delta_ablation_summary=delta_ablation_summary,
        fast_no_delta_summary=fast_no_delta_summary,
    )


def rank_of_edge(scored_edges, target):
    for rank, (_, edge) in enumerate(scored_edges, start=1):
        if edge == target:
            return rank
    return np.nan


def edge_structural_features(h_graph, partition, edge, comm, boundary_scores, local, delta, eb_scores=None):
    edge = canonical_edge(edge)
    u, v = edge
    degrees = dict(h_graph.degree())
    boundary = m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    communities, pair_edges = m18.m17.community_stats(h_graph, partition) if partition else ({}, {})
    cu = partition.get(u) if partition else None
    cv = partition.get(v) if partition else None
    same_comm = bool(cu is not None and cu == cv)
    cross_comm = bool(cu is not None and cv is not None and cu != cv)
    size_u = len(communities.get(cu, [])) if cu is not None else np.nan
    size_v = len(communities.get(cv, [])) if cv is not None else np.nan
    eij = pair_edges.get(m18.m17.edge_sort_key((cu, cv)), 0) if cross_comm else 0
    cn = len(list(nx.common_neighbors(h_graph, u, v))) if h_graph.has_node(u) and h_graph.has_node(v) else 0
    bridge_set = {canonical_edge(item) for item in nx.bridges(h_graph)}
    eb_rank = np.nan
    eb_score = np.nan
    if eb_scores:
        ranked = sorted(((score, e) for e, score in eb_scores.items()), key=lambda item: (-item[0], item[1]))
        eb_score = eb_scores.get(edge, np.nan)
        eb_rank = rank_of_edge(ranked, edge)
    return {
        "miss_edge": str(edge),
        "miss_u": u,
        "miss_v": v,
        "is_cross_community": int(cross_comm),
        "is_intra_community": int(same_comm),
        "community_u": cu,
        "community_v": cv,
        "community_size_u": size_u,
        "community_size_v": size_v,
        "Eij": eij,
        "degree_u": degrees.get(u, 0),
        "degree_v": degrees.get(v, 0),
        "degree_product": degrees.get(u, 0) * degrees.get(v, 0),
        "boundary_degree_u": boundary.get(u, 0),
        "boundary_degree_v": boundary.get(v, 0),
        "boundary_degree_product": boundary.get(u, 0) * boundary.get(v, 0),
        "common_neighbors": cn,
        "is_bridge": int(edge in bridge_set),
        "edge_betweenness": eb_score,
        "edge_betweenness_rank": eb_rank,
        "S_comm": comm.get(edge, 0.0),
        "S_boundary": boundary_scores.get(edge, 0.0),
        "S_local": local.get(edge, 0.0),
        "Delta_GCC": delta.get(edge, 0.0),
    }


def write_candidate_miss_report(detail, path):
    lines = [
        "# M19 candidate miss diagnosis",
        "",
        "This report diagnoses states where the M5 top-1 edge is absent from the M19-theory conservative candidate set.",
        "",
        "Output CSV: `m19_candidate_miss_diagnosis.csv`.",
        "",
    ]
    if detail.empty:
        lines.append("No candidate miss rows were found.")
    else:
        overall = {
            "miss_states": len(detail),
            "graphs": detail["graph_id"].nunique(),
            "cross_community_rate": detail["is_cross_community"].mean(),
            "intra_community_rate": detail["is_intra_community"].mean(),
            "bridge_rate": detail["is_bridge"].mean(),
            "mean_degree_product": detail["degree_product"].mean(),
            "mean_boundary_product": detail["boundary_degree_product"].mean(),
            "mean_common_neighbors": detail["common_neighbors"].mean(),
            "mean_delta_gcc": detail["Delta_GCC"].mean(),
        }
        lines.extend(
            [
                "## Overall",
                "",
                "- Miss states: `{}`.".format(overall["miss_states"]),
                "- Graphs with miss states: `{}`.".format(overall["graphs"]),
                "- Cross-community miss rate: `{:.6f}`.".format(float(overall["cross_community_rate"])),
                "- Intra-community miss rate: `{:.6f}`.".format(float(overall["intra_community_rate"])),
                "- Bridge miss rate: `{:.6f}`.".format(float(overall["bridge_rate"])),
                "- Mean degree product: `{:.3f}`.".format(float(overall["mean_degree_product"])),
                "- Mean boundary-degree product: `{:.3f}`.".format(float(overall["mean_boundary_product"])),
                "- Mean common neighbors: `{:.3f}`.".format(float(overall["mean_common_neighbors"])),
                "- Mean Delta_GCC: `{:.6f}`.".format(float(overall["mean_delta_gcc"])),
                "",
                "## By graph type",
                "",
                md_table(
                    pd.DataFrame(
                        [
                            {
                                "graph_type": key[0],
                                "community_strength": key[1],
                                "miss_states": len(group),
                                "graphs": group["graph_id"].nunique(),
                                "cross_community_rate": group["is_cross_community"].mean(),
                                "bridge_rate": group["is_bridge"].mean(),
                                "mean_degree_product": group["degree_product"].mean(),
                                "mean_delta_gcc": group["Delta_GCC"].mean(),
                            }
                            for key, group in detail.groupby(["graph_type", "community_strength"])
                        ]
                    ),
                    [
                        "graph_type",
                        "community_strength",
                        "miss_states",
                        "graphs",
                        "cross_community_rate",
                        "bridge_rate",
                        "mean_degree_product",
                        "mean_delta_gcc",
                    ],
                ),
                "",
                "## Interpretation",
                "",
                "- Cross-community misses suggest the existing community/boundary channels rank the edge too low despite high M5 betweenness.",
                "- Intra-community misses suggest adding intra-community local bridge / degree-product sources can improve recall.",
                "- Bridge misses suggest replacing full Delta_GCC with bridge-focused Delta_GCC may preserve important cuts at lower cost.",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_candidate_miss_diagnosis(args):
    recall_path = OUT_DIR / "m19_candidate_recall_detail.csv"
    if not recall_path.exists():
        run_candidate_recall(args)
    recall = pd.read_csv(recall_path)
    miss = recall[recall["candidate_miss_top1"] == 1].copy()
    rows = []
    by_graph = {graph_id: group for graph_id, group in fair.load_synthetic_groups(max_graphs=args.max_synthetic)}
    run_args = fair.make_run_args(
        argparse.Namespace(
            max_remove_ratio=args.max_remove_ratio,
            m12_louvain_interval=10,
            candidate_topk=128,
            sample_sources=32,
            tau_bridge=0.05,
            alpha=5.0,
            beta=2.0,
            gamma=1.0,
            delta=0.5,
            m19_louvain_interval=10,
            m19_louvain_drop_threshold=0.05,
        )
    )
    for graph_id, group_miss in miss.groupby("graph_id", sort=False):
        if graph_id not in by_graph:
            continue
        source_group = by_graph[graph_id]
        meta = fair.synthetic_meta(source_group)
        graph = fair.reconstruct_synthetic_graph(source_group)
        checkpoints = sorted(int(step) for step in group_miss["step"].dropna().unique())
        state = {"original_n": graph.number_of_nodes()}
        max_step = max(checkpoints) if checkpoints else -1
        for step in range(0, max_step + 1):
            if step in checkpoints:
                h_graph = m18.m17.largest_cc_subgraph(graph)
                partition = m18.m17.louvain_partition(h_graph)
                k = adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
                candidates, comm, boundary_scores, local, delta = candidate_features(h_graph, partition, k)
                candidate_set = set(candidates)
                eb = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
                eb_scores = {canonical_edge(edge): score for edge, score in eb.items()}
                top1 = sorted(((score, edge) for edge, score in eb_scores.items()), key=lambda item: (-item[0], item[1]))[0][1]
                delta_one = delta_gcc_scores(h_graph, edges=[top1])
                row = {
                    "dataset": "synthetic",
                    "graph_id": meta["graph_id"],
                    "graph_type": meta.get("graph_type", "unknown"),
                    "community_strength": meta.get("community_strength", "unknown"),
                    "step": step,
                    "current_nodes": h_graph.number_of_nodes(),
                    "current_edges": h_graph.number_of_edges(),
                    "adaptive_k": k,
                    "candidate_set_size": len(candidates),
                    "top1_in_candidate": int(top1 in candidate_set),
                }
                row.update(edge_structural_features(h_graph, partition, top1, comm, boundary_scores, local, delta_one, eb_scores))
                rows.append(row)
            if step == max_step:
                break
            edge = m18.choose_m19_edge(graph, step, state, run_args)
            if edge is None or not graph.has_edge(*edge):
                break
            graph.remove_edge(*edge)
        print("miss-diagnosis synthetic {}".format(graph_id), flush=True)
    detail = pd.DataFrame(rows)
    write_csv(detail, OUT_DIR / "m19_candidate_miss_diagnosis.csv")
    write_candidate_miss_report(detail, OUT_DIR / "m19_candidate_miss_diagnosis.md")
    return detail


def correlation_or_nan(x, y, kind):
    if len(x) < 2 or len(y) < 2:
        return np.nan
    if len(set(x)) <= 1 or len(set(y)) <= 1:
        return np.nan
    if kind == "spearman":
        return float(spearmanr(x, y).correlation)
    return float(kendalltau(x, y).correlation)


def candidate_recall_one_state(dataset, meta, graph, step, args, method=METHOD_THEORY_CONSERVATIVE):
    method = canonical_method(method)
    h_graph = m18.m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    partition = m18.m17.louvain_partition(h_graph)
    k = adaptive_k(h_graph.number_of_nodes(), h_graph.number_of_edges(), args.k_min, args.k_max)
    candidates, comm, boundary_scores, local, delta = candidate_features(
        h_graph,
        partition,
        k,
        variant=method_candidate_variant(method),
        delta_mode=method_delta_mode(method),
        step=step,
        args=args,
    )
    candidate_set = set(candidates)
    if not candidates:
        return None

    eb = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
    eb_scores = {canonical_edge(edge): score for edge, score in eb.items()}
    eb_ranked = sorted(((score, edge) for edge, score in eb_scores.items()), key=lambda item: (-item[0], item[1]))
    top1 = eb_ranked[0][1]
    top5 = [edge for _, edge in eb_ranked[:5]]
    top10 = [edge for _, edge in eb_ranked[:10]]

    sample_count = adaptive_sample_count(len(candidates), args.m_min, args.m_max, args.confidence_delta, args.epsilon)
    boundary = m18.m17.boundary_degrees(h_graph, partition) if partition else {}
    sources = select_structured_sources(h_graph, partition, boundary, sample_count, step)
    sampled = sampled_dependencies(h_graph, candidates, sources)
    sampled_ranked = sorted(((sampled.get(edge, 0.0), edge) for edge in candidates), key=lambda item: (-item[0], item[1]))
    sampled_best = sampled_ranked[0][1] if sampled_ranked else None

    eb_on_candidates = [eb_scores.get(edge, 0.0) for edge in candidates]
    sampled_on_candidates = [sampled.get(edge, 0.0) for edge in candidates]
    top1_in = top1 in candidate_set
    top1_sampled_rank = rank_of_edge(sampled_ranked, top1) if top1_in else np.nan
    candidate_miss = not top1_in
    ranking_error = bool(top1_in and sampled_best != top1)
    return {
        "dataset": dataset,
        "graph_id": meta["graph_id"],
        "graph_type": meta.get("graph_type", "unknown"),
        "community_strength": meta.get("community_strength", "unknown"),
        "method": method,
        "method_label": LABELS.get(method, method),
        "step": step,
        "current_nodes": h_graph.number_of_nodes(),
        "current_edges": h_graph.number_of_edges(),
        "adaptive_k": k,
        "sample_sources": sample_count,
        "candidate_set_size": len(candidates),
        "m5_top1_in_candidate": int(top1_in),
        "m5_top5_in_candidate_count": sum(1 for edge in top5 if edge in candidate_set),
        "m5_top10_in_candidate_count": sum(1 for edge in top10 if edge in candidate_set),
        "m5_top5_recall": sum(1 for edge in top5 if edge in candidate_set) / float(max(1, len(top5))),
        "m5_top10_recall": sum(1 for edge in top10 if edge in candidate_set) / float(max(1, len(top10))),
        "sampled_spearman_with_m5_eb": correlation_or_nan(eb_on_candidates, sampled_on_candidates, "spearman"),
        "sampled_kendall_with_m5_eb": correlation_or_nan(eb_on_candidates, sampled_on_candidates, "kendall"),
        "m5_top1_sampled_rank": top1_sampled_rank,
        "candidate_miss_top1": int(candidate_miss),
        "ranking_error_top1": int(ranking_error),
        "diagnosis": "candidate_miss" if candidate_miss else ("ranking_error" if ranking_error else "covered_and_ranked_first"),
    }


def run_candidate_recall(args):
    rows = []
    datasets = [part.strip() for part in args.datasets.split(",") if part.strip()]
    checkpoint_ratios = [float(x) for x in str(args.recall_ratios).split(",") if str(x).strip()]
    recall_methods = [
        METHOD_THEORY_CONSERVATIVE,
        METHOD_THEORY_RECALL_PLUS,
        METHOD_THEORY_FAST_NO_DELTA,
        METHOD_THEORY_FULL_DELTA,
        METHOD_THEORY_NO_DELTA,
        METHOD_THEORY_BRIDGE_DELTA_ONLY,
        METHOD_THEORY_LOCAL_TOP_DELTA_ONLY,
    ]
    for graph_id, group in fair.load_synthetic_groups(max_graphs=args.max_synthetic):
        meta = fair.synthetic_meta(group)
        graph = fair.reconstruct_synthetic_graph(group)
        original_m = graph.number_of_edges()
        checkpoints = sorted({int(round(ratio * original_m)) for ratio in checkpoint_ratios})
        checkpoints = [step for step in checkpoints if step >= 0 and step <= original_m]
        state = {"original_n": graph.number_of_nodes()}
        run_args = fair.make_run_args(argparse.Namespace(
            max_remove_ratio=args.max_remove_ratio,
            m12_louvain_interval=10,
            candidate_topk=128,
            sample_sources=32,
            tau_bridge=0.05,
            alpha=5.0,
            beta=2.0,
            gamma=1.0,
            delta=0.5,
            m19_louvain_interval=10,
            m19_louvain_drop_threshold=0.05,
        ))
        for step in range(0, max(checkpoints) + 1 if checkpoints else 0):
            if step in checkpoints:
                for method in recall_methods:
                    row = candidate_recall_one_state("synthetic", meta, graph, step, args, method=method)
                    if row is not None:
                        rows.append(row)
            if step == max(checkpoints):
                break
            edge = m18.choose_m19_edge(graph, step, state, run_args)
            if edge is None or not graph.has_edge(*edge):
                break
            graph.remove_edge(*edge)
        print("recall synthetic {}".format(graph_id), flush=True)
    if "realworld_m5_subset" in datasets:
        base = pd.read_csv(OUT_DIR / "next_stage_per_graph_results.csv")
        graph_ids = list(base[(base["dataset"] == "realworld") & (base["method"] == fair.METHOD_M5)]["graph_id"].drop_duplicates())
        if args.max_real > 0:
            graph_ids = graph_ids[: args.max_real]
        metadata = fair.load_real_metadata(graph_ids=graph_ids)
        for _, meta_row in metadata.iterrows():
            meta = meta_row.to_dict()
            graph = fair.load_real_graph(meta)
            original_m = graph.number_of_edges()
            checkpoints = sorted({int(round(ratio * original_m)) for ratio in checkpoint_ratios})
            checkpoints = [step for step in checkpoints if step >= 0 and step <= original_m]
            state = {"original_n": graph.number_of_nodes()}
            run_args = fair.make_run_args(argparse.Namespace(
                max_remove_ratio=args.max_remove_ratio,
                m12_louvain_interval=10,
                candidate_topk=128,
                sample_sources=32,
                tau_bridge=0.05,
                alpha=5.0,
                beta=2.0,
                gamma=1.0,
                delta=0.5,
                m19_louvain_interval=10,
                m19_louvain_drop_threshold=0.05,
            ))
            for step in range(0, max(checkpoints) + 1 if checkpoints else 0):
                if step in checkpoints:
                    for method in recall_methods:
                        row = candidate_recall_one_state("realworld", meta, graph, step, args, method=method)
                        if row is not None:
                            rows.append(row)
                if step == max(checkpoints):
                    break
                edge = m18.choose_m19_edge(graph, step, state, run_args)
                if edge is None or not graph.has_edge(*edge):
                    break
                graph.remove_edge(*edge)
            print("recall realworld {}".format(meta["graph_id"]), flush=True)
    detail = pd.DataFrame(rows)
    write_csv(detail, OUT_DIR / "m19_candidate_recall_detail.csv")
    if detail.empty:
        summary = pd.DataFrame()
    else:
        summary_rows = []
        for (dataset, method), group in detail.groupby(["dataset", "method"], sort=False):
            summary_rows.append(
                {
                    "dataset": dataset,
                    "method": method,
                    "method_label": LABELS.get(method, method),
                    "num_graph_step_states": len(group),
                    "num_graphs": group["graph_id"].nunique(),
                    "mean_top1_recall": group["m5_top1_in_candidate"].mean(),
                    "mean_top5_recall": group["m5_top5_recall"].mean(),
                    "mean_top10_recall": group["m5_top10_recall"].mean(),
                    "mean_candidate_set_size": group["candidate_set_size"].mean(),
                    "mean_spearman": group["sampled_spearman_with_m5_eb"].mean(),
                    "mean_kendall": group["sampled_kendall_with_m5_eb"].mean(),
                    "candidate_miss_top1_count": int(group["candidate_miss_top1"].sum()),
                    "ranking_error_top1_count": int(group["ranking_error_top1"].sum()),
                }
            )
        for (method, graph_id), group in detail.groupby(["method", "graph_id"], sort=False):
            summary_rows.append(
                {
                    "dataset": "synthetic_per_graph",
                    "method": method,
                    "method_label": LABELS.get(method, method),
                    "graph_id": graph_id,
                    "num_graph_step_states": len(group),
                    "num_graphs": 1,
                    "mean_top1_recall": group["m5_top1_in_candidate"].mean(),
                    "mean_top5_recall": group["m5_top5_recall"].mean(),
                    "mean_top10_recall": group["m5_top10_recall"].mean(),
                    "mean_candidate_set_size": group["candidate_set_size"].mean(),
                    "mean_spearman": group["sampled_spearman_with_m5_eb"].mean(),
                    "mean_kendall": group["sampled_kendall_with_m5_eb"].mean(),
                    "candidate_miss_top1_count": int(group["candidate_miss_top1"].sum()),
                    "ranking_error_top1_count": int(group["ranking_error_top1"].sum()),
                }
            )
        summary = pd.DataFrame(summary_rows)
    write_csv(summary, OUT_DIR / "m19_candidate_recall_summary.csv")
    write_candidate_recall_report(detail, summary)
    return detail, summary


def write_candidate_recall_report(detail, summary):
    lines = [
        "# M19 candidate recall analysis",
        "",
        "This analysis checks whether M5 high-betweenness edges are present in the M19-theory candidate set, and whether sampled dependency ranks them correctly once present.",
        "",
        "Output files:",
        "",
        "- `m19_candidate_recall_summary.csv`",
        "- `m19_candidate_recall_detail.csv`",
        "",
    ]
    if detail.empty:
        lines.append("No recall rows were generated.")
    else:
        overall = summary[summary["dataset"] == "synthetic"].copy()
        conservative = overall[overall["method"] == METHOD_THEORY_CONSERVATIVE]
        first = conservative.iloc[0] if not conservative.empty else overall.iloc[0]
        lines.extend(
            [
                "## Overall",
                "",
                "- Conservative graph-step states: `{}`.".format(int(first["num_graph_step_states"])),
                "- Graphs: `{}`.".format(int(first["num_graphs"])),
                "",
                md_table(
                    overall,
                    [
                        "method_label",
                        "num_graph_step_states",
                        "num_graphs",
                        "mean_top1_recall",
                        "mean_top5_recall",
                        "mean_top10_recall",
                        "mean_candidate_set_size",
                        "mean_spearman",
                        "mean_kendall",
                        "candidate_miss_top1_count",
                        "ranking_error_top1_count",
                    ],
                ),
                "",
                "## Interpretation rule",
                "",
                "- If the M5 top edge is not in the candidate set, the loss source is `candidate_miss`.",
                "- If the M5 top edge is in the candidate set but sampled dependency does not rank it first, the loss source is `ranking_error`.",
                "",
            ]
        )
        diag = detail["diagnosis"].value_counts().reset_index()
        diag.columns = ["diagnosis", "count"]
        lines.extend(["## Diagnosis Counts", "", md_table(diag, ["diagnosis", "count"])])
    (OUT_DIR / "m19_candidate_recall_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_auc_runtime(summary, path):
    if summary.empty:
        return
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for dataset, marker in [("synthetic", "o"), ("realworld", "s")]:
        df = summary[summary["dataset"] == dataset]
        if df.empty:
            continue
        ax.scatter(df["total_runtime_seconds"], df["mean_normalized_auc"], label=dataset, marker=marker, s=70)
        for _, row in df.iterrows():
            ax.annotate(row["method_label"], (row["total_runtime_seconds"], row["mean_normalized_auc"]), fontsize=8)
    ax.set_title("M19 theory/calibrated vs original: AUC-runtime")
    ax.set_xlabel("Total runtime seconds")
    ax.set_ylabel("Mean normalized AUC")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_gap_stop_auc_runtime(summary, path):
    if summary.empty:
        return
    df = summary[(summary["comparison_scope"] == "all_available") & (summary["dataset"] == "synthetic")].copy()
    if df.empty:
        df = summary[summary["comparison_scope"] == "all_available"].copy()
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.scatter(df["total_runtime_seconds"], df["mean_normalized_auc"], s=70)
    for _, row in df.iterrows():
        ax.annotate(row["method_label"], (row["total_runtime_seconds"], row["mean_normalized_auc"]), fontsize=8)
    ax.set_title("M19 gap-stop comparison: AUC-runtime")
    ax.set_xlabel("Total runtime seconds")
    ax.set_ylabel("Mean normalized AUC")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_fast_no_delta_auc_runtime(summary, path):
    if summary.empty:
        return
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    for dataset, marker in [("synthetic", "o"), ("realworld", "s")]:
        df = summary[summary["dataset"] == dataset].copy()
        if df.empty:
            continue
        ax.scatter(df["total_runtime_seconds"], df["mean_normalized_auc"], label=dataset, marker=marker, s=76)
        for _, row in df.iterrows():
            ax.annotate(row["method_label"], (row["total_runtime_seconds"], row["mean_normalized_auc"]), fontsize=8)
    ax.set_title("M19-sampled-BE-fast comparison: AUC-runtime")
    ax.set_xlabel("Total runtime seconds")
    ax.set_ylabel("Mean normalized AUC")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_gap_stop_sampling_distribution(sampling_stats, path):
    if sampling_stats is None or sampling_stats.empty or "actual_sample_sources" not in sampling_stats.columns:
        return
    df = sampling_stats[sampling_stats["method"].map(canonical_method) == METHOD_THEORY_GAP_STOP].copy()
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    bins = sorted(set([0, 16, 32, 48, 64, 80, 96, 112, 128]))
    max_seen = int(df["actual_sample_sources"].max())
    if max_seen > bins[-1]:
        bins.append(max_seen)
    ax.hist(df["actual_sample_sources"], bins=bins, edgecolor="white", alpha=0.85)
    ax.axvline(df["actual_sample_sources"].mean(), color="C3", linestyle="--", linewidth=1.5, label="mean")
    ax.set_title("M19-theory-gap-stop actual source distribution")
    ax.set_xlabel("Actual sampled sources per attack step")
    ax.set_ylabel("Step count")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def md_table(df, cols):
    if df is None or df.empty:
        return ""
    table = df[[col for col in cols if col in df.columns]].copy()
    lines = ["| " + " | ".join(table.columns) + " |", "| " + " | ".join(["---"] * len(table.columns)) + " |"]
    for _, row in table.iterrows():
        cells = []
        for col in table.columns:
            value = row[col]
            if pd.isna(value):
                cells.append("")
            elif isinstance(value, (float, np.floating)):
                cells.append("{:.6f}".format(float(value)))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_parameter_report(args, weight_df, summary, loss_df):
    lines = [
        "# M19 参数依据化说明：M19-theory 与 M19-calibrated",
        "",
        "本文档解释新增的两个 M19 变体，目标是降低原始 M19 被质疑为手工调参的风险。",
        "",
        "## 1. 原始 M19 的问题",
        "",
        "原始 M19 使用 `alpha=5.0, beta=2.0, gamma=1.0, delta=0.5`，同时固定 `candidate_topk=128, sample_sources=32, tau_bridge=0.05`。这些参数在 synthetic 上有效，但理论解释不足。",
        "",
        "## 2. M19-theory / M19-BE",
        "",
        "M19-theory 把 M19 改写为 M5 edge betweenness 的结构化采样估计器。结构项只负责构造候选集，最终排序只使用 sampled edge-betweenness estimator：",
        "",
        "```text",
        "B_hat(e) = |V_t| / m_t * sum_{s in sampled_sources} dependency_s(e)",
        "e* = argmax_{e in C_t} B_hat(e)",
        "```",
        "",
        "候选集为：",
        "",
        "```text",
        "C_t = TopK(S_comm) union TopK(S_boundary) union TopK(S_local) union TopK(Delta_GCC)",
        "S_comm(e)=|Ci||Cj|/(Eij+1)",
        "S_boundary(e)=|Ci||Cj|/(Eij+1)*(bu+1)*(bv+1)/(CN(u,v)+1)",
        "S_local(e)=ku*kv/(CN(u,v)+1)",
        "Delta_GCC(e)=(|GCC_t|-largest_component_after_removing_e)/|GCC_t|",
        "```",
        "",
        "自适应候选规模：",
        "",
        "```text",
        "K_t = clip(ceil(sqrt(|E_t|) * log(|V_t|)), K_min, K_max)",
        "```",
        "",
        "当前默认：`K_min={}`, `K_max={}`。".format(args.k_min, args.k_max),
        "",
        "自适应采样源数量：",
        "",
        "```text",
        "m_t = min(m_max, max(m_min, ceil(log(2*|C_t|/delta)/(2*epsilon^2))))",
        "```",
        "",
        "当前默认：`m_min={}`, `m_max={}`, `delta={}`, `epsilon={}`。".format(args.m_min, args.m_max, args.confidence_delta, args.epsilon),
        "",
        "原始 `tau_bridge` 被 `Delta_GCC` 替代：不再用固定阈值判断 bridge，而是直接把实际 GCC drop 最大的边纳入候选。",
        "",
        "## 3. M19-calibrated",
        "",
        "M19-calibrated 保留线性组合形式，但用小图上 M5 full edge betweenness 分数学习非负权重：",
        "",
        "```text",
        "x1 = norm(D_sample)",
        "x2 = norm(S_comm)",
        "x3 = norm(S_boundary_local)",
        "x4 = norm(Delta_GCC)",
        "score(e) = theta^T x(e), theta_i >= 0",
        "```",
        "",
        "训练目标是让 `theta^T x` 近似候选边上的 M5 full edge betweenness 排序。实现使用 non-negative least squares，并加入 L2 正则。当前使用 synthetic 小图初始状态做切分：train/validation/test 分别为 `{}/{}/{}` 张图，用 validation/test MSE 检查是否明显过拟合。".format(args.train_graphs, args.validation_graphs, args.test_graphs),
        "",
        "训练、验证、测试网络清单见 `m19_calibration_split_networks.csv`，同时也写入 `m19_calibrated_weights.csv` 的 `train_networks`、`validation_networks`、`test_networks` 字段。",
        "",
        "学习到的权重：",
        "",
        md_table(weight_df, ["feature", "theta", "theta_normalized_sum1", "manual_m19_weight", "status", "train_graphs", "validation_graphs", "test_graphs", "train_mse", "validation_mse", "test_mse", "l2"]),
        "",
        "## 4. 当前对比结果",
        "",
        md_table(summary, ["comparison_scope", "dataset", "method_label", "num_graphs", "mean_normalized_auc", "total_runtime_seconds", "mean_runtime_seconds", "mean_rank", "wins_vs_m19_original", "losses_vs_m19_original", "ties_vs_m19_original"]),
        "",
        "## 5. Loss cases",
        "",
        "Loss-case 定义为 M19-theory 或 M19-calibrated 的 normalized AUC 高于 M19-original。",
        "",
        "- Loss-case CSV: `result/next_stage_fair_comparison/m19_theory_loss_cases.csv`",
        "- 当前 loss-case 数量: {}。".format(0 if loss_df is None or loss_df.empty else len(loss_df)),
        "",
        "## 6. Candidate recall 分析",
        "",
        "候选集召回分析见 `m19_candidate_recall_analysis.md`、`m19_candidate_recall_summary.csv` 和 `m19_candidate_recall_detail.csv`。该分析区分两类误差：",
        "",
        "- `candidate_miss`：M5 高介数边没有进入 M19 candidate set。",
        "- `ranking_error`：M5 高介数边进入候选集，但 sampled dependency 排序没有把它排到前面。",
    ]
    (OUT_DIR / "m19_parameter_explanation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_stage_report(
    summary,
    weight_df,
    loss_df,
    gap_summary=None,
    gap_sampling=None,
    recall_plus_summary=None,
    delta_ablation_summary=None,
    fast_no_delta_summary=None,
):
    path = OUT_DIR / "next_stage_research_summary.md"
    previous = path.read_text(encoding="utf-8") if path.exists() else "# Next-stage Fair Comparison Summary\n"
    marker = "\n## 13. Parameter-grounded M19 Variants\n"
    previous = previous.split(marker)[0].rstrip()
    recall_path = OUT_DIR / "m19_candidate_recall_summary.csv"
    recall_df = pd.read_csv(recall_path) if recall_path.exists() else pd.DataFrame()
    recall_overall = recall_df[recall_df["dataset"] == "synthetic"] if not recall_df.empty and "dataset" in recall_df.columns else pd.DataFrame()
    full_syn = summary[(summary["comparison_scope"] == "new_variant_common_subset") & (summary["dataset"] == "synthetic")]
    by_label = {row["method_label"]: row for _, row in full_syn.iterrows()}
    interpretation = []
    if "M19-theory-conservative" in by_label and "M19-original" in by_label:
        theory = by_label["M19-theory-conservative"]
        original = by_label["M19-original"]
        diff = float(theory["mean_normalized_auc"]) - float(original["mean_normalized_auc"])
        runtime_ratio = float(theory["total_runtime_seconds"]) / float(original["total_runtime_seconds"])
        if diff <= 0:
            interpretation.append(
                "On the full synthetic common subset, M19-theory-conservative is not weaker than M19-original: mean normalized AUC changes by `{:.6f}` (negative is better), but runtime is `{:.2f}x` of original.".format(diff, runtime_ratio)
            )
            interpretation.append(
                "This supports the claim that the hand-set final weights can be removed if the goal is interpretability, although the current estimator is slower because it uses adaptive sample size and Delta_GCC candidates."
            )
        else:
            interpretation.append(
                "On the full synthetic common subset, M19-theory-conservative is weaker than M19-original by `{:.6f}` AUC, suggesting the original community/boundary weights still add useful ranking bias on some networks.".format(diff)
            )
    if "M19-theory-gap-stop" in by_label and "M19-theory-conservative" in by_label:
        gap_stop = by_label["M19-theory-gap-stop"]
        conservative = by_label["M19-theory-conservative"]
        auc_diff = float(gap_stop["mean_normalized_auc"]) - float(conservative["mean_normalized_auc"])
        runtime_ratio = float(gap_stop["total_runtime_seconds"]) / float(conservative["total_runtime_seconds"])
        interpretation.append(
            "M19-theory-gap-stop differs from conservative by `{:.6f}` mean normalized AUC and uses `{:.3f}x` of conservative runtime on the full synthetic common subset.".format(auc_diff, runtime_ratio)
        )
    if "M19-calibrated" in by_label and "M19-original" in by_label:
        calibrated = by_label["M19-calibrated"]
        original = by_label["M19-original"]
        diff = float(calibrated["mean_normalized_auc"]) - float(original["mean_normalized_auc"])
        interpretation.append(
            "M19-calibrated differs from M19-original by `{:.6f}` mean normalized AUC on the full synthetic common subset; learned weights concentrate almost entirely on sampled dependency.".format(diff)
        )
    section = [
        marker.strip(),
        "",
        "This section is generated by `scripts/evaluate_m19_theory_calibrated.py` and uses files `m19_theory_comparison_summary.csv`, `m19_fast_no_delta_comparison_summary.csv`, `m19_calibrated_weights.csv`, `m19_parameter_explanation.md`, `m19_theory_vs_original_auc_runtime.png`, and `m19_theory_loss_cases.csv`.",
        "",
        "Original M19 uses heuristic parameters `alpha=5, beta=2, gamma=1, delta=0.5`, plus fixed `candidate_topk=128`, `sample_sources=32`, and `tau_bridge=0.05`. The new variants address this by replacing fixed weights or fixed sizes with estimator-based and calibrated choices.",
        "",
        "- `M19-theory` / `M19-BE`: keeps the structural candidate set, then ranks candidates only by sampled edge-betweenness estimator `B_hat(e)=|V_t|/m_t * sum_s dependency_s(e)`.",
        "- `M19-theory-conservative`: preserved fixed Hoeffding sample-count version, including the legacy `M19-theory` runs.",
        "- `M19-sampled-BE-fast`: uses only `TopK(S_comm) union TopK(S_boundary) union TopK(S_local)` candidates, removes Delta_GCC, removes significant-bridge bonus, and ranks only by sampled dependency.",
        "- `M19-theory-gap-stop`: uses sequential top-1 gap stopping with per-source normalized sampled dependency, batch size 8, minimum 16 sources, maximum 128 sources, and patience 2.",
        "- `M19-theory-recall-plus`: keeps the final sampled-betweenness ranking unchanged, but adds degree-product, intra-community local-bridge, and small random-exploration candidate sources.",
        "- Delta_GCC ablations compare full Delta_GCC, no Delta_GCC, bridge-only Delta_GCC, and local-top-only Delta_GCC candidate sources.",
        "- Adaptive candidate size: `K_t=clip(ceil(sqrt(|E_t|)log(|V_t|)), K_min, K_max)`.",
        "- Adaptive sample count: `m_t=clip(ceil(log(2|C_t|/delta)/(2epsilon^2)), m_min, m_max)`.",
        "- `tau_bridge` is replaced by direct `Delta_GCC(e)` candidates in conservative/calibrated variants, and removed entirely in `M19-sampled-BE-fast`.",
        "- `M19-calibrated`: learns nonnegative weights from small graphs by fitting M5 full edge-betweenness scores on candidate edges.",
        "",
        "Learned weights:",
        "",
        md_table(weight_df, ["feature", "theta", "theta_normalized_sum1", "manual_m19_weight"]),
        "",
        "Current comparison:",
        "",
        md_table(summary, ["comparison_scope", "dataset", "method_label", "num_graphs", "mean_normalized_auc", "total_runtime_seconds", "mean_runtime_seconds", "mean_rank", "wins_vs_m19_original", "losses_vs_m19_original", "ties_vs_m19_original", "wins_vs_m5", "losses_vs_m5", "ties_vs_m5"]),
        "",
        "Loss cases against M19-original are stored in `result/next_stage_fair_comparison/m19_theory_loss_cases.csv`; current count is `{}`.".format(0 if loss_df is None or loss_df.empty else len(loss_df)),
    ]
    if interpretation:
        section.extend(["", "Interpretation:", ""])
        section.extend(["- " + item for item in interpretation])
    if not recall_overall.empty:
        section.extend(
            [
                "",
                "Candidate recall analysis:",
                "",
                md_table(
                    recall_overall,
                    [
                        "dataset",
                        "num_graph_step_states",
                        "num_graphs",
                        "mean_top1_recall",
                        "mean_top5_recall",
                        "mean_top10_recall",
                        "mean_candidate_set_size",
                        "mean_spearman",
                        "mean_kendall",
                        "candidate_miss_top1_count",
                        "ranking_error_top1_count",
                    ],
                ),
            ]
        )
    miss_path = OUT_DIR / "m19_candidate_miss_diagnosis.csv"
    if miss_path.exists():
        miss_df = pd.read_csv(miss_path)
        if not miss_df.empty:
            section.extend(
                [
                    "",
                    "Candidate miss diagnosis:",
                    "",
                    "Files: `m19_candidate_miss_diagnosis.csv` and `m19_candidate_miss_diagnosis.md`.",
                    "",
                    "- Miss states: `{}`.".format(len(miss_df)),
                    "- Graphs with miss states: `{}`.".format(miss_df["graph_id"].nunique()),
                    "- Cross-community miss rate: `{:.6f}`.".format(float(miss_df["is_cross_community"].mean())),
                    "- Intra-community miss rate: `{:.6f}`.".format(float(miss_df["is_intra_community"].mean())),
                    "- Bridge miss rate: `{:.6f}`.".format(float(miss_df["is_bridge"].mean())),
                    "- Mean degree product: `{:.3f}`.".format(float(miss_df["degree_product"].mean())),
                    "- Mean Delta_GCC of missed M5 top-1 edges: `{:.6f}`.".format(float(miss_df["Delta_GCC"].mean())),
                ]
            )
    if gap_summary is not None and not gap_summary.empty:
        gap_syn = gap_summary[
            (gap_summary["comparison_scope"] == "all_available") & (gap_summary["dataset"] == "synthetic")
        ].copy()
        section.extend(
            [
                "",
                "Gap-stop sampling comparison:",
                "",
                "Files: `m19_gap_stop_comparison_summary.csv`, `m19_gap_stop_per_graph.csv`, `m19_gap_stop_sampling_stats.csv`, `m19_gap_stop_auc_runtime.png`, and `m19_gap_stop_sampling_distribution.png`.",
                "",
                md_table(
                    gap_syn if not gap_syn.empty else gap_summary,
                    [
                        "comparison_scope",
                        "dataset",
                        "method_label",
                        "num_graphs",
                        "mean_normalized_auc",
                        "total_runtime_seconds",
                        "mean_runtime_seconds",
                        "mean_rank",
                        "wins_vs_m19_original",
                        "losses_vs_m19_original",
                    ],
                ),
            ]
        )
        if gap_sampling is not None and not gap_sampling.empty:
            gap_steps = gap_sampling[gap_sampling["method"].map(canonical_method) == METHOD_THEORY_GAP_STOP].copy()
            if not gap_steps.empty:
                section.extend(
                    [
                        "",
                        "- Gap-stop mean actual sampled sources: `{:.2f}`.".format(float(gap_steps["actual_sample_sources"].mean())),
                        "- Gap-stop median actual sampled sources: `{:.2f}`.".format(float(gap_steps["actual_sample_sources"].median())),
                        "- Gap-stop max-source step count: `{}`.".format(int(gap_steps["hit_mmax"].sum())),
                        "- Gap-certified step count: `{}`.".format(int(gap_steps["gap_certified"].sum())),
                        "- Raw/norm top-edge agreement rate: `{:.6f}`.".format(float(gap_steps["top_edge_raw_norm_agree"].mean())),
                    ]
                )
    if recall_plus_summary is not None and not recall_plus_summary.empty:
        section.extend(
            [
                "",
                "Recall-plus candidate expansion:",
                "",
                "Files: `m19_recall_plus_comparison_summary.csv` and `m19_recall_plus_per_graph.csv`.",
                "",
                md_table(
                    recall_plus_summary,
                    [
                        "method_label",
                        "num_graphs",
                        "mean_normalized_auc",
                        "total_runtime_seconds",
                        "mean_rank",
                        "mean_top1_recall",
                        "mean_top5_recall",
                        "mean_top10_recall",
                        "mean_candidate_set_size",
                        "mean_spearman",
                        "mean_kendall",
                        "delta_gcc_runtime_ratio",
                        "sampled_path_runtime_ratio",
                    ],
                ),
            ]
        )
        real_subset = summary[
            (summary["comparison_scope"] == "new_variant_common_subset") & (summary["dataset"] == "realworld")
        ].copy()
        if not real_subset.empty:
            section.extend(
                [
                    "",
                    "M5-finished real-network subset:",
                    "",
                    "This subset compares the 9 real networks where M5 finished with M19-original, M19-no-bridge, M7, M12, M19-theory-conservative, M19-sampled-BE-fast, M19-calibrated, and M19-theory-recall-plus.",
                    "",
                    md_table(
                        real_subset,
                        [
                            "method_label",
                            "num_graphs",
                            "mean_normalized_auc",
                            "total_runtime_seconds",
                            "mean_runtime_seconds",
                            "mean_rank",
                            "wins_vs_m19_original",
                            "losses_vs_m19_original",
                            "wins_vs_m5",
                            "losses_vs_m5",
                        ],
                    ),
                ]
            )
    if fast_no_delta_summary is not None and not fast_no_delta_summary.empty:
        section.extend(
            [
                "",
                "M19 sampled-BE fast no-Delta comparison:",
                "",
                "Files: `m19_fast_no_delta_comparison_summary.csv`, `m19_fast_no_delta_per_graph.csv`, and `m19_fast_no_delta_auc_runtime.png`.",
                "",
                "This is the formal fast sampled-BE method. It does not overwrite M19-original and is named `M19-sampled-BE-fast`.",
                "",
                md_table(
                    fast_no_delta_summary,
                    [
                        "comparison_scope",
                        "dataset",
                        "method_label",
                        "num_graphs",
                        "mean_normalized_auc",
                        "total_runtime_seconds",
                        "mean_runtime_seconds",
                        "mean_rank",
                        "wins_vs_m19_original",
                        "losses_vs_m19_original",
                        "ties_vs_m19_original",
                        "wins_vs_m5",
                        "losses_vs_m5",
                        "ties_vs_m5",
                        "mean_top1_recall",
                        "mean_top5_recall",
                        "mean_top10_recall",
                        "mean_candidate_set_size",
                        "mean_spearman",
                        "mean_kendall",
                    ],
                ),
            ]
        )
    if delta_ablation_summary is not None and not delta_ablation_summary.empty:
        section.extend(
            [
                "",
                "Delta_GCC ablation:",
                "",
                "Files: `m19_delta_gcc_ablation_summary.csv` and `m19_delta_gcc_ablation_per_graph.csv`.",
                "",
                md_table(
                    delta_ablation_summary,
                    [
                        "method_label",
                        "num_graphs",
                        "mean_normalized_auc",
                        "total_runtime_seconds",
                        "mean_rank",
                        "mean_top1_recall",
                        "mean_top5_recall",
                        "mean_top10_recall",
                        "mean_candidate_set_size",
                        "mean_spearman",
                        "mean_kendall",
                        "delta_gcc_runtime_ratio",
                        "sampled_path_runtime_ratio",
                    ],
                ),
            ]
        )
    path.write_text(previous + "\n\n" + "\n".join(section) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate parameter-grounded M19 variants.")
    parser.add_argument("--stage", choices=["smoke", "run", "recall", "miss_diagnosis", "aggregate"], default="smoke")
    parser.add_argument("--datasets", default="synthetic,realworld_m5_subset")
    parser.add_argument("--max-synthetic", type=int, default=2)
    parser.add_argument("--max-real", type=int, default=2)
    parser.add_argument("--max-remove-ratio", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--k-min", type=int, default=64)
    parser.add_argument("--k-max", type=int, default=512)
    parser.add_argument("--m-min", type=int, default=16)
    parser.add_argument("--m-max", type=int, default=128)
    parser.add_argument("--confidence-delta", type=float, default=0.05)
    parser.add_argument("--epsilon", type=float, default=0.10)
    parser.add_argument("--gap-min-sources", type=int, default=16)
    parser.add_argument("--gap-max-sources", type=int, default=128)
    parser.add_argument("--gap-batch-size", type=int, default=8)
    parser.add_argument("--gap-delta", type=float, default=0.05)
    parser.add_argument("--gap-patience", type=int, default=2)
    parser.add_argument("--recall-plus-random-fraction", type=float, default=0.05)
    parser.add_argument("--recall-plus-candidate-multiplier", type=float, default=2.0)
    parser.add_argument("--recall-plus-max-candidates", type=int, default=512)
    parser.add_argument("--louvain-interval", type=int, default=10)
    parser.add_argument("--louvain-drop-threshold", type=float, default=0.05)
    parser.add_argument("--train-graphs", type=int, default=12)
    parser.add_argument("--validation-graphs", type=int, default=4)
    parser.add_argument("--test-graphs", type=int, default=4)
    parser.add_argument("--l2", type=float, default=0.01)
    parser.add_argument("--recall-ratios", default="0,0.05,0.10,0.20")
    parser.add_argument("--overwrite-runs", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "m19_theory_config_last_run.json").write_text(
        json.dumps(vars(args), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    weights, weight_df = train_calibrated_weights(args)
    if args.stage in {"smoke", "run"}:
        run_new_methods(args, weights, args.stage)
    if args.stage == "recall":
        run_candidate_recall(args)
    if args.stage == "miss_diagnosis":
        run_candidate_miss_diagnosis(args)
    aggregate_outputs(args, weight_df)
    print("stage {} complete; outputs in {}".format(args.stage, OUT_DIR), flush=True)


if __name__ == "__main__":
    main()
