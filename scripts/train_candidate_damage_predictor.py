from pathlib import Path
import argparse
import json
import pickle
import random
import time
import warnings

import community as community_louvain
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ml_attack_dataset"
OUT_DIR = ROOT / "result" / "candidate_damage_predictor"
SEED = 20260513
THRESHOLDS = [0.5, 0.2, 0.1]

BASELINE_METHODS = [
    "M2 dynamic degree product",
    "M4 dynamic community internal / pair",
    "M5 dynamic edge betweenness",
    "M7 dynamic community size / pair",
    "M8 dynamic community bridge-degree",
]
METHOD_ORDER = ["Candidate damage predictor"] + BASELINE_METHODS
SOURCE_COLUMNS = [
    "source_m2",
    "source_m4",
    "source_m5",
    "source_m7",
    "source_m8",
    "source_stale_eb",
    "source_path_bridge",
    "source_bridge",
    "source_random",
]
SOURCE_LABELS = {
    "m2": "M2 dynamic degree product",
    "m4": "M4 dynamic community internal / pair",
    "m5": "M5 dynamic edge betweenness",
    "sampled_eb": "Sampled edge betweenness candidates",
    "stale_eb": "Stale edge betweenness candidates",
    "m7": "M7 dynamic community size / pair",
    "m8": "M8 dynamic community bridge-degree",
    "path_bridge": "Shortest-path bridge candidates",
    "bridge": "Bridge candidates",
    "random": "Random candidates",
}
ALL_CANDIDATE_SOURCES = tuple(SOURCE_LABELS.keys())


