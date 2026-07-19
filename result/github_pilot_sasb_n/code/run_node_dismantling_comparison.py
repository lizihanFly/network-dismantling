from pathlib import Path
from collections import deque
import argparse
import hashlib
import json
import math
import random
import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

import evaluate_next_stage_fair_comparison as fair
import evaluate_m19_realworld_40plus as real40

try:
    import community as community_louvain
except Exception:
    community_louvain = None

try:
    import igraph as ig
except Exception:
    ig = None

try:
    from scipy import stats as scipy_stats
except Exception:
    scipy_stats = None


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "result" / "node_sasb_paper"
PLOT_DIR = OUT_DIR / "plots"
PILOT_OUT_DIR = OUT_DIR / "pilot"
PILOT_CONFIG_PATH = OUT_DIR / "pilot_config.json"
REAL_PER_GRAPH = ROOT / "result" / "paper_experiments" / "baselines" / "baseline_realworld_m5_completed_per_graph.csv"
REAL_CLEANED_DIR = ROOT / "data" / "realnetworks_40plus" / "cleaned"

DEFAULT_SEEDS = [20260513, 20260514, 20260515, 20260516, 20260517]
DEFAULT_SOURCE_BUDGETS = [16, 32, 64, 128]
DEFAULT_LOUVAIN_SEED = 20260513

METHOD_STRUCTURED = "SASB-N-structured"
METHOD_RANDOM_SOURCE = "SASB-N-random-source"
METHOD_DEGREE_SOURCE = "SASB-N-degree-source"
METHOD_FROZEN_SOURCE = "SASB-N-frozen-source"
METHOD_M5 = "M5"
METHOD_DYNAMIC_DEGREE = "dynamic-degree"
METHOD_DYNAMIC_CLOSENESS = "dynamic-closeness"
METHOD_DYNAMIC_KCORE = "dynamic-k-core"
METHOD_RANDOM = "random"

SOURCE_METHODS = [
    METHOD_STRUCTURED,
    METHOD_RANDOM_SOURCE,
    METHOD_DEGREE_SOURCE,
    METHOD_FROZEN_SOURCE,
]
BASELINE_METHODS = [
    METHOD_M5,
    METHOD_DYNAMIC_DEGREE,
    METHOD_DYNAMIC_CLOSENESS,
    METHOD_DYNAMIC_KCORE,
    METHOD_RANDOM,
]
DETERMINISTIC_BASELINE_METHODS = [
    METHOD_M5,
    METHOD_DYNAMIC_DEGREE,
    METHOD_DYNAMIC_CLOSENESS,
    METHOD_DYNAMIC_KCORE,
]
METHODS = SOURCE_METHODS + BASELINE_METHODS
METHOD_ALIASES = {
    "sasb": METHOD_STRUCTURED,
    "sasb-n": METHOD_STRUCTURED,
    "structured": METHOD_STRUCTURED,
    "random-source": METHOD_RANDOM_SOURCE,
    "degree-source": METHOD_DEGREE_SOURCE,
    "frozen-source": METHOD_FROZEN_SOURCE,
    "m5": METHOD_M5,
    "degree": METHOD_DYNAMIC_DEGREE,
    "dynamic-degree": METHOD_DYNAMIC_DEGREE,
    "closeness": METHOD_DYNAMIC_CLOSENESS,
    "dynamic-closeness": METHOD_DYNAMIC_CLOSENESS,
    "kcore": METHOD_DYNAMIC_KCORE,
    "k-core": METHOD_DYNAMIC_KCORE,
    "dynamic-k-core": METHOD_DYNAMIC_KCORE,
    "random": METHOD_RANDOM,
}


def parse_list(text):
    return [part.strip() for part in str(text).split(",") if part.strip()]


def parse_int_list(text):
    return [int(part) for part in parse_list(text)]


def parse_methods(text):
    methods = [METHOD_ALIASES.get(part.lower(), part) for part in parse_list(text)]
    if not methods:
        methods = list(METHODS)
    unknown = sorted(set(methods) - set(METHODS))
    if unknown:
        raise ValueError("unknown methods: {}".format(", ".join(unknown)))
    return methods


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp, index=False, encoding="utf-8-sig")
    temp.replace(path)


def write_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def stable_seed(seed, *parts):
    text = "|".join(str(part) for part in (seed,) + parts).encode("utf-8")
    return int(hashlib.sha256(text).hexdigest()[:8], 16)


def stable_hash(items):
    values = [str(item) for item in items]
    values.sort()
    payload = "\n".join(values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def safe_name(text):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(text))


def largest_cc_graph(graph):
    if graph.number_of_nodes() == 0:
        return graph.copy()
    if graph.number_of_edges() == 0:
        return graph.copy()
    nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(nodes).copy()


def gcc_ratio(graph, original_n):
    if original_n <= 0 or graph.number_of_nodes() == 0:
        return 0.0
    if graph.number_of_edges() == 0:
        return 1.0 / float(original_n)
    return len(max(nx.connected_components(graph), key=len)) / float(original_n)


def first_ratio_at_or_below(curve, threshold):
    hit = curve[curve["gcc_ratio"] <= threshold]
    if hit.empty:
        return np.nan
    return float(hit["remove_ratio"].iloc[0])


def trapezoid_auc(y, x):
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def louvain_partition(graph, seed):
    if graph.number_of_nodes() == 0:
        return {}
    if community_louvain is not None:
        return community_louvain.best_partition(graph, random_state=int(seed))
    communities = nx.algorithms.community.greedy_modularity_communities(graph)
    partition = {}
    for idx, community in enumerate(communities):
        for node in community:
            partition[node] = idx
    return partition


def boundary_scores(graph, partition):
    scores = {node: 0 for node in graph.nodes()}
    for u, v in graph.edges():
        if partition.get(u) != partition.get(v):
            scores[u] += 1
            scores[v] += 1
    return scores


def community_count(partition):
    return len(set(partition.values())) if partition else 0


def choose_structured_sources(graph, partition, source_budget, seed, graph_id, step):
    degrees = dict(graph.degree())
    boundary = boundary_scores(graph, partition)
    target = min(int(source_budget), graph.number_of_nodes())
    selected = []
    selected_set = set()

    def add(node):
        if node in graph and node not in selected_set and len(selected) < target:
            selected.append(node)
            selected_set.add(node)

    for node, _ in sorted(boundary.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), str(item[0]))):
        add(node)
    if partition:
        communities = {}
        for node, cid in partition.items():
            if node in graph:
                communities.setdefault(cid, []).append(node)
        for members in sorted(communities.values(), key=lambda xs: (-len(xs), str(min(xs, key=str)))):
            representative = max(members, key=lambda node: (degrees.get(node, 0), boundary.get(node, 0), str(node)))
            add(representative)
    for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], str(item[0]))):
        add(node)
    rng = random.Random(stable_seed(seed, graph_id, step, "structured-fill"))
    shuffled = list(graph.nodes())
    rng.shuffle(shuffled)
    for node in shuffled:
        add(node)
    return selected, boundary


def choose_source_set(graph, method, source_budget, seed, graph_id, step, state):
    louvain_seed = int(seed)
    partition = louvain_partition(graph, louvain_seed)
    degrees = dict(graph.degree())
    target = min(int(source_budget), graph.number_of_nodes())

    if method == METHOD_STRUCTURED:
        selected, boundary = choose_structured_sources(graph, partition, source_budget, seed, graph_id, step)
        pool = selected
        source_set_scope = "dynamic_current_gcc"
    elif method == METHOD_RANDOM_SOURCE:
        boundary = boundary_scores(graph, partition)
        nodes = sorted(graph.nodes(), key=str)
        rng = random.Random(stable_seed(seed, graph_id, step, "random-source"))
        selected = rng.sample(nodes, target) if target < len(nodes) else nodes
        pool = selected
        source_set_scope = "dynamic_current_gcc"
    elif method == METHOD_DEGREE_SOURCE:
        boundary = boundary_scores(graph, partition)
        selected = sorted(degrees, key=lambda node: (-degrees[node], str(node)))[:target]
        pool = selected
        source_set_scope = "dynamic_current_gcc"
    elif method == METHOD_FROZEN_SOURCE:
        if "frozen_source_pool" not in state:
            initial_partition = louvain_partition(state["initial_gcc"], louvain_seed)
            pool, _ = choose_structured_sources(state["initial_gcc"], initial_partition, source_budget, seed, graph_id, 0)
            state["frozen_source_pool"] = list(pool)
            state["frozen_source_pool_hash"] = stable_hash(["frozen_initial_pool"] + list(pool))
        boundary = boundary_scores(graph, partition)
        pool = list(state["frozen_source_pool"])
        selected = [node for node in pool if node in graph]
        source_set_scope = "frozen_initial_pool"
    else:
        raise ValueError(method)

    active_count = len(selected)
    boundary_count = sum(1 for node in selected if boundary.get(node, 0) > 0)
    cross_fraction = boundary_count / float(active_count) if active_count else np.nan
    source_hash = state.get("frozen_source_pool_hash")
    if source_hash is None:
        source_hash = stable_hash([source_set_scope, method] + list(pool))
    source_info = {
        "source_policy": method,
        "source_budget": int(source_budget),
        "active_source_count": int(active_count),
        "current_gcc_node_count": int(graph.number_of_nodes()),
        "effective_source_fraction": active_count / float(graph.number_of_nodes()) if graph.number_of_nodes() else np.nan,
        "community_count": int(community_count(partition)),
        "boundary_source_fraction": cross_fraction,
        "cross_community_source_fraction": cross_fraction,
        "source_set_hash": source_hash,
        "source_set_scope": source_set_scope,
        "active_source_hash": stable_hash(selected),
        "louvain_seed": louvain_seed,
        "candidate_node_count": int(graph.number_of_nodes()),
        "candidate_set_scope": "current_gcc_all_nodes",
        "candidate_is_current_gcc": True,
    }
    return selected, source_info


