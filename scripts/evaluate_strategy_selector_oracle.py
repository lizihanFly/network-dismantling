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
OUT_DIR = ROOT / "result" / "strategy_selector_oracle"
SEED = 20260513

METHOD_ORDER = [
    "Oracle strategy selector",
    "M2 dynamic degree product",
    "M4 dynamic community internal / pair",
    "M5 dynamic edge betweenness",
    "M7 dynamic community size / pair",
    "M8 dynamic community bridge-degree",
]
BASELINE_METHODS = METHOD_ORDER[1:]
ORACLE_TIE_METHOD_ORDER = [
    "M5 dynamic edge betweenness",
    "M4 dynamic community internal / pair",
    "M7 dynamic community size / pair",
    "M8 dynamic community bridge-degree",
    "M2 dynamic degree product",
]
COMMUNITY_METHODS = {
    "M4 dynamic community internal / pair": "m4",
    "M7 dynamic community size / pair": "m7",
    "M8 dynamic community bridge-degree": "m8",
}
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


def choose_degree_product_edge(h_graph):
    if h_graph.number_of_edges() == 0:
        return None
    degrees = dict(h_graph.degree())
    candidates = []
    for edge in h_graph.edges():
        u, v = edge
        candidates.append((degrees[u] * degrees[v], edge_sort_key(edge), edge_sort_key(edge)))
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def choose_betweenness_edge(h_graph):
    if h_graph.number_of_edges() == 0:
        return None
    betweenness = nx.edge_betweenness_centrality(h_graph, normalized=True, weight=None)
    candidates = [
        (score, edge_sort_key(edge), edge_sort_key(edge))
        for edge, score in betweenness.items()
    ]
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def choose_community_edges(h_graph):
    if h_graph.number_of_edges() == 0:
        return {method: None for method in COMMUNITY_METHODS}

    partition = community_louvain.best_partition(h_graph, random_state=SEED)
    communities = {}
    for node, community_id in partition.items():
        communities.setdefault(community_id, set()).add(node)

    if len(communities) < 2:
        fallback = choose_degree_product_edge(h_graph)
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
            candidates[method].append((score, degree_product, edge_sort_key((u, v)), edge_sort_key((u, v))))

    fallback = choose_degree_product_edge(h_graph)
    result = {}
    for method, method_candidates in candidates.items():
        if not method_candidates:
            result[method] = fallback
        else:
            result[method] = max(
                method_candidates, key=lambda item: (item[0], item[1], item[2])
            )[3]
    return result


def candidate_edges(graph):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return {method: None for method in BASELINE_METHODS}
    candidates = {
        "M2 dynamic degree product": choose_degree_product_edge(h_graph),
        "M5 dynamic edge betweenness": choose_betweenness_edge(h_graph),
    }
    candidates.update(choose_community_edges(h_graph))
    return candidates


def candidate_edge_for_method(graph, method):
    h_graph = largest_cc_subgraph(graph)
    if h_graph.number_of_edges() == 0:
        return None
    if method == "M2 dynamic degree product":
        return choose_degree_product_edge(h_graph)
    if method == "M5 dynamic edge betweenness":
        return choose_betweenness_edge(h_graph)
    if method in COMMUNITY_METHODS:
        return choose_community_edges(h_graph).get(method)
    raise ValueError(f"Unknown method: {method}")


def choose_oracle_candidate(graph, original_n):
    candidates = candidate_edges(graph)
    rows = []
    for method in BASELINE_METHODS:
        edge = candidates.get(method)
        if edge is None or not graph.has_edge(*edge):
            continue
        graph.remove_edge(*edge)
        next_gcc = gcc_ratio(graph, original_n)
        graph.add_edge(*edge)
        rows.append((next_gcc, ORACLE_TIE_METHOD_ORDER.index(method), edge_sort_key(edge), method, edge))
    if not rows:
        return None, None, {}
    best = min(rows, key=lambda item: (item[0], item[1], item[2]))
    candidate_map = {method: edge for _, _, _, method, edge in rows}
    return best[4], best[3], candidate_map


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


