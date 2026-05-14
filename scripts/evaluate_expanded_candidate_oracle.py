from pathlib import Path
import argparse
import json

import community as community_louvain
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ml_attack_dataset"
OUT_DIR = ROOT / "result" / "expanded_candidate_oracle"
SEED = 20260513

BASELINE_METHODS = [
    "M2 dynamic degree product",
    "M4 dynamic community internal / pair",
    "M5 dynamic edge betweenness",
    "M7 dynamic community size / pair",
    "M8 dynamic community bridge-degree",
]
COMMUNITY_METHODS = {
    "M4 dynamic community internal / pair": "m4",
    "M7 dynamic community size / pair": "m7",
    "M8 dynamic community bridge-degree": "m8",
}
ORACLE_TIE_METHOD_ORDER = [
    "M5 dynamic edge betweenness",
    "M4 dynamic community internal / pair",
    "M7 dynamic community size / pair",
    "M8 dynamic community bridge-degree",
    "M2 dynamic degree product",
]
THRESHOLDS = [0.5, 0.2, 0.1]


def read_split(name):
    return pd.read_csv(DATA_DIR / f"edge_features_{name}.csv")


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
    return largest_cc_subgraph(graph).number_of_nodes() / float(original_n)


def top_degree_product_edges(h_graph, top_k):
    if h_graph.number_of_edges() == 0:
        return []
    degrees = dict(h_graph.degree())
    candidates = [
        (degrees[u] * degrees[v], edge_sort_key((u, v)))
        for u, v in h_graph.edges()
    ]
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [(edge, score) for score, edge in candidates[:top_k]]


def top_betweenness_edges(h_graph, top_k):
    if h_graph.number_of_edges() == 0:
        return []
    betweenness = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
    candidates = [
        (score, edge_sort_key(edge))
        for edge, score in betweenness.items()
    ]
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [(edge, score) for score, edge in candidates[:top_k]]


def top_community_edges(h_graph, top_k):
    if h_graph.number_of_edges() == 0:
        return {method: [] for method in COMMUNITY_METHODS}

    partition = community_louvain.best_partition(h_graph, random_state=SEED)
    communities = {}
    for node, community_id in partition.items():
        communities.setdefault(community_id, set()).add(node)

    if len(communities) < 2:
        fallback = top_degree_product_edges(h_graph, top_k)
        return {method: fallback for method in COMMUNITY_METHODS}

    ordered_communities = sorted(
        communities.values(), key=lambda nodes: (-len(nodes), min(nodes))
    )
    node_to_comm = {}
    comm_sizes = []
    for cid, nodes in enumerate(ordered_communities):
        comm_sizes.append(len(nodes))
        for node in nodes:
            node_to_comm[node] = cid

    internal_edges = [0] * len(ordered_communities)
    inter_counts = {}
    for u, v in h_graph.edges():
        cu = node_to_comm[u]
        cv = node_to_comm[v]
        if cu == cv:
            internal_edges[cu] += 1
        else:
            key = edge_sort_key((cu, cv))
            inter_counts[key] = inter_counts.get(key, 0) + 1

    degrees = dict(h_graph.degree())
    candidates = {method: [] for method in COMMUNITY_METHODS}
    for u, v in h_graph.edges():
        cu = node_to_comm[u]
        cv = node_to_comm[v]
        if cu == cv:
            continue
        eij = inter_counts.get(edge_sort_key((cu, cv)), 0)
        if eij == 0:
            continue
        ci = comm_sizes[cu]
        cj = comm_sizes[cv]
        ei = internal_edges[cu]
        ej = internal_edges[cv]
        degree_product = degrees[u] * degrees[v]
        scores = {
            "M4 dynamic community internal / pair": (ei * ej) / float(eij),
            "M7 dynamic community size / pair": (ci * cj) / float(eij),
            "M8 dynamic community bridge-degree": (ci * cj) / float(eij) * degree_product,
        }
        for method, score in scores.items():
            candidates[method].append((score, degree_product, edge_sort_key((u, v))))

    fallback = top_degree_product_edges(h_graph, top_k)
    result = {}
    for method, method_candidates in candidates.items():
        if not method_candidates:
            result[method] = fallback
            continue
        method_candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        result[method] = [(edge, score) for score, _, edge in method_candidates[:top_k]]
    return result


