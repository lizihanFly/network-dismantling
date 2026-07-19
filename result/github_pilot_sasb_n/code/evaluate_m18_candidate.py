from pathlib import Path
from collections import deque
import argparse
import json
import math
import random
import sys
import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

import evaluate_m17_candidate as m17


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = ROOT / "result"
SEED = 20260513

METHOD_M5 = m17.METHOD_M5
METHOD_M7 = "M7 dynamic community size / pair"
METHOD_M12 = "M12 CEP-lite stale community attack"
METHOD_M16 = "M16 candidate GCC-drop hybrid"
METHOD_M17 = m17.METHOD_M17
METHOD_M18 = "M18 sampled-shortest-path candidate attack"
METHOD_M18_TUNED = "M18-tuned sampled-shortest-path candidate attack"
METHOD_M19 = "M19 structure-aware sampled community betweenness attack"

METHODS = [METHOD_M5, METHOD_M7, METHOD_M12, METHOD_M16, METHOD_M17, METHOD_M18, METHOD_M18_TUNED, METHOD_M19]
METHOD_ALIASES = {
    "m5": METHOD_M5,
    "m7": METHOD_M7,
    "m12": METHOD_M12,
    "m12_stale": METHOD_M12,
    "m16": METHOD_M16,
    "m17": METHOD_M17,
    "m18": METHOD_M18,
    "m18_tuned": METHOD_M18_TUNED,
    "m18-tuned": METHOD_M18_TUNED,
    "m_new": METHOD_M18,
    "mnew": METHOD_M18,
    "m19": METHOD_M19,
}
METHOD_LABELS = {
    METHOD_M5: "M5 betweenness",
    METHOD_M7: "M7 community",
    METHOD_M12: "M12 stale",
    METHOD_M16: "M16 cand-GCC",
    METHOD_M17: "M17 induced bridge",
    METHOD_M18: "M18 sampled paths",
    METHOD_M18_TUNED: "M18 tuned",
    METHOD_M19: "M19 structure-aware",
}
METHOD_COLORS = {
    METHOD_M5: "C0",
    METHOD_M7: "C1",
    METHOD_M12: "C2",
    METHOD_M16: "C5",
    METHOD_M17: "C3",
    METHOD_M18: "C4",
    METHOD_M18_TUNED: "C6",
    METHOD_M19: "C7",
}