def parse_list(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_candidate_sources(text):
    sources = parse_list(text)
    unknown = sorted(set(sources) - set(ALL_CANDIDATE_SOURCES))
    if unknown:
        raise ValueError(f"Unknown candidate sources: {', '.join(unknown)}")
    return sources or list(ALL_CANDIDATE_SOURCES)


def read_split(name):
    return pd.read_csv(DATA_DIR / f"edge_features_{name}.csv")


def select_graph_groups(df, max_graphs=None, max_graphs_per_group=None):
    groups = list(df.groupby(["split", "graph_id"], sort=False))
    if max_graphs_per_group:
        selected = []
        counts = {}
        for key, group in groups:
            group_key = (
                group["split"].iloc[0],
                group["graph_type"].iloc[0],
                group["community_strength"].iloc[0]
                if "community_strength" in group.columns
                else "unknown",
            )
            counts[group_key] = counts.get(group_key, 0) + 1
            if counts[group_key] <= max_graphs_per_group:
                selected.append((key, group))
        groups = selected
    if max_graphs:
        groups = groups[:max_graphs]
    return groups


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
    if nx.is_connected(graph):
        return graph.copy()
    nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(nodes).copy()


def gcc_ratio(graph, original_n):
    if original_n == 0 or graph.number_of_nodes() == 0:
        return 0.0
    if graph.number_of_edges() == 0:
        return graph.number_of_nodes() / float(original_n)
    return len(max(nx.connected_components(graph), key=len)) / float(original_n)


def gcc_delta_for_edge(graph, edge, original_n):
    before = gcc_ratio(graph, original_n)
    if not graph.has_edge(*edge):
        return 0.0
    graph.remove_edge(*edge)
    after = gcc_ratio(graph, original_n)
    graph.add_edge(*edge)
    return max(0.0, before - after)


def rollout_edge(
    graph,
    policy,
    top_k,
    random_candidate_count,
    bridge_top_k,
    original_n,
    seed_offset,
    candidate_sources=None,
    sampled_eb_k=16,
):
    if policy == "m5":
        return choose_dynamic_edge(graph, "M5 dynamic edge betweenness")
    edge_info = candidate_edges(
        graph,
        top_k,
        random_candidate_count=random_candidate_count,
        bridge_top_k=bridge_top_k,
        seed_offset=seed_offset,
        candidate_sources=candidate_sources,
        sampled_eb_k=sampled_eb_k,
    )
    if not edge_info:
        return None
    if policy == "damage_oracle":
        return max(
            edge_info,
            key=lambda candidate: (
                gcc_delta_for_edge(graph, candidate, original_n),
                -edge_sort_key(candidate)[0],
                -edge_sort_key(candidate)[1],
            ),
        )
    if policy == "random":
        rng = random.Random(SEED + seed_offset)
        return rng.choice(sorted(edge_info))
    raise ValueError(f"Unsupported damage rollout policy: {policy}")


def h_step_gcc_delta_for_edge(
    graph,
    edge,
    original_n,
    horizon,
    rollout_policy,
    top_k,
    random_candidate_count,
    bridge_top_k,
    seed_offset,
    candidate_sources=None,
    sampled_eb_k=16,
):
    if horizon <= 1:
        return gcc_delta_for_edge(graph, edge, original_n)
    if not graph.has_edge(*edge):
        return 0.0

    before = gcc_ratio(graph, original_n)
    sim_graph = graph.copy()
    sim_graph.remove_edge(*edge)
    for depth in range(horizon - 1):
        if sim_graph.number_of_edges() == 0:
            break
        rollout = rollout_edge(
            sim_graph,
            rollout_policy,
            top_k,
            random_candidate_count,
            bridge_top_k,
            original_n,
            seed_offset + depth + 1,
            candidate_sources=candidate_sources,
            sampled_eb_k=sampled_eb_k,
        )
        if rollout is None or not sim_graph.has_edge(*rollout):
            break
        sim_graph.remove_edge(*rollout)
    after = gcc_ratio(sim_graph, original_n)
    return max(0.0, before - after)


def louvain_partition(graph):
    if graph.number_of_edges() == 0:
        return {node: 0 for node in graph.nodes()}
    return community_louvain.best_partition(graph, random_state=SEED)


def community_stats(graph, partition):
    communities = {}
    for node, community_id in partition.items():
        communities.setdefault(community_id, set()).add(node)

    internal_edges = {community_id: 0 for community_id in communities}
    pair_edges = {}
    for u, v in graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            internal_edges[cu] += 1
        else:
            key = edge_sort_key((cu, cv))
            pair_edges[key] = pair_edges.get(key, 0) + 1
    return communities, internal_edges, pair_edges


def top_degree_product_edges(graph, top_k):
    if graph.number_of_edges() == 0:
        return []
    degrees = dict(graph.degree())
    rows = [
        (degrees[u] * degrees[v], edge_sort_key((u, v)))
        for u, v in graph.edges()
    ]
    rows.sort(key=lambda item: (-item[0], item[1]))
    return [edge for _, edge in rows[:top_k]]


def top_betweenness_edges(graph, top_k):
    if graph.number_of_edges() == 0:
        return []
    betweenness = nx.edge_betweenness_centrality(graph, normalized=True)
    rows = [(score, edge_sort_key(edge)) for edge, score in betweenness.items()]
    rows.sort(key=lambda item: (-item[0], item[1]))
    return [edge for _, edge in rows[:top_k]]


def top_sampled_betweenness_edges(graph, top_k, sample_k, seed_offset):
    if graph.number_of_edges() == 0:
        return []
    k = min(max(1, sample_k), graph.number_of_nodes())
    betweenness = nx.edge_betweenness_centrality(
        graph,
        k=k,
        normalized=True,
        seed=SEED + seed_offset,
    )
    rows = [(score, edge_sort_key(edge)) for edge, score in betweenness.items()]
    rows.sort(key=lambda item: (-item[0], item[1]))
    return [edge for _, edge in rows[:top_k]]


def top_community_edges(graph, top_k, mode):
    if graph.number_of_edges() == 0:
        return []
    partition = louvain_partition(graph)
    communities, internal_edges, pair_edges = community_stats(graph, partition)
    if len(communities) <= 1:
        return top_degree_product_edges(graph, top_k)

    degrees = dict(graph.degree())
    rows = []
    for u, v in graph.edges():
        cu = partition[u]
        cv = partition[v]
        if cu == cv:
            continue
        pair_count = pair_edges.get(edge_sort_key((cu, cv)), 0)
        if pair_count == 0:
            continue
        size_product = len(communities[cu]) * len(communities[cv])
        internal_product = internal_edges[cu] * internal_edges[cv]
        if mode == "m4":
            score = internal_product / float(pair_count)
        elif mode == "m7":
            score = size_product / float(pair_count)
        elif mode == "m8":
            score = (size_product / float(pair_count)) * degrees[u] * degrees[v]
        else:
            raise ValueError(f"Unknown community mode: {mode}")
        rows.append((score, edge_sort_key((u, v))))

    if not rows:
        return top_degree_product_edges(graph, top_k)
    rows.sort(key=lambda item: (-item[0], item[1]))
    return [edge for _, edge in rows[:top_k]]


def top_bridge_edges(graph, top_k):
    if top_k <= 0 or graph.number_of_edges() == 0:
        return []
    degrees = dict(graph.degree())
    rows = [
        (degrees[u] * degrees[v], edge_sort_key((u, v)))
        for u, v in nx.bridges(graph)
    ]
    rows.sort(key=lambda item: (-item[0], item[1]))
    return [edge for _, edge in rows[:top_k]]


def top_path_bridge_edges(graph, top_k):
    if top_k <= 0 or graph.number_of_edges() == 0:
        return []
    bridges = {edge_sort_key(edge) for edge in nx.bridges(graph)}
    if not bridges:
        return []
    degrees = dict(graph.degree())
    closeness = nx.closeness_centrality(graph)
    rows = []
    for u, v in bridges:
        score = (
            degrees[u] * degrees[v],
            closeness.get(u, 0.0) + closeness.get(v, 0.0),
        )
        rows.append((score, edge_sort_key((u, v))))
    rows.sort(key=lambda item: (-item[0][0], -item[0][1], item[1]))
    return [edge for _, edge in rows[:top_k]]


def random_candidate_edges(graph, count, seed_offset):
    if count <= 0 or graph.number_of_edges() == 0:
        return []
    edges = sorted(edge_sort_key(edge) for edge in graph.edges())
    rng = random.Random(SEED + seed_offset)
    rng.shuffle(edges)
    return edges[: min(count, len(edges))]


def candidate_edges(
    graph,
    top_k,
    random_candidate_count=0,
    bridge_top_k=0,
    seed_offset=0,
    candidate_sources=None,
    sampled_eb_k=16,
    stale_eb_edges=None,
):
    if candidate_sources is None:
        candidate_sources = ALL_CANDIDATE_SOURCES
    candidate_sources = set(candidate_sources)
    h_graph = largest_cc_subgraph(graph)
    source_edges = {}
    if "m2" in candidate_sources:
        source_edges["m2"] = top_degree_product_edges(h_graph, top_k)
    if "m4" in candidate_sources:
        source_edges["m4"] = top_community_edges(h_graph, top_k, "m4")
    if "m5" in candidate_sources:
        source_edges["m5"] = top_betweenness_edges(h_graph, top_k)
    if "sampled_eb" in candidate_sources:
        source_edges["sampled_eb"] = top_sampled_betweenness_edges(
            h_graph, top_k, sampled_eb_k, seed_offset
        )
    if "stale_eb" in candidate_sources:
        if stale_eb_edges is None:
            source_edges["stale_eb"] = top_betweenness_edges(h_graph, top_k)
        else:
            source_edges["stale_eb"] = [
                edge for edge in stale_eb_edges if h_graph.has_edge(*edge)
            ][:top_k]
    if "m7" in candidate_sources:
        source_edges["m7"] = top_community_edges(h_graph, top_k, "m7")
    if "m8" in candidate_sources:
        source_edges["m8"] = top_community_edges(h_graph, top_k, "m8")
    if "path_bridge" in candidate_sources:
        source_edges["path_bridge"] = top_path_bridge_edges(h_graph, bridge_top_k)
    if "bridge" in candidate_sources:
        source_edges["bridge"] = top_bridge_edges(h_graph, bridge_top_k)
    if "random" in candidate_sources:
        source_edges["random"] = random_candidate_edges(h_graph, random_candidate_count, seed_offset)
    edge_info = {}
    for source, edges in source_edges.items():
        for rank, edge in enumerate(edges, start=1):
            info = edge_info.setdefault(edge, {"sources": set(), "rank_min": rank})
            info["sources"].add(source)
            info["rank_min"] = min(info["rank_min"], rank)
    return edge_info


def dynamic_features_for_candidates(
    graph,
    edge_info,
    original_n,
    meta,
    step,
    damage_horizon=1,
    damage_rollout_policy="m5",
    top_k=5,
    random_candidate_count=0,
    bridge_top_k=0,
    candidate_sources=None,
    sampled_eb_k=16,
    compute_target=True,
):
    if not edge_info:
        return []

    h_graph = largest_cc_subgraph(graph)
    partition = louvain_partition(h_graph)
    communities, internal_edges, pair_edges = community_stats(h_graph, partition)
    degrees = dict(h_graph.degree())
    clustering = nx.clustering(h_graph)
    pagerank = nx.pagerank(h_graph, alpha=0.85) if h_graph.number_of_edges() else {}
    node_betweenness = nx.betweenness_centrality(h_graph, normalized=True)

    rows = []
    current_gcc = gcc_ratio(graph, original_n)
    current_m = max(1, graph.number_of_edges())
    for edge, info in edge_info.items():
        u, v = edge
        if not h_graph.has_edge(u, v):
            continue
        cu = partition[u]
        cv = partition[v]
        is_inter = int(cu != cv)
        pair_count = pair_edges.get(edge_sort_key((cu, cv)), 0) if is_inter else 0
        community_size_u = len(communities[cu])
        community_size_v = len(communities[cv])
        internal_u = internal_edges[cu]
        internal_v = internal_edges[cv]
        degree_product = degrees[u] * degrees[v]
        source_flags = {f"source_{source}": int(source in info["sources"]) for source in SOURCE_LABELS}

        if compute_target:
            target_delta = h_step_gcc_delta_for_edge(
                graph,
                edge,
                original_n,
                damage_horizon,
                damage_rollout_policy,
                top_k,
                random_candidate_count,
                bridge_top_k,
                seed_offset=step * 1009 + u * 9176 + v,
                candidate_sources=candidate_sources,
                sampled_eb_k=sampled_eb_k,
            )
        else:
            target_delta = 0.0

        row = {
            "split": meta["split"],
            "graph_id": meta["graph_id"],
            "graph_type": meta["graph_type"],
            "community_strength": meta.get("community_strength", "unknown"),
            "step": step,
            "remove_ratio": step / float(current_m + step),
            "u": u,
            "v": v,
            "n": original_n,
            "current_nodes": h_graph.number_of_nodes(),
            "current_edges": h_graph.number_of_edges(),
            "current_gcc_ratio": current_gcc,
            "density": nx.density(h_graph),
            "avg_degree": 2.0 * h_graph.number_of_edges() / h_graph.number_of_nodes(),
            "num_communities": len(communities),
            "candidate_rank_min": info["rank_min"],
            "candidate_source_count": len(info["sources"]),
            "is_inter_community": is_inter,
            "same_community": int(cu == cv),
            "degree_u": degrees[u],
            "degree_v": degrees[v],
            "degree_sum": degrees[u] + degrees[v],
            "degree_abs_diff": abs(degrees[u] - degrees[v]),
            "degree_product": degree_product,
            "degree_min": min(degrees[u], degrees[v]),
            "degree_max": max(degrees[u], degrees[v]),
            "clustering_u": clustering.get(u, 0.0),
            "clustering_v": clustering.get(v, 0.0),
            "clustering_product": clustering.get(u, 0.0) * clustering.get(v, 0.0),
            "pagerank_u": pagerank.get(u, 0.0),
            "pagerank_v": pagerank.get(v, 0.0),
            "pagerank_product": pagerank.get(u, 0.0) * pagerank.get(v, 0.0),
            "node_betweenness_u": node_betweenness.get(u, 0.0),
            "node_betweenness_v": node_betweenness.get(v, 0.0),
            "node_betweenness_product": node_betweenness.get(u, 0.0) * node_betweenness.get(v, 0.0),
            "community_size_u": community_size_u,
            "community_size_v": community_size_v,
            "community_size_product": community_size_u * community_size_v,
            "community_internal_edges_u": internal_u,
            "community_internal_edges_v": internal_v,
            "community_internal_product": internal_u * internal_v,
            "community_pair_edges": pair_count,
            "m4_score": (internal_u * internal_v / float(pair_count)) if is_inter and pair_count else 0.0,
            "m7_score": (community_size_u * community_size_v / float(pair_count)) if is_inter and pair_count else 0.0,
            "m8_score": ((community_size_u * community_size_v / float(pair_count)) * degree_product) if is_inter and pair_count else 0.0,
            "gcc_delta": target_delta,
        }
        row.update(source_flags)
        rows.append(row)

    return rows


def choose_dynamic_edge(graph, method):
    if method == "M2 dynamic degree product":
        source = "m2"
    elif method == "M4 dynamic community internal / pair":
        source = "m4"
    elif method == "M5 dynamic edge betweenness":
        source = "m5"
    elif method == "M7 dynamic community size / pair":
        source = "m7"
    elif method == "M8 dynamic community bridge-degree":
        source = "m8"
    else:
        raise ValueError(f"Unsupported method: {method}")
    edges = candidate_edges(graph, 1, candidate_sources=[source])
    if not edges:
        return None
    for edge, info in edges.items():
        if source in info["sources"]:
            return edge
    return next(iter(edges))


def collect_candidate_rows_for_graph(
    group,
    top_k,
    random_candidate_count,
    bridge_top_k,
    damage_horizon,
    damage_rollout_policy,
    max_steps,
    max_remove_ratio,
    rollout_policy,
    candidate_sources,
    sampled_eb_k,
    stale_eb_interval,
):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    meta = {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
        "community_strength": group["community_strength"].iloc[0]
        if "community_strength" in group.columns
        else "unknown",
    }
    rows = []
    step = 0
    rng = random.Random(SEED)
    stale_eb_edges = None
    while graph.number_of_edges() > 0:
        if max_steps and step >= max_steps:
            break
        if max_remove_ratio and step / float(original_m) >= max_remove_ratio:
            break
        if "stale_eb" in candidate_sources and (
            stale_eb_edges is None
            or stale_eb_interval <= 1
            or step % stale_eb_interval == 0
        ):
            stale_eb_edges = top_betweenness_edges(largest_cc_subgraph(graph), top_k)
        edge_info = candidate_edges(
            graph,
            top_k,
            random_candidate_count=random_candidate_count,
            bridge_top_k=bridge_top_k,
            seed_offset=original_m * 1009 + step,
            candidate_sources=candidate_sources,
            sampled_eb_k=sampled_eb_k,
            stale_eb_edges=stale_eb_edges,
        )
        rows.extend(
            dynamic_features_for_candidates(
                graph,
                edge_info,
                original_n,
                meta,
                step,
                damage_horizon=damage_horizon,
                damage_rollout_policy=damage_rollout_policy,
                top_k=top_k,
                random_candidate_count=random_candidate_count,
                bridge_top_k=bridge_top_k,
                candidate_sources=candidate_sources,
                sampled_eb_k=sampled_eb_k,
                compute_target=True,
            )
        )

        if rollout_policy == "m5":
            edge = choose_dynamic_edge(graph, "M5 dynamic edge betweenness")
        elif rollout_policy == "damage_oracle":
            if not edge_info:
                break
            edge = max(
                edge_info,
                key=lambda candidate: (
                    gcc_delta_for_edge(graph, candidate, original_n),
                    -edge_sort_key(candidate)[0],
                    -edge_sort_key(candidate)[1],
                ),
            )
        elif rollout_policy == "random":
            if not edge_info:
                break
            edge = rng.choice(sorted(edge_info))
        else:
            raise ValueError(f"Unsupported rollout policy: {rollout_policy}")
        if edge is None or not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
    return rows


def build_candidate_dataset(
    split_names,
    top_k,
    random_candidate_count,
    bridge_top_k,
    damage_horizon,
    damage_rollout_policy,
    max_steps,
    max_remove_ratio,
    max_graphs,
    max_graphs_per_group,
    graph_ids,
    rollout_policy,
    candidate_sources,
    sampled_eb_k,
    stale_eb_interval,
):
    frames = [read_split(name) for name in split_names]
    df = pd.concat(frames, ignore_index=True)
    if graph_ids:
        df = df[df["graph_id"].isin(graph_ids)].copy()
    groups = select_graph_groups(
        df,
        max_graphs=max_graphs,
        max_graphs_per_group=max_graphs_per_group,
    )

    rows = []
    for index, (_, group) in enumerate(groups, start=1):
        label = f"{group['split'].iloc[0]}/{group['graph_id'].iloc[0]}"
        print(f"[dataset {index:03d}/{len(groups):03d}] {label}", flush=True)
        rows.extend(
            collect_candidate_rows_for_graph(
                group,
                top_k=top_k,
                random_candidate_count=random_candidate_count,
                bridge_top_k=bridge_top_k,
                damage_horizon=damage_horizon,
                damage_rollout_policy=damage_rollout_policy,
                max_steps=max_steps,
                max_remove_ratio=max_remove_ratio,
                rollout_policy=rollout_policy,
                candidate_sources=candidate_sources,
                sampled_eb_k=sampled_eb_k,
                stale_eb_interval=stale_eb_interval,
            )
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["damage_rank"] = (
        result.groupby(["split", "graph_id", "step"])["gcc_delta"]
        .rank(method="min", ascending=False)
        .astype(int)
    )
    return result


def feature_columns(df):
    blocked = {
        "split",
        "graph_id",
        "graph_type",
        "community_strength",
        "u",
        "v",
        "gcc_delta",
        "damage_rank",
    }
    return [
        column
        for column in df.columns
        if column not in blocked and pd.api.types.is_numeric_dtype(df[column])
    ]


class PairwiseLogisticRanker:
    def __init__(self, max_iter=500, max_pairs_per_state=32, min_delta=0.0, random_state=SEED):
        self.max_pairs_per_state = max_pairs_per_state
        self.min_delta = min_delta
        self.random_state = random_state
        self.model = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "logistic",
                    LogisticRegression(
                        max_iter=max_iter,
                        class_weight="balanced",
                        random_state=random_state,
                    ),
                ),
            ]
        )

    def fit(self, df, feature_cols):
        x_rows = []
        y_rows = []
        rng = random.Random(self.random_state)
        state_cols = ["split", "graph_id", "step"]
        for _, group in df.groupby(state_cols, sort=False):
            if len(group) <= 1:
                continue
            values = group[feature_cols].values
            labels = group["gcc_delta"].values
            pairs = [
                (i, j)
                for i in range(len(group))
                for j in range(i + 1, len(group))
                if abs(labels[i] - labels[j]) > self.min_delta
            ]
            if self.max_pairs_per_state and len(pairs) > self.max_pairs_per_state:
                pairs = rng.sample(pairs, self.max_pairs_per_state)
            for i, j in pairs:
                label = 1 if labels[i] > labels[j] else 0
                diff = values[i] - values[j]
                x_rows.append(diff)
                y_rows.append(label)
                x_rows.append(-diff)
                y_rows.append(1 - label)
        if not x_rows:
            raise RuntimeError("No pairwise ranking examples were generated.")
        self.model.fit(np.asarray(x_rows), np.asarray(y_rows))
        return self

    def predict(self, values):
        return self.model.decision_function(values)