def shared_node_dependencies(graph, sources):
    scores = {node: 0.0 for node in graph.nodes()}
    adjacency = {node: tuple(graph.neighbors(node)) for node in graph.nodes()}
    for source in sources:
        if source not in adjacency:
            continue
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
                delta[v] = delta.get(v, 0.0) + contribution
            if w != source:
                scores[w] = scores.get(w, 0.0) + delta.get(w, 0.0)
    return scores


def sort_nodes_by_score(scores, graph):
    degrees = dict(graph.degree())
    return sorted(scores, key=lambda node: (-scores.get(node, 0.0), -degrees.get(node, 0), str(node)))


def igraph_scores(graph, kind):
    if ig is None:
        return None
    nodes = sorted(graph.nodes(), key=str)
    node_index = {node: idx for idx, node in enumerate(nodes)}
    edges = [(node_index[u], node_index[v]) for u, v in graph.edges()]
    ig_graph = ig.Graph(n=len(nodes), edges=edges, directed=False)
    if kind == "betweenness":
        values = ig_graph.betweenness(directed=False)
    elif kind == "closeness":
        values = ig_graph.closeness(mode="all", normalized=True)
    else:
        raise ValueError(kind)
    return {node: float(values[idx]) for idx, node in enumerate(nodes)}


def choose_node(graph, method, graph_id, step, rng, args, source_budget, run_seed, state):
    if graph.number_of_nodes() == 0:
        return None, {}
    if method in SOURCE_METHODS:
        sources, source_info = choose_source_set(graph, method, source_budget, run_seed, graph_id, step, state)
        scores = shared_node_dependencies(graph, sources)
        return sort_nodes_by_score(scores, graph)[0], source_info
    if method == METHOD_M5:
        scores = igraph_scores(graph, "betweenness") if args.use_igraph else None
        if scores is None:
            scores = nx.betweenness_centrality(graph, normalized=True, weight=None)
        return sort_nodes_by_score(scores, graph)[0], {}
    if method == METHOD_DYNAMIC_DEGREE:
        degrees = dict(graph.degree())
        return sorted(degrees, key=lambda node: (-degrees[node], str(node)))[0], {}
    if method == METHOD_DYNAMIC_CLOSENESS:
        scores = igraph_scores(graph, "closeness") if args.use_igraph else None
        if scores is None:
            scores = nx.closeness_centrality(graph)
        return sort_nodes_by_score(scores, graph)[0], {}
    if method == METHOD_DYNAMIC_KCORE:
        try:
            scores = nx.core_number(graph) if graph.number_of_edges() else {node: 0 for node in graph.nodes()}
        except nx.NetworkXError:
            scores = {node: 0 for node in graph.nodes()}
        return sort_nodes_by_score(scores, graph)[0], {}
    if method == METHOD_RANDOM:
        nodes = sorted(graph.nodes(), key=str)
        return rng.choice(nodes), {}
    raise ValueError(method)


def empty_source_info(source_budget):
    return {
        "source_policy": "none",
        "source_budget": int(source_budget),
        "active_source_count": np.nan,
        "current_gcc_node_count": np.nan,
        "effective_source_fraction": np.nan,
        "community_count": np.nan,
        "boundary_source_fraction": np.nan,
        "cross_community_source_fraction": np.nan,
        "source_set_hash": "",
        "source_set_scope": "none",
        "active_source_hash": "",
        "louvain_seed": np.nan,
        "candidate_node_count": np.nan,
        "candidate_set_scope": "current_gcc_all_nodes",
        "candidate_is_current_gcc": True,
    }


def curve_row(dataset_group, meta, method, seed, source_budget, step, original_n, graph, removed_node="", source_info=None):
    info = source_info if source_info is not None else empty_source_info(source_budget)
    row = {
        "dataset_group": dataset_group,
        "graph_id": meta["graph_id"],
        "graph_name": meta.get("graph_name", meta["graph_id"]),
        "graph_type": meta.get("graph_type", "unknown"),
        "method": method,
        "seed": int(seed),
        "source_budget": int(source_budget),
        "initial_gcc_node_count": int(original_n),
        "removed_nodes": int(step),
        "removed_node": removed_node,
        "remove_ratio": step / float(max(1, original_n)),
        "gcc_ratio": gcc_ratio(graph, original_n),
    }
    row.update(info)
    return row


def summarize_curve(curve, runtime_seconds, status):
    x = curve["remove_ratio"].astype(float).values
    y = curve["gcc_ratio"].astype(float).values
    observed = float(x[-1]) if len(x) else 0.0
    auc = trapezoid_auc(y, x) if len(x) else np.nan
    source_rows = curve[pd.to_numeric(curve["active_source_count"], errors="coerce").notna()].copy()
    source_first = source_rows.iloc[0] if not source_rows.empty else None
    source_policy = str(source_first["source_policy"]) if source_first is not None else "none"
    summary = {
        "dataset_group": curve["dataset_group"].iloc[0],
        "graph_id": curve["graph_id"].iloc[0],
        "graph_name": curve["graph_name"].iloc[0],
        "graph_type": curve["graph_type"].iloc[0],
        "method": curve["method"].iloc[0],
        "seed": int(curve["seed"].iloc[0]),
        "source_budget": int(curve["source_budget"].iloc[0]),
        "source_policy": source_policy,
        "status": status,
        "auc": auc,
        "normalized_auc": auc / observed if observed > 0 else np.nan,
        "observed_remove_ratio": observed,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "runtime_seconds": float(runtime_seconds),
        "current_gcc_node_count": int(source_first["current_gcc_node_count"]) if source_first is not None else int(curve["initial_gcc_node_count"].iloc[0]),
        "active_source_count": int(source_first["active_source_count"]) if source_first is not None else np.nan,
        "effective_source_fraction": float(source_first["effective_source_fraction"]) if source_first is not None else np.nan,
        "community_count": int(source_first["community_count"]) if source_first is not None else np.nan,
        "boundary_source_fraction": float(source_first["boundary_source_fraction"]) if source_first is not None else np.nan,
        "source_set_hash": str(source_first["source_set_hash"]) if source_first is not None else "",
        "source_set_scope": str(source_first["source_set_scope"]) if source_first is not None else "none",
        "removed_nodes": int(curve["removed_nodes"].max()) if len(curve) else 0,
        "remove_ratio_gcc_le_0.5": first_ratio_at_or_below(curve, 0.5),
        "remove_ratio_gcc_le_0.2": first_ratio_at_or_below(curve, 0.2),
        "remove_ratio_gcc_le_0.1": first_ratio_at_or_below(curve, 0.1),
        "mean_effective_source_fraction": pd.to_numeric(curve["effective_source_fraction"], errors="coerce").mean(),
        "mean_boundary_source_fraction": pd.to_numeric(curve["boundary_source_fraction"], errors="coerce").mean(),
        "mean_cross_community_source_fraction": pd.to_numeric(curve["cross_community_source_fraction"], errors="coerce").mean(),
        "mean_active_source_count": pd.to_numeric(curve["active_source_count"], errors="coerce").mean(),
    }
    return summary


def run_one(dataset_group, meta, graph0, method, source_budget, run_seed, args):
    out_root = args.output_dir / "runs" / dataset_group / meta["graph_id"] / safe_name(method) / "B{}".format(source_budget) / "seed{}".format(run_seed)
    summary_path = out_root / "summary.csv"
    curve_path = out_root / "curve.csv"
    if not args.force and summary_path.exists() and curve_path.exists():
        summary = pd.read_csv(summary_path)
        if not summary.empty and str(summary.iloc[0].get("status")) == "finished":
            return summary.iloc[0].to_dict(), pd.read_csv(curve_path)

    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    rng_budget = source_budget if method in SOURCE_METHODS else 0
    rng = random.Random(stable_seed(run_seed, dataset_group, meta["graph_id"], method, rng_budget))
    rows = [curve_row(dataset_group, meta, method, run_seed, source_budget, 0, original_n, graph)]
    state = {"initial_gcc": largest_cc_graph(graph)}
    started = time.perf_counter()
    status = "finished"
    step = 0
    while graph.number_of_nodes() > 0:
        if args.timeout_seconds > 0 and time.perf_counter() - started > args.timeout_seconds:
            status = "timeout"
            break
        h_graph = largest_cc_graph(graph)
        if h_graph.number_of_nodes() == 0:
            break
        node, source_info = choose_node(h_graph, method, meta["graph_id"], step, rng, args, source_budget, run_seed, state)
        if node is None or node not in graph:
            break
        graph.remove_node(node)
        step += 1
        rows.append(curve_row(dataset_group, meta, method, run_seed, source_budget, step, original_n, graph, node, source_info))
        if step >= original_n:
            break
    curve = pd.DataFrame(rows)
    summary = summarize_curve(curve, time.perf_counter() - started, status)
    write_csv(curve, curve_path)
    write_csv(pd.DataFrame([summary]), summary_path)
    return summary, curve


