from pathlib import Path
import argparse
import json
import time

import community as community_louvain
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ml_attack_dataset"
DEFAULT_OUT_ROOT = ROOT / "result"
SEED = 20260513

BASELINE_METHODS = [
    "M2 dynamic degree product",
    "M4 dynamic community internal / pair",
    "M5 dynamic edge betweenness",
    "M7 dynamic community size / pair",
    "M8 dynamic community bridge-degree",
]
NEW_METHODS = [
    "M9 dynamic community local bridge",
    "M10 dynamic local bridge degree product",
    "M11 dynamic phase-aware hybrid",
    "M12 CEP-lite stale community attack",
    "M12 dynamic Louvain attack",
    "M13 edge collective influence-lite",
    "M14 bridge-aware CEP-lite attack",
    "M15 significant-bridge CEP-lite attack",
    "M16 candidate GCC-drop hybrid",
]
METHODS = BASELINE_METHODS + NEW_METHODS
METHOD_LABELS = {
    "M2 dynamic degree product": "M2 degree product",
    "M4 dynamic community internal / pair": "M4 community",
    "M5 dynamic edge betweenness": "M5 betweenness",
    "M7 dynamic community size / pair": "M7 community size",
    "M8 dynamic community bridge-degree": "M8 bridge-degree",
    "M9 dynamic community local bridge": "M9 local bridge",
    "M10 dynamic local bridge degree product": "M10 local degree",
    "M11 dynamic phase-aware hybrid": "M11 hybrid",
    "M12 CEP-lite stale community attack": "M12 stale Louvain",
    "M12 dynamic Louvain attack": "M12 dynamic Louvain",
    "M13 edge collective influence-lite": "M13 ECI-lite",
    "M14 bridge-aware CEP-lite attack": "M14 bridge-aware",
    "M15 significant-bridge CEP-lite attack": "M15 sig-bridge",
    "M16 candidate GCC-drop hybrid": "M16 cand-GCC",
}
METHOD_COLORS = {
    method: "C{}".format(index % 10)
    for index, method in enumerate(METHODS)
}