def train_model(
    train_df,
    feature_cols,
    model_type,
    max_iter,
    pairwise_max_pairs_per_state=32,
    pairwise_min_delta=0.0,
):
    if model_type == "mlp":
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "mlp",
                    MLPRegressor(
                        hidden_layer_sizes=(96, 48),
                        activation="relu",
                        solver="adam",
                        alpha=1e-4,
                        batch_size=256,
                        learning_rate_init=1e-3,
                        max_iter=max_iter,
                        early_stopping=True,
                        validation_fraction=0.12,
                        random_state=SEED,
                    ),
                ),
            ]
        )
    elif model_type == "random_forest":
        model = RandomForestRegressor(
            n_estimators=160,
            min_samples_leaf=2,
            random_state=SEED,
            n_jobs=-1,
        )
    elif model_type == "gbdt":
        model = GradientBoostingRegressor(
            n_estimators=max_iter,
            learning_rate=0.05,
            max_depth=3,
            random_state=SEED,
        )
    elif model_type == "pairwise_logistic":
        model = PairwiseLogisticRanker(
            max_iter=max_iter,
            max_pairs_per_state=pairwise_max_pairs_per_state,
            min_delta=pairwise_min_delta,
            random_state=SEED,
        )
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        if model_type == "pairwise_logistic":
            model.fit(train_df, feature_cols)
        else:
            model.fit(train_df[feature_cols].values, train_df["gcc_delta"].values)
    return model