def parse_list(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_methods(text):
    methods = []
    for part in parse_list(text):
        methods.append(METHOD_ALIASES.get(part.lower(), part))
    unknown = sorted(set(methods) - set(METHODS))
    if unknown:
        raise ValueError("Unknown methods: {}".format(", ".join(unknown)))
    return methods


def parse_networks(text):
    parts = parse_list(text)
    if not parts or any(part.lower() == "all" for part in parts):
        return list(m17.CANONICAL_NETWORKS)
    unknown = sorted(set(parts) - set(m17.CANONICAL_NETWORKS))
    if unknown:
        raise ValueError("Unknown networks: {}".format(", ".join(unknown)))
    return parts


def top_rows(rows, limit):
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[: max(0, limit)]


def normalize(value, maximum):
    return value / maximum if maximum > 0 else 0.0


def classify_dataset(path):
    rel = str(path.relative_to(ROOT)).replace("\\", "/").lower()
    name = path.stem.lower()
    if "/real_networks/" in rel:
        return "real"
    if "/data/sbm/" in rel:
        return "SBM"
    if "large300" in rel and "/synthetic_test/" in rel:
        return "large300 synthetic_test"
    if "_ba" in name or name.endswith("ba") or "/ba" in rel:
        return "BA"
    if "_er" in name or name.endswith("er") or "/er" in rel:
        return "ER"
    if "_ws" in name or name.endswith("ws") or "/ws" in rel:
        return "WS"
    if "sbm" in name or "/sbm" in rel:
        return "SBM"
    return "other"


def build_dataset_inventory():
    rows = []
    for path in sorted((ROOT / "data").rglob("*")):
        if path.suffix.lower() not in {".gml", ".mtx"}:
            continue
        rel = path.relative_to(ROOT)
        rows.append(
            {
                "path": str(rel),
                "file_name": path.name,
                "extension": path.suffix.lower(),
                "category": classify_dataset(path),
                "size_bytes": path.stat().st_size,
                "is_canonical": str(path) in {str(p) for p in m17.CANONICAL_NETWORKS.values()},
            }
        )
    return pd.DataFrame(rows)


def get_stale_partition(h_graph, step, state, prefix, interval):
    cached_step = state.get("{}_partition_step".format(prefix))
    cached_partition = state.get("{}_partition".format(prefix))
    current_nodes = set(h_graph.nodes())
    cached_nodes = state.get("{}_partition_nodes".format(prefix), set())
    needs_recompute = (
        cached_partition is None
        or cached_step is None
        or step - cached_step >= interval
        or not current_nodes.issubset(cached_nodes)
    )
    if needs_recompute:
        cached_partition = m17.louvain_partition(h_graph)
        state["{}_partition".format(prefix)] = cached_partition
        state["{}_partition_step".format(prefix)] = step
        state["{}_partition_nodes".format(prefix)] = current_nodes
    return {node: cached_partition[node] for node in h_graph.nodes() if node in cached_partition}


def get_adaptive_stale_partition(h_graph, step, state, prefix, interval, drop_threshold):
    cached_step = state.get("{}_partition_step".format(prefix))
    cached_partition = state.get("{}_partition".format(prefix))
    current_nodes = set(h_graph.nodes())
    cached_nodes = state.get("{}_partition_nodes".format(prefix), set())
    original_n = max(1, state.get("original_n", h_graph.number_of_nodes()))
    current_gcc_ratio = h_graph.number_of_nodes() / float(original_n)
    cached_gcc_ratio = state.get("{}_partition_gcc_ratio".format(prefix))
    needs_recompute = (
        cached_partition is None
        or cached_step is None
        or step - cached_step >= interval
        or not current_nodes.issubset(cached_nodes)
        or (
            cached_gcc_ratio is not None
            and cached_gcc_ratio - current_gcc_ratio > drop_threshold
        )
    )
    if needs_recompute:
        cached_partition = m17.louvain_partition(h_graph)
        state["{}_partition".format(prefix)] = cached_partition
        state["{}_partition_step".format(prefix)] = step
        state["{}_partition_nodes".format(prefix)] = current_nodes
        state["{}_partition_gcc_ratio".format(prefix)] = current_gcc_ratio
        state["{}_louvain_recomputes".format(prefix)] = state.get("{}_louvain_recomputes".format(prefix), 0) + 1
    return {node: cached_partition[node] for node in h_graph.nodes() if node in cached_partition}


def score_m7_edges(h_graph, partition):
    if not partition or len(set(partition.values())) <= 1:
        return {}
    communities, pair_edges = m17.community_stats(h_graph, partition)
    scores = {}
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            continue
        pair_count = pair_edges.get(m17.edge_sort_key((cu, cv)), 0)
        if pair_count <= 0:
            continue
        edge = m17.canonical_edge((u, v))
        scores[edge] = len(communities[cu]) * len(communities[cv]) / float(pair_count)
    return scores


def common_neighbor_counts_for_edges(h_graph):
    neighbor_sets = {node: set(h_graph.neighbors(node)) for node in h_graph.nodes()}
    counts = {}
    for u, v in h_graph.edges():
        if len(neighbor_sets[u]) < len(neighbor_sets[v]):
            small, large = u, v
        else:
            small, large = v, u
        counts[m17.canonical_edge((u, v))] = sum(
            1 for node in neighbor_sets[small] if node in neighbor_sets[large]
        )
    return counts


def score_m12_edges(h_graph, partition):
    if not partition:
        return {}
    communities, pair_edges = m17.community_stats(h_graph, partition)
    degrees = dict(h_graph.degree())
    boundary = m17.boundary_degrees(h_graph, partition)
    common_neighbors = common_neighbor_counts_for_edges(h_graph)
    scores = {}
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        edge = m17.canonical_edge((u, v))
        cn = common_neighbors.get(edge, 0)
        if cu != cv:
            pair_count = pair_edges.get(m17.edge_sort_key((cu, cv)), 0)
            if pair_count <= 0:
                continue
            score = (
                len(communities[cu])
                * len(communities[cv])
                / float(pair_count)
                * (boundary[u] + 1)
                * (boundary[v] + 1)
                / float(cn + 1)
            )
        else:
            score = len(communities[cu]) * degrees[u] * degrees[v] / float(cn + 1)
        scores[edge] = score
    return scores


def score_m19_community_edges(h_graph, partition):
    if not partition or len(set(partition.values())) <= 1:
        return {}
    communities, pair_edges = m17.community_stats(h_graph, partition)
    scores = {}
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            continue
        pair_count = pair_edges.get(m17.edge_sort_key((cu, cv)), 0)
        edge = m17.canonical_edge((u, v))
        scores[edge] = len(communities[cu]) * len(communities[cv]) / float(pair_count + 1)
    return scores


def score_m19_boundary_priority_edges(h_graph, partition):
    if not partition:
        return {}
    communities, pair_edges = m17.community_stats(h_graph, partition)
    boundary = m17.boundary_degrees(h_graph, partition)
    common_neighbors = common_neighbor_counts_for_edges(h_graph)
    scores = {}
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            continue
        pair_count = pair_edges.get(m17.edge_sort_key((cu, cv)), 0)
        edge = m17.canonical_edge((u, v))
        cn = common_neighbors.get(edge, 0)
        scores[edge] = (
            len(communities[cu])
            * len(communities[cv])
            / float(pair_count + 1)
            * (boundary[u] + 1)
            * (boundary[v] + 1)
            / float(cn + 1)
        )
    return scores


def score_local_and_degree_edges(h_graph):
    degrees = dict(h_graph.degree())
    common_neighbors = common_neighbor_counts_for_edges(h_graph)
    local_scores = {}
    degree_scores = {}
    for u, v in h_graph.edges():
        edge = m17.canonical_edge((u, v))
        degree_product = degrees[u] * degrees[v]
        local_scores[edge] = degree_product / float(common_neighbors.get(edge, 0) + 1)
        degree_scores[edge] = degree_product
    return local_scores, degree_scores


def bridge_split_sizes(graph):
    """Return smaller-side split size for every bridge in an undirected graph."""
    n = graph.number_of_nodes()
    if n == 0 or graph.number_of_edges() == 0:
        return {}
    sys.setrecursionlimit(max(sys.getrecursionlimit(), n + 100))
    adjacency = {node: list(graph.neighbors(node)) for node in graph.nodes()}
    visited = set()
    discovery = {}
    low = {}
    subtree_size = {}
    splits = {}
    time_counter = [0]

    def dfs(node, parent):
        visited.add(node)
        discovery[node] = time_counter[0]
        low[node] = time_counter[0]
        time_counter[0] += 1
        subtree_size[node] = 1
        for neighbor in adjacency[node]:
            if neighbor == parent:
                continue
            if neighbor not in visited:
                dfs(neighbor, node)
                subtree_size[node] += subtree_size[neighbor]
                low[node] = min(low[node], low[neighbor])
                if low[neighbor] > discovery[node]:
                    split = min(subtree_size[neighbor], n - subtree_size[neighbor])
                    splits[m17.canonical_edge((node, neighbor))] = float(split)
            else:
                low[node] = min(low[node], discovery[neighbor])

    for node in graph.nodes():
        if node not in visited:
            dfs(node, None)
    return splits


def score_bridge_edges(h_graph):
    degrees = dict(h_graph.degree())
    scores = {}
    n = float(max(1, h_graph.number_of_nodes()))
    for edge, split_size in bridge_split_sizes(h_graph).items():
        scores[edge] = split_size / n + 1e-9 * degrees[edge[0]] * degrees[edge[1]]
    return scores


def bridge_split_ratio(h_graph, edge):
    split_size = bridge_split_sizes(h_graph).get(m17.canonical_edge(edge), 0.0)
    return split_size / float(max(1, h_graph.number_of_nodes()))


def score_significant_bridge_edges(h_graph, tau_bridge):
    scores = {}
    n = float(max(1, h_graph.number_of_nodes()))
    for edge, split_size in bridge_split_sizes(h_graph).items():
        ratio = split_size / n
        if ratio >= tau_bridge:
            scores[edge] = 1.0 + ratio
    return scores


def choose_m16_edge(graph, step, state, args):
    h_graph = m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    limit = max(1, args.m16_candidate_k)
    min_drop_ratio = max(0.0, args.m16_min_drop_ratio)
    current_gcc_size = h_graph.number_of_nodes()
    degrees = dict(h_graph.degree())
    bridge_rows = []
    for raw_edge in nx.bridges(h_graph):
        edge = m17.canonical_edge(raw_edge)
        split = m17.bridge_balance_score(h_graph, edge)
        bridge_rows.append((split, degrees[edge[0]] * degrees[edge[1]], edge))
    bridge_rows.sort(key=lambda item: (-item[0], -item[1], item[2]))
    rows = []
    for rank, (_, degree_product, edge) in enumerate(bridge_rows[:limit]):
        after_size, _ = m17.gcc_size_and_induced_bridge_after_removal(h_graph, edge)
        gcc_drop = current_gcc_size - after_size
        rank_bonus = (limit - rank) / float(limit)
        rows.append((gcc_drop, rank_bonus, degree_product, edge))
    rows.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    if rows and rows[0][0] / float(max(1, current_gcc_size)) >= min_drop_ratio:
        return rows[0][3]

    partition = m17.louvain_partition(h_graph)
    scores = score_m7_edges(h_graph, partition)
    if scores:
        return top_rows([(score, edge) for edge, score in scores.items()], 1)[0][1]
    return choose_degree_product_edge(h_graph)


def choose_m7_edge(graph):
    h_graph = m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    partition = m17.louvain_partition(h_graph)
    scores = score_m7_edges(h_graph, partition)
    if not scores:
        return choose_degree_product_edge(h_graph)
    return top_rows([(score, edge) for edge, score in scores.items()], 1)[0][1]


def choose_degree_product_edge(graph):
    h_graph = m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    degrees = dict(h_graph.degree())
    rows = [(degrees[u] * degrees[v], m17.canonical_edge((u, v))) for u, v in h_graph.edges()]
    return top_rows(rows, 1)[0][1] if rows else None


def choose_m12_edge(graph, step, state, args):
    h_graph = m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    partition = get_stale_partition(h_graph, step, state, "m12", max(1, args.m12_louvain_interval))
    scores = score_m12_edges(h_graph, partition)
    if not scores:
        return choose_degree_product_edge(h_graph)
    return top_rows([(score, edge) for edge, score in scores.items()], 1)[0][1]


def select_m18_sources(h_graph, candidate_edges, boundary, args, step):
    degrees = dict(h_graph.degree())
    endpoint_scores = {}
    for u, v in candidate_edges:
        endpoint_scores[u] = max(endpoint_scores.get(u, 0), boundary.get(u, 0) * 1000 + degrees.get(u, 0))
        endpoint_scores[v] = max(endpoint_scores.get(v, 0), boundary.get(v, 0) * 1000 + degrees.get(v, 0))
    selected = [
        node
        for node, _ in sorted(endpoint_scores.items(), key=lambda item: (-item[1], item[0]))
    ][: max(1, args.m18_sample_sources // 2)]
    for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], item[0])):
        if node not in selected:
            selected.append(node)
        if len(selected) >= max(1, args.m18_sample_sources * 3 // 4):
            break
    rng = random.Random(SEED + step)
    nodes = list(h_graph.nodes())
    rng.shuffle(nodes)
    for node in nodes:
        if node not in selected:
            selected.append(node)
        if len(selected) >= args.m18_sample_sources:
            break
    return selected[: max(1, args.m18_sample_sources)]


def sampled_candidate_edge_dependencies(h_graph, candidate_edges, sources):
    candidate_set = {m17.canonical_edge(edge) for edge in candidate_edges}
    dependency_scores = {edge: 0.0 for edge in candidate_set}
    adjacency = {node: tuple(h_graph.neighbors(node)) for node in h_graph.nodes()}
    for source in sources:
        stack = []
        predecessors = {}
        sigma = {source: 1.0}
        distance = {source: 0}
        sigma[source] = 1.0
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
    return dependency_scores


def select_m19_sources(h_graph, partition, boundary, args, step):
    limit = max(1, args.m19_sample_sources)
    degrees = dict(h_graph.degree())
    selected = []

    for node, _ in sorted(boundary.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), item[0])):
        if node not in selected:
            selected.append(node)
        if len(selected) >= max(1, limit * 2 // 5):
            break

    for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], item[0])):
        if node not in selected:
            selected.append(node)
        if len(selected) >= max(1, limit * 7 // 10):
            break

    if partition:
        communities = {}
        for node, community_id in partition.items():
            communities.setdefault(community_id, []).append(node)
        community_rows = sorted(
            communities.values(),
            key=lambda nodes: (-len(nodes), min(nodes)),
        )
        for nodes in community_rows:
            representative = max(nodes, key=lambda node: (degrees.get(node, 0), boundary.get(node, 0), -node))
            if representative not in selected:
                selected.append(representative)
            if len(selected) >= max(1, limit * 9 // 10):
                break

    rng = random.Random(SEED + 7919 + step)
    nodes = list(h_graph.nodes())
    rng.shuffle(nodes)
    for node in nodes:
        if node not in selected:
            selected.append(node)
        if len(selected) >= limit:
            break
    return selected[:limit]


def choose_m19_edge(graph, step, state, args):
    h_graph = m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    timings = state.setdefault(
        "m19_timings",
        {
            "candidate_generation_seconds": 0.0,
            "feature_scoring_seconds": 0.0,
            "sampled_path_scoring_seconds": 0.0,
            "model_scoring_seconds": 0.0,
            "total_selection_seconds": 0.0,
        },
    )
    selection_start = time.perf_counter()

    candidate_start = time.perf_counter()
    partition = get_adaptive_stale_partition(
        h_graph,
        step,
        state,
        "m19",
        max(1, args.m19_louvain_interval),
        max(0.0, args.m19_louvain_drop_threshold),
    )
    community_scores = score_m19_community_edges(h_graph, partition)
    boundary_scores = score_m19_boundary_priority_edges(h_graph, partition)
    local_scores, _ = score_local_and_degree_edges(h_graph)
    bridge_scores = score_significant_bridge_edges(h_graph, max(0.0, args.m19_tau_bridge))

    candidates = set()
    for source_scores in [community_scores, boundary_scores, local_scores]:
        for _, edge in top_rows([(score, edge) for edge, score in source_scores.items()], args.m19_candidate_topk):
            candidates.add(edge)
    candidates.update(bridge_scores)

    if not candidates:
        fallback = choose_degree_product_edge(h_graph)
        return fallback

    candidates = [
        edge
        for _, edge in top_rows(
            [
                (
                    max(
                        community_scores.get(edge, 0.0),
                        boundary_scores.get(edge, 0.0),
                        local_scores.get(edge, 0.0),
                        bridge_scores.get(edge, 0.0),
                    ),
                    edge,
                )
                for edge in candidates
            ],
            max(1, args.m19_candidate_topk),
        )
    ]
    timings["candidate_generation_seconds"] += time.perf_counter() - candidate_start

    feature_start = time.perf_counter()
    boundary = m17.boundary_degrees(h_graph, partition) if partition else {}
    sources = select_m19_sources(h_graph, partition, boundary, args, step)
    boundary_local_scores = {
        edge: max(boundary_scores.get(edge, 0.0), local_scores.get(edge, 0.0))
        for edge in candidates
    }
    timings["feature_scoring_seconds"] += time.perf_counter() - feature_start

    sampled_start = time.perf_counter()
    sampled_scores = sampled_candidate_edge_dependencies(h_graph, candidates, sources)
    timings["sampled_path_scoring_seconds"] += time.perf_counter() - sampled_start

    scoring_start = time.perf_counter()
    maxima = {
        "sampled": max((sampled_scores.get(edge, 0.0) for edge in candidates), default=0.0),
        "community": max((community_scores.get(edge, 0.0) for edge in candidates), default=0.0),
        "boundary_local": max((boundary_local_scores.get(edge, 0.0) for edge in candidates), default=0.0),
    }
    scored = []
    for edge in candidates:
        score = (
            args.m19_alpha * normalize(sampled_scores.get(edge, 0.0), maxima["sampled"])
            + args.m19_beta * normalize(community_scores.get(edge, 0.0), maxima["community"])
            + args.m19_gamma * normalize(boundary_local_scores.get(edge, 0.0), maxima["boundary_local"])
            + args.m19_delta * bridge_scores.get(edge, 0.0)
        )
        scored.append(
            (
                score,
                sampled_scores.get(edge, 0.0),
                community_scores.get(edge, 0.0),
                boundary_local_scores.get(edge, 0.0),
                bridge_scores.get(edge, 0.0),
                edge,
            )
        )
    scored.sort(key=lambda item: (-item[0], -item[1], -item[2], -item[3], -item[4], item[5]))
    timings["model_scoring_seconds"] += time.perf_counter() - scoring_start
    timings["total_selection_seconds"] += time.perf_counter() - selection_start
    return scored[0][5] if scored else None


def m18_tuned_args(args):
    tuned = argparse.Namespace(**vars(args))
    tuned.m18_sample_sources = 32
    tuned.m18_candidate_k = 128
    tuned.m18_alpha_sampled_path = 5.0
    tuned.m18_beta_community = 2.0
    tuned.m18_beta_m12 = 1.0
    tuned.m18_gamma_local_bridge = 0.4
    tuned.m18_delta_degree_product = 0.1
    tuned.m18_eta_bridge_bonus = 0.3
    return tuned


def choose_m18_edge(graph, step, state, args):
    h_graph = m17.largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    timings = state.setdefault(
        "m18_timings",
        {
            "candidate_generation_seconds": 0.0,
            "feature_scoring_seconds": 0.0,
            "sampled_path_scoring_seconds": 0.0,
            "model_scoring_seconds": 0.0,
            "total_selection_seconds": 0.0,
        },
    )
    selection_start = time.perf_counter()

    candidate_start = time.perf_counter()
    partition = get_stale_partition(h_graph, step, state, "m18", max(1, args.m18_louvain_interval))
    m7_scores = score_m7_edges(h_graph, partition)
    m12_scores = score_m12_edges(h_graph, partition)
    local_scores, degree_scores = score_local_and_degree_edges(h_graph)
    bridge_scores = score_bridge_edges(h_graph)
    candidates = set()
    for source_scores, limit in [
        (m7_scores, args.m18_m7_k),
        (m12_scores, args.m18_m12_k),
        (local_scores, args.m18_local_k),
        (degree_scores, args.m18_degree_k),
        (bridge_scores, args.m18_bridge_k),
    ]:
        for _, edge in top_rows([(score, edge) for edge, score in source_scores.items()], limit):
            candidates.add(edge)
    if not candidates:
        fallback = choose_degree_product_edge(h_graph)
        return fallback
    candidates = [
        edge
        for _, edge in top_rows(
            [
                (
                    max(
                        m7_scores.get(edge, 0.0),
                        m12_scores.get(edge, 0.0),
                        local_scores.get(edge, 0.0),
                        degree_scores.get(edge, 0.0),
                        bridge_scores.get(edge, 0.0),
                    ),
                    edge,
                )
                for edge in candidates
            ],
            max(1, args.m18_candidate_k),
        )
    ]
    timings["candidate_generation_seconds"] += time.perf_counter() - candidate_start

    feature_start = time.perf_counter()
    boundary = m17.boundary_degrees(h_graph, partition) if partition else {}
    sources = select_m18_sources(h_graph, candidates, boundary, args, step)
    timings["feature_scoring_seconds"] += time.perf_counter() - feature_start

    sampled_start = time.perf_counter()
    sampled_scores = sampled_candidate_edge_dependencies(h_graph, candidates, sources)
    timings["sampled_path_scoring_seconds"] += time.perf_counter() - sampled_start

    scoring_start = time.perf_counter()
    maxima = {
        "sampled": max((sampled_scores.get(edge, 0.0) for edge in candidates), default=0.0),
        "m7": max((m7_scores.get(edge, 0.0) for edge in candidates), default=0.0),
        "m12": max((m12_scores.get(edge, 0.0) for edge in candidates), default=0.0),
        "local": max((local_scores.get(edge, 0.0) for edge in candidates), default=0.0),
        "bridge": max((bridge_scores.get(edge, 0.0) for edge in candidates), default=0.0),
        "degree": max((degree_scores.get(edge, 0.0) for edge in candidates), default=0.0),
    }
    scored = []
    for edge in candidates:
        score = (
            args.m18_alpha_sampled_path * normalize(sampled_scores.get(edge, 0.0), maxima["sampled"])
            + args.m18_beta_community * normalize(m7_scores.get(edge, 0.0), maxima["m7"])
            + args.m18_beta_m12 * normalize(m12_scores.get(edge, 0.0), maxima["m12"])
            + args.m18_gamma_local_bridge * normalize(local_scores.get(edge, 0.0), maxima["local"])
            + args.m18_eta_bridge_bonus * normalize(bridge_scores.get(edge, 0.0), maxima["bridge"])
            + args.m18_delta_degree_product * normalize(degree_scores.get(edge, 0.0), maxima["degree"])
        )
        scored.append(
            (
                score,
                sampled_scores.get(edge, 0.0),
                m7_scores.get(edge, 0.0),
                m12_scores.get(edge, 0.0),
                local_scores.get(edge, 0.0),
                bridge_scores.get(edge, 0.0),
                degree_scores.get(edge, 0.0),
                edge,
            )
        )
    scored.sort(key=lambda item: (-item[0], -item[1], -item[2], -item[3], -item[4], -item[5], -item[6], item[7]))
    timings["model_scoring_seconds"] += time.perf_counter() - scoring_start
    timings["total_selection_seconds"] += time.perf_counter() - selection_start
    return scored[0][7] if scored else None


def choose_edge(graph, method, step, state, args):
    if method == METHOD_M5:
        return m17.choose_betweenness_edge(graph)
    if method == METHOD_M7:
        return choose_m7_edge(graph)
    if method == METHOD_M12:
        return choose_m12_edge(graph, step, state, args)
    if method == METHOD_M16:
        return choose_m16_edge(graph, step, state, args)
    if method == METHOD_M17:
        return m17.choose_m17_edge(graph, step, state, args)
    if method == METHOD_M18:
        return choose_m18_edge(graph, step, state, args)
    if method == METHOD_M18_TUNED:
        return choose_m18_edge(graph, step, state, m18_tuned_args(args))
    if method == METHOD_M19:
        return choose_m19_edge(graph, step, state, args)
    raise ValueError("Unsupported method: {}".format(method))


def curve_row(network, method, step, original_m, ratio):
    return {
        "network": network,
        "method": method,
        "removed_edges": step,
        "remove_ratio": step / float(max(1, original_m)),
        "gcc_ratio": ratio,
    }


def simulate_attack(network, graph0, method, args):
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    rows = [curve_row(network, method, 0, original_m, m17.gcc_ratio(graph, original_n))]
    state = {"original_n": original_n}
    step = 0
    start = time.perf_counter()
    while graph.number_of_edges() > 0 and step / float(max(1, original_m)) < args.max_remove_ratio:
        edge = choose_edge(graph, method, step, state, args)
        if edge is None or not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
        rows.append(curve_row(network, method, step, original_m, m17.gcc_ratio(graph, original_n)))
    elapsed = time.perf_counter() - start
    for row in rows:
        row["elapsed_seconds"] = elapsed
    timings = {}
    if method in {METHOD_M18, METHOD_M18_TUNED}:
        timings = state.get("m18_timings", {})
    elif method == METHOD_M19:
        timings = state.get("m19_timings", {}).copy()
        timings["louvain_recomputes"] = state.get("m19_louvain_recomputes", 0)
    elif method == METHOD_M17:
        timings = state.get("m17_timings", {})
    return rows, elapsed, timings


def summarize_curve(curve_df, elapsed_seconds, timings):
    x = curve_df["remove_ratio"].values
    y = curve_df["gcc_ratio"].values
    auc = float(np.trapz(y, x))
    observed_remove_ratio = float(x[-1]) if len(x) else 0.0
    row = {
        "network": curve_df["network"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "auc": auc,
        "normalized_auc": auc / observed_remove_ratio if observed_remove_ratio > 0 else np.nan,
        "observed_remove_ratio": observed_remove_ratio,
        "gcc_at_budget": float(y[-1]) if len(y) else np.nan,
        "remove_ratio_gcc_le_0.5": m17.first_remove_ratio_at_or_below(curve_df, 0.5),
        "remove_ratio_gcc_le_0.2": m17.first_remove_ratio_at_or_below(curve_df, 0.2),
        "remove_ratio_gcc_le_0.1": m17.first_remove_ratio_at_or_below(curve_df, 0.1),
        "num_steps": int(curve_df["removed_edges"].max()),
        "elapsed_seconds": float(elapsed_seconds),
    }
    for key, value in timings.items():
        method = curve_df["method"].iloc[0]
        if method == METHOD_M19:
            prefix = "m19"
        elif method in {METHOD_M18, METHOD_M18_TUNED}:
            prefix = "m18"
        else:
            prefix = "m17"
        row["{}_{}".format(prefix, key)] = value
    return row


def plot_network_curves(curve_df, path):
    plt.figure(figsize=(7.5, 4.8))
    for method, group in curve_df.groupby("method", sort=False):
        plt.plot(
            group["remove_ratio"],
            group["gcc_ratio"],
            label=METHOD_LABELS.get(method, method),
            color=METHOD_COLORS.get(method),
            linewidth=1.5,
        )
    plt.xlabel("Removed edge ratio")
    plt.ylabel("GCC ratio")
    plt.title("{}: edge attack comparison".format(curve_df["network"].iloc[0]))
    plt.grid(alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_all_network_curves(curve_df, path):
    networks = list(curve_df["network"].drop_duplicates())
    if not networks:
        return
    cols = 2
    rows = int(np.ceil(len(networks) / float(cols)))
    fig, axes = plt.subplots(rows, cols, figsize=(12, max(4, rows * 3.6)), squeeze=False)
    for ax, network in zip(axes.ravel(), networks):
        network_df = curve_df[curve_df["network"] == network]
        for method, group in network_df.groupby("method", sort=False):
            ax.plot(
                group["remove_ratio"],
                group["gcc_ratio"],
                label=METHOD_LABELS.get(method, method),
                color=METHOD_COLORS.get(method),
                linewidth=1.3,
            )
        ax.set_title(network)
        ax.set_xlabel("Removed edge ratio")
        ax.set_ylabel("GCC ratio")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=6)
    for ax in axes.ravel()[len(networks):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_method_comparison(summary_df):
    rows = []
    for method, group in summary_df.groupby("method", sort=False):
        rows.append(
            {
                "method": method,
                "num_networks": len(group),
                "mean_normalized_auc": group["normalized_auc"].mean(),
                "mean_auc": group["auc"].mean(),
                "total_runtime_seconds": group["elapsed_seconds"].sum(),
                "mean_runtime_seconds": group["elapsed_seconds"].mean(),
                "mean_gcc_at_budget": group["gcc_at_budget"].mean(),
            }
        )
    return pd.DataFrame(rows)


def build_auc_rank_runtime_summary(summary_df):
    rows = []
    for network, group in summary_df.groupby("network", sort=False):
        ranked = group.sort_values(["normalized_auc", "elapsed_seconds", "method"], ascending=[True, True, True])
        for rank, (_, row) in enumerate(ranked.iterrows(), start=1):
            rows.append(
                {
                    "network": network,
                    "method": row["method"],
                    "normalized_auc": float(row["normalized_auc"]),
                    "auc_rank": rank,
                    "elapsed_seconds": float(row["elapsed_seconds"]),
                    "runtime_rank": int(
                        group["elapsed_seconds"].rank(method="min", ascending=True).loc[row.name]
                    ),
                    "gcc_at_budget": float(row["gcc_at_budget"]),
                }
            )
    return pd.DataFrame(rows)


def build_speedup_vs_m5(summary_df):
    rows = []
    for network, group in summary_df.groupby("network", sort=False):
        by_method = {row["method"]: row for _, row in group.iterrows()}
        if METHOD_M5 not in by_method:
            continue
        m5_time = float(by_method[METHOD_M5]["elapsed_seconds"])
        m5_auc = float(by_method[METHOD_M5]["normalized_auc"])
        for method, row in by_method.items():
            if method == METHOD_M5:
                continue
            runtime = float(row["elapsed_seconds"])
            auc = float(row["normalized_auc"])
            rows.append(
                {
                    "network": network,
                    "method": method,
                    "m5_runtime_seconds": m5_time,
                    "method_runtime_seconds": runtime,
                    "speedup_vs_m5": m5_time / runtime if runtime > 0 else np.nan,
                    "runtime_ratio_vs_m5": runtime / m5_time if m5_time > 0 else np.nan,
                    "m5_normalized_auc": m5_auc,
                    "method_normalized_auc": auc,
                    "auc_gap_vs_m5": auc - m5_auc,
                    "beats_m5_auc": bool(auc < m5_auc),
                }
            )
    return pd.DataFrame(rows)


def build_m18_summary(summary_df):
    rows = []
    for network, group in summary_df.groupby("network", sort=False):
        by_method = {row["method"]: row for _, row in group.iterrows()}
        if METHOD_M18 not in by_method:
            continue
        m18_row = by_method[METHOD_M18]
        row = {
            "network": network,
            "m18_normalized_auc": float(m18_row["normalized_auc"]),
            "m18_runtime_seconds": float(m18_row["elapsed_seconds"]),
            "m18_candidate_generation_seconds": float(m18_row.get("m18_candidate_generation_seconds", 0.0)),
            "m18_feature_scoring_seconds": float(m18_row.get("m18_feature_scoring_seconds", 0.0)),
            "m18_sampled_path_scoring_seconds": float(m18_row.get("m18_sampled_path_scoring_seconds", 0.0)),
            "m18_model_scoring_seconds": float(m18_row.get("m18_model_scoring_seconds", 0.0)),
            "m18_total_selection_seconds": float(m18_row.get("m18_total_selection_seconds", 0.0)),
        }
        for method, short in [(METHOD_M5, "m5"), (METHOD_M7, "m7"), (METHOD_M12, "m12"), (METHOD_M17, "m17")]:
            if method not in by_method:
                continue
            other = by_method[method]
            other_auc = float(other["normalized_auc"])
            other_time = float(other["elapsed_seconds"])
            row["{}_normalized_auc".format(short)] = other_auc
            row["{}_runtime_seconds".format(short)] = other_time
            row["m18_vs_{}_auc_improvement_pct".format(short)] = (
                (other_auc - row["m18_normalized_auc"]) / other_auc * 100.0
                if other_auc
                else np.nan
            )
            row["m18_vs_{}_runtime_ratio".format(short)] = (
                row["m18_runtime_seconds"] / other_time if other_time else np.nan
            )
            row["m18_beats_{}_auc".format(short)] = bool(row["m18_normalized_auc"] < other_auc)
        rows.append(row)
    return pd.DataFrame(rows)


def build_method_vs_m5_summary(summary_df, target_method, target_prefix):
    rows = []
    for network, group in summary_df.groupby("network", sort=False):
        by_method = {row["method"]: row for _, row in group.iterrows()}
        if target_method not in by_method:
            continue
        target = by_method[target_method]
        row = {
            "network": network,
            "{}_normalized_auc".format(target_prefix): float(target["normalized_auc"]),
            "{}_runtime_seconds".format(target_prefix): float(target["elapsed_seconds"]),
        }
        if METHOD_M5 in by_method:
            m5_row = by_method[METHOD_M5]
            m5_auc = float(m5_row["normalized_auc"])
            m5_time = float(m5_row["elapsed_seconds"])
            row["m5_normalized_auc"] = m5_auc
            row["m5_runtime_seconds"] = m5_time
            row["{}_vs_m5_auc_gap".format(target_prefix)] = float(target["normalized_auc"]) - m5_auc
            row["{}_vs_m5_runtime_ratio".format(target_prefix)] = (
                float(target["elapsed_seconds"]) / m5_time if m5_time else np.nan
            )
            row["{}_speedup_vs_m5".format(target_prefix)] = (
                m5_time / float(target["elapsed_seconds"]) if float(target["elapsed_seconds"]) else np.nan
            )
            row["{}_beats_m5_auc".format(target_prefix)] = bool(float(target["normalized_auc"]) < m5_auc)
        rows.append(row)
    return pd.DataFrame(rows)


def empty_stage_summary(stage):
    return pd.DataFrame([{"stage": stage, "status": "not_run"}])


def write_report(out_dir, args, inventory_df, graph_meta_df, summary_df, m18_summary_df, method_df):
    m18_vs_m5 = m18_summary_df.get("m18_beats_m5_auc", pd.Series(dtype=bool))
    beats_m5 = int(m18_vs_m5.sum()) if len(m18_vs_m5) else 0
    mean_runtime_ratio = (
        float(m18_summary_df["m18_vs_m5_runtime_ratio"].mean())
        if "m18_vs_m5_runtime_ratio" in m18_summary_df
        else np.nan
    )
    lines = [
        "# M18/M19 Sampled Candidate Attack Report",
        "",
        "## Scope",
        "",
        "- This run executes the requested smoke stage only.",
        "- Full 8-network core benchmark and full synthetic evaluation were not run.",
        "- M5 implementation and AUC/GCC evaluation are unchanged.",
        "",
        "## Dataset inventory",
        "",
        "Inventory rows: {}. Categories: {}.".format(
            len(inventory_df),
            ", ".join(
                "{}={}".format(cat, count)
                for cat, count in inventory_df["category"].value_counts().sort_index().items()
            ),
        ),
        "",
        "## M18 method",
        "",
        "M18 builds a small candidate set from M7/M12 stale community boundary scores, local bridge scores, bridge edges, and degree-product scores. It then estimates shortest-path importance using Brandes-style dependency accumulation from a small sampled source set.",
        "",
        "```text",
        "S18(e) = 3.0*sampled_path_norm + 1.5*m7_boundary_norm + 1.0*m12_priority_norm + 0.8*local_bridge_norm + 0.5*bridge_balance_norm + 0.3*degree_product_norm",
        "```",
        "",
        "M18 does not call full dynamic edge betweenness. Its sampled-path cost is O(s*m) per step, where s is --m18-sample-sources.",
        "",
        "## M19 method",
        "",
        "M19 builds candidates from top-k M7 community bottlenecks, top-k M12 boundary priorities, significant bridges, and top-k local bridge edges on the current GCC. It scores candidates with sampled shortest-path dependency and structure-aware normalized community/local terms.",
        "",
        "```text",
        "S19(e) = alpha*norm(sampled_path) + beta*norm(community_bottleneck) + gamma*norm(boundary_local_score) + delta*bridge_bonus",
        "```",
        "",
        "Defaults: candidate_topk={}, sample_sources={}, tau_bridge={:.3f}, alpha={:.1f}, beta={:.1f}, gamma={:.1f}, delta={:.1f}.".format(
            args.m19_candidate_topk,
            args.m19_sample_sources,
            args.m19_tau_bridge,
            args.m19_alpha,
            args.m19_beta,
            args.m19_gamma,
            args.m19_delta,
        ),
        "",
        "## Dynamic recomputation policy",
        "",
        "- GCC: recomputed after every edge deletion for every method.",
        "- M5: exact edge betweenness is dynamically recomputed on the current GCC.",
        "- M7: Louvain is dynamically recomputed on the current GCC.",
        "- M12/M18: stale Louvain is recomputed every configured interval or when cache coverage fails.",
        "- M19: Louvain is adaptive-stale, recomputed every {} deletion step(s) or early when GCC ratio drops by more than {:.3f} since the last Louvain recomputation.".format(args.m19_louvain_interval, args.m19_louvain_drop_threshold),
        "- M17: retained as the induced-bridge negative-result comparator.",
        "- M18/M19: sampled shortest-path dependencies are recomputed every step from sampled sources only; full edge betweenness is not computed.",
        "",
        "## Smoke graph metadata",
        "",
        m17.dataframe_to_markdown(graph_meta_df),
        "",
        "## Smoke results",
        "",
        m17.dataframe_to_markdown(m18_summary_df),
        "",
        "## Method averages",
        "",
        m17.dataframe_to_markdown(method_df),
        "",
        "## Smoke conclusion",
        "",
        "- M18 beats M5 by normalized AUC on {} / {} smoke networks.".format(beats_m5, len(m18_summary_df)),
        "- Mean M18/M5 runtime ratio on smoke networks: {:.3f}.".format(mean_runtime_ratio),
        "- Continue to core benchmark only if this tradeoff looks acceptable from `m18_smoke_summary.csv` and the PNG curves.",
    ]
    (out_dir / "m18_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ablation_grid_sbm_medium():
    return [
        {
            "config_name": "baseline_s16",
            "m18_sample_sources": 16,
            "alpha_sampled_path": 3.0,
            "beta_community": 1.5,
            "beta_m12": 1.0,
            "gamma_local_bridge": 0.8,
            "delta_degree_product": 0.3,
            "eta_bridge_bonus": 0.5,
            "candidate_topk": 128,
        },
        {
            "config_name": "path_s32",
            "m18_sample_sources": 32,
            "alpha_sampled_path": 3.0,
            "beta_community": 1.5,
            "beta_m12": 1.0,
            "gamma_local_bridge": 0.8,
            "delta_degree_product": 0.3,
            "eta_bridge_bonus": 0.5,
            "candidate_topk": 128,
        },
        {
            "config_name": "path_heavy_s32",
            "m18_sample_sources": 32,
            "alpha_sampled_path": 5.0,
            "beta_community": 1.5,
            "beta_m12": 1.0,
            "gamma_local_bridge": 0.5,
            "delta_degree_product": 0.1,
            "eta_bridge_bonus": 0.3,
            "candidate_topk": 128,
        },
        {
            "config_name": "path_comm_s32",
            "m18_sample_sources": 32,
            "alpha_sampled_path": 5.0,
            "beta_community": 2.0,
            "beta_m12": 1.0,
            "gamma_local_bridge": 0.4,
            "delta_degree_product": 0.1,
            "eta_bridge_bonus": 0.3,
            "candidate_topk": 128,
        },
        {
            "config_name": "path_comm_s24",
            "m18_sample_sources": 24,
            "alpha_sampled_path": 5.0,
            "beta_community": 2.0,
            "beta_m12": 1.0,
            "gamma_local_bridge": 0.4,
            "delta_degree_product": 0.1,
            "eta_bridge_bonus": 0.3,
            "candidate_topk": 128,
        },
        {
            "config_name": "path_comm_small_k",
            "m18_sample_sources": 32,
            "alpha_sampled_path": 5.0,
            "beta_community": 2.0,
            "beta_m12": 1.0,
            "gamma_local_bridge": 0.4,
            "delta_degree_product": 0.1,
            "eta_bridge_bonus": 0.3,
            "candidate_topk": 96,
        },
    ]


def apply_m18_ablation_config(args, config):
    cfg_args = argparse.Namespace(**vars(args))
    cfg_args.m18_sample_sources = config["m18_sample_sources"]
    cfg_args.m18_candidate_k = config["candidate_topk"]
    cfg_args.m18_alpha_sampled_path = config["alpha_sampled_path"]
    cfg_args.m18_beta_community = config["beta_community"]
    cfg_args.m18_beta_m12 = config["beta_m12"]
    cfg_args.m18_gamma_local_bridge = config["gamma_local_bridge"]
    cfg_args.m18_delta_degree_product = config["delta_degree_product"]
    cfg_args.m18_eta_bridge_bonus = config["eta_bridge_bonus"]
    return cfg_args


def plot_ablation_sbm_medium(ablation_df, path):
    x = np.arange(len(ablation_df))
    labels = ablation_df["config_name"].tolist()
    fig, ax_auc = plt.subplots(figsize=(9.8, 5.2))
    ax_runtime = ax_auc.twinx()

    bars = ax_auc.bar(
        x,
        ablation_df["m18_normalized_auc"],
        width=0.58,
        color="C4",
        alpha=0.78,
        label="M18 normalized AUC",
    )
    m5_auc = float(ablation_df["m5_normalized_auc"].iloc[0])
    ax_auc.axhline(m5_auc, color="C0", linestyle="--", linewidth=1.5, label="M5 normalized AUC")
    ax_runtime.plot(
        x,
        ablation_df["runtime_ratio"],
        color="C3",
        marker="o",
        linewidth=1.4,
        label="M18/M5 runtime ratio",
    )
    ax_runtime.axhline(1.2, color="0.35", linestyle=":", linewidth=1.3, label="1.2 runtime target")

    ax_auc.set_xticks(x)
    ax_auc.set_xticklabels(labels, rotation=30, ha="right")
    ax_auc.set_ylabel("Normalized AUC (lower is better)")
    ax_runtime.set_ylabel("Runtime ratio")
    ax_auc.set_title("sbm_medium M18 ablation at 20% edge-removal budget")
    ax_auc.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, ablation_df["m18_normalized_auc"]):
        ax_auc.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            "{:.3f}".format(value),
            ha="center",
            va="bottom",
            fontsize=8,
        )

    lines_a, labels_a = ax_auc.get_legend_handles_labels()
    lines_b, labels_b = ax_runtime.get_legend_handles_labels()
    ax_auc.legend(lines_a + lines_b, labels_a + labels_b, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def append_ablation_report(out_dir, ablation_df):
    runtime_ok = ablation_df["runtime_ratio"] <= 1.2
    if runtime_ok.any():
        candidates = ablation_df[runtime_ok].sort_values(["auc_gap_vs_m5", "runtime_ratio"], ascending=[True, True])
    else:
        candidates = ablation_df.sort_values(["auc_gap_vs_m5", "runtime_ratio"], ascending=[True, True])
    best = candidates.iloc[0]
    baseline = ablation_df[ablation_df["config_name"] == "baseline_s16"].iloc[0]
    improved = bool(best["auc_gap_vs_m5"] < baseline["auc_gap_vs_m5"])
    tuned = improved and bool(best["runtime_ratio"] <= 1.2)
    if tuned:
        conclusion = "This forms an M18-tuned candidate for the next karate re-run."
    else:
        conclusion = "This is a negative ablation result for sbm_medium; do not treat it as an M5 replacement yet."

    lines = [
        "",
        "## sbm_medium ablation",
        "",
        "- Scope: sbm_medium only, M5 and M18 only, max-remove-ratio = 0.2.",
        "- M5 was run once and reused across the six M18 configurations.",
        "- M18 keeps stale Louvain with interval 5 and sampled shortest-path scoring; M5 scoring was not modified.",
        "",
        "Best configuration by AUC gap among runtime-safe rows:",
        "",
        m17.dataframe_to_markdown(pd.DataFrame([best])),
        "",
        "- Baseline gap vs M5: {:.6f}.".format(float(baseline["auc_gap_vs_m5"])),
        "- Best gap vs M5: {:.6f}.".format(float(best["auc_gap_vs_m5"])),
        "- Best runtime ratio: {:.3f}.".format(float(best["runtime_ratio"])),
        "- M18-tuned status: {}.".format("yes" if tuned else "no"),
        "- Recommendation: {} {}".format(
            "Use this configuration to re-run karate after confirmation." if tuned else "Do not re-run karate yet unless this negative diagnostic is still useful.",
            conclusion,
        ),
    ]
    report_path = out_dir / "m18_report.md"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def run_ablation_sbm_medium(out_dir, args):
    if args.ablation_grid != "sbm_medium_small":
        raise ValueError("Unsupported ablation grid: {}".format(args.ablation_grid))
    network = "sbm_medium"
    graph = m17.load_simple_graph(m17.CANONICAL_NETWORKS[network])
    m5_args = argparse.Namespace(**vars(args))
    m5_args.max_remove_ratio = args.max_remove_ratio
    print("{} {}".format(network, METHOD_M5), flush=True)
    m5_rows, m5_elapsed, m5_timings = simulate_attack(network, graph, METHOD_M5, m5_args)
    m5_summary = summarize_curve(pd.DataFrame(m5_rows), m5_elapsed, m5_timings)
    rows = []
    for config in ablation_grid_sbm_medium():
        cfg_args = apply_m18_ablation_config(args, config)
        print("{} {} {}".format(network, METHOD_M18, config["config_name"]), flush=True)
        m18_rows, m18_elapsed, m18_timings = simulate_attack(network, graph, METHOD_M18, cfg_args)
        m18_summary = summarize_curve(pd.DataFrame(m18_rows), m18_elapsed, m18_timings)
        rows.append(
            {
                "config_name": config["config_name"],
                "m18_sample_sources": config["m18_sample_sources"],
                "alpha_sampled_path": config["alpha_sampled_path"],
                "beta_community": config["beta_community"],
                "beta_m12": config["beta_m12"],
                "gamma_local_bridge": config["gamma_local_bridge"],
                "delta_degree_product": config["delta_degree_product"],
                "eta_bridge_bonus": config["eta_bridge_bonus"],
                "candidate_topk": config["candidate_topk"],
                "m18_normalized_auc": float(m18_summary["normalized_auc"]),
                "m5_normalized_auc": float(m5_summary["normalized_auc"]),
                "auc_gap_vs_m5": float(m18_summary["normalized_auc"] - m5_summary["normalized_auc"]),
                "m18_runtime": float(m18_summary["elapsed_seconds"]),
                "m5_runtime": float(m5_summary["elapsed_seconds"]),
                "runtime_ratio": float(m18_summary["elapsed_seconds"] / m5_summary["elapsed_seconds"])
                if m5_summary["elapsed_seconds"]
                else np.nan,
                "m18_candidate_generation_seconds": float(
                    m18_summary.get("m18_candidate_generation_seconds", 0.0)
                ),
                "m18_feature_scoring_seconds": float(m18_summary.get("m18_feature_scoring_seconds", 0.0)),
                "m18_sampled_path_scoring_seconds": float(
                    m18_summary.get("m18_sampled_path_scoring_seconds", 0.0)
                ),
                "m18_model_scoring_seconds": float(m18_summary.get("m18_model_scoring_seconds", 0.0)),
                "m18_total_selection_seconds": float(m18_summary.get("m18_total_selection_seconds", 0.0)),
            }
        )
    ablation_df = pd.DataFrame(rows)
    m17.write_csv(ablation_df, out_dir / "ablation_sbm_medium.csv")
    plot_ablation_sbm_medium(ablation_df, out_dir / "ablation_sbm_medium.png")
    append_ablation_report(out_dir, ablation_df)
    print("Wrote sbm_medium ablation outputs to {}".format(out_dir), flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate M18/M19 sampled candidate edge attacks.")
    parser.add_argument("--out-root", default=str(m17.DEFAULT_OUT_ROOT))
    parser.add_argument("--out-name", default="m19_candidate")
    parser.add_argument("--networks", default="karate,sbm_medium")
    parser.add_argument("--methods", default="m5,m7,m12,m16,m18_tuned,m19")
    parser.add_argument("--evaluation-stage", default="smoke", choices=["smoke", "core", "full_synthetic", "ablation"])
    parser.add_argument("--ablation-grid", default="sbm_medium_small")
    parser.add_argument("--max-remove-ratio", type=float, default=0.20)
    parser.add_argument("--m12-louvain-interval", type=int, default=5)
    parser.add_argument("--m17-louvain-interval", type=int, default=5)
    parser.add_argument("--m17-candidate-k", type=int, default=100)
    parser.add_argument("--m17-cross-k", type=int, default=60)
    parser.add_argument("--m17-local-k", type=int, default=40)
    parser.add_argument("--m17-bridge-k", type=int, default=30)
    parser.add_argument("--m17-min-drop-ratio", type=float, default=0.0)
    parser.add_argument("--m16-candidate-k", type=int, default=30)
    parser.add_argument("--m16-min-drop-ratio", type=float, default=0.05)
    parser.add_argument("--m18-sample-sources", type=int, default=16)
    parser.add_argument("--m18-candidate-k", type=int, default=128)
    parser.add_argument("--m18-m7-k", type=int, default=40)
    parser.add_argument("--m18-m12-k", type=int, default=40)
    parser.add_argument("--m18-local-k", type=int, default=40)
    parser.add_argument("--m18-degree-k", type=int, default=30)
    parser.add_argument("--m18-bridge-k", type=int, default=30)
    parser.add_argument("--m18-louvain-interval", type=int, default=5)
    parser.add_argument("--m18-alpha-sampled-path", type=float, default=3.0)
    parser.add_argument("--m18-beta-community", type=float, default=1.5)
    parser.add_argument("--m18-beta-m12", type=float, default=1.0)
    parser.add_argument("--m18-gamma-local-bridge", type=float, default=0.8)
    parser.add_argument("--m18-delta-degree-product", type=float, default=0.3)
    parser.add_argument("--m18-eta-bridge-bonus", type=float, default=0.5)
    parser.add_argument("--m19-candidate-topk", type=int, default=128)
    parser.add_argument("--m19-sample-sources", type=int, default=32)
    parser.add_argument("--m19-tau-bridge", type=float, default=0.05)
    parser.add_argument("--m19-alpha", type=float, default=5.0)
    parser.add_argument("--m19-beta", type=float, default=2.0)
    parser.add_argument("--m19-gamma", type=float, default=1.0)
    parser.add_argument("--m19-delta", type=float, default=0.5)
    parser.add_argument("--m19-louvain-interval", type=int, default=10)
    parser.add_argument("--m19-louvain-drop-threshold", type=float, default=0.05)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.evaluation_stage == "ablation":
        out_dir = Path(args.out_root) / args.out_name
        out_dir.mkdir(parents=True, exist_ok=True)
        run_ablation_sbm_medium(out_dir, args)
        return

    networks = parse_networks(args.networks)
    methods = parse_methods(args.methods)
    out_dir = m17.make_out_dir(args.out_root, args.out_name)
    out_dir.mkdir(parents=True, exist_ok=False)

    inventory_df = build_dataset_inventory()
    m17.write_csv(inventory_df, out_dir / "dataset_inventory.csv")

    all_curves = []
    summary_rows = []
    graph_meta_rows = []
    log_lines = []

    for network in networks:
        path = m17.CANONICAL_NETWORKS[network]
        graph = m17.load_simple_graph(path)
        graph_meta_rows.append(
            {
                "network": network,
                "path": str(path.relative_to(ROOT)),
                "format": path.suffix.lower(),
                "nodes_initial_gcc": graph.number_of_nodes(),
                "edges_initial_gcc": graph.number_of_edges(),
                "average_degree": 2.0 * graph.number_of_edges() / float(max(1, graph.number_of_nodes())),
                "directed_after_load": False,
                "weighted_after_load": False,
            }
        )
        network_rows = []
        for method in methods:
            label = "{} {}".format(network, method)
            print(label, flush=True)
            log_lines.append(label)
            rows, elapsed, timings = simulate_attack(network, graph, method, args)
            curve_df = pd.DataFrame(rows)
            summary_rows.append(summarize_curve(curve_df, elapsed, timings))
            all_curves.extend(rows)
            network_rows.extend(rows)
        network_curve_df = pd.DataFrame(network_rows)
        m17.write_csv(network_curve_df, out_dir / "{}_m18_attacks.csv".format(network))
        plot_network_curves(network_curve_df, out_dir / "{}_m18_attacks.png".format(network))

    graph_meta_df = pd.DataFrame(graph_meta_rows)
    curves_df = pd.DataFrame(all_curves)
    summary_df = pd.DataFrame(summary_rows)
    m18_summary_df = build_m18_summary(summary_df)
    m19_summary_df = build_method_vs_m5_summary(summary_df, METHOD_M19, "m19")
    method_df = build_method_comparison(summary_df)
    rank_runtime_df = build_auc_rank_runtime_summary(summary_df)
    speedup_df = build_speedup_vs_m5(summary_df)

    m17.write_csv(curves_df, out_dir / "m18_attack_curves_all.csv")
    m17.write_csv(curves_df, out_dir / "attack_curves.csv")
    m17.write_csv(graph_meta_df, out_dir / "m18_graph_metadata.csv")
    m17.write_csv(summary_df, out_dir / "m18_summary_by_network.csv")
    m17.write_csv(summary_df, out_dir / "per_graph_results.csv")
    m17.write_csv(m18_summary_df, out_dir / "m18_summary.csv")
    m17.write_csv(m18_summary_df, out_dir / "m18_m5_comparison.csv")
    m17.write_csv(m19_summary_df, out_dir / "m19_summary.csv")
    m17.write_csv(m19_summary_df, out_dir / "m19_m5_comparison.csv")
    m17.write_csv(method_df, out_dir / "m18_method_comparison.csv")
    m17.write_csv(method_df, out_dir / "attack_summary_overall.csv")
    m17.write_csv(rank_runtime_df, out_dir / "auc_rank_runtime_summary.csv")
    m17.write_csv(speedup_df, out_dir / "speedup_vs_m5.csv")
    plot_all_network_curves(curves_df, out_dir / "gcc_curves.png")
    if args.evaluation_stage == "smoke":
        m17.write_csv(m18_summary_df, out_dir / "m18_smoke_summary.csv")
        m17.write_csv(empty_stage_summary("core"), out_dir / "m18_core_summary.csv")
        m17.write_csv(empty_stage_summary("full_synthetic"), out_dir / "m18_full_synthetic_summary.csv")
    elif args.evaluation_stage == "core":
        m17.write_csv(m18_summary_df, out_dir / "m18_core_summary.csv")
        m17.write_csv(empty_stage_summary("smoke"), out_dir / "m18_smoke_summary.csv")
        m17.write_csv(empty_stage_summary("full_synthetic"), out_dir / "m18_full_synthetic_summary.csv")
    else:
        m17.write_csv(m18_summary_df, out_dir / "m18_full_synthetic_summary.csv")
        m17.write_csv(empty_stage_summary("smoke"), out_dir / "m18_smoke_summary.csv")
        m17.write_csv(empty_stage_summary("core"), out_dir / "m18_core_summary.csv")
    write_report(out_dir, args, inventory_df, graph_meta_df, summary_df, m18_summary_df, method_df)
    (out_dir / "run_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8-sig")
    (out_dir / "config.json").write_text(
        json.dumps(vars(args), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Wrote M18 outputs to {}".format(out_dir), flush=True)


if __name__ == "__main__":
    main()
