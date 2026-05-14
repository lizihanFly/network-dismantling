from pathlib import Path
import argparse
import csv
import json
import pickle
import warnings

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import community as community_louvain
from scipy.stats import kendalltau, spearmanr
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ml_attack_dataset"
OUT_DIR = ROOT / "result" / "ml_mlp_attack_ranker"
SEED = 20260513

TARGET_COLUMN = "edge_betweenness_rank_pct"
IDENTIFIER_COLUMNS = {
    "split",
    "graph_id",
    "graph_type",
    "community_strength",
    "u",
    "v",
}
LEAKAGE_COLUMNS = {
    "edge_betweenness",
    "edge_betweenness_rank",
    "edge_betweenness_rank_pct",
    "gcc_delta",
    "gcc_delta_rank",
    "gcc_delta_rank_pct",
}
METHOD_ORDER = [
    "MLP teacher-rank",
    "M2 dynamic degree product",
    "M4 dynamic community internal / pair",
    "M5 dynamic edge betweenness",
    "M7 dynamic community size / pair",
    "M8 dynamic community bridge-degree",
]
THRESHOLDS = [0.5, 0.2, 0.1]


def read_split(name):
    return pd.read_csv(DATA_DIR / f"edge_features_{name}.csv")


def feature_columns(df, target_column):
    blocked = IDENTIFIER_COLUMNS | LEAKAGE_COLUMNS | {target_column}
    columns = []
    for column in df.columns:
        if column in blocked:
            continue
        if pd.api.types.is_numeric_dtype(df[column]):
            columns.append(column)
    return columns


def train_model(train_df, feature_cols, target_column, max_iter, hidden_layers):
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPRegressor(
                    hidden_layer_sizes=hidden_layers,
                    activation="relu",
                    solver="adam",
                    alpha=1e-4,
                    batch_size=256,
                    learning_rate_init=1e-3,
                    max_iter=max_iter,
                    early_stopping=True,
                    validation_fraction=0.12,
                    random_state=SEED,
                    verbose=False,
                ),
            ),
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model.fit(train_df[feature_cols].values, train_df[target_column].values)
    return model


def add_predictions(model, df, feature_cols):
    result = df.copy()
    pred = model.predict(result[feature_cols].values)
    result["mlp_pred_rank_pct"] = np.clip(pred, 0.0, 1.0)
    return result


def top_fraction_overlap(y_true, y_pred, fraction):
    n = len(y_true)
    if n == 0:
        return 0.0
    k = max(1, int(round(n * fraction)))
    true_top = set(np.argsort(y_true)[:k])
    pred_top = set(np.argsort(y_pred)[:k])
    return len(true_top & pred_top) / float(k)


def ranking_metrics_for_group(group, target_column):
    y_true = group[target_column].values
    y_pred = group["mlp_pred_rank_pct"].values
    spearman = spearmanr(y_true, y_pred).correlation
    kendall = kendalltau(y_true, y_pred).correlation
    if np.isnan(spearman):
        spearman = 0.0
    if np.isnan(kendall):
        kendall = 0.0
    return {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
        "n_edges": len(group),
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": mean_squared_error(y_true, y_pred) ** 0.5,
        "spearman": spearman,
        "kendall": kendall,
        "top_1pct_overlap": top_fraction_overlap(y_true, y_pred, 0.01),
        "top_5pct_overlap": top_fraction_overlap(y_true, y_pred, 0.05),
        "top_10pct_overlap": top_fraction_overlap(y_true, y_pred, 0.10),
    }


def evaluate_ranking(df, target_column):
    rows = []
    for _, group in df.groupby(["split", "graph_id"]):
        rows.append(ranking_metrics_for_group(group, target_column))
    return pd.DataFrame(rows)


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


def attack_curve_for_edges(group, ordered_edges, method):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, len(ordered_edges))
    rows = [
        {
            "split": group["split"].iloc[0],
            "graph_id": group["graph_id"].iloc[0],
            "graph_type": group["graph_type"].iloc[0],
            "method": method,
            "removed_edges": 0,
            "remove_ratio": 0.0,
            "gcc_ratio": gcc_ratio(graph, original_n),
        }
    ]
    for step, (u, v) in enumerate(ordered_edges, start=1):
        if graph.has_edge(u, v):
            graph.remove_edge(u, v)
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