def evaluate_candidate_ranking(model, df, feature_cols):
    result = df.copy()
    result["pred_gcc_delta"] = model.predict(result[feature_cols].values)
    rows = []
    for (split, graph_id, step), group in result.groupby(["split", "graph_id", "step"], sort=False):
        if len(group) <= 1:
            continue
        y_true = group["gcc_delta"].values
        y_pred = group["pred_gcc_delta"].values
        spearman = spearmanr(y_true, y_pred).correlation
        kendall = kendalltau(y_true, y_pred).correlation
        rows.append(
            {
                "split": split,
                "graph_id": graph_id,
                "step": step,
                "candidate_count": len(group),
                "mae": mean_absolute_error(y_true, y_pred),
                "rmse": mean_squared_error(y_true, y_pred) ** 0.5,
                "spearman": 0.0 if np.isnan(spearman) else spearman,
                "kendall": 0.0 if np.isnan(kendall) else kendall,
                "top1_hit": int(group.iloc[y_pred.argmax()]["damage_rank"] == 1),
                "best_true_delta": float(y_true.max()),
                "chosen_true_delta": float(group.iloc[y_pred.argmax()]["gcc_delta"]),
            }
        )
    return pd.DataFrame(rows), result


def should_stop_attack(step, original_m, max_attack_steps, attack_max_remove_ratio):
    if max_attack_steps and step >= max_attack_steps:
        return True
    if attack_max_remove_ratio and step / float(original_m) >= attack_max_remove_ratio:
        return True
    return False