def real_completed_metadata():
    if not REAL_PER_GRAPH.exists():
        return pd.DataFrame()
    df = pd.read_csv(REAL_PER_GRAPH)
    m5 = df[(df["method_label"].eq("M5")) & (df["status"].eq("finished"))].copy()
    if "observed_remove_ratio" in m5:
        m5["observed_remove_ratio"] = pd.to_numeric(m5["observed_remove_ratio"], errors="coerce")
        m5 = m5[m5["observed_remove_ratio"] >= 0.999999]
    columns = ["graph_id", "graph_name", "graph_type", "num_nodes_gcc", "num_edges_gcc", "size_bin"]
    available = [column for column in columns if column in m5.columns]
    metadata = m5[available].drop_duplicates("graph_id", keep="last").copy()
    metadata["cleaned_file"] = metadata["graph_id"].astype(str).map(
        lambda graph_id: str(REAL_CLEANED_DIR / "{}.edges".format(graph_id))
    )
    metadata = metadata[metadata["cleaned_file"].map(lambda p: Path(p).exists())].copy()
    return metadata.sort_values(["num_edges_gcc", "num_nodes_gcc", "graph_id"], na_position="last")


def load_all_graphs(args):
    datasets = {part.strip() for part in args.datasets.split(",") if part.strip()}
    selected_graphs = {part.strip() for part in args.graph_ids.split(",") if part.strip()}
    if "synthetic45" in datasets:
        for graph_id, group in fair.load_synthetic_groups(max_graphs=0):
            if selected_graphs and graph_id not in selected_graphs:
                continue
            graph = fair.reconstruct_synthetic_graph(group)
            meta = fair.synthetic_meta(group)
            yield "synthetic45", meta, graph
    if "realworld_completed" in datasets:
        metadata = real_completed_metadata()
        for _, row in metadata.iterrows():
            meta = row.to_dict()
            if selected_graphs and meta["graph_id"] not in selected_graphs:
                continue
            graph = real40.load_cleaned_graph(Path(meta["cleaned_file"]))
            yield "realworld_completed", meta, graph


def load_smoke_graphs(args):
    synthetic = []
    realworld = []
    old_datasets = args.datasets
    args.datasets = "synthetic45,realworld_completed"
    for dataset_group, meta, graph in load_all_graphs(args):
        if dataset_group == "synthetic45" and len(synthetic) < 2:
            synthetic.append((dataset_group, meta, graph))
        if dataset_group == "realworld_completed" and len(realworld) < 2:
            realworld.append((dataset_group, meta, graph))
        if len(synthetic) == 2 and len(realworld) == 2:
            break
    args.datasets = old_datasets
    return synthetic + realworld


def selected_runs(args, smoke=False):
    methods = parse_methods(args.methods)
    budgets = [32] if smoke else parse_int_list(args.source_budgets)
    seeds = [parse_int_list(args.seeds)[0]] if smoke else parse_int_list(args.seeds)
    graphs = load_smoke_graphs(args) if smoke else list(load_all_graphs(args))
    for dataset_group, meta, graph in graphs:
        for method in methods:
            if method in SOURCE_METHODS:
                for budget in budgets:
                    for run_seed in seeds:
                        yield dataset_group, meta, graph, method, budget, run_seed
            elif method == METHOD_RANDOM:
                for run_seed in seeds:
                    yield dataset_group, meta, graph, method, budgets[0], run_seed
            else:
                for budget in budgets[:1]:
                    for run_seed in seeds[:1]:
                        yield dataset_group, meta, graph, method, budget, run_seed


def run_experiment(args, smoke=False):
    summaries = []
    curves = []
    for dataset_group, meta, graph, method, budget, run_seed in selected_runs(args, smoke=smoke):
        print(
            "loaded {} {} n={} m={} method={} B={} seed={}".format(
                dataset_group, meta["graph_id"], graph.number_of_nodes(), graph.number_of_edges(), method, budget, run_seed
            ),
            flush=True,
        )
        summary, curve = run_one(dataset_group, meta, graph, method, budget, run_seed, args)
        summaries.append(summary)
        curves.append(curve)
        print(
            "node-attack {} {} {} {} auc={:.6f}".format(
                dataset_group, meta["graph_id"], method, summary["status"], float(summary.get("normalized_auc", np.nan))
            ),
            flush=True,
        )
    if summaries:
        prefix = "smoke_" if smoke else "formal_"
        write_csv(pd.DataFrame(summaries), args.output_dir / "{}node_results.csv".format(prefix))
    if curves:
        prefix = "smoke_" if smoke else "formal_"
        write_csv(pd.concat(curves, ignore_index=True, sort=False), args.output_dir / "{}node_curves.csv".format(prefix))


def load_run_results(args):
    rows = []
    curves = []
    for summary_path in (args.output_dir / "runs").rglob("summary.csv"):
        rows.append(pd.read_csv(summary_path))
    for curve_path in (args.output_dir / "runs").rglob("curve.csv"):
        curves.append(pd.read_csv(curve_path))
    per = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    all_curves = pd.concat(curves, ignore_index=True, sort=False) if curves else pd.DataFrame()
    return per, all_curves


def rank_hit_rate(curves, method, m5, fraction):
    method_nodes = list(curves[curves["method"].eq(method)].sort_values("removed_nodes")["removed_node"])
    m5_nodes = list(m5.sort_values("removed_nodes")["removed_node"])
    method_nodes = [node for node in method_nodes if str(node) != "" and str(node).lower() != "nan"]
    m5_nodes = [node for node in m5_nodes if str(node) != "" and str(node).lower() != "nan"]
    k = max(1, int(math.ceil(len(m5_nodes) * fraction)))
    if not method_nodes or not m5_nodes:
        return np.nan
    return len(set(method_nodes[:k]) & set(m5_nodes[:k])) / float(k)


def spearman_with_m5(curves, method, m5):
    method_nodes = [node for node in curves[curves["method"].eq(method)].sort_values("removed_nodes")["removed_node"] if str(node) not in {"", "nan"}]
    m5_nodes = [node for node in m5.sort_values("removed_nodes")["removed_node"] if str(node) not in {"", "nan"}]
    common = sorted(set(method_nodes) & set(m5_nodes), key=str)
    if len(common) < 3:
        return np.nan
    r_method = {node: idx for idx, node in enumerate(method_nodes)}
    r_m5 = {node: idx for idx, node in enumerate(m5_nodes)}
    x = [r_method[node] for node in common]
    y = [r_m5[node] for node in common]
    if scipy_stats is not None:
        return float(scipy_stats.spearmanr(x, y).statistic)
    return float(pd.Series(x).corr(pd.Series(y), method="spearman"))


def add_order_metrics(per, curves):
    if per.empty or curves.empty:
        return per
    rows = []
    for _, row in per.iterrows():
        subset = curves[
            curves["dataset_group"].eq(row["dataset_group"])
            & curves["graph_id"].eq(row["graph_id"])
            & curves["source_budget"].eq(row["source_budget"])
            & curves["seed"].eq(row["seed"])
        ]
        m5 = subset[subset["method"].eq(METHOD_M5)]
        if m5.empty:
            m5 = curves[
                curves["dataset_group"].eq(row["dataset_group"])
                & curves["graph_id"].eq(row["graph_id"])
                & curves["method"].eq(METHOD_M5)
            ]
        rec = row.to_dict()
        if not m5.empty:
            rec["spearman_with_m5"] = spearman_with_m5(subset, row["method"], m5)
            rec["top_1pct_m5_hit_rate"] = rank_hit_rate(subset, row["method"], m5, 0.01)
            rec["top_5pct_m5_hit_rate"] = rank_hit_rate(subset, row["method"], m5, 0.05)
            rec["top_10pct_m5_hit_rate"] = rank_hit_rate(subset, row["method"], m5, 0.10)
        else:
            rec["spearman_with_m5"] = np.nan
            rec["top_1pct_m5_hit_rate"] = np.nan
            rec["top_5pct_m5_hit_rate"] = np.nan
            rec["top_10pct_m5_hit_rate"] = np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def mechanism_metrics(args):
    rows = []
    for dataset_group, meta, graph in load_all_graphs(args):
        graph = largest_cc_graph(graph)
        n = graph.number_of_nodes()
        m = graph.number_of_edges()
        partition = louvain_partition(graph, DEFAULT_LOUVAIN_SEED)
        boundary = boundary_scores(graph, partition)
        degrees = np.array([degree for _, degree in graph.degree()], dtype=float)
        cross_edges = sum(1 for u, v in graph.edges() if partition.get(u) != partition.get(v))
        try:
            modularity = nx.algorithms.community.quality.modularity(
                graph,
                [set(node for node, cid in partition.items() if cid == community) for community in sorted(set(partition.values()))],
            )
        except Exception:
            modularity = np.nan
        try:
            assortativity = nx.degree_assortativity_coefficient(graph)
        except Exception:
            assortativity = np.nan
        rows.append(
            {
                "dataset_group": dataset_group,
                "graph_id": meta["graph_id"],
                "graph_type": meta.get("graph_type", "unknown"),
                "node_count": n,
                "edge_count": m,
                "graph_density": nx.density(graph) if n > 1 else 0.0,
                "louvain_modularity": modularity,
                "community_count": community_count(partition),
                "cross_community_edge_fraction": cross_edges / float(m) if m else np.nan,
                "bridge_node_fraction": sum(1 for value in boundary.values() if value > 0) / float(n) if n else np.nan,
                "degree_heterogeneity": float(np.std(degrees) / np.mean(degrees)) if len(degrees) and np.mean(degrees) else np.nan,
                "clustering_coefficient": nx.average_clustering(graph) if n else np.nan,
                "degree_assortativity": assortativity,
            }
        )
    return pd.DataFrame(rows)


