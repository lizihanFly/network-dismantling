from pathlib import Path
import argparse
import csv
import json
import math
import random
import shutil

import networkx as nx
from scipy.io import mmread

try:
    import community as community_louvain
except ImportError as exc:
    raise RuntimeError(
        "python-louvain is required. Install it in the active environment before running."
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "ml_attack_dataset"
SYN_GRAPH_DIR = OUT_DIR / "synthetic_graphs"
REAL_DATA_DIR = ROOT / "data" / "real_networks"
SEED = 20260513

SPLIT_COUNTS = {"train": 84, "val": 18, "synthetic_test": 18}
GRAPH_TYPE_WEIGHTS = [
    ("sbm", 0.50),
    ("ba", 0.20),
    ("ws", 0.15),
    ("er", 0.15),
]

EDGE_FIELDNAMES = [
    "split",
    "graph_id",
    "graph_type",
    "u",
    "v",
    "n",
    "m",
    "density",
    "avg_degree",
    "num_communities",
    "modularity",
    "community_strength",
    "is_inter_community",
    "same_community",
    "degree_u",
    "degree_v",
    "degree_sum",
    "degree_abs_diff",
    "degree_product",
    "degree_min",
    "degree_max",
    "clustering_u",
    "clustering_v",
    "clustering_product",
    "pagerank_u",
    "pagerank_v",
    "pagerank_product",
    "node_betweenness_u",
    "node_betweenness_v",
    "node_betweenness_product",
    "community_size_u",
    "community_size_v",
    "community_size_product",
    "community_internal_edges_u",
    "community_internal_edges_v",
    "community_internal_product",
    "community_pair_edges",
    "m3_score",
    "m4_score",
    "m6_score",
    "m7_score",
    "m8_score",
    "edge_betweenness",
    "edge_betweenness_rank",
    "edge_betweenness_rank_pct",
    "gcc_delta",
    "gcc_delta_rank",
    "gcc_delta_rank_pct",
]

META_FIELDNAMES = [
    "split",
    "graph_id",
    "graph_type",
    "n",
    "m",
    "density",
    "avg_degree",
    "num_communities",
    "modularity",
    "community_strength",
    "seed",
    "graph_path",
]


def stable_edge(u, v):
    return (u, v) if u <= v else (v, u)


def largest_connected_simple_graph(graph):
    graph = nx.Graph(graph)
    graph.remove_edges_from(nx.selfloop_edges(graph))
    graph.remove_nodes_from(list(nx.isolates(graph)))
    if graph.number_of_nodes() == 0:
        return graph
    if not nx.is_connected(graph):
        largest_nodes = max(nx.connected_components(graph), key=len)
        graph = graph.subgraph(largest_nodes).copy()
    return nx.convert_node_labels_to_integers(graph, ordering="sorted")


def generate_sbm(rng, seed):
    num_blocks = rng.choice([3, 4, 5, 6])
    block_size = rng.randint(22, 48)
    sizes = [block_size + rng.randint(-6, 6) for _ in range(num_blocks)]
    sizes = [max(14, size) for size in sizes]
    strength = rng.choice(["strong", "medium", "weak", "mixed"])

    if strength == "strong":
        p_in = rng.uniform(0.12, 0.20)
        p_out = rng.uniform(0.004, 0.015)
    elif strength == "medium":
        p_in = rng.uniform(0.08, 0.15)
        p_out = rng.uniform(0.018, 0.040)
    elif strength == "weak":
        p_in = rng.uniform(0.05, 0.10)
        p_out = rng.uniform(0.035, 0.070)
    else:
        p_in = rng.uniform(0.06, 0.16)
        p_out = rng.uniform(0.010, 0.055)

    probs = []
    for i in range(num_blocks):
        row = []
        for j in range(num_blocks):
            row.append(p_in if i == j else p_out)
        probs.append(row)

    graph = nx.stochastic_block_model(sizes, probs, seed=seed)
    graph.graph["community_strength"] = strength
    graph.graph["generator_params"] = {
        "sizes": sizes,
        "p_in": p_in,
        "p_out": p_out,
        "strength": strength,
    }
    return graph


def generate_ba(rng, seed):
    n = rng.randint(80, 240)
    attach_m = rng.randint(2, 5)
    graph = nx.barabasi_albert_graph(n, attach_m, seed=seed)
    graph.graph["community_strength"] = "none"
    graph.graph["generator_params"] = {"n": n, "attach_m": attach_m}
    return graph


def generate_ws(rng, seed):
    n = rng.randint(80, 220)
    k = rng.choice([4, 6, 8, 10])
    if k >= n:
        k = max(2, n // 10)
    p = rng.uniform(0.04, 0.28)
    graph = nx.watts_strogatz_graph(n, k, p, seed=seed)
    graph.graph["community_strength"] = "none"
    graph.graph["generator_params"] = {"n": n, "k": k, "p": p}
    return graph


def generate_er(rng, seed):
    n = rng.randint(80, 220)
    target_avg_degree = rng.uniform(4.0, 10.0)
    p = min(0.18, max(0.02, target_avg_degree / max(1, n - 1)))
    graph = nx.gnp_random_graph(n, p, seed=seed)
    graph.graph["community_strength"] = "none"
    graph.graph["generator_params"] = {"n": n, "p": p}
    return graph


def make_graph_type_schedule(count, rng):
    raw_counts = {
        graph_type: int(math.floor(count * weight))
        for graph_type, weight in GRAPH_TYPE_WEIGHTS
    }
    assigned = sum(raw_counts.values())
    remainders = sorted(
        (
            (count * weight - raw_counts[graph_type], graph_type)
            for graph_type, weight in GRAPH_TYPE_WEIGHTS
        ),
        reverse=True,
    )
    for _, graph_type in remainders[: count - assigned]:
        raw_counts[graph_type] += 1

    schedule = []
    for graph_type, _ in GRAPH_TYPE_WEIGHTS:
        schedule.extend([graph_type] * raw_counts[graph_type])
    rng.shuffle(schedule)
    return schedule


def generate_one_synthetic_graph(graph_id, split, graph_type, rng):
    for attempt in range(20):
        seed = rng.randint(0, 2**31 - 1)
        if graph_type == "sbm":
            graph = generate_sbm(rng, seed)
        elif graph_type == "ba":
            graph = generate_ba(rng, seed)
        elif graph_type == "ws":
            graph = generate_ws(rng, seed)
        elif graph_type == "er":
            graph = generate_er(rng, seed)
        else:
            raise ValueError(f"Unknown graph type: {graph_type}")

        graph = largest_connected_simple_graph(graph)
        if graph.number_of_nodes() >= 40 and graph.number_of_edges() >= 60:
            graph.graph["graph_id"] = graph_id
            graph.graph["split"] = split
            graph.graph["graph_type"] = graph_type
            graph.graph["seed"] = seed
            return graph
    raise RuntimeError(f"Could not generate a usable graph after retries: {graph_id}")


def load_mtx_graph(path):
    graph = nx.Graph()
    try:
        matrix = mmread(str(path)).tocoo()
        for u, v in zip(matrix.row, matrix.col):
            if u != v:
                graph.add_edge(int(u), int(v))
        return graph
    except ValueError:
        pass

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        first_data_line_seen = False
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("%"):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            if len(parts) >= 3 and not first_data_line_seen:
                first_data_line_seen = True
                continue
            first_data_line_seen = True
            u = int(parts[0]) - 1
            v = int(parts[1]) - 1
            if u != v:
                graph.add_edge(u, v)
    return graph


def load_real_graphs():
    candidates = [
        ("karate", REAL_DATA_DIR / "karate" / "karate.gml"),
        ("football", REAL_DATA_DIR / "football" / "football.gml"),
        ("ca_netscience", REAL_DATA_DIR / "ca-netscience" / "ca-netscience.mtx"),
        ("bio_diseasome", REAL_DATA_DIR / "bio-diseasome" / "bio-diseasome.mtx"),
        ("inf_USAir97", REAL_DATA_DIR / "inf-USAir97" / "inf-USAir97.mtx"),
    ]
    graphs = []
    for name, path in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == ".gml":
            graph = nx.read_gml(path, label=None)
        elif path.suffix.lower() == ".mtx":
            graph = load_mtx_graph(path)
        else:
            continue
        graph = largest_connected_simple_graph(graph)
        graph.graph["graph_id"] = name
        graph.graph["split"] = "real_external_test"
        graph.graph["graph_type"] = "real"
        graph.graph["community_strength"] = "real"
        graph.graph["seed"] = ""
        graph.graph["generator_params"] = {"source_path": str(path.relative_to(ROOT))}
        graphs.append(graph)
    return graphs


def louvain_partition(graph, seed):
    if graph.number_of_edges() == 0:
        return {node: 0 for node in graph.nodes()}
    return community_louvain.best_partition(graph, random_state=seed)


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
            key = stable_edge(cu, cv)
            pair_edges[key] = pair_edges.get(key, 0) + 1
    return communities, internal_edges, pair_edges


def rank_descending(values):
    sorted_indices = sorted(range(len(values)), key=lambda idx: (-values[idx], idx))
    ranks = [0] * len(values)
    previous_value = None
    previous_rank = 0
    for order, idx in enumerate(sorted_indices, start=1):
        value = values[idx]
        if previous_value is None or value != previous_value:
            previous_rank = order
            previous_value = value
        ranks[idx] = previous_rank
    return ranks


def compute_gcc_delta(graph, edge):
    before = len(max(nx.connected_components(graph), key=len)) / graph.number_of_nodes()
    graph.remove_edge(*edge)
    if graph.number_of_edges() == 0:
        after = 1.0 / graph.number_of_nodes()
    else:
        after = len(max(nx.connected_components(graph), key=len)) / graph.number_of_nodes()
    graph.add_edge(*edge)
    return max(0.0, before - after)


def safe_ratio(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator


def graph_features(graph, graph_id, graph_type, split, seed):
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    density = nx.density(graph)
    avg_degree = 2.0 * m / n if n else 0.0

    partition = louvain_partition(graph, seed if seed != "" else SEED)
    communities, internal_edges, pair_edges = community_stats(graph, partition)
    modularity = community_louvain.modularity(partition, graph) if m else 0.0

    degrees = dict(graph.degree())
    clustering = nx.clustering(graph)
    pagerank = nx.pagerank(graph, alpha=0.85)
    node_betweenness = nx.betweenness_centrality(graph, normalized=True)
    edge_betweenness = nx.edge_betweenness_centrality(graph, normalized=True)
    edge_betweenness = {stable_edge(*edge): value for edge, value in edge_betweenness.items()}

    edges = [stable_edge(u, v) for u, v in graph.edges()]
    edge_betweenness_values = [edge_betweenness[edge] for edge in edges]
    gcc_delta_values = [compute_gcc_delta(graph, edge) for edge in edges]
    edge_betweenness_ranks = rank_descending(edge_betweenness_values)
    gcc_delta_ranks = rank_descending(gcc_delta_values)
    denom = max(1, len(edges) - 1)

    rows = []
    for idx, (u, v) in enumerate(edges):
        cu = partition[u]
        cv = partition[v]
        is_inter = int(cu != cv)
        community_pair_edges = pair_edges.get(stable_edge(cu, cv), 0) if is_inter else 0
        community_size_u = len(communities[cu])
        community_size_v = len(communities[cv])
        internal_u = internal_edges[cu]
        internal_v = internal_edges[cv]

        m3_score = community_size_u * community_size_v if is_inter else 0.0
        m4_score = safe_ratio(internal_u * internal_v, community_pair_edges) if is_inter else 0.0
        m6_score = internal_u * internal_v if is_inter else 0.0
        m7_score = safe_ratio(community_size_u * community_size_v, community_pair_edges) if is_inter else 0.0
        degree_product = degrees[u] * degrees[v]
        m8_score = m7_score * degree_product

        rows.append(
            {
                "split": split,
                "graph_id": graph_id,
                "graph_type": graph_type,
                "u": u,
                "v": v,
                "n": n,
                "m": m,
                "density": density,
                "avg_degree": avg_degree,
                "num_communities": len(communities),
                "modularity": modularity,
                "community_strength": graph.graph.get("community_strength", "unknown"),
                "is_inter_community": is_inter,
                "same_community": int(cu == cv),
                "degree_u": degrees[u],
                "degree_v": degrees[v],
                "degree_sum": degrees[u] + degrees[v],
                "degree_abs_diff": abs(degrees[u] - degrees[v]),
                "degree_product": degree_product,
                "degree_min": min(degrees[u], degrees[v]),
                "degree_max": max(degrees[u], degrees[v]),
                "clustering_u": clustering[u],
                "clustering_v": clustering[v],
                "clustering_product": clustering[u] * clustering[v],
                "pagerank_u": pagerank[u],
                "pagerank_v": pagerank[v],
                "pagerank_product": pagerank[u] * pagerank[v],
                "node_betweenness_u": node_betweenness[u],
                "node_betweenness_v": node_betweenness[v],
                "node_betweenness_product": node_betweenness[u] * node_betweenness[v],
                "community_size_u": community_size_u,
                "community_size_v": community_size_v,
                "community_size_product": community_size_u * community_size_v,
                "community_internal_edges_u": internal_u,
                "community_internal_edges_v": internal_v,
                "community_internal_product": internal_u * internal_v,
                "community_pair_edges": community_pair_edges,
                "m3_score": m3_score,
                "m4_score": m4_score,
                "m6_score": m6_score,
                "m7_score": m7_score,
                "m8_score": m8_score,
                "edge_betweenness": edge_betweenness_values[idx],
                "edge_betweenness_rank": edge_betweenness_ranks[idx],
                "edge_betweenness_rank_pct": (edge_betweenness_ranks[idx] - 1) / denom,
                "gcc_delta": gcc_delta_values[idx],
                "gcc_delta_rank": gcc_delta_ranks[idx],
                "gcc_delta_rank_pct": (gcc_delta_ranks[idx] - 1) / denom,
            }
        )

    metadata = {
        "split": split,
        "graph_id": graph_id,
        "graph_type": graph_type,
        "n": n,
        "m": m,
        "density": density,
        "avg_degree": avg_degree,
        "num_communities": len(communities),
        "modularity": modularity,
        "community_strength": graph.graph.get("community_strength", "unknown"),
        "seed": seed,
        "graph_path": graph.graph.get("graph_path", ""),
    }
    return rows, metadata


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_graph_gml(graph, graph_path):
    clean_graph = nx.Graph()
    clean_graph.add_nodes_from(graph.nodes())
    clean_graph.add_edges_from(graph.edges())
    for key in [
        "graph_id",
        "split",
        "graph_type",
        "seed",
        "community_strength",
        "graph_path",
    ]:
        value = graph.graph.get(key)
        if value is not None:
            clean_graph.graph[key] = value
    nx.write_gml(clean_graph, graph_path)


def build_dataset(num_synthetic, seed):
    rng = random.Random(seed)
    total_default = sum(SPLIT_COUNTS.values())
    if num_synthetic != total_default:
        train_count = int(math.floor(num_synthetic * 0.70))
        val_count = int(math.floor(num_synthetic * 0.15))
        SPLIT_COUNTS["train"] = train_count
        SPLIT_COUNTS["val"] = val_count
        SPLIT_COUNTS["synthetic_test"] = num_synthetic - train_count - val_count

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if SYN_GRAPH_DIR.exists():
        shutil.rmtree(SYN_GRAPH_DIR)
    SYN_GRAPH_DIR.mkdir(parents=True, exist_ok=True)

    synthetic_graphs = []
    for split, count in SPLIT_COUNTS.items():
        graph_type_schedule = make_graph_type_schedule(count, rng)
        for idx, graph_type in enumerate(graph_type_schedule):
            graph_id = f"{split}_{idx:03d}"
            graph = generate_one_synthetic_graph(graph_id, split, graph_type, rng)
            graph_path = SYN_GRAPH_DIR / split / f"{graph_id}_{graph.graph['graph_type']}.gml"
            graph_path.parent.mkdir(parents=True, exist_ok=True)
            graph.graph["graph_path"] = str(graph_path.relative_to(ROOT))
            write_graph_gml(graph, graph_path)
            synthetic_graphs.append(graph)

    real_graphs = load_real_graphs()
    all_graphs = synthetic_graphs + real_graphs

    edge_rows = []
    graph_rows = []
    for index, graph in enumerate(all_graphs, start=1):
        graph_id = graph.graph["graph_id"]
        split = graph.graph["split"]
        graph_type = graph.graph["graph_type"]
        graph_seed = graph.graph.get("seed", seed)
        print(f"[{index:03d}/{len(all_graphs):03d}] features: {split}/{graph_id}")
        rows, metadata = graph_features(graph, graph_id, graph_type, split, graph_seed)
        edge_rows.extend(rows)
        graph_rows.append(metadata)

    write_csv(OUT_DIR / "edge_features_all.csv", edge_rows, EDGE_FIELDNAMES)
    write_csv(
        OUT_DIR / "edge_features_synthetic_train.csv",
        [row for row in edge_rows if row["split"] == "train"],
        EDGE_FIELDNAMES,
    )
    write_csv(
        OUT_DIR / "edge_features_synthetic_val.csv",
        [row for row in edge_rows if row["split"] == "val"],
        EDGE_FIELDNAMES,
    )
    write_csv(
        OUT_DIR / "edge_features_synthetic_test.csv",
        [row for row in edge_rows if row["split"] == "synthetic_test"],
        EDGE_FIELDNAMES,
    )
    write_csv(
        OUT_DIR / "edge_features_real_external_test.csv",
        [row for row in edge_rows if row["split"] == "real_external_test"],
        EDGE_FIELDNAMES,
    )
    write_csv(OUT_DIR / "graph_metadata.csv", graph_rows, META_FIELDNAMES)

    manifest = {
        "seed": seed,
        "synthetic_graph_count": len(synthetic_graphs),
        "real_external_test_graph_count": len(real_graphs),
        "split_counts": SPLIT_COUNTS,
        "edge_feature_rows": len(edge_rows),
        "feature_file": str((OUT_DIR / "edge_features_all.csv").relative_to(ROOT)),
        "graph_metadata_file": str((OUT_DIR / "graph_metadata.csv").relative_to(ROOT)),
        "labels": {
            "edge_betweenness": "M5 teacher score; higher means more central edge.",
            "edge_betweenness_rank_pct": "0 is top-ranked by M5 within the graph.",
            "gcc_delta": "One-step GCC-ratio drop after removing this edge.",
            "gcc_delta_rank_pct": "0 is top-ranked by one-step GCC damage within the graph.",
        },
        "note": "Use only split=train/val/synthetic_test for model development; keep real_external_test as external benchmark.",
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build synthetic edge-level datasets for ML/GNN attack ranking."
    )
    parser.add_argument("--num-synthetic", type=int, default=sum(SPLIT_COUNTS.values()))
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def main():
    args = parse_args()
    manifest = build_dataset(args.num_synthetic, args.seed)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