def edge_sort_key(edge):
    u, v = edge
    return (min(u, v), max(u, v))


def choose_dynamic_degree_product_edge(graph):
    graph = largest_cc_subgraph(graph)
    if graph.number_of_edges() == 0:
        return None
    degrees = dict(graph.degree())
    return max(
        graph.edges(),
        key=lambda edge: (degrees[edge[0]] * degrees[edge[1]], -edge_sort_key(edge)[0], -edge_sort_key(edge)[1]),
    )


def louvain_partition(graph):
    if graph.number_of_edges() == 0:
        return {node: 0 for node in graph.nodes()}
    return community_louvain.best_partition(graph, random_state=SEED)


def choose_dynamic_community_edge(graph, mode):
    graph = largest_cc_subgraph(graph)
    if graph.number_of_edges() == 0:
        return None
    partition = louvain_partition(graph)
    communities = {}
    for node, community_id in partition.items():
        communities.setdefault(community_id, set()).add(node)
    if len(communities) <= 1:
        return choose_dynamic_degree_product_edge(graph)

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

    degrees = dict(graph.degree())
    scored_edges = []
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
        scored_edges.append((score, edge_sort_key((u, v))))

    if not scored_edges:
        return choose_dynamic_degree_product_edge(graph)
    return max(scored_edges, key=lambda item: (item[0], -item[1][0], -item[1][1]))[1]


def choose_dynamic_betweenness_edge(graph):
    graph = largest_cc_subgraph(graph)
    if graph.number_of_edges() == 0:
        return None
    betweenness = nx.edge_betweenness_centrality(graph, normalized=True)
    return max(
        betweenness,
        key=lambda edge: (
            betweenness[edge],
            -edge_sort_key(edge)[0],
            -edge_sort_key(edge)[1],
        ),
    )


def choose_dynamic_edge(graph, method):
    if method == "M2 dynamic degree product":
        return choose_dynamic_degree_product_edge(graph)
    if method == "M4 dynamic community internal / pair":
        return choose_dynamic_community_edge(graph, "m4")
    if method == "M5 dynamic edge betweenness":
        return choose_dynamic_betweenness_edge(graph)
    if method == "M7 dynamic community size / pair":
        return choose_dynamic_community_edge(graph, "m7")
    if method == "M8 dynamic community bridge-degree":
        return choose_dynamic_community_edge(graph, "m8")
    raise ValueError(f"Unsupported dynamic method: {method}")


def dynamic_attack_curve(group, method):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    rows = [
        {
            "split": group["split"].iloc[0],
            "graph_id": group["graph_id"].iloc[0],
            "graph_type": group["graph_type"].iloc[0],
            "method": method,
            "removed_edges": 0,
            "remove_ratio": 0.0,
            "gcc_ratio": gcc_ratio(graph, original_n),
        }
    ]
    step = 0
    while graph.number_of_edges() > 0:
        edge = choose_dynamic_edge(graph, method)
        if edge is None:
            break
        if graph.has_edge(*edge):
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


def ordered_edges_by_column(group, score_column, ascending):
    ordered = group.sort_values(
        [score_column, "u", "v"], ascending=[ascending, True, True]
    )
    return [(int(row.u), int(row.v)) for row in ordered[["u", "v"]].itertuples(index=False)]