def paired_bootstrap_ci(values, seed=20260513, iterations=5000):
    values = np.array([value for value in values if not pd.isna(value)], dtype=float)
    if len(values) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(iterations):
        sample = rng.choice(values, size=len(values), replace=True)
        means.append(np.mean(sample))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def effect_size(values):
    values = np.array([value for value in values if not pd.isna(value)], dtype=float)
    if len(values) < 2:
        return np.nan
    std = np.std(values, ddof=1)
    return float(np.mean(values) / std) if std > 0 else np.nan


def statistical_tests(per):
    rows = []
    finished = per[per["status"].eq("finished")].copy()
    for dataset_group in sorted(finished["dataset_group"].dropna().unique()):
        for budget in sorted(finished["source_budget"].dropna().unique()):
            subset = finished[(finished["dataset_group"].eq(dataset_group)) & (finished["source_budget"].eq(budget))]
            structured = subset[subset["method"].eq(METHOD_STRUCTURED)]
            for baseline, label in [(METHOD_M5, "delta_auc"), (METHOD_RANDOM_SOURCE, "policy_delta")]:
                base = subset[subset["method"].eq(baseline)]
                if structured.empty or base.empty:
                    continue
                merged = structured.merge(
                    base,
                    on=["dataset_group", "graph_id", "source_budget", "seed"],
                    suffixes=("_structured", "_baseline"),
                )
                if merged.empty and baseline == METHOD_M5:
                    merged = structured.merge(base, on=["dataset_group", "graph_id"], suffixes=("_structured", "_baseline"))
                if merged.empty:
                    continue
                delta = merged["normalized_auc_structured"] - merged["normalized_auc_baseline"]
                ci_low, ci_high = paired_bootstrap_ci(delta)
                if scipy_stats is not None and len(delta.dropna()) > 0:
                    try:
                        wilcoxon_p = float(scipy_stats.wilcoxon(delta.dropna()).pvalue)
                    except Exception:
                        wilcoxon_p = np.nan
                else:
                    wilcoxon_p = np.nan
                rows.append(
                    {
                        "dataset_group": dataset_group,
                        "source_budget": int(budget),
                        "comparison": "{} vs {}".format(METHOD_STRUCTURED, baseline),
                        "delta_definition": label,
                        "n_pairs": int(delta.notna().sum()),
                        "mean_delta": float(delta.mean()),
                        "median_delta": float(delta.median()),
                        "wins": int((delta < -1e-12).sum()),
                        "ties": int((delta.abs() <= 1e-12).sum()),
                        "losses": int((delta > 1e-12).sum()),
                        "wilcoxon_p": wilcoxon_p,
                        "bootstrap_ci95_low": ci_low,
                        "bootstrap_ci95_high": ci_high,
                        "cohen_d_paired": effect_size(delta),
                    }
                )
    return pd.DataFrame(rows)


def aggregate(args, smoke=False, dataset_scope=None, pilot_config=None):
    per, curves = load_run_results(args)
    if dataset_scope:
        per = per[per["dataset_group"].eq(dataset_scope)].copy()
        curves = curves[curves["dataset_group"].eq(dataset_scope)].copy()
    if pilot_config and not smoke:
        per, curves = restrict_pilot_schedule(per, curves, pilot_config, dataset_scope=dataset_scope)
    if per.empty or curves.empty:
        raise RuntimeError("No SASB-N node results available.")
    per = add_order_metrics(per, curves)
    prefix = "smoke_" if smoke else "formal_"
    write_csv(per, args.output_dir / "{}node_results.csv".format(prefix))
    write_csv(curves, args.output_dir / "{}node_curves.csv".format(prefix))
    source_curves = curves[curves["method"].isin(SOURCE_METHODS)].copy()
    if not source_curves.empty:
        write_csv(source_curves, args.output_dir / "{}source_step_metrics.csv".format(prefix))
    if not smoke:
        write_csv(source_policy_ablation(per), args.output_dir / "source_policy_ablation.csv")
        write_csv(source_budget_ablation(per), args.output_dir / "source_budget_ablation.csv")
        write_csv(mechanism_metrics(args), args.output_dir / "node_mechanism_metrics.csv")
        write_csv(statistical_tests(per), args.output_dir / "node_statistical_tests.csv")
        write_report(args, per)
    return per, curves