def parse_list(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_methods(text):
    if not text:
        return list(METHODS)
    aliases = {
        "m2": "M2 dynamic degree product",
        "m4": "M4 dynamic community internal / pair",
        "m5": "M5 dynamic edge betweenness",
        "m7": "M7 dynamic community size / pair",
        "m8": "M8 dynamic community bridge-degree",
        "m9": "M9 dynamic community local bridge",
        "m10": "M10 dynamic local bridge degree product",
        "m11": "M11 dynamic phase-aware hybrid",
        "m12": "M12 CEP-lite stale community attack",
        "m12_stale": "M12 CEP-lite stale community attack",
        "m12_stale_louvain": "M12 CEP-lite stale community attack",
        "m12_dynamic": "M12 dynamic Louvain attack",
        "m12_dynamic_louvain": "M12 dynamic Louvain attack",
        "m13": "M13 edge collective influence-lite",
        "m14": "M14 bridge-aware CEP-lite attack",
        "m15": "M15 significant-bridge CEP-lite attack",
        "m16": "M16 candidate GCC-drop hybrid",
    }
    methods = []
    for part in parse_list(text):
        key = part.lower()
        methods.append(aliases.get(key, part))
    unknown = sorted(set(methods) - set(METHODS))
    if unknown:
        raise ValueError("Unknown methods: {}".format(", ".join(unknown)))
    return methods


def method_label(method):
    return METHOD_LABELS.get(method, method)


def edge_sort_key(edge):
    u, v = edge
    return (min(int(u), int(v)), max(int(u), int(v)))


def reconstruct_graph(group):
    n = int(group["n"].iloc[0])
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    for row in group[["u", "v"]].itertuples(index=False):
        graph.add_edge(int(row.u), int(row.v))
    return graph


def largest_cc_subgraph(graph):
    if graph.number_of_nodes() == 0:
        return graph.copy()
    if graph.number_of_edges() == 0:
        return graph.copy()
    nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(nodes).copy()


def gcc_ratio(graph, original_n):
    if original_n == 0 or graph.number_of_nodes() == 0:
        return 0.0
    return len(max(nx.connected_components(graph), key=len)) / float(original_n)


def louvain_partition(graph):
    if graph.number_of_edges() == 0:
        return {node: index for index, node in enumerate(graph.nodes())}
    return community_louvain.best_partition(graph, random_state=SEED)


def community_stats(graph, partition):
    communities = {}
    internal_edges = {}
    pair_edges = {}
    for node, community_id in partition.items():
        communities.setdefault(community_id, set()).add(node)
        internal_edges.setdefault(community_id, 0)
    for u, v in graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            internal_edges[cu] += 1
        else:
            key = edge_sort_key((cu, cv))
            pair_edges[key] = pair_edges.get(key, 0) + 1
    return communities, internal_edges, pair_edges


def boundary_degrees(graph, partition):
    counts = {node: 0 for node in graph.nodes()}
    for u, v in graph.edges():
        if partition[u] != partition[v]:
            counts[u] += 1
            counts[v] += 1
    return counts


def common_neighbor_count(graph, u, v):
    return len(set(graph.neighbors(u)).intersection(graph.neighbors(v)))


def choose_degree_product_edge(graph):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    degrees = dict(h_graph.degree())
    rows = [
        (degrees[u] * degrees[v], edge_sort_key((u, v)))
        for u, v in h_graph.edges()
    ]
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[0][1] if rows else None


def choose_betweenness_edge(graph):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    betweenness = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
    rows = [(score, edge_sort_key(edge)) for edge, score in betweenness.items()]
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[0][1] if rows else None


def choose_community_edge(graph, mode):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    partition = louvain_partition(h_graph)
    communities, internal_edges, pair_edges = community_stats(h_graph, partition)
    if len(communities) <= 1:
        return choose_degree_product_edge(h_graph)

    degrees = dict(h_graph.degree())
    rows = []
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            continue
        pair_count = pair_edges.get(edge_sort_key((cu, cv)), 0)
        if pair_count == 0:
            continue
        if mode == "m4":
            score = internal_edges[cu] * internal_edges[cv] / float(pair_count)
        elif mode == "m7":
            score = len(communities[cu]) * len(communities[cv]) / float(pair_count)
        elif mode == "m8":
            score = (
                len(communities[cu])
                * len(communities[cv])
                / float(pair_count)
                * degrees[u]
                * degrees[v]
            )
        elif mode == "m9":
            score = (
                len(communities[cu])
                * len(communities[cv])
                / float(pair_count)
                / float(common_neighbor_count(h_graph, u, v) + 1)
            )
        else:
            raise ValueError("Unknown community mode: {}".format(mode))
        rows.append((score, edge_sort_key((u, v))))

    if not rows:
        if mode == "m9":
            return choose_m10_edge(h_graph)
        return choose_degree_product_edge(h_graph)
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[0][1]


def ranked_community_edges(graph, mode, limit):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return []
    partition = louvain_partition(h_graph)
    communities, internal_edges, pair_edges = community_stats(h_graph, partition)
    if len(communities) <= 1:
        edge = choose_degree_product_edge(h_graph)
        return [(0.0, edge)] if edge is not None else []

    degrees = dict(h_graph.degree())
    rows = []
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            continue
        pair_count = pair_edges.get(edge_sort_key((cu, cv)), 0)
        if pair_count == 0:
            continue
        if mode == "m7":
            score = len(communities[cu]) * len(communities[cv]) / float(pair_count)
        elif mode == "m9":
            score = (
                len(communities[cu])
                * len(communities[cv])
                / float(pair_count)
                / float(common_neighbor_count(h_graph, u, v) + 1)
            )
        elif mode == "m4":
            score = internal_edges[cu] * internal_edges[cv] / float(pair_count)
        else:
            raise ValueError("Unsupported ranked community mode: {}".format(mode))
        rows.append((score, edge_sort_key((u, v))))
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[:limit]


def choose_m10_edge(graph):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    degrees = dict(h_graph.degree())
    rows = []
    for u, v in h_graph.edges():
        score = degrees[u] * degrees[v] / float(common_neighbor_count(h_graph, u, v) + 1)
        rows.append((score, edge_sort_key((u, v))))
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[0][1] if rows else None


def bridge_balance_score(graph, edge):
    u, v = edge
    if not graph.has_edge(u, v):
        return (0, 0, 0)
    graph.remove_edge(u, v)
    sizes = sorted((len(component) for component in nx.connected_components(graph)), reverse=True)
    graph.add_edge(u, v)
    if len(sizes) < 2:
        return (0, 0, 0)
    left = sizes[0]
    right = sizes[1]
    degrees = dict(graph.degree())
    return (min(left, right), left * right, degrees[u] * degrees[v])


def choose_bridge_balance_edge(graph):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    rows = []
    for edge in nx.bridges(h_graph):
        rows.append((bridge_balance_score(h_graph, edge), edge_sort_key(edge)))
    rows.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[1]))
    return rows[0][1] if rows else None