def attack_curve_for_model(
    group,
    model,
    feature_cols,
    top_k,
    random_candidate_count,
    bridge_top_k,
    max_attack_steps,
    attack_max_remove_ratio,
    candidate_sources,
    sampled_eb_k,
    stale_eb_interval,
):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    meta = {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
        "community_strength": group["community_strength"].iloc[0]
        if "community_strength" in group.columns
        else "unknown",
    }
    rows = [curve_row(meta, "Candidate damage predictor", 0, original_m, gcc_ratio(graph, original_n))]
    step = 0
    stale_eb_edges = None
    while graph.number_of_edges() > 0 and not should_stop_attack(
        step, original_m, max_attack_steps, attack_max_remove_ratio
    ):
        if "stale_eb" in candidate_sources and (
            stale_eb_edges is None
            or stale_eb_interval <= 1
            or step % stale_eb_interval == 0
        ):
            stale_eb_edges = top_betweenness_edges(largest_cc_subgraph(graph), top_k)
        edge_info = candidate_edges(
            graph,
            top_k,
            random_candidate_count=random_candidate_count,
            bridge_top_k=bridge_top_k,
            seed_offset=original_m * 1009 + step,
            candidate_sources=candidate_sources,
            sampled_eb_k=sampled_eb_k,
            stale_eb_edges=stale_eb_edges,
        )
        candidate_rows = dynamic_features_for_candidates(
            graph,
            edge_info,
            original_n,
            meta,
            step,
            top_k=top_k,
            random_candidate_count=random_candidate_count,
            bridge_top_k=bridge_top_k,
            candidate_sources=candidate_sources,
            sampled_eb_k=sampled_eb_k,
            compute_target=False,
        )
        if not candidate_rows:
            break
        candidate_df = pd.DataFrame(candidate_rows)
        candidate_df["pred_gcc_delta"] = model.predict(candidate_df[feature_cols].values)
        candidate_df = candidate_df.sort_values(["pred_gcc_delta", "u", "v"], ascending=[False, True, True])
        edge = (int(candidate_df.iloc[0]["u"]), int(candidate_df.iloc[0]["v"]))
        if not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
        rows.append(curve_row(meta, "Candidate damage predictor", step, original_m, gcc_ratio(graph, original_n)))
    return rows


def dynamic_attack_curve(group, method, max_attack_steps, attack_max_remove_ratio):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
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
    while graph.number_of_edges() > 0 and not should_stop_attack(
        step, original_m, max_attack_steps, attack_max_remove_ratio
    ):
        edge = choose_dynamic_edge(graph, method)
        if edge is None or not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
        rows.append(curve_row(meta, method, step, original_m, gcc_ratio(graph, original_n)))
    return rows


def curve_row(meta, method, step, original_m, ratio):
    return {
        "split": meta["split"],
        "graph_id": meta["graph_id"],
        "graph_type": meta["graph_type"],
        "community_strength": meta.get("community_strength", "unknown"),
        "method": method,
        "removed_edges": step,
        "remove_ratio": step / float(original_m),
        "gcc_ratio": ratio,
    }


def threshold_remove_ratio(curve_df, threshold):
    reached = curve_df[curve_df["gcc_ratio"] <= threshold]
    if reached.empty:
        return np.nan
    return float(reached["remove_ratio"].iloc[0])