def expanded_candidate_edges(graph, top_k):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return []

    raw = {
        "M2 dynamic degree product": top_degree_product_edges(h_graph, top_k),
        "M5 dynamic edge betweenness": top_betweenness_edges(h_graph, top_k),
    }
    raw.update(top_community_edges(h_graph, top_k))

    candidates = []
    seen = set()
    for method in BASELINE_METHODS:
        for rank, (edge, heuristic_score) in enumerate(raw.get(method, []), start=1):
            key = edge_sort_key(edge)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "edge": key,
                    "source_method": method,
                    "source_rank": rank,
                    "heuristic_score": float(heuristic_score),
                }
            )
    return candidates


def choose_degree_product_edge(h_graph):
    edges = top_degree_product_edges(h_graph, 1)
    return edges[0][0] if edges else None


def choose_betweenness_edge(h_graph):
    edges = top_betweenness_edges(h_graph, 1)
    return edges[0][0] if edges else None


def choose_community_edge(h_graph, method):
    edges = top_community_edges(h_graph, 1).get(method, [])
    return edges[0][0] if edges else None


def candidate_edge_for_method(graph, method):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    if method == "M2 dynamic degree product":
        return choose_degree_product_edge(h_graph)
    if method == "M5 dynamic edge betweenness":
        return choose_betweenness_edge(h_graph)
    if method in COMMUNITY_METHODS:
        return choose_community_edge(h_graph, method)
    raise ValueError(f"Unknown method: {method}")


def rollout_score(graph, original_n, first_edge, top_k, depth):
    simulation = graph.copy()
    gcc_values = []
    if not simulation.has_edge(*first_edge):
        return float("inf"), []

    simulation.remove_edge(*first_edge)
    gcc_values.append(gcc_ratio(simulation, original_n))
    rollout_edges = [first_edge]

    for _ in range(max(0, depth - 1)):
        edge, _, _, _ = choose_expanded_oracle_candidate(
            simulation, original_n, top_k=top_k, rollout_depth=1
        )
        if edge is None or not simulation.has_edge(*edge):
            break
        simulation.remove_edge(*edge)
        rollout_edges.append(edge)
        gcc_values.append(gcc_ratio(simulation, original_n))

    if not gcc_values:
        return float("inf"), rollout_edges
    # Lower is better. This is a short-horizon GCC area after candidate removal.
    return float(np.mean(gcc_values)), rollout_edges


def choose_expanded_oracle_candidate(graph, original_n, top_k, rollout_depth):
    candidates = expanded_candidate_edges(graph, top_k)
    rows = []
    for item in candidates:
        edge = item["edge"]
        if not graph.has_edge(*edge):
            continue
        score, rollout_edges = rollout_score(
            graph, original_n, edge, top_k=top_k, depth=rollout_depth
        )
        graph.remove_edge(*edge)
        immediate_gcc = gcc_ratio(graph, original_n)
        graph.add_edge(*edge)
        method_tie = ORACLE_TIE_METHOD_ORDER.index(item["source_method"])
        rows.append(
            (
                score,
                immediate_gcc,
                item["source_rank"],
                method_tie,
                edge_sort_key(edge),
                item,
                rollout_edges,
            )
        )

    if not rows:
        return None, None, [], []
    best = min(rows, key=lambda row: (row[0], row[1], row[2], row[3], row[4]))
    return best[5]["edge"], best[5], candidates, best[6]


def curve_header(group, method, graph, original_n):
    return {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
        "method": method,
        "removed_edges": 0,
        "remove_ratio": 0.0,
        "gcc_ratio": gcc_ratio(graph, original_n),
    }