def choose_m11_edge(graph, step, original_m):
    remove_ratio = step / float(max(1, original_m))
    if remove_ratio < 0.10:
        return choose_m10_edge(graph)
    edge = choose_bridge_balance_edge(graph)
    if edge is not None:
        return edge
    return choose_community_edge(graph, "m9")


def choose_m12_edge_from_partition(h_graph, partition):
    communities, _, pair_edges = community_stats(h_graph, partition)
    degrees = dict(h_graph.degree())
    boundary = boundary_degrees(h_graph, partition)

    cross_rows = []
    internal_rows = []
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        cn = common_neighbor_count(h_graph, u, v)
        edge = edge_sort_key((u, v))
        if cu != cv:
            pair_count = pair_edges.get(edge_sort_key((cu, cv)), 0)
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
            cross_rows.append((score, edge))
        else:
            score = (
                len(communities[cu])
                * degrees[u]
                * degrees[v]
                / float(cn + 1)
            )
            internal_rows.append((score, edge))

    rows = cross_rows if cross_rows else internal_rows
    if not rows:
        return choose_m10_edge(h_graph)
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[0][1]


def choose_m12_edge(graph, step, state):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    interval = max(1, state.get("m12_louvain_interval", 5))
    cached_step = state.get("m12_partition_step")
    if cached_step is None or step - cached_step >= interval:
        state["m12_partition"] = louvain_partition(h_graph)
        state["m12_partition_step"] = step
        state["m12_partition_nodes"] = set(h_graph.nodes())
    partition = state.get("m12_partition", {})
    if set(h_graph.nodes()) != state.get("m12_partition_nodes", set()):
        partition = louvain_partition(h_graph)
        state["m12_partition"] = partition
        state["m12_partition_step"] = step
        state["m12_partition_nodes"] = set(h_graph.nodes())
    return choose_m12_edge_from_partition(h_graph, partition)


def choose_m12_dynamic_louvain_edge(graph):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    partition = louvain_partition(h_graph)
    return choose_m12_edge_from_partition(h_graph, partition)


def ranked_m12_edges(graph, step, state, limit):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return []
    interval = max(1, state.get("m12_louvain_interval", 5))
    cached_step = state.get("m12_partition_step")
    if cached_step is None or step - cached_step >= interval:
        state["m12_partition"] = louvain_partition(h_graph)
        state["m12_partition_step"] = step
        state["m12_partition_nodes"] = set(h_graph.nodes())
    partition = state.get("m12_partition", {})
    if set(h_graph.nodes()) != state.get("m12_partition_nodes", set()):
        partition = louvain_partition(h_graph)
        state["m12_partition"] = partition
        state["m12_partition_step"] = step
        state["m12_partition_nodes"] = set(h_graph.nodes())
    communities, _, pair_edges = community_stats(h_graph, partition)
    degrees = dict(h_graph.degree())
    boundary = boundary_degrees(h_graph, partition)

    cross_rows = []
    internal_rows = []
    for u, v in h_graph.edges():
        cu = partition[u]
        cv = partition[v]
        cn = common_neighbor_count(h_graph, u, v)
        edge = edge_sort_key((u, v))
        if cu != cv:
            pair_count = pair_edges.get(edge_sort_key((cu, cv)), 0)
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
            cross_rows.append((score, edge))
        else:
            score = (
                len(communities[cu])
                * degrees[u]
                * degrees[v]
                / float(cn + 1)
            )
            internal_rows.append((score, edge))

    rows = cross_rows if cross_rows else internal_rows
    if not rows:
        edge = choose_m10_edge(h_graph)
        return [(0.0, edge)] if edge is not None else []
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[:limit]


def edge_degree(degrees, edge):
    u, v = edge
    return degrees[u] + degrees[v] - 2


def edge_neighbors(graph, edge):
    u, v = edge
    neighbors = set()
    for node in (u, v):
        for nbr in graph.neighbors(node):
            candidate = edge_sort_key((node, nbr))
            if candidate != edge:
                neighbors.add(candidate)
    return neighbors


def edge_boundary_at_radius(graph, edge, radius):
    seen = {edge}
    frontier = {edge}
    for _ in range(radius):
        next_frontier = set()
        for current in frontier:
            next_frontier.update(edge_neighbors(graph, current))
        next_frontier.difference_update(seen)
        seen.update(next_frontier)
        frontier = next_frontier
        if not frontier:
            break
    return frontier


