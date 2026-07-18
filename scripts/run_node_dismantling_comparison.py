from pathlib import Path
from collections import deque
import argparse
import hashlib
import math
import random
import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

import evaluate_next_stage_fair_comparison as fair
import evaluate_m18_candidate as m18
import evaluate_m19_realworld_40plus as real40

try:
    import igraph as ig
except Exception:
    ig = None


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "result" / "algorithm_summary" / "node_attack_comparison"
PLOT_DIR = ROOT / "result" / "algorithm_summary" / "plots"
REAL_PER_GRAPH = ROOT / "result" / "paper_experiments" / "baselines" / "baseline_realworld_m5_completed_per_graph.csv"
REAL_CLEANED_DIR = ROOT / "data" / "realnetworks_40plus" / "cleaned"
SEED = 20260513

METHOD_SASB = "SASB"
METHOD_M5 = "M5"
METHOD_DYNAMIC_DEGREE = "dynamic-degree"
METHOD_DYNAMIC_CLOSENESS = "dynamic-closeness"
METHOD_RANDOM = "random"
METHOD_DYNAMIC_KCORE = "dynamic-k-core"
METHODS = [
    METHOD_SASB,
    METHOD_M5,
    METHOD_DYNAMIC_DEGREE,
    METHOD_DYNAMIC_CLOSENESS,
    METHOD_RANDOM,
    METHOD_DYNAMIC_KCORE,
]


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp, index=False, encoding="utf-8-sig")
    temp.replace(path)


def stable_seed(*parts):
    text = "|".join(str(part) for part in (SEED,) + parts).encode("utf-8")
    return int(hashlib.sha256(text).hexdigest()[:8], 16)


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


def summarize_curve(curve, runtime_seconds, status):
    x = curve["remove_ratio"].astype(float).values
    y = curve["gcc_ratio"].astype(float).values
    observed = float(x[-1]) if len(x) else 0.0
    auc = float(np.trapz(y, x)) if len(x) else np.nan
    return {
        "dataset_group": curve["dataset_group"].iloc[0],
        "graph_id": curve["graph_id"].iloc[0],
        "graph_name": curve["graph_name"].iloc[0],
        "graph_type": curve["graph_type"].iloc[0],
        "method": curve["method"].iloc[0],
        "status": status,
        "auc": auc,
        "normalized_auc": auc / observed if observed > 0 else np.nan,
        "observed_remove_ratio": observed,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "runtime_seconds": float(runtime_seconds),
        "removed_nodes": int(curve["removed_nodes"].max()) if len(curve) else 0,
        "remove_ratio_gcc_le_0.5": first_ratio_at_or_below(curve, 0.5),
        "remove_ratio_gcc_le_0.2": first_ratio_at_or_below(curve, 0.2),
        "remove_ratio_gcc_le_0.1": first_ratio_at_or_below(curve, 0.1),
    }


def curve_row(dataset_group, meta, method, step, original_n, graph):
    return {
        "dataset_group": dataset_group,
        "graph_id": meta["graph_id"],
        "graph_name": meta.get("graph_name", meta["graph_id"]),
        "graph_type": meta.get("graph_type", "unknown"),
        "method": method,
        "removed_nodes": int(step),
        "remove_ratio": step / float(max(1, original_n)),
        "gcc_ratio": gcc_ratio(graph, original_n),
    }


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


def boundary_scores(graph, partition):
    scores = {node: 0 for node in graph.nodes()}
    if not partition:
        return scores
    for node in graph.nodes():
        community = partition.get(node)
        scores[node] = sum(1 for nbr in graph.neighbors(node) if partition.get(nbr) != community)
    return scores