def dynamic_baseline_curve(group, method):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    rows = [curve_header(group, method, graph, original_n)]
    step = 0
    while largest_cc_subgraph(graph).number_of_edges() > 0:
        edge = candidate_edge_for_method(graph, method)
        if edge is None or not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
        rows.append(
            {
                "split": group["split"].iloc[0],
                "graph_id": group["graph_id"].iloc[0],
                "graph_type": group["graph_type"].iloc[0],
                "method": method,
                "removed_edges": step,
                "remove_ratio": step / float(original_m),
                "gcc_ratio": gcc_ratio(graph, original_n),
            }
        )
    return rows


def expanded_oracle_curve(group, top_k, rollout_depth):
    method = f"Expanded oracle top-{top_k} h{rollout_depth}"
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    rows = [curve_header(group, method, graph, original_n)]
    decisions = []
    step = 0

    while largest_cc_subgraph(graph).number_of_edges() > 0:
        edge, selected, candidates, rollout_edges = choose_expanded_oracle_candidate(
            graph, original_n, top_k=top_k, rollout_depth=rollout_depth
        )
        if edge is None or selected is None or not graph.has_edge(*edge):
            break
        before_gcc = gcc_ratio(graph, original_n)
        graph.remove_edge(*edge)
        step += 1
        after_gcc = gcc_ratio(graph, original_n)
        rows.append(
            {
                "split": group["split"].iloc[0],
                "graph_id": group["graph_id"].iloc[0],
                "graph_type": group["graph_type"].iloc[0],
                "method": method,
                "removed_edges": step,
                "remove_ratio": step / float(original_m),
                "gcc_ratio": after_gcc,
            }
        )
        decisions.append(
            {
                "split": group["split"].iloc[0],
                "graph_id": group["graph_id"].iloc[0],
                "graph_type": group["graph_type"].iloc[0],
                "method": method,
                "step": step,
                "remove_ratio": step / float(original_m),
                "u": edge[0],
                "v": edge[1],
                "selected_source_method": selected["source_method"],
                "selected_source_rank": selected["source_rank"],
                "gcc_before": before_gcc,
                "gcc_after": after_gcc,
                "gcc_delta": before_gcc - after_gcc,
                "num_unique_candidates": len(candidates),
                "rollout_depth": rollout_depth,
                "rollout_edges": " ".join(f"{u}-{v}" for u, v in rollout_edges),
            }
        )
    return rows, decisions


def threshold_remove_ratio(curve_df, threshold):
    reached = curve_df[curve_df["gcc_ratio"] <= threshold]
    if reached.empty:
        return np.nan
    return float(reached["remove_ratio"].iloc[0])


def summarize_curve(curve_df):
    x = curve_df["remove_ratio"].values
    y = curve_df["gcc_ratio"].values
    row = {
        "split": curve_df["split"].iloc[0],
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "auc": float(np.trapz(y, x)),
    }
    for threshold in THRESHOLDS:
        key = "remove_ratio_gcc_le_" + str(threshold).replace(".", "_")
        row[key] = threshold_remove_ratio(curve_df, threshold)
    return row