def choose_m13_edge(graph, radius):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    radius = max(1, radius)
    degrees = dict(h_graph.degree())
    rows = []
    for raw_edge in h_graph.edges():
        edge = edge_sort_key(raw_edge)
        ke = max(0, edge_degree(degrees, edge) - 1)
        if ke == 0:
            boundary_sum = 0
        else:
            boundary_sum = sum(
                max(0, edge_degree(degrees, boundary_edge) - 1)
                for boundary_edge in edge_boundary_at_radius(h_graph, edge, radius)
            )
        u, v = edge
        score = ke * boundary_sum / float(common_neighbor_count(h_graph, u, v) + 1)
        rows.append((score, edge))
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[0][1] if rows else None


def choose_m14_edge(graph, step, state):
    edge = choose_bridge_balance_edge(graph)
    if edge is not None:
        return edge
    return choose_m12_edge(graph, step, state)


def choose_m15_edge(graph, step, state):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    threshold = max(0.0, state.get("m15_bridge_min_side_ratio", 0.05))
    rows = []
    for edge in nx.bridges(h_graph):
        score = bridge_balance_score(h_graph, edge)
        rows.append((score, edge_sort_key(edge)))
    rows.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], item[1]))
    if rows:
        best_score, best_edge = rows[0]
        if best_score[0] / float(max(1, h_graph.number_of_nodes())) >= threshold:
            return best_edge
    return choose_m12_edge(graph, step, state)


def ranked_bridge_edges(graph, limit):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return []
    rows = []
    for edge in nx.bridges(h_graph):
        score = bridge_balance_score(h_graph, edge)
        numeric_score = score[0] * max(1, h_graph.number_of_nodes()) + score[1]
        rows.append((numeric_score, edge_sort_key(edge)))
    rows.sort(key=lambda item: (-item[0], item[1]))
    return rows[:limit]


def gcc_size_after_removing_edge(graph, edge):
    if not graph.has_edge(*edge):
        return graph.number_of_nodes()
    graph.remove_edge(*edge)
    if graph.number_of_nodes() == 0:
        size = 0
    else:
        size = len(max(nx.connected_components(graph), key=len))
    graph.add_edge(*edge)
    return size


def choose_m16_edge(graph, step, state):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    limit = max(1, state.get("m16_candidate_k", 30))
    min_drop_ratio = max(0.0, state.get("m16_min_drop_ratio", 0.05))
    current_gcc_size = h_graph.number_of_nodes()
    rows = []
    degrees = dict(h_graph.degree())
    for rank, (bridge_score, edge) in enumerate(ranked_bridge_edges(h_graph, limit)):
        if edge is None or not h_graph.has_edge(*edge):
            continue
        after_size = gcc_size_after_removing_edge(h_graph, edge)
        gcc_drop = current_gcc_size - after_size
        degree_product = degrees[edge[0]] * degrees[edge[1]]
        rank_bonus = (limit - rank) / float(limit)
        rows.append((gcc_drop, bridge_score + rank_bonus, degree_product, edge))
    rows.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    if rows and rows[0][0] / float(max(1, current_gcc_size)) >= min_drop_ratio:
        return rows[0][3]

    community_rows = ranked_community_edges(h_graph, "m7", limit)
    if community_rows:
        return community_rows[0][1]
    return choose_m12_edge(h_graph, step, state)


def choose_dynamic_edge(graph, method, step, original_m, state):
    if method == "M2 dynamic degree product":
        return choose_degree_product_edge(graph)
    if method == "M4 dynamic community internal / pair":
        return choose_community_edge(graph, "m4")
    if method == "M5 dynamic edge betweenness":
        return choose_betweenness_edge(graph)
    if method == "M7 dynamic community size / pair":
        return choose_community_edge(graph, "m7")
    if method == "M8 dynamic community bridge-degree":
        return choose_community_edge(graph, "m8")
    if method == "M9 dynamic community local bridge":
        return choose_community_edge(graph, "m9")
    if method == "M10 dynamic local bridge degree product":
        return choose_m10_edge(graph)
    if method == "M11 dynamic phase-aware hybrid":
        return choose_m11_edge(graph, step, original_m)
    if method == "M12 CEP-lite stale community attack":
        return choose_m12_edge(graph, step, state)
    if method == "M12 dynamic Louvain attack":
        return choose_m12_dynamic_louvain_edge(graph)
    if method == "M13 edge collective influence-lite":
        return choose_m13_edge(graph, state.get("m13_radius", 2))
    if method == "M14 bridge-aware CEP-lite attack":
        return choose_m14_edge(graph, step, state)
    if method == "M15 significant-bridge CEP-lite attack":
        return choose_m15_edge(graph, step, state)
    if method == "M16 candidate GCC-drop hybrid":
        return choose_m16_edge(graph, step, state)
    raise ValueError("Unsupported method: {}".format(method))