def choose_sasb_node(graph, graph_id, step, args):
    degrees = dict(graph.degree())
    nodes = list(graph.nodes())
    if not nodes:
        return None
    try:
        partition = m18.m17.louvain_partition(graph)
    except Exception:
        partition = {}
    boundary = boundary_scores(graph, partition)
    selected = []
    selected_set = set()

    def add(node):
        if node in graph and node not in selected_set:
            selected.append(node)
            selected_set.add(node)

    for node, _ in sorted(boundary.items(), key=lambda item: (-item[1], -degrees.get(item[0], 0), str(item[0]))):
        if len(selected) >= args.sasb_sources:
            break
        add(node)
    if len(selected) < args.sasb_sources and partition:
        communities = {}
        for node, community in partition.items():
            if node in graph:
                communities.setdefault(community, []).append(node)
        for community_nodes in sorted(communities.values(), key=lambda xs: (-len(xs), str(min(xs)))):
            if len(selected) >= args.sasb_sources:
                break
            representative = max(community_nodes, key=lambda node: (degrees.get(node, 0), boundary.get(node, 0), str(node)))
            add(representative)
    for node, _ in sorted(degrees.items(), key=lambda item: (-item[1], str(item[0]))):
        if len(selected) >= args.sasb_sources:
            break
        add(node)
    rng = random.Random(stable_seed(graph_id, step, "sasb_fill"))
    shuffled = list(nodes)
    rng.shuffle(shuffled)
    for node in shuffled:
        if len(selected) >= min(args.sasb_sources, len(nodes)):
            break
        add(node)

    scores = shared_node_dependencies(graph, selected)
    return sort_nodes_by_score(scores, graph)[0]


def choose_node(graph, method, graph_id, step, rng, args):
    if graph.number_of_nodes() == 0:
        return None
    if method == METHOD_SASB:
        return choose_sasb_node(graph, graph_id, step, args)
    if method == METHOD_M5:
        scores = igraph_scores(graph, "betweenness") if args.use_igraph else None
        if scores is None:
            scores = nx.betweenness_centrality(graph, normalized=True, weight=None)
        return sort_nodes_by_score(scores, graph)[0]
    if method == METHOD_DYNAMIC_DEGREE:
        degrees = dict(graph.degree())
        return sorted(degrees, key=lambda node: (-degrees[node], str(node)))[0]
    if method == METHOD_DYNAMIC_CLOSENESS:
        scores = igraph_scores(graph, "closeness") if args.use_igraph else None
        if scores is None:
            scores = nx.closeness_centrality(graph)
        return sort_nodes_by_score(scores, graph)[0]
    if method == METHOD_RANDOM:
        nodes = sorted(graph.nodes(), key=str)
        return rng.choice(nodes)
    if method == METHOD_DYNAMIC_KCORE:
        try:
            scores = nx.core_number(graph) if graph.number_of_edges() else {node: 0 for node in graph.nodes()}
        except nx.NetworkXError:
            scores = {node: 0 for node in graph.nodes()}
        return sort_nodes_by_score(scores, graph)[0]
    raise ValueError(method)


def run_one(dataset_group, meta, graph0, method, args):
    out_root = OUT_DIR / "runs" / dataset_group / meta["graph_id"] / method
    summary_path = out_root / "summary.csv"
    curve_path = out_root / "curve.csv"
    if not args.force and summary_path.exists() and curve_path.exists():
        summary = pd.read_csv(summary_path)
        if not summary.empty and str(summary.iloc[0].get("status")) == "finished":
            return summary.iloc[0].to_dict(), pd.read_csv(curve_path)

    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    rng = random.Random(stable_seed(dataset_group, meta["graph_id"], method))
    rows = [curve_row(dataset_group, meta, method, 0, original_n, graph)]
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
        node = choose_node(h_graph, method, meta["graph_id"], step, rng, args)
        if node is None or node not in graph:
            break
        graph.remove_node(node)
        step += 1
        rows.append(curve_row(dataset_group, meta, method, step, original_n, graph))
        if step >= original_n:
            break
    curve = pd.DataFrame(rows)
    summary = summarize_curve(curve, time.perf_counter() - started, status)
    write_csv(curve, curve_path)
    write_csv(pd.DataFrame([summary]), summary_path)
    return summary, curve