def aggregate_summary(summary_df, method_order):
    rows = []
    for (split, method), group in summary_df.groupby(["split", "method"]):
        row = {
            "split": split,
            "method": method,
            "num_graphs": len(group),
            "mean_auc": group["auc"].mean(),
            "median_auc": group["auc"].median(),
            "std_auc": group["auc"].std(),
        }
        for threshold in THRESHOLDS:
            column = "remove_ratio_gcc_le_" + str(threshold).replace(".", "_")
            row[f"mean_{column}"] = group[column].mean()
        rows.append(row)
    result = pd.DataFrame(rows)
    result["method"] = pd.Categorical(result["method"], method_order, ordered=True)
    return result.sort_values(["split", "method"])


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def plot_auc(aggregate_df, split, method_order, path):
    plot_df = aggregate_df[aggregate_df["split"] == split].copy()
    if plot_df.empty:
        return
    plot_df["method"] = pd.Categorical(plot_df["method"], method_order, ordered=True)
    plot_df = plot_df.sort_values("method")
    plt.figure(figsize=(10.8, 4.8))
    x = np.arange(len(plot_df))
    plt.bar(x, plot_df["mean_auc"].values, yerr=plot_df["std_auc"].fillna(0).values, capsize=4)
    plt.xticks(x, plot_df["method"].values, rotation=25, ha="right")
    plt.ylabel("Mean AUC (lower is better)")
    plt.title(f"{split}: expanded candidate oracle")
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_example_curves(curves_df, summary_df, split, method_order, path):
    split_summary = summary_df[summary_df["split"] == split]
    if split_summary.empty:
        return
    oracle_method = [method for method in method_order if method.startswith("Expanded oracle")][0]
    oracle_rows = split_summary[split_summary["method"] == oracle_method].sort_values("auc")
    graph_id = oracle_rows.iloc[len(oracle_rows) // 2]["graph_id"]
    plot_df = curves_df[(curves_df["split"] == split) & (curves_df["graph_id"] == graph_id)]
    plt.figure(figsize=(8.8, 5.2))
    for method in method_order:
        method_df = plot_df[plot_df["method"] == method]
        if method_df.empty:
            continue
        plt.plot(method_df["remove_ratio"], method_df["gcc_ratio"], label=method, linewidth=1.8)
    plt.xlabel("Removed edge ratio")
    plt.ylabel("GCC ratio")
    plt.title(f"{split}: representative expanded oracle curve ({graph_id})")
    plt.legend(frameon=True, fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def write_notes(aggregate_df, decision_df, top_k, depths):
    lines = [
        "# Expanded Candidate Oracle",
        "",
        f"Each step builds a candidate pool from the top-{top_k} edges suggested by M2/M4/M5/M7/M8, deduplicates those edges, and lets an oracle choose from the expanded pool.",
        "",
        "For horizon `h1`, the oracle chooses the edge with the largest immediate GCC reduction. For larger horizons, it scores the first edge by simulating greedy expanded-oracle choices for the remaining horizon and minimizing the short-horizon average GCC.",
        "",
        "## AUC Summary",
        "",
    ]
    for split, group in aggregate_df.groupby("split"):
        ranked = group.sort_values("mean_auc")
        best = ranked.iloc[0]
        lines.append(
            f"- {split}: best={best['method']} (mean AUC={best['mean_auc']:.3f})"
        )
    if not decision_df.empty:
        lines.extend(["", "## Candidate Pool", ""])
        pool_stats = (
            decision_df.groupby(["split", "method"])["num_unique_candidates"]
            .agg(["mean", "median", "min", "max"])
            .reset_index()
        )
        for row in pool_stats.itertuples(index=False):
            lines.append(
                f"- {row.split} / {row.method}: mean candidates={row.mean:.1f}, "
                f"median={row.median:.1f}, range={int(row.min)}-{int(row.max)}"
            )
        lines.extend(["", "## Selected Source Usage", ""])
        usage = (
            decision_df.groupby(["split", "method", "selected_source_method"])
            .size()
            .reset_index(name="count")
            .sort_values(["split", "method", "count"], ascending=[True, True, False])
        )
        for (split, method), group in usage.groupby(["split", "method"]):
            total = group["count"].sum()
            parts = [
                f"{row.selected_source_method}: {row['count']} ({row['count'] / total:.1%})"
                for _, row in group.iterrows()
            ]
            lines.append(f"- {split} / {method}: " + "; ".join(parts))
    lines.extend(["", "## Config", "", f"- top_k={top_k}", f"- rollout_depths={depths}"])
    (OUT_DIR / "expanded_candidate_oracle_notes.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8-sig"
    )


def parse_int_list(text):
    return [int(part.strip()) for part in text.split(",") if part.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate expanded top-k candidate oracle selectors.")
    parser.add_argument("--attack-splits", default="synthetic_test,real_external_test")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--rollout-depths", default="1,3")
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Output directory for CSV, figures, config, and notes.",
    )
    parser.add_argument(
        "--graph-ids",
        default="",
        help="Optional comma-separated graph_id filter for quick targeted runs.",
    )
    parser.add_argument(
        "--max-graphs",
        type=int,
        default=0,
        help="Optional maximum number of split/graph groups to evaluate.",
    )
    parser.add_argument(
        "--skip-baselines",
        action="store_true",
        help="Only evaluate expanded oracle methods. Useful because dynamic baselines are already produced by other scripts.",
    )
    return parser.parse_args()


def main():
    global OUT_DIR
    args = parse_args()
    OUT_DIR = Path(args.out_dir)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    splits = [split.strip() for split in args.attack_splits.split(",") if split.strip()]
    depths = parse_int_list(args.rollout_depths)
    oracle_methods = [f"Expanded oracle top-{args.top_k} h{depth}" for depth in depths]
    method_order = oracle_methods if args.skip_baselines else oracle_methods + BASELINE_METHODS

    frames = [read_split(split) for split in splits]
    df = pd.concat(frames, ignore_index=True)
    graph_ids = {graph_id.strip() for graph_id in args.graph_ids.split(",") if graph_id.strip()}
    if graph_ids:
        df = df[df["graph_id"].isin(graph_ids)].copy()

    curve_rows = []
    decision_rows = []
    summary_rows = []
    groups = list(df.groupby(["split", "graph_id"]))
    if args.max_graphs > 0:
        groups = groups[: args.max_graphs]
    for index, (_, group) in enumerate(groups, start=1):
        label = f"{group['split'].iloc[0]}/{group['graph_id'].iloc[0]}"
        print(f"[{index:03d}/{len(groups):03d}] {label}", flush=True)
        for depth in depths:
            rows, decisions = expanded_oracle_curve(group, args.top_k, depth)
            curve_rows.extend(rows)
            decision_rows.extend(decisions)
            summary_rows.append(summarize_curve(pd.DataFrame(rows)))
        if not args.skip_baselines:
            for method in BASELINE_METHODS:
                baseline_rows = dynamic_baseline_curve(group, method)
                curve_rows.extend(baseline_rows)
                summary_rows.append(summarize_curve(pd.DataFrame(baseline_rows)))

    curves_df = pd.DataFrame(curve_rows)
    decisions_df = pd.DataFrame(decision_rows)
    summary_df = pd.DataFrame(summary_rows)
    aggregate_df = aggregate_summary(summary_df, method_order)

    write_csv(curves_df, OUT_DIR / "expanded_oracle_attack_curves.csv")
    write_csv(decisions_df, OUT_DIR / "expanded_oracle_decisions.csv")
    write_csv(summary_df, OUT_DIR / "expanded_oracle_attack_summary_by_graph.csv")
    write_csv(aggregate_df, OUT_DIR / "expanded_oracle_attack_summary_aggregate.csv")

    config = {
        "seed": SEED,
        "attack_splits": splits,
        "top_k": args.top_k,
        "rollout_depths": depths,
        "candidate_methods": BASELINE_METHODS,
        "graph_ids": sorted(graph_ids),
        "max_graphs": args.max_graphs,
        "skip_baselines": args.skip_baselines,
        "oracle_rule": "Expanded top-k candidate pool; h1 minimizes next-step GCC, h>1 minimizes greedy rollout average GCC.",
    }
    (OUT_DIR / "expanded_oracle_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for split in splits:
        plot_auc(aggregate_df, split, method_order, OUT_DIR / f"{split}_expanded_oracle_auc_by_method.png")
        plot_example_curves(curves_df, summary_df, split, method_order, OUT_DIR / f"{split}_expanded_oracle_example_curves.png")
    write_notes(aggregate_df, decisions_df, args.top_k, depths)

    print(f"Wrote expanded candidate oracle outputs to {OUT_DIR}")
    print(aggregate_df.to_string(index=False))


if __name__ == "__main__":
    main()
