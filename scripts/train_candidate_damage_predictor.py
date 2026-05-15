from pathlib import Path
import argparse
import json
import pickle
import random
import warnings

import community as community_louvain
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import ConvergenceWarning
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
]
SOURCE_LABELS = {
    "m2": "M2 dynamic degree product",
    "m4": "M4 dynamic community internal / pair",
    "m5": "M5 dynamic edge betweenness",
    "m7": "M7 dynamic community size / pair",
    "m8": "M8 dynamic community bridge-degree",
}


def parse_list(text):
    return [part.strip() for part in text.split(",") if part.strip()]


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


def candidate_edges(graph, top_k):
    h_graph = largest_cc_subgraph(graph)
    source_edges = {
        "m2": top_degree_product_edges(h_graph, top_k),
        "m4": top_community_edges(h_graph, top_k, "m4"),
        "m5": top_betweenness_edges(h_graph, top_k),
        "m7": top_community_edges(h_graph, top_k, "m7"),
        "m8": top_community_edges(h_graph, top_k, "m8"),
    }
    edge_info = {}
    for source, edges in source_edges.items():
        for rank, edge in enumerate(edges, start=1):
            info = edge_info.setdefault(edge, {"sources": set(), "rank_min": rank})
            info["sources"].add(source)
            info["rank_min"] = min(info["rank_min"], rank)
    return edge_info


def dynamic_features_for_candidates(graph, edge_info, original_n, meta, step):
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

        row = {
            "split": meta["split"],
            "graph_id": meta["graph_id"],
            "graph_type": meta["graph_type"],
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
            "gcc_delta": gcc_delta_for_edge(graph, edge, original_n),
        }
        row.update(source_flags)
        rows.append(row)

    return rows


def choose_dynamic_edge(graph, method):
    edges = candidate_edges(graph, 1)
    if not edges:
        return None
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
    for edge, info in edges.items():
        if source in info["sources"]:
            return edge
    return next(iter(edges))


def collect_candidate_rows_for_graph(group, top_k, max_steps, max_remove_ratio, rollout_policy):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    meta = {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
    }
    rows = []
    step = 0
    rng = random.Random(SEED)
    while graph.number_of_edges() > 0:
        if max_steps and step >= max_steps:
            break
        if max_remove_ratio and step / float(original_m) >= max_remove_ratio:
            break
        edge_info = candidate_edges(graph, top_k)
        rows.extend(dynamic_features_for_candidates(graph, edge_info, original_n, meta, step))

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