def real_completed_ids():
    if not REAL_PER_GRAPH.exists():
        return []
    df = pd.read_csv(REAL_PER_GRAPH)
    m5 = df[(df["method_label"].eq("M5")) & (df["status"].eq("finished"))].copy()
    if "observed_remove_ratio" in m5:
        m5["observed_remove_ratio"] = pd.to_numeric(m5["observed_remove_ratio"], errors="coerce")
        m5 = m5[m5["observed_remove_ratio"] >= 0.999999]
    return sorted(m5["graph_id"].dropna().unique())


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


def load_graphs(args):
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


def run_experiment(args):
    summaries = []
    curves = []
    methods = [part.strip() for part in args.methods.split(",") if part.strip()]
    if not methods:
        methods = METHODS
    for dataset_group, meta, graph in load_graphs(args):
        print("loaded {} {} n={} m={}".format(dataset_group, meta["graph_id"], graph.number_of_nodes(), graph.number_of_edges()), flush=True)
        for method in methods:
            if method not in METHODS:
                raise ValueError("unknown method: {}".format(method))
            summary, curve = run_one(dataset_group, meta, graph, method, args)
            summaries.append(summary)
            curves.append(curve)
            print("node-attack {} {} {} {} auc={:.6f}".format(dataset_group, meta["graph_id"], method, summary["status"], float(summary.get("normalized_auc", np.nan))), flush=True)
    if summaries:
        write_csv(pd.DataFrame(summaries), OUT_DIR / "node_attack_per_graph.csv")
    if curves:
        write_csv(pd.concat(curves, ignore_index=True, sort=False), OUT_DIR / "node_attack_curves.csv")


def load_results():
    per_path = OUT_DIR / "node_attack_per_graph.csv"
    curve_path = OUT_DIR / "node_attack_curves.csv"
    per = pd.read_csv(per_path) if per_path.exists() else pd.DataFrame()
    curves = pd.read_csv(curve_path) if curve_path.exists() else pd.DataFrame()
    return per, curves


def aggregate(args):
    rows = []
    curves = []
    for summary_path in (OUT_DIR / "runs").rglob("summary.csv"):
        rows.append(pd.read_csv(summary_path))
    for curve_path in (OUT_DIR / "runs").rglob("curve.csv"):
        curves.append(pd.read_csv(curve_path))
    if rows:
        write_csv(pd.concat(rows, ignore_index=True, sort=False), OUT_DIR / "node_attack_per_graph.csv")
    if curves:
        write_csv(pd.concat(curves, ignore_index=True, sort=False), OUT_DIR / "node_attack_curves.csv")
    per, all_curves = load_results()
    if per.empty or all_curves.empty:
        raise RuntimeError("No node attack results available.")
    per["normalized_auc"] = pd.to_numeric(per["normalized_auc"], errors="coerce")
    finished = per[per["status"].eq("finished")].copy()
    method_summary = (
        finished.groupby(["dataset_group", "method"])
        .agg(
            {
                "graph_id": pd.Series.nunique,
                "normalized_auc": ["mean", "median"],
                "runtime_seconds": "mean",
            }
        )
        .reset_index()
    )
    method_summary.columns = [
        "dataset_group",
        "method",
        "graph_count",
        "mean_normalized_auc",
        "median_normalized_auc",
        "mean_runtime_seconds",
    ]
    method_summary = method_summary.sort_values(["dataset_group", "mean_normalized_auc"])
    write_csv(method_summary, OUT_DIR / "node_attack_method_summary.csv")

    best_rows = []
    for (dataset_group, graph_id), group in finished.groupby(["dataset_group", "graph_id"]):
        if set(METHODS).issubset(set(group["method"])):
            min_auc = group["normalized_auc"].min()
            sasb = group[group["method"].eq(METHOD_SASB)]
            if not sasb.empty and abs(float(sasb["normalized_auc"].iloc[0]) - float(min_auc)) < 1e-12:
                best_rows.append(sasb.iloc[0].to_dict())
    best = pd.DataFrame(best_rows)
    write_csv(best, OUT_DIR / "sasb_best_networks.csv")
    plot_best_networks(best, all_curves)