def oracle_curve(group):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    rows = [curve_header(group, "Oracle strategy selector", graph, original_n)]
    decisions = []
    step = 0
    while largest_cc_subgraph(graph).number_of_edges() > 0:
        edge, selected_method, candidate_map = choose_oracle_candidate(graph, original_n)
        if edge is None or selected_method is None or not graph.has_edge(*edge):
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
                "method": "Oracle strategy selector",
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
                "step": step,
                "remove_ratio": step / float(original_m),
                "selected_method": selected_method,
                "u": edge[0],
                "v": edge[1],
                "gcc_before": before_gcc,
                "gcc_after": after_gcc,
                "gcc_delta": before_gcc - after_gcc,
                "num_candidate_methods": len(candidate_map),
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
        }
        for threshold in THRESHOLDS:
            column = "remove_ratio_gcc_le_" + str(threshold).replace(".", "_")
            row[f"mean_{column}"] = group[column].mean()
        rows.append(row)
    result = pd.DataFrame(rows)
    result["method"] = pd.Categorical(result["method"], METHOD_ORDER, ordered=True)
    return result.sort_values(["split", "method"])


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def plot_auc(aggregate_df, split, path):
    plot_df = aggregate_df[aggregate_df["split"] == split].copy()
    if plot_df.empty:
        return
    plot_df["method"] = pd.Categorical(plot_df["method"], METHOD_ORDER, ordered=True)
    plot_df = plot_df.sort_values("method")
    plt.figure(figsize=(9.6, 4.8))
    x = np.arange(len(plot_df))
    plt.bar(x, plot_df["mean_auc"].values, yerr=plot_df["std_auc"].fillna(0).values, capsize=4)
    plt.xticks(x, plot_df["method"].values, rotation=25, ha="right")
    plt.ylabel("Mean AUC (lower is better)")
    plt.title(f"{split}: oracle selector vs dynamic strategies")
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_example_curves(curves_df, summary_df, split, path):
    split_summary = summary_df[summary_df["split"] == split]
    if split_summary.empty:
        return
    oracle_rows = split_summary[split_summary["method"] == "Oracle strategy selector"].sort_values("auc")
    graph_id = oracle_rows.iloc[len(oracle_rows) // 2]["graph_id"]
    plot_df = curves_df[(curves_df["split"] == split) & (curves_df["graph_id"] == graph_id)]
    plt.figure(figsize=(8.4, 5.0))
    for method in METHOD_ORDER:
        method_df = plot_df[plot_df["method"] == method]
        plt.plot(method_df["remove_ratio"], method_df["gcc_ratio"], label=method, linewidth=1.8)
    plt.xlabel("Removed edge ratio")
    plt.ylabel("GCC ratio")
    plt.title(f"{split}: representative oracle curve ({graph_id})")
    plt.legend(frameon=True, fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def write_notes(aggregate_df, decision_df):
    lines = [
        "# Strategy Selector Oracle",
        "",
        "At each step, the oracle asks M2/M4/M5/M7/M8 for their next dynamic edge, tries those candidate deletions, and chooses the one with the largest immediate GCC drop. Ties prefer M5, then M4, M7, M8, and M2.",
        "",
        "This is an upper-bound check for a future learned strategy selector. It is not a trainable model yet.",
        "",
        "## AUC Summary",
        "",
    ]
    for split, group in aggregate_df.groupby("split"):
        ranked = group.sort_values("mean_auc")
        best = ranked.iloc[0]
        oracle = group[group["method"] == "Oracle strategy selector"].iloc[0]
        lines.append(
            f"- {split}: best={best['method']} (mean AUC={best['mean_auc']:.3f}); "
            f"oracle mean AUC={oracle['mean_auc']:.3f}"
        )
    lines.extend(["", "## Oracle Method Usage", ""])
    if not decision_df.empty:
        usage = (
            decision_df.groupby(["split", "selected_method"])
            .size()
            .reset_index(name="count")
            .sort_values(["split", "count"], ascending=[True, False])
        )
        for split, group in usage.groupby("split"):
            total = group["count"].sum()
            parts = [
                f"{row.selected_method}: {row['count']} ({row['count'] / total:.1%})"
                for _, row in group.iterrows()
            ]
            lines.append(f"- {split}: " + "; ".join(parts))
    (OUT_DIR / "strategy_selector_oracle_notes.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8-sig"
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate an oracle selector over dynamic attack strategies.")
    parser.add_argument("--attack-splits", default="synthetic_test,real_external_test")
    return parser.parse_args()


def main():
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    splits = [split.strip() for split in args.attack_splits.split(",") if split.strip()]

    frames = []
    for split in splits:
        frames.append(read_split(split))
    df = pd.concat(frames, ignore_index=True)

    curve_rows = []
    decision_rows = []
    summary_rows = []
    groups = list(df.groupby(["split", "graph_id"]))
    for index, (_, group) in enumerate(groups, start=1):
        label = f"{group['split'].iloc[0]}/{group['graph_id'].iloc[0]}"
        print(f"[{index:03d}/{len(groups):03d}] {label}", flush=True)
        rows, decisions = oracle_curve(group)
        curve_rows.extend(rows)
        decision_rows.extend(decisions)
        summary_rows.append(summarize_curve(pd.DataFrame(rows)))
        for method in BASELINE_METHODS:
            baseline_rows = dynamic_baseline_curve(group, method)
            curve_rows.extend(baseline_rows)
            summary_rows.append(summarize_curve(pd.DataFrame(baseline_rows)))

    curves_df = pd.DataFrame(curve_rows)
    decisions_df = pd.DataFrame(decision_rows)
    summary_df = pd.DataFrame(summary_rows)
    aggregate_df = aggregate_summary(summary_df)

    write_csv(curves_df, OUT_DIR / "oracle_attack_curves.csv")
    write_csv(decisions_df, OUT_DIR / "oracle_decisions.csv")
    write_csv(summary_df, OUT_DIR / "oracle_attack_summary_by_graph.csv")
    write_csv(aggregate_df, OUT_DIR / "oracle_attack_summary_aggregate.csv")

    config = {
        "seed": SEED,
        "attack_splits": splits,
        "candidate_methods": BASELINE_METHODS,
        "oracle_rule": "Select the candidate edge with the lowest next-step GCC ratio; ties prefer M5, then M4, M7, M8, M2.",
    }
    (OUT_DIR / "oracle_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for split in splits:
        plot_auc(aggregate_df, split, OUT_DIR / f"{split}_oracle_auc_by_method.png")
        plot_example_curves(curves_df, summary_df, split, OUT_DIR / f"{split}_oracle_example_curves.png")
    write_notes(aggregate_df, decisions_df)

    print(f"Wrote oracle selector outputs to {OUT_DIR}")
    print(aggregate_df.to_string(index=False))


if __name__ == "__main__":
    main()