def build_candidate_dataset(split_names, top_k, max_steps, max_remove_ratio, max_graphs, graph_ids, rollout_policy):
    frames = [read_split(name) for name in split_names]
    df = pd.concat(frames, ignore_index=True)
    if graph_ids:
        df = df[df["graph_id"].isin(graph_ids)].copy()
    groups = list(df.groupby(["split", "graph_id"], sort=False))
    if max_graphs:
        groups = groups[:max_graphs]

    rows = []
    for index, (_, group) in enumerate(groups, start=1):
        label = f"{group['split'].iloc[0]}/{group['graph_id'].iloc[0]}"
        print(f"[dataset {index:03d}/{len(groups):03d}] {label}", flush=True)
        rows.extend(
            collect_candidate_rows_for_graph(
                group,
                top_k=top_k,
                max_steps=max_steps,
                max_remove_ratio=max_remove_ratio,
                rollout_policy=rollout_policy,
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
    blocked = {"split", "graph_id", "graph_type", "u", "v", "gcc_delta", "damage_rank"}
    return [
        column
        for column in df.columns
        if column not in blocked and pd.api.types.is_numeric_dtype(df[column])
    ]


def train_model(train_df, feature_cols, model_type, max_iter):
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
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
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


def attack_curve_for_model(group, model, feature_cols, top_k):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    meta = {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
    }
    rows = [curve_row(meta, "Candidate damage predictor", 0, original_m, gcc_ratio(graph, original_n))]
    step = 0
    while graph.number_of_edges() > 0:
        edge_info = candidate_edges(graph, top_k)
        candidate_rows = dynamic_features_for_candidates(graph, edge_info, original_n, meta, step)
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


def dynamic_attack_curve(group, method):
    graph = reconstruct_graph(group)
    original_n = graph.number_of_nodes()
    original_m = max(1, graph.number_of_edges())
    meta = {
        "split": group["split"].iloc[0],
        "graph_id": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
    }
    rows = [curve_row(meta, method, 0, original_m, gcc_ratio(graph, original_n))]
    step = 0
    while graph.number_of_edges() > 0:
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
        column = "remove_ratio_gcc_le_" + str(threshold).replace(".", "_")
        row[column] = threshold_remove_ratio(curve_df, threshold)
    return row


def evaluate_attack_curves(model, eval_df, feature_cols, top_k, attack_splits, max_eval_graphs, graph_ids, skip_baselines):
    df = eval_df[eval_df["split"].isin(attack_splits)].copy()
    if graph_ids:
        df = df[df["graph_id"].isin(graph_ids)].copy()
    groups = list(df.groupby(["split", "graph_id"], sort=False))
    if max_eval_graphs:
        groups = groups[:max_eval_graphs]

    curve_rows = []
    summary_rows = []
    for index, (_, group) in enumerate(groups, start=1):
        label = f"{group['split'].iloc[0]}/{group['graph_id'].iloc[0]}"
        print(f"[attack {index:03d}/{len(groups):03d}] {label}", flush=True)
        rows = attack_curve_for_model(group, model, feature_cols, top_k)
        curve_rows.extend(rows)
        summary_rows.append(summarize_curve(pd.DataFrame(rows)))
        if not skip_baselines:
            for method in BASELINE_METHODS:
                baseline_rows = dynamic_attack_curve(group, method)
                curve_rows.extend(baseline_rows)
                summary_rows.append(summarize_curve(pd.DataFrame(baseline_rows)))
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
        }
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
        "This experiment changes the supervised target from teacher-rank imitation to direct one-step damage prediction.",
        "",
        "At each dynamic state, candidates are built from the top-k edges suggested by M2/M4/M5/M7/M8. The model predicts `gcc_delta` for each candidate and removes the edge with the largest predicted damage.",
        "",
        "## Config",
        "",
        f"- model_type={args.model_type}",
        f"- top_k={args.top_k}",
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
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model-type", choices=["mlp", "random_forest", "gbdt"], default="gbdt")
    parser.add_argument("--max-iter", type=int, default=180)
    parser.add_argument("--train-splits", default="synthetic_train")
    parser.add_argument("--eval-splits", default="synthetic_val,synthetic_test,real_external_test")
    parser.add_argument("--attack-splits", default="synthetic_test,real_external_test")
    parser.add_argument("--graph-ids", default="")
    parser.add_argument("--max-train-graphs", type=int, default=0)
    parser.add_argument("--max-eval-graphs", type=int, default=0)
    parser.add_argument("--max-train-steps", type=int, default=80)
    parser.add_argument("--train-max-remove-ratio", type=float, default=0.35)
    parser.add_argument("--rollout-policy", choices=["m5", "damage_oracle", "random"], default="m5")
    parser.add_argument("--skip-baselines", action="store_true")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    return parser.parse_args()


def main():
    global OUT_DIR
    args = parse_args()
    OUT_DIR = Path(args.out_dir)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    graph_ids = set(parse_list(args.graph_ids))

    train_candidate_df = build_candidate_dataset(
        parse_list(args.train_splits),
        top_k=args.top_k,
        max_steps=args.max_train_steps,
        max_remove_ratio=args.train_max_remove_ratio,
        max_graphs=args.max_train_graphs,
        graph_ids=graph_ids,
        rollout_policy=args.rollout_policy,
    )
    if train_candidate_df.empty:
        raise RuntimeError("No candidate training rows were generated.")
    feature_cols = feature_columns(train_candidate_df)
    model = train_model(train_candidate_df, feature_cols, args.model_type, args.max_iter)

    eval_candidate_df = build_candidate_dataset(
        parse_list(args.eval_splits),
        top_k=args.top_k,
        max_steps=args.max_train_steps,
        max_remove_ratio=args.train_max_remove_ratio,
        max_graphs=args.max_eval_graphs,
        graph_ids=graph_ids,
        rollout_policy=args.rollout_policy,
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
        attack_splits=parse_list(args.attack_splits),
        max_eval_graphs=args.max_eval_graphs,
        graph_ids=graph_ids,
        skip_baselines=args.skip_baselines,
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
                "model_type": args.model_type,
            },
            handle,
        )

    config = vars(args).copy()
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