def curve_row(meta, method, step, original_m, ratio):
    return {
        "split": meta["split"],
        "graph_id": meta["graph_id"],
        "graph_type": meta["graph_type"],
        "community_strength": meta.get("community_strength", "unknown"),
        "method": method,
        "removed_edges": step,
        "remove_ratio": step / float(max(1, original_m)),
        "gcc_ratio": ratio,
    }


def dynamic_attack_curve(group, method, max_remove_ratio, args):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    meta = {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
        "community_strength": group["community_strength"].iloc[0]
        if "community_strength" in group.columns
        else "unknown",
    }
    rows = [curve_row(meta, method, 0, original_m, gcc_ratio(graph, original_n))]
    step = 0
    state = {
        "m12_louvain_interval": args.m12_louvain_interval,
        "m13_radius": args.m13_radius,
        "m15_bridge_min_side_ratio": args.m15_bridge_min_side_ratio,
        "m16_candidate_k": args.m16_candidate_k,
        "m16_min_drop_ratio": args.m16_min_drop_ratio,
    }
    while graph.number_of_edges() > 0 and step / float(max(1, original_m)) < max_remove_ratio:
        edge = choose_dynamic_edge(graph, method, step, original_m, state)
        if edge is None or not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
        rows.append(curve_row(meta, method, step, original_m, gcc_ratio(graph, original_n)))
    return rows


def first_remove_ratio_at_or_below(curve_df, threshold):
    hit = curve_df[curve_df["gcc_ratio"] <= threshold]
    if hit.empty:
        return np.nan
    return float(hit["remove_ratio"].iloc[0])