def source_policy_ablation(per):
    finished = per[per["status"].eq("finished") & per["method"].isin(SOURCE_METHODS)].copy()
    if finished.empty:
        return pd.DataFrame()
    return (
        finished.groupby(["dataset_group", "source_budget", "method"])
        .agg(
            graph_count=("graph_id", "nunique"),
            run_count=("normalized_auc", "size"),
            mean_normalized_auc=("normalized_auc", "mean"),
            median_normalized_auc=("normalized_auc", "median"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            mean_effective_source_fraction=("mean_effective_source_fraction", "mean"),
            mean_boundary_source_fraction=("mean_boundary_source_fraction", "mean"),
        )
        .reset_index()
    )


def source_budget_ablation(per):
    structured = per[per["status"].eq("finished") & per["method"].eq(METHOD_STRUCTURED)].copy()
    if structured.empty:
        return pd.DataFrame()
    return (
        structured.groupby(["dataset_group", "source_budget"])
        .agg(
            graph_count=("graph_id", "nunique"),
            run_count=("normalized_auc", "size"),
            mean_normalized_auc=("normalized_auc", "mean"),
            median_normalized_auc=("normalized_auc", "median"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            mean_boundary_source_fraction=("mean_boundary_source_fraction", "mean"),
        )
        .reset_index()
    )


def write_report(args, per):
    lines = [
        "# SASB-N Formal Node Dismantling Report",
        "",
        "## 1. 科学问题",
        "",
        "SASB-N 检验的是结构化源点采样是否在节点瓦解中产生有条件有益的结构偏差。",
        "",
        "## 2. SASB-N 算法原理",
        "",
        "SASB-N 是节点瓦解版本。每一步只在当前最大连通分量的全部节点中选择一个节点删除。",
        "",
        "## 3. 节点依赖分数公式",
        "",
        "$$",
        "\\widehat{B}_{\\mathcal{S}}(v)=\\frac{|V_t|}{|\\mathcal{S}_t|}\\sum_{s\\in\\mathcal{S}_t}\\delta_s(v)",
        "$$",
        "",
        "$$",
        "v_t=\\underset{v\\in V(\\mathrm{GCC}(G_t))}{\\arg\\max}\\;\\widehat{B}_{\\mathcal{S}_t}(v)",
        "$$",
        "",
        "## 4. 源点策略区别",
        "",
        "structured 使用社区边界、社区代表、节点度和稳定随机补足；random-source 均匀采样；degree-source 按度选择；frozen-source 只在初始 GCC 选择一次 structured 源点。",
        "",
        "## 5. 与 M5 的区别",
        "",
        "M5 是完整动态节点介数基线；SASB-N 使用少量源点近似节点依赖分数。",
        "",
        "## 6. 数据集和实验设置",
        "",
        "正式设置为 synthetic45 的 45 个网络和 realworld_completed 的 28 个网络，预算 B=16,32,64,128，多随机种子。",
        "",
        "## 7. 源点预算实验",
        "",
        "见 source_budget_ablation.csv。",
        "",
        "## 8. 源点策略消融",
        "",
        "见 source_policy_ablation.csv。",
        "",
        "## 9. 多种子统计结果",
        "",
        "见 node_statistical_tests.csv。",
        "",
        "## 10. 网络结构机制分析",
        "",
        "见 node_mechanism_metrics.csv。",
        "",
        "## 11. 运行时间和精度权衡",
        "",
        "运行时间必须与 AUC 和策略差异分开解释。",
        "",
        "## 12. 成功案例",
        "",
        "待正式全量实验后填写。",
        "",
        "## 13. 失败案例",
        "",
        "待正式全量实验后填写。",
        "",
        "## 14. 当前可以写入论文的结论",
        "",
        "可以写入实验定义、对照设置和评价指标。",
        "",
        "## 15. 当前不能写入论文的过度结论",
        "",
        "不能声称 SASB-N 普遍优于 M5，也不能混合 edge 与 node AUC。",
        "",
        "## 16. 局限性",
        "",
        "节点 SASB-N 当前没有原始 edge SASB 的候选边集合；节点候选集合默认是当前 GCC 的全部节点。",
        "",
        "## 17. 下一步实验建议",
        "",
        "先完成 smoke validation，再运行全量正式实验和统计检验。",
    ]
    (args.output_dir / "node_sasb_formal_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def graph_topology_features(dataset_group, meta, graph):
    graph = largest_cc_graph(graph)
    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    partition = louvain_partition(graph, DEFAULT_LOUVAIN_SEED)
    groups = [
        {node for node, community in partition.items() if community == label}
        for label in sorted(set(partition.values()))
    ]
    if edge_count and len(groups) > 1:
        modularity = nx.algorithms.community.quality.modularity(graph, groups)
    else:
        modularity = 0.0
    return {
        "dataset_group": dataset_group,
        "graph_id": str(meta["graph_id"]),
        "graph_name": str(meta.get("graph_name", meta["graph_id"])),
        "graph_type": str(meta.get("graph_type", "unknown")),
        "node_count": int(node_count),
        "edge_count": int(edge_count),
        "graph_density": float(nx.density(graph)) if node_count > 1 else 0.0,
        "louvain_modularity": float(modularity),
        "community_count": int(community_count(partition)),
    }


def select_stratified_pilot_rows(frame, count=12):
    if len(frame) < count:
        raise ValueError("Need at least {} graphs for pilot selection.".format(count))
    selected = frame.copy()
    selected["size_quantile"] = selected["node_count"].rank(method="first", pct=True)
    selected["modularity_quantile"] = selected["louvain_modularity"].rank(method="first", pct=True)
    selected["size_stratum"] = np.minimum(2, np.floor(selected["size_quantile"] * 3).astype(int)) + 1
    selected["modularity_stratum"] = np.minimum(3, np.floor(selected["modularity_quantile"] * 4).astype(int)) + 1
    selected["stratum"] = selected.apply(
        lambda row: "size{}_modularity{}".format(int(row["size_stratum"]), int(row["modularity_stratum"])),
        axis=1,
    )
    available = set(selected.index)
    chosen_indices = []
    targets = []
    for size_bin in range(3):
        for modularity_bin in range(4):
            targets.append(((size_bin + 0.5) / 3.0, (modularity_bin + 0.5) / 4.0))
    for size_target, modularity_target in targets:
        candidates = selected.loc[sorted(available)]
        distances = (
            (candidates["size_quantile"] - size_target).abs()
            + (candidates["modularity_quantile"] - modularity_target).abs()
        )
        best = candidates.assign(_distance=distances).sort_values(
            ["_distance", "graph_id"], kind="mergesort"
        ).index[0]
        chosen_indices.append(best)
        available.remove(best)
    chosen = selected.loc[chosen_indices].copy()
    chosen["selection_rank"] = range(1, len(chosen) + 1)
    return chosen.drop(columns=["_distance"], errors="ignore")


def build_pilot_config(args):
    original_graph_ids = args.graph_ids
    original_datasets = args.datasets
    args.graph_ids = ""
    args.datasets = "synthetic45,realworld_completed"
    feature_rows = []
    for dataset_group, meta, graph in load_all_graphs(args):
        feature_rows.append(graph_topology_features(dataset_group, meta, graph))
    args.graph_ids = original_graph_ids
    args.datasets = original_datasets
    features = pd.DataFrame(feature_rows)
    selected_rows = []
    selection_by_dataset = {}
    for dataset_group in ["synthetic45", "realworld_completed"]:
        group = features[features["dataset_group"].eq(dataset_group)].copy()
        chosen = select_stratified_pilot_rows(group, count=12)
        selection_by_dataset[dataset_group] = {
            "available_network_count": int(len(group)),
            "selected_network_count": int(len(chosen)),
            "stratification": "3 size strata x 4 Louvain-modularity target strata",
            "graph_ids": chosen["graph_id"].tolist(),
            "selected_rows": chosen.to_dict(orient="records"),
        }
        selected_rows.extend(chosen.to_dict(orient="records"))
    config = {
        "experiment_name": "SASB-N node dismantling formal pilot",
        "formal_algorithm_name": "SASB-N",
        "formal_algorithm_full_name": "Structure-Aware Source-sampled Betweenness for Node Dismantling",
        "node_dismantling_version": True,
        "edge_sasb_candidate_set_used": False,
        "node_candidate_set": "all nodes in current GCC",
        "datasets": ["synthetic45", "realworld_completed"],
        "methods": list(METHODS),
        "source_budgets": list(DEFAULT_SOURCE_BUDGETS),
        "seeds": list(DEFAULT_SEEDS),
        "louvain_seed_policy": "fixed to the run seed for each source-selection step",
        "pilot_network_count": 24,
        "network_selection": {
            "rule": "Select by initial GCC node count and fixed-seed Louvain modularity only; SASB AUC and attack results are excluded.",
            "features_used": ["initial_gcc_node_count", "louvain_modularity"],
            "selection_uses_sasb_auc": False,
            "selection_uses_attack_results": False,
            "louvain_seed": int(DEFAULT_LOUVAIN_SEED),
            "strata": "3 size strata x 4 modularity target strata per dataset",
            "per_dataset": selection_by_dataset,
        },
        "selected_networks": selected_rows,
        "baseline_schedule": {
            "M5": "one run per graph at the first source_budget and first seed",
            "dynamic-degree": "one run per graph at the first source_budget and first seed",
            "dynamic-closeness": "one run per graph at the first source_budget and first seed",
            "dynamic-k-core": "one run per graph at the first source_budget and first seed",
            "random": "one run per graph and seed at the first source_budget; source_budget is not an input to random ranking",
        },
        "source_policy_schedule": "four source policies x four budgets x five seeds per graph",
        "pilot_output_dir": "result/node_sasb_paper/pilot",
        "smoke_schedule": {
            "graphs_per_dataset": 2,
            "source_budget": 32,
            "seeds": [int(DEFAULT_SEEDS[0])],
            "purpose": "pipeline validation only; not a scientific result",
        },
        "old_result_boundary": "result/algorithm_summary/node_attack_comparison is read-only and is never used as an output directory",
    }
    write_json(config, PILOT_CONFIG_PATH)
    write_json(config, PILOT_OUT_DIR / "pilot_config.json")
    return config


def load_pilot_config(path=None):
    config_path = Path(path) if path else PILOT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError("Pilot config does not exist: {}".format(config_path))
    return json.loads(config_path.read_text(encoding="utf-8"))


def apply_pilot_config(args, config, smoke=False, dataset_filter=None):
    selected = config["selected_networks"]
    if smoke:
        selected = []
        for dataset_group in ["synthetic45", "realworld_completed"]:
            selected.extend(
                [row for row in config["selected_networks"] if row["dataset_group"] == dataset_group][:2]
            )
    if dataset_filter:
        selected = [row for row in selected if row["dataset_group"] == dataset_filter]
    args.datasets = dataset_filter or ",".join(config["datasets"])
    args.graph_ids = ",".join(row["graph_id"] for row in selected)
    args.methods = ",".join(config["methods"])
    args.source_budgets = "32" if smoke else ",".join(str(value) for value in config["source_budgets"])
    args.seeds = str(config["smoke_schedule"]["seeds"][0]) if smoke else ",".join(str(value) for value in config["seeds"])
    args.output_dir = PILOT_OUT_DIR
    args.pilot_config = config
    args.pilot_selected_networks = selected
    args.pilot_scope = dataset_filter or None


def pilot_statistical_summary(per):
    finished = per[per["status"].eq("finished")].copy()
    if finished.empty:
        return pd.DataFrame()
    rows = []
    for dataset_group in sorted(finished["dataset_group"].dropna().unique()):
        structured_all = finished[
            finished["dataset_group"].eq(dataset_group) & finished["method"].eq(METHOD_STRUCTURED)
        ]
        m5 = finished[finished["dataset_group"].eq(dataset_group) & finished["method"].eq(METHOD_M5)]
        for budget in sorted(structured_all["source_budget"].dropna().unique()):
            structured = (
                structured_all[structured_all["source_budget"].eq(budget)]
                .groupby(["dataset_group", "graph_id", "source_budget"], as_index=False)["normalized_auc"]
                .mean()
                .rename(columns={"normalized_auc": "structured_auc"})
            )
            comparisons = [
                (METHOD_M5, "delta_m5", m5, ["dataset_group", "graph_id"]),
                (METHOD_RANDOM_SOURCE, "delta_policy_random_source", finished, ["dataset_group", "graph_id", "source_budget"]),
                (METHOD_FROZEN_SOURCE, "delta_policy_frozen_source", finished, ["dataset_group", "graph_id", "source_budget"]),
                (METHOD_DEGREE_SOURCE, "delta_policy_degree_source", finished, ["dataset_group", "graph_id", "source_budget"]),
            ]
            for baseline, delta_definition, baseline_frame, merge_keys in comparisons:
                if baseline != METHOD_M5:
                    baseline_frame = baseline_frame[
                        baseline_frame["dataset_group"].eq(dataset_group)
                        & baseline_frame["method"].eq(baseline)
                    ]
                    baseline_frame = (
                        baseline_frame.groupby(merge_keys, as_index=False)["normalized_auc"]
                        .mean()
                        .rename(columns={"normalized_auc": "baseline_auc"})
                    )
                else:
                    baseline_frame = (
                        baseline_frame[baseline_frame["method"].eq(METHOD_M5)]
                        .groupby(merge_keys, as_index=False)["normalized_auc"]
                        .mean()
                        .rename(columns={"normalized_auc": "baseline_auc"})
                    )
                if structured.empty or baseline_frame.empty:
                    continue
                merged = structured.merge(
                    baseline_frame,
                    on=merge_keys,
                )
                if merged.empty:
                    continue
                delta = pd.to_numeric(merged["structured_auc"], errors="coerce") - pd.to_numeric(
                    merged["baseline_auc"], errors="coerce"
                )
                delta = delta.dropna()
                ci_low, ci_high = paired_bootstrap_ci(delta)
                if scipy_stats is not None and len(delta) > 0:
                    try:
                        wilcoxon_p = float(scipy_stats.wilcoxon(delta).pvalue)
                    except Exception:
                        wilcoxon_p = np.nan
                else:
                    wilcoxon_p = np.nan
                rows.append(
                    {
                        "dataset_group": dataset_group,
                        "source_budget": int(budget),
                        "comparison": "{} vs {}".format(METHOD_STRUCTURED, baseline),
                        "delta_definition": delta_definition,
                        "n_pairs": int(len(delta)),
                        "mean_delta": float(delta.mean()) if len(delta) else np.nan,
                        "median_delta": float(delta.median()) if len(delta) else np.nan,
                        "wins": int((delta < -1e-12).sum()),
                        "ties": int((delta.abs() <= 1e-12).sum()),
                        "losses": int((delta > 1e-12).sum()),
                        "wilcoxon_p": wilcoxon_p,
                        "bootstrap_ci95_low": ci_low,
                        "bootstrap_ci95_high": ci_high,
                        "cohen_d_paired": effect_size(delta),
                    }
                )
    return pd.DataFrame(rows)


def restrict_pilot_schedule(per, curves, config, dataset_scope=None):
    dataset_groups = [dataset_scope] if dataset_scope else list(config["datasets"])
    selected_ids = {
        row["graph_id"]
        for row in config["selected_networks"]
        if row["dataset_group"] in dataset_groups
    }
    first_budget = int(config["source_budgets"][0])
    first_seed = int(config["seeds"][0])
    budgets = {int(value) for value in config["source_budgets"]}
    seeds = {int(value) for value in config["seeds"]}

    def allowed(frame):
        base = frame["dataset_group"].isin(dataset_groups) & frame["graph_id"].isin(selected_ids)
        source = frame["method"].isin(SOURCE_METHODS) & frame["source_budget"].isin(budgets) & frame["seed"].isin(seeds)
        random_base = frame["method"].eq(METHOD_RANDOM) & frame["source_budget"].eq(first_budget) & frame["seed"].isin(seeds)
        deterministic = frame["method"].isin(DETERMINISTIC_BASELINE_METHODS) & frame["source_budget"].eq(first_budget) & frame["seed"].eq(first_seed)
        return frame[base & (source | random_base | deterministic)].copy()

    return allowed(per), allowed(curves)


def write_pilot_plot(per, curves, output_dir, filename="pilot_gcc_curves.png"):
    plot_dir = output_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    if curves.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for axis, dataset_group in zip(axes, ["synthetic45", "realworld_completed"]):
        subset = curves[curves["dataset_group"].eq(dataset_group)]
        for method in METHODS:
            method_curves = subset[subset["method"].eq(method)]
            if method_curves.empty:
                continue
            average = method_curves.groupby("remove_ratio", as_index=False)["gcc_ratio"].mean()
            axis.plot(average["remove_ratio"], average["gcc_ratio"], label=method, linewidth=1.5)
        axis.set_title(dataset_group)
        axis.set_xlabel("Removed-node ratio")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Mean GCC ratio")
    handles, labels = axes[-1].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=8)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(plot_dir / filename, dpi=180)
    plt.close(fig)


def estimate_pilot_runtime(config, pilot_results, dataset_scope=None):
    dataset_groups = [dataset_scope] if dataset_scope else list(config["datasets"])
    selected = pd.DataFrame(
        [row for row in config["selected_networks"] if row["dataset_group"] in dataset_groups]
    )
    graph_count = len(selected)
    expected_runs = graph_count * (
        len(SOURCE_METHODS) * len(config["source_budgets"]) * len(config["seeds"])
        + len(config["seeds"])
        + len(DETERMINISTIC_BASELINE_METHODS)
    )
    if pilot_results.empty:
        return {"estimated_runs": expected_runs, "estimated_runtime_seconds": np.nan, "range_seconds": [np.nan, np.nan]}
    target_complexity = selected.assign(complexity=selected["node_count"] * selected["edge_count"])
    target_complexity = target_complexity.groupby("dataset_group")["complexity"].mean()
    smoke_rows = []
    for dataset_group in dataset_groups:
        smoke_rows.extend(
            [row for row in selected.to_dict(orient="records") if row["dataset_group"] == dataset_group][:2]
        )
    smoke_frame = pd.DataFrame(smoke_rows)
    smoke_complexity = smoke_frame.assign(complexity=smoke_frame["node_count"] * smoke_frame["edge_count"]).groupby("dataset_group")["complexity"].mean()
    estimate = 0.0
    method_rows = []
    for method in METHODS:
        method_estimate = 0.0
        for dataset_group in ["synthetic45", "realworld_completed"]:
            observed = pilot_results[
                pilot_results["dataset_group"].eq(dataset_group) & pilot_results["method"].eq(method)
            ]
            if observed.empty:
                continue
            complexity_factor = float(target_complexity[dataset_group] / max(1.0, smoke_complexity[dataset_group]))
            graph_factor = float(
                len(selected[selected["dataset_group"].eq(dataset_group)])
                / max(1, len(smoke_frame[smoke_frame["dataset_group"].eq(dataset_group)]))
            )
            if method in SOURCE_METHODS:
                budget_factor = float(np.mean(config["source_budgets"]) / 32.0)
                seed_factor = float(len(config["seeds"]))
                run_factor = graph_factor * complexity_factor * budget_factor * seed_factor
            elif method == METHOD_RANDOM:
                run_factor = graph_factor * complexity_factor * len(config["seeds"])
            else:
                run_factor = graph_factor * complexity_factor
            method_estimate += float(observed["runtime_seconds"].mean()) * run_factor
        method_rows.append({"method": method, "estimated_runtime_seconds": method_estimate})
        estimate += method_estimate
    return {
        "estimated_runs": int(expected_runs),
        "estimated_runtime_seconds": float(estimate),
        "range_seconds": [float(estimate * 0.5), float(estimate * 2.0)],
        "range_hours": [float(estimate * 0.5 / 3600.0), float(estimate * 2.0 / 3600.0)],
        "method_estimates": method_rows,
        "assumptions": [
            "Uses pilot-smoke runtime by dataset and method as the baseline.",
            "Scales by mean node-count x edge-count complexity and the requested run multiplicity.",
            "This is a planning range, not a benchmark or a guarantee; large M5/dynamic-closeness graphs may dominate the tail.",
        ],
    }


def write_pilot_report(
    config,
    per,
    stats,
    output_dir,
    smoke=False,
    runtime_estimate=None,
    report_name="pilot_report.md",
    dataset_scope=None,
):
    dataset_groups = [dataset_scope] if dataset_scope else list(config["datasets"])
    selected_count = sum(
        1 for row in config["selected_networks"] if row["dataset_group"] in dataset_groups
    )
    expected_source_runs = selected_count * len(SOURCE_METHODS) * len(config["source_budgets"]) * len(config["seeds"])
    expected_runs = selected_count * (
        len(SOURCE_METHODS) * len(config["source_budgets"]) * len(config["seeds"])
        + len(config["seeds"])
        + len(DETERMINISTIC_BASELINE_METHODS)
    )
    complete = len(per) >= expected_runs and per["status"].eq("finished").all()
    status = "pilot_smoke_only" if smoke else ("pilot_complete" if complete else "pilot_incomplete")
    finished = per[per["status"].eq("finished")].copy()

    def fmt(value, digits=4):
        if value is None or pd.isna(value):
            return "NA"
        return "{:.{}f}".format(float(value), digits)

    def markdown_table(headers, rows):
        if not rows:
            return []
        lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
        return lines

    lines = [
        "# SASB-N Node Dismantling Pilot Report",
        "",
        "## 研究状态",
        "",
        "本文件当前状态：`{}`。smoke 验证只用于检查实验管线，不是科学证据。".format(status),
        "本 pilot 是节点 SASB-N 实验，不使用原始 edge SASB 的候选边集合，也不与 edge AUC 混合。",
        "",
        "## 研究问题与定义",
        "",
        "研究问题是：在相同当前 GCC、相同源点预算和相同种子下，结构化源点是否产生有条件有益的结构偏差。",
        "SASB-N-structured 动态选择源点；random-source 均匀采样；degree-source 按当前节点度选择；frozen-source 只在初始 GCC 选择 structured 源点，后续只保留仍存在的源点。",
        "节点候选集合始终是当前最大连通分量的全部节点。",
        "",
        "## 数据和抽样",
        "",
        "本报告覆盖 {}，包含 {} 个 pilot 网络。选网只使用初始 GCC 节点数和固定 seed 的 Louvain 模块度，未使用 SASB AUC 或任何攻击结果。".format(
            ", ".join(dataset_groups), selected_count
        ),
        "完整 pilot 预算为 B=16,32,64,128，种子为 20260513--20260517。M5、dynamic-degree、dynamic-closeness、dynamic-k-core 每网络运行一次；random 每网络每种子运行一次，预算不参与 random 排序。",
        "",
        "## 指标和差值",
        "",
        "`delta_m5 = AUC_SASB - AUC_M5`；`delta_policy = AUC_structured - AUC_random_source`。AUC 越低越好，因此负值表示前者更好。统计汇总见 `pilot_statistical_summary.csv`。",
        "",
        "## 八个决策问题",
        "",
    ]
    if smoke:
        answers = [
            "1. structured 是否比 random-source 稳定？当前不能判断；本文件只有 4 个网络、B=32、1 个种子的 smoke。",
            "2. dynamic-source 是否比 frozen-source 稳定？当前不能判断；需要完整 pilot 的多网络、多预算和多种子配对结果。",
            "3. 64 个源点是否已经足够？当前不能判断；smoke 没有完成预算比较。",
            "4. 128 个源点的额外收益是否值得额外成本？当前不能判断；需要同时比较 AUC 和 runtime。",
            "5. SASB-N 的优势是否只出现在某些网络？当前不能判断；smoke 不允许形成网络机制结论。",
            "6. 是否值得继续运行 73 个网络的全量正式实验？建议先完成 24 网络 pilot，再依据预注册的稳定性和成本规则决定。",
            "7. 正式实验保留哪些 source_budget？当前建议 pilot 保留 16、32、64、128 四档；不提前删掉 64 或 128。",
            "8. 当前结果能否支持论文结论？不能。当前只能支持实验管线通过 smoke 验证，不能支持 SASB-N 有效或优于 M5。",
        ]
    else:
        answers = [
            "1. structured 是否比 random-source 稳定？见 `delta_policy_random_source` 的逐预算 paired 结果；只有跨网络方向稳定且置信区间支持时，才可称为 pilot 支持。",
            "2. dynamic-source 是否比 frozen-source 稳定？这里用 structured 与 frozen-source 的配对差值回答；不能把动态重算的优势写成结构化源点本身的普遍优势。",
            "3. 64 个源点是否已经足够？比较 B=64 与 B=128 的 AUC 差异及其置信区间；若收益接近零，才可把 B=64 视为候选折中点。",
            "4. 128 个源点的额外收益是否值得额外成本？必须同时查看 AUC 改善和 runtime 增长，不能只看 AUC。",
            "5. SASB-N 的优势是否只出现在某些网络？按网络输出 paired delta，并与 `node_mechanism_metrics.csv` 的模块度、桥接节点比例等结构量关联。",
            "6. 是否值得继续运行 73 个网络的全量正式实验？本报告只给出 pilot 级建议；不能因为 pilot 平均值有利就自动批准全量。",
            "7. 正式实验保留哪些 source_budget？由 B=64/128 的收益-成本比较决定；在没有稳定差异前保留四档。",
            "8. 当前结果能否支持论文结论？即使 pilot 完整，也只能支持有条件的 pilot 证据；普遍优于 M5 仍不能写入论文。",
        ]
    lines.extend(["- " + answer for answer in answers])
    if not finished.empty:
        summary = (
            finished.groupby(["method", "source_budget"], dropna=False)
            .agg(
                run_count=("normalized_auc", "size"),
                mean_auc=("normalized_auc", "mean"),
                mean_runtime=("runtime_seconds", "mean"),
            )
            .reset_index()
        )
        summary["method_order"] = summary["method"].map({method: index for index, method in enumerate(METHODS)})
        summary = summary.sort_values(["method_order", "source_budget"])
        lines.extend(
            [
                "",
                "## 数值结果摘要",
                "",
                "下表按已完成运行汇总；random 和确定性基线只显示配置中实际执行的预算。",
                "",
            ]
        )
        summary_rows = []
        for _, row in summary.iterrows():
            summary_rows.append(
                [
                    row["method"],
                    int(row["source_budget"]) if not pd.isna(row["source_budget"]) else "NA",
                    int(row["run_count"]),
                    fmt(row["mean_auc"]),
                    fmt(row["mean_runtime"], 3),
                ]
            )
        lines.extend(markdown_table(["method", "source_budget", "runs", "mean normalized AUC", "mean runtime (s)"], summary_rows))

        source_summary = summary[summary["method"].isin(SOURCE_METHODS)]
        lines.extend(
            [
                "",
                "### Source budget 与效果/成本",
                "",
                "源点策略的 budget 关系如下。AUC 越低越好，runtime 为单次运行的平均值；这张表不把预算增加本身解释成效果改进。",
                "",
            ]
        )
        budget_rows = []
        for _, row in source_summary.iterrows():
            budget_rows.append(
                [
                    row["method"],
                    int(row["source_budget"]),
                    int(row["run_count"]),
                    fmt(row["mean_auc"]),
                    fmt(row["mean_runtime"], 3),
                ]
            )
        lines.extend(markdown_table(["source policy", "budget", "runs", "mean normalized AUC", "mean runtime (s)"], budget_rows))

        if not stats.empty:
            comparison_rows = []
            for _, row in stats.sort_values(["source_budget", "comparison"]).iterrows():
                comparison_rows.append(
                    [
                        int(row["source_budget"]),
                        row["comparison"],
                        int(row["n_pairs"]),
                        fmt(row["mean_delta"]),
                        "{}/{}/{}".format(int(row["wins"]), int(row["ties"]), int(row["losses"])),
                        fmt(row["bootstrap_ci95_low"]),
                        fmt(row["bootstrap_ci95_high"]),
                        fmt(row["wilcoxon_p"], 3),
                    ]
                )
            lines.extend(
                [
                    "",
                    "### 配对差值、胜平负与 bootstrap CI",
                    "",
                    "统计单位是网络：同一网络内先对 5 个 seed 的 normalized AUC 求均值，再进行配对比较。因此 `n_pairs` 是网络数，胜/平/负也是网络级统计；M5 等确定性基线只运行一次。",
                    "",
                ]
            )
            lines.extend(markdown_table(["budget", "comparison", "n_pairs", "mean delta", "wins/ties/losses", "CI low", "CI high", "Wilcoxon p"], comparison_rows))

        lines.extend(
            [
                "",
                "## Pilot-level interpretation",
                "",
                "以下判断只适用于本 pilot 的 24 个网络，不替代完整网络集合上的正式实验。delta<0 表示 structured 的 AUC 更低。",
            ]
        )
        for dataset_group in dataset_groups:
            dataset_stats = stats[stats["dataset_group"].eq(dataset_group)] if not stats.empty else pd.DataFrame()
            dataset_finished = finished[finished["dataset_group"].eq(dataset_group)]
            lines.extend(["", "### {}".format(dataset_group), ""])

            def delta_series(comparison):
                if dataset_stats.empty:
                    return []
                rows_for_comparison = dataset_stats[dataset_stats["comparison"].eq(comparison)].sort_values("source_budget")
                return [
                    "B={}: {:.4f} (W/T/L={}/{}/{})".format(
                        int(row["source_budget"]),
                        float(row["mean_delta"]),
                        int(row["wins"]),
                        int(row["ties"]),
                        int(row["losses"]),
                    )
                    for _, row in rows_for_comparison.iterrows()
                ]

            random_deltas = delta_series("{} vs {}".format(METHOD_STRUCTURED, METHOD_RANDOM_SOURCE))
            m5_deltas = delta_series("{} vs {}".format(METHOD_STRUCTURED, METHOD_M5))
            frozen_deltas = delta_series("{} vs {}".format(METHOD_STRUCTURED, METHOD_FROZEN_SOURCE))
            degree_deltas = delta_series("{} vs {}".format(METHOD_STRUCTURED, METHOD_DEGREE_SOURCE))
            lines.append(
                "- structured vs random-source：{}。这组 delta 的符号决定 structured 是更好还是更差；不能据此写成普遍优势。".format(
                    "; ".join(random_deltas) if random_deltas else "无数据"
                )
            )
            lines.append(
                "- structured vs M5：{}。M5 是完整动态节点介数基线，当前结果只能说明二者的 pilot 差异。".format(
                    "; ".join(m5_deltas) if m5_deltas else "无数据"
                )
            )
            lines.append(
                "- structured vs frozen-source：{}。该比较直接反映动态重新选择源点相对于冻结初始源点的差异。".format(
                    "; ".join(frozen_deltas) if frozen_deltas else "无数据"
                )
            )
            lines.append(
                "- structured vs degree-source：{}。若 CI 跨过 0，应视为未分出稳定差异。".format(
                    "; ".join(degree_deltas) if degree_deltas else "无数据"
                )
            )

            budget_frame = (
                dataset_finished[dataset_finished["method"].eq(METHOD_STRUCTURED)]
                .groupby("source_budget", as_index=False)
                .agg(mean_auc=("normalized_auc", "mean"), mean_runtime=("runtime_seconds", "mean"))
            )
            budget_frame = budget_frame.set_index("source_budget")
            if 64 in budget_frame.index and 128 in budget_frame.index:
                auc64 = float(budget_frame.loc[64, "mean_auc"])
                auc128 = float(budget_frame.loc[128, "mean_auc"])
                runtime64 = float(budget_frame.loc[64, "mean_runtime"])
                runtime128 = float(budget_frame.loc[128, "mean_runtime"])
                runtime_change = 100.0 * (runtime128 / runtime64 - 1.0) if runtime64 else np.nan
                lines.append(
                    "- B=64 与 B=128：structured 平均 AUC 为 {:.4f} -> {:.4f}，平均 runtime 为 {:.3f}s -> {:.3f}s（runtime 变化 {:.1f}%）。因此 B=64 可作为成本-效果候选，B=128 更适合作为敏感性档位；这不能证明 B=64 在所有网络上已经足够。".format(
                        auc64, auc128, runtime64, runtime128, runtime_change
                    )
                )
            else:
                lines.append("- B=64 与 B=128：数据不足，不能判断额外收益是否值得成本。")
            lines.append(
                "- full experiment 决策：pilot 只能用于决定是否值得继续以及优先保留哪些 budget；不能把本 pilot 的平均差异写成 SASB-N 普遍优于 M5，也不能事后按 AUC 筛选网络。"
            )

        total_runtime = pd.to_numeric(finished["runtime_seconds"], errors="coerce").sum()
        nan_auc = int(pd.to_numeric(per["normalized_auc"], errors="coerce").isna().sum())
        nan_runtime = int(pd.to_numeric(per["runtime_seconds"], errors="coerce").isna().sum())
        unfinished = int((~per["status"].eq("finished")).sum())
        lines.extend(
            [
                "",
                "### 完整性与运行时间",
                "",
                "完成记录：{} / {}；unfinished：{}；normalized_auc NaN：{}；runtime_seconds NaN：{}。".format(
                    len(finished), expected_runs, unfinished, nan_auc, nan_runtime
                ),
                "已完成运行的 runtime_seconds 累计为 {:.3f} 秒；该值是各运行 CPU/算法计时之和，不等同于并行作业的墙钟时间。".format(
                    float(total_runtime)
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## 运行量和成本",
            "",
            "本报告范围预计运行 {} 条记录：source policies {} 条，random {} 条，确定性基线 {} 条。".format(
                expected_runs,
                expected_source_runs,
                selected_count * len(config["seeds"]),
                selected_count * len(DETERMINISTIC_BASELINE_METHODS),
            ),
            "断点目录按 `dataset_group/graph_id/method/B{source_budget}/seed{seed}` 组织，已完成且 status=finished 的运行会复用，不会覆盖旧的 edge/node 结果目录。",
        ]
    )
    if runtime_estimate:
        lines.extend(
            [
                "预计运行时间约为 {:.2f}--{:.2f} 小时（规划区间，不是实测保证）。".format(
                    runtime_estimate["range_hours"][0], runtime_estimate["range_hours"][1]
                ),
                "估计假设和分方法明细见 `pilot_runtime_estimate.json`。",
            ]
        )
    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "本 pilot 不删除失败网络，不按 SASB AUC 事后筛选主要证据，不把 runtime 下降写成瓦解效果提升。任何论文结论都必须基于完整网络集合、逐网络配对差值和统计检验。",
        ]
    )
    (output_dir / report_name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pilot_artifacts(config, per, curves, output_dir, smoke=False, artifact_prefix="pilot", dataset_scope=None):
    stats = pilot_statistical_summary(per)
    write_csv(per, output_dir / "{}_results.csv".format(artifact_prefix))
    write_csv(curves, output_dir / "{}_curves.csv".format(artifact_prefix))
    write_csv(curves[curves["method"].isin(SOURCE_METHODS)], output_dir / "{}_source_step_metrics.csv".format(artifact_prefix))
    write_csv(stats, output_dir / "{}_statistical_summary.csv".format(artifact_prefix))
    write_pilot_plot(per, curves, output_dir, filename="{}_gcc_curves.png".format(artifact_prefix))
    estimate = estimate_pilot_runtime(config, per, dataset_scope=dataset_scope)
    write_json(estimate, output_dir / "{}_runtime_estimate.json".format(artifact_prefix))
    write_pilot_report(
        config,
        per,
        stats,
        output_dir,
        smoke=smoke,
        runtime_estimate=estimate,
        report_name="{}_report.md".format(artifact_prefix),
        dataset_scope=dataset_scope,
    )
    return stats, estimate


def validate_pilot_smoke(args, config):
    checks = validate_smoke(args)
    per = pd.read_csv(args.output_dir / "pilot_results.csv")
    expected_methods = set(config["methods"])
    checks["pilot_smoke_selected_graph_count"] = bool(per["graph_id"].nunique() == 4)
    checks["pilot_smoke_expected_run_count"] = bool(len(per) == 4 * len(expected_methods))
    checks["pilot_smoke_methods_complete"] = bool(set(per["method"].unique()) == expected_methods)
    checks["pilot_smoke_passed"] = bool(all(checks.values()))
    write_json(checks, args.output_dir / "pilot_smoke_validation.json")
    return checks


def validate_smoke(args):
    per = pd.read_csv(args.output_dir / "smoke_node_results.csv")
    curves = pd.read_csv(args.output_dir / "smoke_node_curves.csv")
    source_curves = curves[curves["method"].isin(SOURCE_METHODS) & (curves["removed_nodes"] > 0)].copy()
    checks = {
        "all_methods_finished": bool(per["status"].eq("finished").all()),
        "required_fields_present": all(
            field in curves.columns
            for field in [
                "source_budget",
                "active_source_count",
                "current_gcc_node_count",
                "effective_source_fraction",
                "community_count",
                "boundary_source_fraction",
                "source_set_hash",
                "source_set_scope",
                "source_policy",
                "louvain_seed",
                "candidate_node_count",
                "candidate_set_scope",
                "candidate_is_current_gcc",
            ]
        ),
        "auc_runtime_gcc_no_nan": bool(
            per["normalized_auc"].notna().all()
            and per["runtime_seconds"].notna().all()
            and curves["gcc_ratio"].notna().all()
        ),
        "candidate_set_is_current_gcc": bool(
            curves["candidate_is_current_gcc"].fillna(True).astype(bool).all()
            and curves["candidate_set_scope"].fillna("current_gcc_all_nodes").eq("current_gcc_all_nodes").all()
        ),
    }
    if not source_curves.empty:
        non_frozen = source_curves[source_curves["method"].isin([METHOD_STRUCTURED, METHOD_RANDOM_SOURCE, METHOD_DEGREE_SOURCE])]
        checks["non_frozen_source_count_correct"] = bool(
            (
                non_frozen["active_source_count"].astype(float)
                == non_frozen[["source_budget", "current_gcc_node_count"]].min(axis=1).astype(float)
            ).all()
        )
        frozen = source_curves[source_curves["method"].eq(METHOD_FROZEN_SOURCE)]
        checks["frozen_source_not_regenerated"] = bool(
            frozen.groupby(["dataset_group", "graph_id", "source_budget", "seed"])["source_set_hash"].nunique().le(1).all()
        )
        checks["source_hash_scope_is_explicit"] = bool(
            non_frozen["source_set_scope"].eq("dynamic_current_gcc").all()
            and frozen["source_set_scope"].eq("frozen_initial_pool").all()
            and frozen["source_set_hash"].notna().all()
            and frozen["source_set_hash"].ne("").all()
        )
        checks["frozen_active_source_count_not_above_budget_or_gcc"] = bool(
            (
                frozen["active_source_count"].astype(float)
                <= frozen[["source_budget", "current_gcc_node_count"]].min(axis=1).astype(float)
            ).all()
        )
    else:
        checks["non_frozen_source_count_correct"] = False
        checks["frozen_source_not_regenerated"] = False
        checks["source_hash_scope_is_explicit"] = False
        checks["frozen_active_source_count_not_above_budget_or_gcc"] = False
    checks["smoke_passed"] = all(checks.values())
    write_json(checks, args.output_dir / "smoke_validation.json")
    return checks


def write_config(args):
    config = {
        "formal_algorithm_name": "SASB-N",
        "formal_algorithm_full_name": "Structure-Aware Source-sampled Betweenness for Node Dismantling",
        "node_dismantling_version": True,
        "edge_sasb_candidate_set_used": False,
        "node_candidate_set": "all nodes in current GCC",
        "datasets": parse_list(args.datasets),
        "methods": parse_methods(args.methods),
        "source_budgets": parse_int_list(args.source_budgets),
        "seeds": parse_int_list(args.seeds),
        "louvain_seed_policy": "fixed to the run seed for each source-selection step",
        "use_igraph": bool(args.use_igraph),
    }
    write_json(config, args.output_dir / "experiment_config.json")


def parse_args():
    parser = argparse.ArgumentParser(description="Run SASB-N node dismantling experiments.")
    parser.add_argument(
        "--stage",
        choices=["smoke", "run", "aggregate", "all", "pilot-config", "pilot-smoke", "pilot-run", "pilot-aggregate"],
        default="smoke",
    )
    parser.add_argument("--datasets", default="synthetic45,realworld_completed")
    parser.add_argument("--graph-ids", default="")
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--source-budgets", default=",".join(str(value) for value in DEFAULT_SOURCE_BUDGETS))
    parser.add_argument("--seeds", default=",".join(str(value) for value in DEFAULT_SEEDS))
    parser.add_argument("--timeout-seconds", type=float, default=0.0)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--pilot-config", type=Path, default=PILOT_CONFIG_PATH)
    parser.add_argument("--pilot-dataset", choices=["synthetic45", "realworld_completed"], default="")
    parser.add_argument("--use-igraph", action="store_true", default=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.stage == "pilot-config":
        config = build_pilot_config(args)
        print(
            "pilot config written: {} ({} networks)".format(
                PILOT_CONFIG_PATH, len(config["selected_networks"])
            ),
            flush=True,
        )
        return
    if args.stage in {"pilot-smoke", "pilot-run", "pilot-aggregate"}:
        config = load_pilot_config(args.pilot_config)
        apply_pilot_config(
            args,
            config,
            smoke=args.stage == "pilot-smoke",
            dataset_filter=args.pilot_dataset or None,
        )
    args.output_dir = Path(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "plots").mkdir(parents=True, exist_ok=True)
    if args.stage not in {"pilot-smoke", "pilot-run", "pilot-aggregate"}:
        write_config(args)
    if args.stage == "smoke":
        run_experiment(args, smoke=True)
        aggregate(args, smoke=True)
        checks = validate_smoke(args)
        print("smoke validation: {}".format("passed" if checks["smoke_passed"] else "failed"), flush=True)
    elif args.stage == "run":
        run_experiment(args, smoke=False)
    elif args.stage == "aggregate":
        aggregate(args, smoke=False)
    elif args.stage == "all":
        run_experiment(args, smoke=False)
        aggregate(args, smoke=False)
    elif args.stage == "pilot-smoke":
        run_experiment(args, smoke=True)
        per, curves = aggregate(args, smoke=True)
        write_pilot_artifacts(config, per, curves, args.output_dir, smoke=True)
        checks = validate_pilot_smoke(args, config)
        print("pilot smoke validation: {}".format("passed" if checks["pilot_smoke_passed"] else "failed"), flush=True)
    elif args.stage == "pilot-run":
        run_experiment(args, smoke=False)
    elif args.stage == "pilot-aggregate":
        per, curves = aggregate(
            args,
            smoke=False,
            dataset_scope=args.pilot_dataset or None,
            pilot_config=config,
        )
        artifact_prefix = "{}_pilot".format(args.pilot_dataset) if args.pilot_dataset else "pilot"
        write_pilot_artifacts(
            config,
            per,
            curves,
            args.output_dir,
            smoke=False,
            artifact_prefix=artifact_prefix,
            dataset_scope=args.pilot_dataset or None,
        )
    print("SASB-N node comparison complete: {}".format(args.output_dir), flush=True)


if __name__ == "__main__":
    main()