def summarize_curve(curve_df, elapsed_seconds=None):
    x = curve_df["remove_ratio"].values
    y = curve_df["gcc_ratio"].values
    auc = float(np.trapz(y, x))
    observed_remove_ratio = float(x[-1]) if len(x) else 0.0
    normalized_auc = auc / observed_remove_ratio if observed_remove_ratio > 0 else np.nan
    row = {
        "split": curve_df["split"].iloc[0],
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "community_strength": curve_df["community_strength"].iloc[0]
        if "community_strength" in curve_df.columns
        else "unknown",
        "method": curve_df["method"].iloc[0],
        "auc": auc,
        "normalized_auc": normalized_auc,
        "robustness_index": normalized_auc,
        "observed_remove_ratio": observed_remove_ratio,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "num_steps": int(curve_df["removed_edges"].max()),
    }
    if elapsed_seconds is not None:
        row["elapsed_seconds"] = float(elapsed_seconds)
    for threshold in THRESHOLDS:
        column = "remove_ratio_gcc_le_" + str(threshold).replace(".", "_")
        row[column] = threshold_remove_ratio(curve_df, threshold)
    return row


def evaluate_attack_curves(
    model,
    eval_df,
    feature_cols,
    top_k,
    random_candidate_count,
    bridge_top_k,
    attack_splits,
    max_eval_graphs,
    max_eval_graphs_per_group,
    graph_ids,
    skip_baselines,
    max_attack_steps,
    attack_max_remove_ratio,
    candidate_sources,
    sampled_eb_k,
    stale_eb_interval,
):
    df = eval_df[eval_df["split"].isin(attack_splits)].copy()
    if graph_ids:
        df = df[df["graph_id"].isin(graph_ids)].copy()
    groups = select_graph_groups(
        df,
        max_graphs=max_eval_graphs,
        max_graphs_per_group=max_eval_graphs_per_group,
    )

    curve_rows = []
    summary_rows = []
    for index, (_, group) in enumerate(groups, start=1):
        label = f"{group['split'].iloc[0]}/{group['graph_id'].iloc[0]}"
        print(f"[attack {index:03d}/{len(groups):03d}] {label}", flush=True)
        start_time = time.perf_counter()
        rows = attack_curve_for_model(
            group,
            model,
            feature_cols,
            top_k,
            random_candidate_count,
            bridge_top_k,
            max_attack_steps,
            attack_max_remove_ratio,
            candidate_sources,
            sampled_eb_k,
            stale_eb_interval,
        )
        elapsed_seconds = time.perf_counter() - start_time
        curve_rows.extend(rows)
        summary_rows.append(summarize_curve(pd.DataFrame(rows), elapsed_seconds))
        if not skip_baselines:
            for method in BASELINE_METHODS:
                start_time = time.perf_counter()
                baseline_rows = dynamic_attack_curve(
                    group, method, max_attack_steps, attack_max_remove_ratio
                )
                elapsed_seconds = time.perf_counter() - start_time
                curve_rows.extend(baseline_rows)
                summary_rows.append(summarize_curve(pd.DataFrame(baseline_rows), elapsed_seconds))
    return pd.DataFrame(curve_rows), pd.DataFrame(summary_rows)


def aggregate_summary(summary_df):
    rows = []
    for (split, method), group in summary_df.groupby(["split", "method"]):
        row = {
            "split": split,
            "method": method,
            "num_graphs": len(group),
            "mean_auc": group["auc"].mean(),
            "median_auc": group["auc"].median(),
            "std_auc": group["auc"].std(),
            "mean_normalized_auc": group["normalized_auc"].mean(),
            "median_normalized_auc": group["normalized_auc"].median(),
            "mean_robustness_index": group["robustness_index"].mean(),
            "mean_observed_remove_ratio": group["observed_remove_ratio"].mean(),
            "mean_final_gcc_ratio": group["final_gcc_ratio"].mean(),
            "mean_num_steps": group["num_steps"].mean(),
        }
        if "elapsed_seconds" in group:
            row["mean_elapsed_seconds"] = group["elapsed_seconds"].mean()
        for threshold in THRESHOLDS:
            column = "remove_ratio_gcc_le_" + str(threshold).replace(".", "_")
            row[f"mean_{column}"] = group[column].mean()
        rows.append(row)
    result = pd.DataFrame(rows)
    result["method"] = pd.Categorical(result["method"], METHOD_ORDER, ordered=True)
    return result.sort_values(["split", "method"])