def summarize_curve(curve_df, elapsed_seconds):
    x = curve_df["remove_ratio"].values
    y = curve_df["gcc_ratio"].values
    auc = float(np.trapz(y, x))
    observed_remove_ratio = float(x[-1]) if len(x) else 0.0
    normalized_auc = auc / observed_remove_ratio if observed_remove_ratio > 0 else np.nan
    gcc_at_budget = float(y[-1]) if len(y) else np.nan
    return {
        "split": curve_df["split"].iloc[0],
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "community_strength": curve_df["community_strength"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "auc": auc,
        "normalized_auc": normalized_auc,
        "observed_remove_ratio": observed_remove_ratio,
        "gcc_at_budget": gcc_at_budget,
        "final_gcc_ratio": gcc_at_budget,
        "remove_ratio_gcc_le_0.5": first_remove_ratio_at_or_below(curve_df, 0.5),
        "remove_ratio_gcc_le_0.2": first_remove_ratio_at_or_below(curve_df, 0.2),
        "remove_ratio_gcc_le_0.1": first_remove_ratio_at_or_below(curve_df, 0.1),
        "num_steps": int(curve_df["removed_edges"].max()),
        "elapsed_seconds": float(elapsed_seconds),
    }


def aggregate_summary(summary_df):
    rows = []
    group_cols = ["graph_type", "community_strength", "method"]
    for key, group in summary_df.groupby(group_cols, sort=False):
        graph_type, community_strength, method = key
        rows.append(
            {
                "graph_type": graph_type,
                "community_strength": community_strength,
                "method": method,
                "num_graphs": len(group),
                "mean_auc": group["auc"].mean(),
                "mean_normalized_auc": group["normalized_auc"].mean(),
                "mean_gcc_at_budget": group["gcc_at_budget"].mean(),
                "mean_final_gcc_ratio": group["final_gcc_ratio"].mean(),
                "mean_remove_ratio_gcc_le_0.5": group["remove_ratio_gcc_le_0.5"].mean(),
                "mean_remove_ratio_gcc_le_0.2": group["remove_ratio_gcc_le_0.2"].mean(),
                "mean_remove_ratio_gcc_le_0.1": group["remove_ratio_gcc_le_0.1"].mean(),
                "hit_rate_gcc_le_0.5": group["remove_ratio_gcc_le_0.5"].notna().mean(),
                "hit_rate_gcc_le_0.2": group["remove_ratio_gcc_le_0.2"].notna().mean(),
                "hit_rate_gcc_le_0.1": group["remove_ratio_gcc_le_0.1"].notna().mean(),
                "mean_elapsed_seconds": group["elapsed_seconds"].mean(),
                "mean_num_steps": group["num_steps"].mean(),
            }
        )
    by_group = pd.DataFrame(rows)

    rows = []
    for method, group in summary_df.groupby("method", sort=False):
        rows.append(
            {
                "method": method,
                "num_graphs": len(group),
                "mean_auc": group["auc"].mean(),
                "median_auc": group["auc"].median(),
                "mean_normalized_auc": group["normalized_auc"].mean(),
                "mean_gcc_at_budget": group["gcc_at_budget"].mean(),
                "mean_final_gcc_ratio": group["final_gcc_ratio"].mean(),
                "mean_remove_ratio_gcc_le_0.5": group["remove_ratio_gcc_le_0.5"].mean(),
                "mean_remove_ratio_gcc_le_0.2": group["remove_ratio_gcc_le_0.2"].mean(),
                "mean_remove_ratio_gcc_le_0.1": group["remove_ratio_gcc_le_0.1"].mean(),
                "hit_rate_gcc_le_0.5": group["remove_ratio_gcc_le_0.5"].notna().mean(),
                "hit_rate_gcc_le_0.2": group["remove_ratio_gcc_le_0.2"].notna().mean(),
                "hit_rate_gcc_le_0.1": group["remove_ratio_gcc_le_0.1"].notna().mean(),
                "total_elapsed_seconds": group["elapsed_seconds"].sum(),
                "mean_elapsed_seconds": group["elapsed_seconds"].mean(),
            }
        )
    overall = pd.DataFrame(rows)
    return by_group, overall


def select_balanced_pilot_groups(df, graph_ids, max_graphs_per_group):
    if graph_ids:
        df = df[df["graph_id"].isin(set(graph_ids))].copy()
    selected = []
    for _, group in df.groupby(["graph_type", "community_strength"], sort=True):
        graph_sizes = (
            group.groupby("graph_id", as_index=False)
            .agg({"m": "first", "n": "first"})
            .sort_values(["m", "n", "graph_id"])
        )
        for graph_id in graph_sizes["graph_id"].head(max_graphs_per_group):
            selected.append((graph_id, group[group["graph_id"] == graph_id].copy()))
    return selected


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def plot_overall_auc(overall_df, path):
    plot_df = overall_df.sort_values("mean_auc")
    plt.figure(figsize=(10, 5))
    x = np.arange(len(plot_df))
    plt.bar(x, plot_df["mean_auc"].values)
    plt.xticks(x, plot_df["method"].values, rotation=25, ha="right")
    plt.ylabel("Mean AUC, lower is better")
    plt.title("Balanced pilot: GCC attack AUC")
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_curves(curve_df, path, max_remove_ratio):
    groups = list(curve_df.groupby(["graph_id", "graph_type", "community_strength"], sort=False))
    if not groups:
        return
    methods = list(curve_df["method"].drop_duplicates())
    cols = 2
    rows = int(np.ceil(len(groups) / float(cols)))
    fig, axes = plt.subplots(rows, cols, figsize=(12, max(4, rows * 3.4)), squeeze=False)
    for ax, (_, group) in zip(axes.ravel(), groups):
        title = "{} / {}-{}".format(
            group["graph_id"].iloc[0],
            group["graph_type"].iloc[0],
            group["community_strength"].iloc[0],
        )
        for method, method_df in group.groupby("method", sort=False):
            ax.plot(
                method_df["remove_ratio"],
                method_df["gcc_ratio"],
                label=method_label(method),
                color=METHOD_COLORS.get(method),
                linewidth=1.3,
            )
        ax.set_title(title)
        ax.set_xlabel("Removed edge ratio")
        ax.set_ylabel("GCC ratio")
        ax.set_xlim(0, max_remove_ratio * 1.025)
        ax.grid(alpha=0.25)
        ax.legend(loc="upper right", fontsize=6, framealpha=0.78)
    for ax in axes.ravel()[len(groups):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    legend_path = path.with_name("{}_legend.png".format(path.stem))
    legend_fig, legend_ax = plt.subplots(figsize=(8, max(1.6, len(methods) * 0.34)))
    for method in methods:
        legend_ax.plot([], [], label=method_label(method), color=METHOD_COLORS.get(method), linewidth=2)
    legend_ax.axis("off")
    legend_ax.legend(loc="center", ncol=2, fontsize=10, frameon=False)
    legend_fig.tight_layout()
    legend_fig.savefig(legend_path, dpi=220, bbox_inches="tight")
    plt.close(legend_fig)


def write_notes(out_dir, args, selected_graphs, overall_df):
    policy = [
        "# Heuristic Edge Attack Evaluation",
        "",
        "## Data",
        "",
        "- Split: {}.".format(args.split),
        "- File format: synthetic graphs are generated GML files; real external graphs are originally mixed GML/MTX. This script reconstructs undirected, unweighted NetworkX graphs from edge-feature CSV rows.",
        "- Selection: at most {} graph(s) for each graph_type/community_strength structure group; graphs are selected by ascending edge count.".format(args.max_graphs_per_group),
        "- Attack budget: {:.3f} edge-removal ratio.".format(args.max_remove_ratio),
        "- Metric naming: gcc_at_budget is the GCC ratio at the configured attack budget. The legacy final_gcc_ratio column is kept as a compatibility alias and should not be interpreted as full-collapse final GCC unless the budget reaches complete edge removal.",
        "- Random seed: {}.".format(SEED),
        "",
        "## Dynamic recomputation policy",
        "",
        "- GCC: dynamically recomputed after every removed edge for all methods.",
        "- Louvain: dynamically recomputed on the current GCC for M4, M7, M8, M9, and the M9 phase of M11.",
        "- Edge betweenness: dynamically recomputed on the current GCC only for M5.",
        "- Bridges: dynamically recomputed on the current GCC for the bridge-balance phase of M11.",
        "- Common neighbors: dynamically recomputed on the current GCC for M9, M10, and M11 phases that use them.",
        "- M12 communities: stale Louvain on the current GCC, recomputed every {} deletion step(s) or when GCC node membership changes.".format(args.m12_louvain_interval),
        "- M12 dynamic Louvain: Louvain is recomputed on the current GCC at every deletion step before scoring M12 candidate edges. Community sizes, inter-community edge counts, boundary degrees, and common neighbors are then recomputed from that current partition.",
        "- M13 edge collective influence: edge-degree and radius-{} edge boundary are dynamically recomputed on the current GCC; it does not use Louvain or edge betweenness.".format(args.m13_radius),
        "- M14 bridge-aware CEP-lite: bridges are dynamically recomputed on the current GCC; if no bridge exists, it falls back to M12 with the same stale Louvain interval. During the M12 fallback, common_neighbors is dynamically recomputed on the current GCC.",
        "- M15 significant-bridge CEP-lite: bridges are dynamically recomputed on the current GCC, but bridge-balance is used only when the smaller split side is at least {:.3f} of current GCC nodes; otherwise it falls back to M12. During the M12 fallback, common_neighbors is dynamically recomputed on the current GCC.".format(args.m15_bridge_min_side_ratio),
        "- M16 candidate GCC-drop hybrid: bridge candidates are recomputed on the current GCC; at most {} bridge candidates are temporarily removed and scored by one-step GCC drop. A bridge is used only when the one-step GCC drop is at least {:.3f} of the current GCC; otherwise the method falls back to dynamic M7 community size/pair. It does not compute edge betweenness.".format(args.m16_candidate_k, args.m16_min_drop_ratio),
        "",
        "## Reported metrics",
        "",
        "- AUC: trapezoidal area under GCC-ratio vs removed-edge-ratio curve over the observed budget; lower is more destructive.",
        "- normalized AUC: AUC divided by observed_remove_ratio; lower is more destructive.",
        "- gcc_at_budget: GCC ratio at the configured budget endpoint.",
        "- remove_ratio_gcc_le_0.5 / 0.2 / 0.1: first removed-edge ratio where GCC ratio is at or below the threshold; blank if not reached.",
        "- hit_rate_gcc_le_0.5 / 0.2 / 0.1: fraction of evaluated graphs that reached each GCC threshold within the budget.",
        "",
        "## Selected graphs",
        "",
    ]
    for graph_id, graph_type, strength in selected_graphs:
        policy.append("- {}: graph_type={}, community_strength={}".format(graph_id, graph_type, strength))
    policy.extend(["", "## Overall summary", ""])
    ranked = overall_df.sort_values("mean_auc")
    for _, row in ranked.iterrows():
        policy.append(
            "- {}: AUC={:.6f}, normalized AUC={:.6f}, gcc_at_budget={:.6f}, reach<=0.5={:.6f} (hit {:.1%}), reach<=0.2={:.6f} (hit {:.1%}), reach<=0.1={:.6f} (hit {:.1%}), total runtime={:.3f}s".format(
                row["method"],
                row["mean_auc"],
                row["mean_normalized_auc"],
                row["mean_gcc_at_budget"],
                row["mean_remove_ratio_gcc_le_0.5"],
                row["hit_rate_gcc_le_0.5"],
                row["mean_remove_ratio_gcc_le_0.2"],
                row["hit_rate_gcc_le_0.2"],
                row["mean_remove_ratio_gcc_le_0.1"],
                row["hit_rate_gcc_le_0.1"],
                row["total_elapsed_seconds"],
            )
        )
    (out_dir / "notes.md").write_text("\n".join(policy) + "\n", encoding="utf-8-sig")


def make_out_dir(out_root, name):
    base = Path(out_root) / name
    if not base.exists():
        return base
    suffix = 2
    while True:
        candidate = Path(out_root) / "{}_{}".format(name, suffix)
        if not candidate.exists():
            return candidate
        suffix += 1


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate cheap heuristic edge attacks.")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--out-name", default="heuristic_m9_m10_m11_smoke")
    parser.add_argument("--split", default="synthetic_test")
    parser.add_argument("--graph-ids", default="")
    parser.add_argument("--max-graphs-per-group", type=int, default=1)
    parser.add_argument("--max-remove-ratio", type=float, default=0.20)
    parser.add_argument("--m12-louvain-interval", type=int, default=5)
    parser.add_argument("--m13-radius", type=int, default=2)
    parser.add_argument("--m15-bridge-min-side-ratio", type=float, default=0.05)
    parser.add_argument("--m16-candidate-k", type=int, default=30)
    parser.add_argument("--m16-min-drop-ratio", type=float, default=0.05)
    parser.add_argument(
        "--methods",
        default="",
        help="Comma-separated method aliases, e.g. m2,m4,m5,m7,m8,m9,m11,m12,m12_dynamic,m14,m15,m16. Defaults to all methods.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    data_dir = Path(args.data_dir)
    out_dir = make_out_dir(args.out_root, args.out_name)
    out_dir.mkdir(parents=True, exist_ok=False)

    df = pd.read_csv(data_dir / "edge_features_{}.csv".format(args.split))
    groups = select_balanced_pilot_groups(
        df,
        parse_list(args.graph_ids),
        max(1, args.max_graphs_per_group),
    )
    if not groups:
        raise RuntimeError("No graph groups selected.")

    curve_rows = []
    summary_rows = []
    log_lines = []
    selected_graphs = []
    methods = parse_methods(args.methods)
    total_jobs = len(groups) * len(methods)
    job = 0
    for graph_id, group in groups:
        graph_type = group["graph_type"].iloc[0]
        strength = group["community_strength"].iloc[0]
        selected_graphs.append((graph_id, graph_type, strength))
        for method in methods:
            job += 1
            label = "[{}/{}] {} {} {} {}".format(
                job, total_jobs, graph_id, graph_type, strength, method
            )
            print(label, flush=True)
            log_lines.append(label)
            start = time.perf_counter()
            rows = dynamic_attack_curve(group, method, args.max_remove_ratio, args)
            elapsed = time.perf_counter() - start
            curve_rows.extend(rows)
            summary_rows.append(summarize_curve(pd.DataFrame(rows), elapsed))

    curve_df = pd.DataFrame(curve_rows)
    summary_df = pd.DataFrame(summary_rows)
    by_group_df, overall_df = aggregate_summary(summary_df)

    write_csv(curve_df, out_dir / "attack_curves.csv")
    write_csv(summary_df, out_dir / "attack_summary_by_graph.csv")
    write_csv(by_group_df, out_dir / "attack_summary_by_structure.csv")
    write_csv(overall_df, out_dir / "attack_summary_overall.csv")
    plot_overall_auc(overall_df, out_dir / "overall_auc.png")
    plot_curves(curve_df, out_dir / "attack_curves.png", args.max_remove_ratio)
    write_notes(out_dir, args, selected_graphs, overall_df)
    (out_dir / "run_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8-sig")
    (out_dir / "config.json").write_text(
        json.dumps(vars(args), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Wrote heuristic smoke-test outputs to {}".format(out_dir), flush=True)


if __name__ == "__main__":
    main()