def evaluate_attack_curves(df):
    curve_rows = []
    summary_rows = []
    total_groups = df.groupby(["split", "graph_id"]).ngroups
    for index, (_, group) in enumerate(df.groupby(["split", "graph_id"]), start=1):
        graph_label = f"{group['split'].iloc[0]}/{group['graph_id'].iloc[0]}"
        print(f"[attack {index:03d}/{total_groups:03d}] {graph_label}", flush=True)
        mlp_edges = ordered_edges_by_column(group, "mlp_pred_rank_pct", True)
        for method in METHOD_ORDER:
            if method == "MLP teacher-rank":
                rows = attack_curve_for_edges(group, mlp_edges, method)
            else:
                rows = dynamic_attack_curve(group, method)
            curve_rows.extend(rows)
            summary_rows.append(summarize_curve(pd.DataFrame(rows)))
    return pd.DataFrame(curve_rows), pd.DataFrame(summary_rows)


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def plot_split_attack_summary(summary_df, split, path):
    split_df = summary_df[summary_df["split"] == split].copy()
    if split_df.empty:
        return
    grouped = (
        split_df.groupby("method")["auc"]
        .agg(["mean", "std"])
        .reindex(METHOD_ORDER)
        .reset_index()
    )
    plt.figure(figsize=(9.6, 4.8))
    x = np.arange(len(grouped))
    plt.bar(x, grouped["mean"].values, yerr=grouped["std"].fillna(0).values, capsize=4)
    plt.xticks(x, grouped["method"].values, rotation=25, ha="right")
    plt.ylabel("Mean AUC (lower is better)")
    plt.title(f"{split}: attack curve AUC by method")
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_example_curves(curve_df, summary_df, split, path):
    split_summary = summary_df[summary_df["split"] == split].copy()
    if split_summary.empty:
        return
    # Pick the median graph by M5 AUC as a stable representative.
    m5_rows = split_summary[
        split_summary["method"] == "M5 dynamic edge betweenness"
    ].sort_values("auc")
    graph_id = m5_rows.iloc[len(m5_rows) // 2]["graph_id"]
    plot_df = curve_df[(curve_df["split"] == split) & (curve_df["graph_id"] == graph_id)]
    plt.figure(figsize=(8.2, 5.0))
    for method in METHOD_ORDER:
        method_df = plot_df[plot_df["method"] == method]
        plt.plot(method_df["remove_ratio"], method_df["gcc_ratio"], label=method, linewidth=1.8)
    plt.xlabel("Removed edge ratio")
    plt.ylabel("GCC ratio")
    plt.title(f"{split}: representative attack curve ({graph_id})")
    plt.legend(frameon=True, fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def aggregate_summary(summary_df):
    grouped = summary_df.groupby(["split", "method"])
    rows = []
    for (split, method), group in grouped:
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
    ordered_columns = [
        "split",
        "method",
        "num_graphs",
        "mean_auc",
        "median_auc",
        "std_auc",
        "mean_remove_ratio_gcc_le_0_5",
        "mean_remove_ratio_gcc_le_0_2",
        "mean_remove_ratio_gcc_le_0_1",
    ]
    return result.sort_values(["split", "method"])[ordered_columns]


def aggregate_ranking(ranking_df):
    rows = []
    for split, group in ranking_df.groupby("split"):
        rows.append(
            {
                "split": split,
                "num_graphs": len(group),
                "mean_mae": group["mae"].mean(),
                "mean_rmse": group["rmse"].mean(),
                "mean_spearman": group["spearman"].mean(),
                "mean_kendall": group["kendall"].mean(),
                "mean_top_1pct_overlap": group["top_1pct_overlap"].mean(),
                "mean_top_5pct_overlap": group["top_5pct_overlap"].mean(),
                "mean_top_10pct_overlap": group["top_10pct_overlap"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("split")


def write_notes(aggregate_df, ranking_aggregate_df, target):
    lines = [
        "# MLP Attack Ranker Baseline",
        "",
        f"Target: `{target}`. Lower predicted values are removed earlier.",
        "",
        "Training uses synthetic `train` only. Validation, synthetic test, and real external test are never mixed into fitting.",
        "",
        "## Ranking Quality",
        "",
    ]
    for row in ranking_aggregate_df.itertuples(index=False):
        lines.append(
            f"- {row.split}: Spearman={row.mean_spearman:.3f}, "
            f"Kendall={row.mean_kendall:.3f}, MAE={row.mean_mae:.3f}, "
            f"top-5% overlap={row.mean_top_5pct_overlap:.3f}"
        )

    lines.extend(["", "## Attack AUC", ""])
    for split, group in aggregate_df.groupby("split"):
        ranked = group.sort_values("mean_auc")
        best = ranked.iloc[0]
        mlp = group[group["method"] == "MLP teacher-rank"].iloc[0]
        lines.append(
            f"- {split}: best={best['method']} "
            f"(mean AUC={best['mean_auc']:.3f}); "
            f"MLP mean AUC={mlp['mean_auc']:.3f}"
        )

    lines.extend(
        [
            "",
            "## Generated Files",
            "",
            "- `ranking_metrics_by_graph.csv`",
            "- `ranking_metrics_aggregate.csv`",
            "- `attack_summary_by_graph.csv`",
            "- `attack_summary_aggregate.csv`",
            "- `attack_curves.csv`",
            "- `mlp_attack_ranker.pkl`",
            "- `*_auc_by_method.png`",
            "- `*_example_curves.png`",
        ]
    )
    (OUT_DIR / "mlp_attack_ranker_notes.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8-sig"
    )


def parse_hidden_layers(text):
    return tuple(int(part.strip()) for part in text.split(",") if part.strip())


def parse_args():
    parser = argparse.ArgumentParser(description="Train an MLP edge attack ranker baseline.")
    parser.add_argument("--target", default=TARGET_COLUMN)
    parser.add_argument("--max-iter", type=int, default=250)
    parser.add_argument("--hidden-layers", default="64,32")
    parser.add_argument(
        "--attack-splits",
        default="synthetic_test,real_external_test",
        help="Comma-separated splits for expensive dynamic attack-curve evaluation.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    train_df = read_split("synthetic_train")
    val_df = read_split("synthetic_val")
    synthetic_test_df = read_split("synthetic_test")
    real_test_df = read_split("real_external_test")
    feature_cols = feature_columns(train_df, args.target)

    print(f"Training rows: {len(train_df)}")
    print(f"Feature count: {len(feature_cols)}")
    print(f"Target: {args.target}")

    model = train_model(
        train_df,
        feature_cols,
        args.target,
        max_iter=args.max_iter,
        hidden_layers=parse_hidden_layers(args.hidden_layers),
    )

    eval_df = pd.concat([val_df, synthetic_test_df, real_test_df], ignore_index=True)
    eval_df = add_predictions(model, eval_df, feature_cols)

    ranking_df = evaluate_ranking(eval_df, args.target)
    attack_splits = [split.strip() for split in args.attack_splits.split(",") if split.strip()]
    attack_eval_df = eval_df[eval_df["split"].isin(attack_splits)].copy()
    curve_df, attack_summary_df = evaluate_attack_curves(attack_eval_df)
    aggregate_df = aggregate_summary(attack_summary_df)
    ranking_aggregate_df = aggregate_ranking(ranking_df)

    write_csv(pd.DataFrame({"feature": feature_cols}), OUT_DIR / "mlp_feature_columns.csv")
    write_csv(ranking_df, OUT_DIR / "ranking_metrics_by_graph.csv")
    write_csv(ranking_aggregate_df, OUT_DIR / "ranking_metrics_aggregate.csv")
    write_csv(curve_df, OUT_DIR / "attack_curves.csv")
    write_csv(attack_summary_df, OUT_DIR / "attack_summary_by_graph.csv")
    write_csv(aggregate_df, OUT_DIR / "attack_summary_aggregate.csv")

    with (OUT_DIR / "mlp_attack_ranker.pkl").open("wb") as handle:
        pickle.dump({"model": model, "feature_cols": feature_cols, "target": args.target}, handle)

    config = {
        "target": args.target,
        "seed": SEED,
        "hidden_layers": parse_hidden_layers(args.hidden_layers),
        "max_iter": args.max_iter,
        "train_rows": len(train_df),
        "feature_count": len(feature_cols),
        "attack_splits": attack_splits,
        "excluded_columns": sorted(IDENTIFIER_COLUMNS | LEAKAGE_COLUMNS),
    }
    (OUT_DIR / "training_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for split in attack_splits:
        plot_split_attack_summary(attack_summary_df, split, OUT_DIR / f"{split}_auc_by_method.png")
        plot_example_curves(curve_df, attack_summary_df, split, OUT_DIR / f"{split}_example_curves.png")

    write_notes(aggregate_df, ranking_aggregate_df, args.target)

    print(f"Wrote MLP attack-ranker outputs to {OUT_DIR}")
    print(aggregate_df.to_string(index=False))


if __name__ == "__main__":
    main()