def aggregate_candidate_metrics(metrics_df):
    rows = []
    for split, group in metrics_df.groupby("split"):
        rows.append(
            {
                "split": split,
                "num_states": len(group),
                "mean_candidate_count": group["candidate_count"].mean(),
                "mean_mae": group["mae"].mean(),
                "mean_rmse": group["rmse"].mean(),
                "mean_spearman": group["spearman"].mean(),
                "mean_kendall": group["kendall"].mean(),
                "mean_top1_hit": group["top1_hit"].mean(),
                "mean_chosen_delta_ratio": (
                    group["chosen_true_delta"] / group["best_true_delta"].replace(0.0, np.nan)
                ).mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("split")


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def plot_auc(aggregate_df, split, path):
    split_df = aggregate_df[aggregate_df["split"] == split].copy()
    if split_df.empty:
        return
    split_df = split_df.sort_values("mean_auc")
    plt.figure(figsize=(9.6, 4.8))
    x = np.arange(len(split_df))
    plt.bar(x, split_df["mean_auc"].values, yerr=split_df["std_auc"].fillna(0).values, capsize=4)
    plt.xticks(x, split_df["method"].values, rotation=25, ha="right")
    plt.ylabel("Mean AUC (lower is better)")
    plt.title(f"{split}: candidate damage predictor")
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def write_notes(aggregate_df, candidate_aggregate_df, args):
    lines = [
        "# Candidate Damage Predictor",
        "",
        f"This experiment changes the supervised target from teacher-rank imitation to direct {args.damage_horizon}-step damage prediction.",
        "",
        "At each dynamic state, candidates are built from M2/M4/M5/M7/M8 plus optional random and bridge candidates. The model predicts candidate damage and removes the edge with the largest predicted damage.",
        "",
        "## Config",
        "",
        f"- model_type={args.model_type}",
        f"- top_k={args.top_k}",
        f"- random_candidate_count={args.random_candidates}",
        f"- bridge_top_k={args.bridge_top_k}",
        f"- candidate_sources={args.candidate_sources}",
        f"- train_candidate_sources={args.train_candidate_sources or args.candidate_sources}",
        f"- eval_candidate_sources={args.eval_candidate_sources or args.candidate_sources}",
        f"- attack_candidate_sources={args.attack_candidate_sources or args.candidate_sources}",
        f"- sampled_eb_k={args.sampled_eb_k}",
        f"- stale_eb_interval={args.stale_eb_interval}",
        f"- pairwise_max_pairs_per_state={args.pairwise_max_pairs_per_state}",
        f"- pairwise_min_delta={args.pairwise_min_delta}",
        f"- damage_horizon={args.damage_horizon}",
        f"- damage_rollout_policy={args.damage_rollout_policy}",
        f"- rollout_policy={args.rollout_policy}",
        f"- max_train_steps={args.max_train_steps}",
        f"- train_max_remove_ratio={args.train_max_remove_ratio}",
        "",
        "## Candidate Ranking Quality",
        "",
    ]
    for row in candidate_aggregate_df.itertuples(index=False):
        lines.append(
            f"- {row.split}: states={row.num_states}, top1_hit={row.mean_top1_hit:.3f}, "
            f"Spearman={row.mean_spearman:.3f}, chosen/best delta={row.mean_chosen_delta_ratio:.3f}"
        )
    lines.extend(["", "## Attack AUC", ""])
    for split, group in aggregate_df.groupby("split"):
        ranked = group.sort_values("mean_auc")
        best = ranked.iloc[0]
        damage = group[group["method"] == "Candidate damage predictor"].iloc[0]
        lines.append(
            f"- {split}: best={best['method']} (mean AUC={best['mean_auc']:.3f}); "
            f"damage predictor mean AUC={damage['mean_auc']:.3f}"
        )
    (OUT_DIR / "candidate_damage_predictor_notes.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8-sig"
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Train a candidate-set damage predictor for edge attacks.")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--random-candidates",
        type=int,
        default=0,
        help="Number of extra random candidate edges to add at each state.",
    )
    parser.add_argument(
        "--bridge-top-k",
        type=int,
        default=0,
        help="Number of bridge candidate edges to add at each state, ranked by degree product.",
    )
    parser.add_argument(
        "--candidate-sources",
        default="m2,m4,m5,m7,m8,bridge,random",
        help="Default comma-separated candidate sources selected from m2,m4,m5,sampled_eb,stale_eb,m7,m8,path_bridge,bridge,random.",
    )
    parser.add_argument(
        "--train-candidate-sources",
        default="",
        help="Candidate sources for training rows. Defaults to --candidate-sources.",
    )
    parser.add_argument(
        "--eval-candidate-sources",
        default="",
        help="Candidate sources for ranking evaluation rows. Defaults to --candidate-sources.",
    )
    parser.add_argument(
        "--attack-candidate-sources",
        default="",
        help="Candidate sources used by the learned policy during dynamic attack. Defaults to --candidate-sources.",
    )
    parser.add_argument(
        "--sampled-eb-k",
        type=int,
        default=16,
        help="Number of source nodes sampled for sampled_eb candidate generation.",
    )
    parser.add_argument(
        "--stale-eb-interval",
        type=int,
        default=10,
        help="Recompute stale_eb candidates every N deletion steps; 1 matches fully dynamic EB candidates.",
    )
    parser.add_argument(
        "--model-type",
        choices=["mlp", "random_forest", "gbdt", "pairwise_logistic"],
        default="gbdt",
    )
    parser.add_argument("--max-iter", type=int, default=180)
    parser.add_argument(
        "--pairwise-max-pairs-per-state",
        type=int,
        default=32,
        help="Maximum unordered candidate pairs sampled per state for pairwise_logistic.",
    )
    parser.add_argument(
        "--pairwise-min-delta",
        type=float,
        default=0.0,
        help="Minimum absolute damage difference needed to create a pairwise ranking example.",
    )
    parser.add_argument("--train-splits", default="synthetic_train")
    parser.add_argument("--eval-splits", default="synthetic_val,synthetic_test,real_external_test")
    parser.add_argument("--attack-splits", default="synthetic_test,real_external_test")
    parser.add_argument("--graph-ids", default="")
    parser.add_argument("--max-train-graphs", type=int, default=0)
    parser.add_argument("--max-eval-graphs", type=int, default=0)
    parser.add_argument(
        "--max-train-graphs-per-group",
        type=int,
        default=0,
        help="Limit training graphs per split/graph_type/community_strength group before the global cap.",
    )
    parser.add_argument(
        "--max-eval-graphs-per-group",
        type=int,
        default=0,
        help="Limit eval and attack graphs per split/graph_type/community_strength group before the global cap.",
    )
    parser.add_argument("--max-train-steps", type=int, default=80)
    parser.add_argument("--max-attack-steps", type=int, default=0)
    parser.add_argument("--train-max-remove-ratio", type=float, default=0.35)
    parser.add_argument("--attack-max-remove-ratio", type=float, default=0.0)
    parser.add_argument(
        "--damage-horizon",
        type=int,
        default=1,
        help="Number of deletion steps used to label candidate damage. 1 is one-step gcc_delta.",
    )
    parser.add_argument(
        "--damage-rollout-policy",
        choices=["m5", "damage_oracle", "random"],
        default="m5",
        help="Policy used after the first candidate deletion when damage_horizon > 1.",
    )
    parser.add_argument("--rollout-policy", choices=["m5", "damage_oracle", "random"], default="m5")
    parser.add_argument("--skip-baselines", action="store_true")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    return parser.parse_args()


def main():
    global DATA_DIR, OUT_DIR
    args = parse_args()
    DATA_DIR = Path(args.data_dir)
    OUT_DIR = Path(args.out_dir)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graph_ids = set(parse_list(args.graph_ids))
    candidate_sources = parse_candidate_sources(args.candidate_sources)
    train_candidate_sources = parse_candidate_sources(
        args.train_candidate_sources or args.candidate_sources
    )
    eval_candidate_sources = parse_candidate_sources(
        args.eval_candidate_sources or args.candidate_sources
    )
    attack_candidate_sources = parse_candidate_sources(
        args.attack_candidate_sources or args.candidate_sources
    )

    train_candidate_df = build_candidate_dataset(
        parse_list(args.train_splits),
        top_k=args.top_k,
        random_candidate_count=args.random_candidates,
        bridge_top_k=args.bridge_top_k,
        damage_horizon=args.damage_horizon,
        damage_rollout_policy=args.damage_rollout_policy,
        max_steps=args.max_train_steps,
        max_remove_ratio=args.train_max_remove_ratio,
        max_graphs=args.max_train_graphs,
        max_graphs_per_group=args.max_train_graphs_per_group,
        graph_ids=graph_ids,
        rollout_policy=args.rollout_policy,
        candidate_sources=train_candidate_sources,
        sampled_eb_k=args.sampled_eb_k,
        stale_eb_interval=args.stale_eb_interval,
    )
    if train_candidate_df.empty:
        raise RuntimeError("No candidate training rows were generated.")
    feature_cols = feature_columns(train_candidate_df)
    model = train_model(
        train_candidate_df,
        feature_cols,
        args.model_type,
        args.max_iter,
        pairwise_max_pairs_per_state=args.pairwise_max_pairs_per_state,
        pairwise_min_delta=args.pairwise_min_delta,
    )

    eval_candidate_df = build_candidate_dataset(
        parse_list(args.eval_splits),
        top_k=args.top_k,
        random_candidate_count=args.random_candidates,
        bridge_top_k=args.bridge_top_k,
        damage_horizon=args.damage_horizon,
        damage_rollout_policy=args.damage_rollout_policy,
        max_steps=args.max_train_steps,
        max_remove_ratio=args.train_max_remove_ratio,
        max_graphs=args.max_eval_graphs,
        max_graphs_per_group=args.max_eval_graphs_per_group,
        graph_ids=graph_ids,
        rollout_policy=args.rollout_policy,
        candidate_sources=eval_candidate_sources,
        sampled_eb_k=args.sampled_eb_k,
        stale_eb_interval=args.stale_eb_interval,
    )
    candidate_metrics_df, eval_candidate_scored_df = evaluate_candidate_ranking(
        model, eval_candidate_df, feature_cols
    )
    candidate_aggregate_df = aggregate_candidate_metrics(candidate_metrics_df)

    eval_frames = [read_split(split) for split in parse_list(args.eval_splits)]
    eval_df = pd.concat(eval_frames, ignore_index=True)
    attack_curve_df, attack_summary_df = evaluate_attack_curves(
        model,
        eval_df,
        feature_cols,
        top_k=args.top_k,
        random_candidate_count=args.random_candidates,
        bridge_top_k=args.bridge_top_k,
        attack_splits=parse_list(args.attack_splits),
        max_eval_graphs=args.max_eval_graphs,
        max_eval_graphs_per_group=args.max_eval_graphs_per_group,
        graph_ids=graph_ids,
        skip_baselines=args.skip_baselines,
        max_attack_steps=args.max_attack_steps,
        attack_max_remove_ratio=args.attack_max_remove_ratio,
        candidate_sources=attack_candidate_sources,
        sampled_eb_k=args.sampled_eb_k,
        stale_eb_interval=args.stale_eb_interval,
    )
    aggregate_df = aggregate_summary(attack_summary_df)

    write_csv(pd.DataFrame({"feature": feature_cols}), OUT_DIR / "candidate_damage_feature_columns.csv")
    write_csv(train_candidate_df, OUT_DIR / "candidate_damage_train_rows.csv")
    write_csv(eval_candidate_scored_df, OUT_DIR / "candidate_damage_eval_rows_scored.csv")
    write_csv(candidate_metrics_df, OUT_DIR / "candidate_ranking_metrics_by_state.csv")
    write_csv(candidate_aggregate_df, OUT_DIR / "candidate_ranking_metrics_aggregate.csv")
    write_csv(attack_curve_df, OUT_DIR / "attack_curves.csv")
    write_csv(attack_summary_df, OUT_DIR / "attack_summary_by_graph.csv")
    write_csv(aggregate_df, OUT_DIR / "attack_summary_aggregate.csv")

    with (OUT_DIR / "candidate_damage_model.pkl").open("wb") as handle:
        pickle.dump(
            {
                "model": model,
                "feature_cols": feature_cols,
                "target": "gcc_delta",
                "top_k": args.top_k,
                "random_candidates": args.random_candidates,
                "bridge_top_k": args.bridge_top_k,
                "candidate_sources": candidate_sources,
                "train_candidate_sources": train_candidate_sources,
                "eval_candidate_sources": eval_candidate_sources,
                "attack_candidate_sources": attack_candidate_sources,
                "sampled_eb_k": args.sampled_eb_k,
                "stale_eb_interval": args.stale_eb_interval,
                "damage_horizon": args.damage_horizon,
                "damage_rollout_policy": args.damage_rollout_policy,
                "model_type": args.model_type,
                "pairwise_max_pairs_per_state": args.pairwise_max_pairs_per_state,
                "pairwise_min_delta": args.pairwise_min_delta,
            },
            handle,
        )

    config = vars(args).copy()
    config["data_dir"] = str(DATA_DIR)
    config["candidate_sources"] = candidate_sources
    config["train_candidate_sources"] = train_candidate_sources
    config["eval_candidate_sources"] = eval_candidate_sources
    config["attack_candidate_sources"] = attack_candidate_sources
    config["feature_count"] = len(feature_cols)
    config["train_rows"] = len(train_candidate_df)
    config["eval_candidate_rows"] = len(eval_candidate_df)
    (OUT_DIR / "candidate_damage_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for split in parse_list(args.attack_splits):
        plot_auc(aggregate_df, split, OUT_DIR / f"{split}_candidate_damage_auc_by_method.png")
    write_notes(aggregate_df, candidate_aggregate_df, args)

    print(f"Wrote candidate damage predictor outputs to {OUT_DIR}")
    print(candidate_aggregate_df.to_string(index=False))
    print(aggregate_df.to_string(index=False))


if __name__ == "__main__":
    main()