def plot_best_networks(best, curves):
    for old in PLOT_DIR.glob("node_sasb_best_gcc_curve_*.png"):
        old.unlink()
    if best.empty:
        return
    colors = {
        METHOD_SASB: "#ff7f0e",
        METHOD_M5: "#1f77b4",
        METHOD_DYNAMIC_DEGREE: "#2ca02c",
        METHOD_DYNAMIC_CLOSENESS: "#9467bd",
        METHOD_RANDOM: "#d62728",
        METHOD_DYNAMIC_KCORE: "#8c564b",
    }
    manifest_rows = []
    for row in best.sort_values(["dataset_group", "graph_id"]).itertuples(index=False):
        subset = curves[(curves["dataset_group"].eq(row.dataset_group)) & (curves["graph_id"].eq(row.graph_id))].copy()
        if subset.empty:
            continue
        fig, ax = plt.subplots(figsize=(8.2, 5.2), dpi=160)
        for method in METHODS:
            c = subset[subset["method"].eq(method)].sort_values("remove_ratio")
            if c.empty:
                continue
            auc = best_auc_label(curves, row.dataset_group, row.graph_id, method)
            ax.plot(
                c["remove_ratio"],
                c["gcc_ratio"],
                label="{} (AUC={:.4f})".format(method, auc) if not np.isnan(auc) else method,
                color=colors.get(method),
                linewidth=2.6 if method in {METHOD_SASB, METHOD_M5} else 1.8,
                alpha=1.0 if method in {METHOD_SASB, METHOD_M5} else 0.85,
            )
        ax.set_title("{} / {} ({})".format(row.dataset_group, row.graph_id, row.graph_type))
        ax.set_xlabel("Removed-node ratio")
        ax.set_ylabel("GCC ratio")
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.28)
        ax.legend(fontsize=7.5, loc="best", frameon=True)
        fig.tight_layout()
        name = "node_sasb_best_gcc_curve_{}_{}.png".format(safe_name(row.dataset_group), safe_name(row.graph_id))
        fig.savefig(PLOT_DIR / name)
        plt.close(fig)
        manifest_rows.append(
            {
                "dataset_group": row.dataset_group,
                "graph_id": row.graph_id,
                "graph_type": row.graph_type,
                "sasb_normalized_auc": row.normalized_auc,
                "plot_file": name,
            }
        )
    write_csv(pd.DataFrame(manifest_rows), PLOT_DIR / "node_sasb_best_gcc_curve_manifest.csv")


def best_auc_label(curves, dataset_group, graph_id, method):
    c = curves[(curves["dataset_group"].eq(dataset_group)) & (curves["graph_id"].eq(graph_id)) & (curves["method"].eq(method))].sort_values("remove_ratio")
    if c.empty:
        return np.nan
    x = c["remove_ratio"].astype(float).values
    y = c["gcc_ratio"].astype(float).values
    observed = float(x[-1]) if len(x) else 0.0
    auc = float(np.trapz(y, x)) if len(x) else np.nan
    return auc / observed if observed > 0 else np.nan


def safe_name(text):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(text))


def parse_args():
    parser = argparse.ArgumentParser(description="Run dynamic node-removal attacks and export SASB-best GCC curves.")
    parser.add_argument("--stage", choices=["run", "aggregate", "all"], default="all")
    parser.add_argument("--datasets", default="synthetic45,realworld_completed")
    parser.add_argument("--graph-ids", default="")
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--timeout-seconds", type=float, default=0.0)
    parser.add_argument("--sasb-sources", type=int, default=64)
    parser.add_argument("--use-igraph", action="store_true", default=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    if args.stage in {"run", "all"}:
        run_experiment(args)
    if args.stage in {"aggregate", "all"}:
        aggregate(args)
    print("node attack comparison complete: {}".format(OUT_DIR), flush=True)


if __name__ == "__main__":
    main()
