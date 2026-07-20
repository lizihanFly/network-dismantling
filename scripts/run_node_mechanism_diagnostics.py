"""Formal mechanism diagnostics for the SASB-N node pilot.

This pipeline deliberately reruns only the four SASB-N source policies at
source_budget=64. It records source-set structure during each policy's own
trajectory and compares sampled dependency rankings with exact M5 rankings on
the same current GCC state at prespecified checkpoints.
"""

import argparse
import itertools
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

import run_node_dismantling_comparison as node


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "result" / "node_sasb_paper" / "mechanism_diagnostics"
PILOT_CONFIG = ROOT / "result" / "node_sasb_paper" / "pilot_config.json"
PILOT_RESULTS = ROOT / "result" / "node_sasb_paper" / "pilot" / "pilot_results.csv"
SOURCE_METHODS = [
    node.METHOD_STRUCTURED,
    node.METHOD_RANDOM_SOURCE,
    node.METHOD_DEGREE_SOURCE,
    node.METHOD_FROZEN_SOURCE,
]
METHOD_LABELS = {
    node.METHOD_STRUCTURED: "structured",
    node.METHOD_RANDOM_SOURCE: "random-source",
    node.METHOD_DEGREE_SOURCE: "degree-source",
    node.METHOD_FROZEN_SOURCE: "frozen-source",
}
COLORS = {
    node.METHOD_STRUCTURED: "#d95f02",
    node.METHOD_RANDOM_SOURCE: "#1b9e77",
    node.METHOD_DEGREE_SOURCE: "#7570b3",
    node.METHOD_FROZEN_SOURCE: "#e7298a",
}
SEEDS = [20260513, 20260514, 20260515, 20260516, 20260517]
SOURCE_BUDGET = 64
CHECKPOINT_TARGETS = [0.0, 0.1, 0.2, 0.3, 0.5]
DISTANCE_PAIR_LIMIT = 64


def write_csv(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temp, index=False, encoding="utf-8-sig")
    temp.replace(path)


def write_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def mean(values):
    values = [float(value) for value in values if value is not None and not pd.isna(value)]
    return float(sum(values) / len(values)) if values else np.nan


def markdown_table(frame, columns):
    if frame.empty:
        return "无结果"
    view = frame[columns].copy().round(4)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in view.iterrows():
        values = []
        for column in columns:
            value = row[column]
            values.append("" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def safe_name(text):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(text))


def display_path(path):
    path = Path(path)
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_pilot_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def selected_networks(config, smoke=False):
    selected = list(config["selection"]["selected_networks"] if "selection" in config else config["selected_networks"])
    if not smoke:
        return selected
    result = []
    for dataset_group in ["synthetic45", "realworld_completed"]:
        group = [row for row in selected if row["dataset_group"] == dataset_group]
        result.extend(group[:2])
    return result


def load_graphs(config, smoke=False):
    selected = selected_networks(config, smoke=smoke)
    ids = {row["graph_id"] for row in selected}
    args = SimpleNamespace(datasets="synthetic45,realworld_completed", graph_ids=",")
    found = {}
    for dataset_group, meta, graph in node.load_all_graphs(args):
        if meta["graph_id"] in ids:
            found[(dataset_group, meta["graph_id"])] = (meta, graph)
    missing = sorted(ids - {graph_id for _, graph_id in found})
    if missing:
        raise RuntimeError("Missing selected networks: {}".format(", ".join(missing)))
    return [(row["dataset_group"], row, found[(row["dataset_group"], row["graph_id"])] [1]) for row in selected]


def checkpoint_steps(node_count):
    return {
        target: min(range(max(1, node_count)), key=lambda step: abs(step / float(max(1, node_count)) - target))
        for target in CHECKPOINT_TARGETS
    }


def source_pair_distances(graph, sources, seed, graph_id, method, step):
    sources = sorted(set(sources), key=str)
    pairs = list(itertools.combinations(sources, 2))
    total_pairs = len(pairs)
    if total_pairs == 0:
        return 0.0, 0.0, 0, 0, "all_pairs_if_at_most_64_else_fixed_64_pairs; zero_when_fewer_than_two_sources"
    if total_pairs > DISTANCE_PAIR_LIMIT:
        rng = random.Random(node.stable_seed(seed, graph_id, method, step, "source-distance-pairs"))
        pairs = rng.sample(pairs, DISTANCE_PAIR_LIMIT)
    distances = {}
    values = []
    for source in sorted({pair[0] for pair in pairs}, key=str):
        distances[source] = nx.single_source_shortest_path_length(graph, source)
    for u, v in pairs:
        distance = distances.get(u, {}).get(v)
        if distance is not None:
            values.append(float(distance))
    if not values:
        return 0.0, 0.0, len(pairs), total_pairs, "all_pairs_if_at_most_64_else_fixed_64_pairs; zero_when_fewer_than_two_sources"
    return (
        float(sum(values) / len(values)),
        float(statistics.median(values)),
        len(values),
        total_pairs,
        "all_pairs_if_at_most_64_else_fixed_64_pairs",
    )


def source_community_metrics(graph, partition, sources):
    active = [source for source in sources if source in graph]
    counts = {}
    for source in active:
        community = partition.get(source)
        counts[community] = counts.get(community, 0) + 1
    total_communities = node.community_count(partition)
    coverage = len(counts) / float(total_communities) if total_communities else 0.0
    total = float(len(active))
    entropy = 0.0
    if total:
        for count in counts.values():
            probability = count / total
            entropy -= probability * math.log(probability)
    pair_count = len(active) * (len(active) - 1) // 2
    cross_pairs = 0
    for u, v in itertools.combinations(active, 2):
        if partition.get(u) != partition.get(v):
            cross_pairs += 1
    cross_fraction = cross_pairs / float(pair_count) if pair_count else 0.0
    return coverage, float(entropy), cross_fraction


def scipy_metric(name, x, y):
    if node.scipy_stats is not None:
        try:
            result = getattr(node.scipy_stats, name)(x, y)
            if hasattr(result, "statistic"):
                value = float(result.statistic)
            elif hasattr(result, "correlation"):
                value = float(result.correlation)
            else:
                value = float(result[0])
            return value if not pd.isna(value) else 0.0
        except Exception:
            return 0.0
    return 0.0


def rank_nodes(scores, graph):
    return node.sort_nodes_by_score(scores, graph)


def ranking_metrics(graph, sampled_scores, exact_scores, removed_node):
    nodes = list(graph.nodes())
    sampled_order = rank_nodes(sampled_scores, graph)
    exact_order = rank_nodes(exact_scores, graph)
    exact_rank = {value: index + 1 for index, value in enumerate(exact_order)}
    sampled_values = [float(sampled_scores.get(value, 0.0)) for value in nodes]
    exact_values = [float(exact_scores.get(value, 0.0)) for value in nodes]
    row = {
        "spearman_rank_correlation": scipy_metric("spearmanr", sampled_values, exact_values),
        "kendall_rank_correlation": scipy_metric("kendalltau", sampled_values, exact_values),
        "pearson_score_correlation": float(np.corrcoef(sampled_values, exact_values)[0, 1]) if len(set(sampled_values)) > 1 and len(set(exact_values)) > 1 else 0.0,
        "sampled_score_mean": mean(sampled_values),
        "exact_m5_score_mean": mean(exact_values),
    }
    for fraction, label in [(0.01, "1pct"), (0.05, "5pct"), (0.10, "10pct")]:
        k = max(1, int(math.ceil(len(nodes) * fraction)))
        sampled_top = set(sampled_order[:k])
        exact_top = set(exact_order[:k])
        overlap = len(sampled_top & exact_top)
        row["top_{}_overlap".format(label)] = overlap / float(k)
        row["precision_at_{}".format(label)] = overlap / float(k)
        row["recall_at_{}".format(label)] = overlap / float(k)
    if removed_node in exact_rank:
        rank = exact_rank[removed_node]
        row["removed_node_m5_rank"] = rank
        row["removed_node_m5_rank_percentile"] = (rank - 1) / float(max(1, len(nodes) - 1))
        row["removed_node_m5_top_1pct"] = rank <= max(1, int(math.ceil(len(nodes) * 0.01)))
        row["removed_node_m5_top_5pct"] = rank <= max(1, int(math.ceil(len(nodes) * 0.05)))
        row["removed_node_m5_top_10pct"] = rank <= max(1, int(math.ceil(len(nodes) * 0.10)))
        row["sampled_score_at_removed"] = float(sampled_scores.get(removed_node, 0.0))
        row["exact_m5_score_at_removed"] = float(exact_scores.get(removed_node, 0.0))
    else:
        row["removed_node_m5_rank"] = np.nan
        row["removed_node_m5_rank_percentile"] = np.nan
        row["removed_node_m5_top_1pct"] = np.nan
        row["removed_node_m5_top_5pct"] = np.nan
        row["removed_node_m5_top_10pct"] = np.nan
        row["sampled_score_at_removed"] = np.nan
        row["exact_m5_score_at_removed"] = np.nan
    return row


def exact_m5_scores(graph, use_igraph=True):
    scores = node.igraph_scores(graph, "betweenness") if use_igraph else None
    if scores is None:
        scores = nx.betweenness_centrality(graph, normalized=True, weight=None)
    return scores


def run_diagnostic(dataset_group, meta, graph0, method, seed, args):
    graph_id = meta["graph_id"]
    run_dir = args.output_dir / "runs" / dataset_group / safe_name(graph_id) / safe_name(method) / "B64" / "seed{}".format(seed)
    summary_path = run_dir / "summary.json"
    source_path = run_dir / "source_step_metrics.csv"
    ranking_path = run_dir / "ranking_step_metrics.csv"
    if not args.force and summary_path.exists() and source_path.exists() and ranking_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("status") == "finished":
            return summary, pd.read_csv(source_path), pd.read_csv(ranking_path)

    run_dir.mkdir(parents=True, exist_ok=True)
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    state = {"initial_gcc": node.largest_cc_graph(graph)}
    previous_sources = None
    source_rows = []
    ranking_rows = []
    targets = checkpoint_steps(original_n)
    checkpoint_by_step = {step: target for target, step in targets.items()}
    started = time.perf_counter()
    step = 0
    status = "finished"
    while graph.number_of_nodes() > 0:
        h_graph = node.largest_cc_graph(graph)
        if h_graph.number_of_nodes() == 0:
            break
        sources, source_info = node.choose_source_set(
            h_graph, method, SOURCE_BUDGET, seed, graph_id, step, state
        )
        sampled_scores = node.shared_node_dependencies(h_graph, sources)
        ordered = rank_nodes(sampled_scores, h_graph)
        removed_node = ordered[0] if ordered else None
        partition = node.louvain_partition(h_graph, seed)
        coverage, entropy, cross_pair_fraction = source_community_metrics(h_graph, partition, sources)
        distance_mean, distance_median, distance_sample_count, distance_total_count, distance_rule = source_pair_distances(
            h_graph, sources, seed, graph_id, method, step
        )
        source_set = set(sources)
        jaccard = 1.0
        if previous_sources is not None:
            union = previous_sources | source_set
            jaccard = len(previous_sources & source_set) / float(len(union)) if union else 1.0
        degrees = [h_graph.degree(source) for source in sources]
        proxy_values = [sampled_scores.get(source, 0.0) for source in sources]
        source_row = {
            "dataset_group": dataset_group,
            "graph_id": graph_id,
            "graph_name": meta.get("graph_name", graph_id),
            "graph_type": meta.get("graph_type", "unknown"),
            "method": method,
            "seed": int(seed),
            "source_budget": SOURCE_BUDGET,
            "step": int(step),
            "removed_node": removed_node,
            "remove_ratio": step / float(max(1, original_n)),
            "gcc_ratio": node.gcc_ratio(graph, original_n),
            "current_gcc_node_count": int(h_graph.number_of_nodes()),
            "active_source_count": int(source_info["active_source_count"]),
            "effective_source_fraction": float(source_info["effective_source_fraction"]),
            "community_count": int(source_info["community_count"]),
            "community_coverage": coverage,
            "community_entropy": entropy,
            "boundary_source_fraction": float(source_info["boundary_source_fraction"]),
            "cross_community_source_pair_fraction": cross_pair_fraction,
            "source_pairwise_distance_mean": distance_mean,
            "source_pairwise_distance_median": distance_median,
            "source_pair_sample_count": distance_sample_count,
            "source_pair_total_count": distance_total_count,
            "source_pair_sampling_rule": distance_rule,
            "source_set_jaccard_previous_step": jaccard,
            "positive_dependency_node_fraction": sum(1 for value in sampled_scores.values() if value > 0) / float(h_graph.number_of_nodes()) if h_graph.number_of_nodes() else np.nan,
            "source_node_degree_mean": mean(degrees),
            "source_node_degree_median": statistics.median(degrees) if degrees else np.nan,
            "source_betweenness_proxy_mean": mean(proxy_values),
            "source_set_size_over_current_gcc": len(sources) / float(h_graph.number_of_nodes()) if h_graph.number_of_nodes() else np.nan,
            "source_set_hash": source_info["source_set_hash"],
            "active_source_hash": source_info["active_source_hash"],
            "source_set_scope": source_info["source_set_scope"],
            "louvain_seed": source_info["louvain_seed"],
            "candidate_node_count": source_info["candidate_node_count"],
            "candidate_set_scope": source_info["candidate_set_scope"],
            "candidate_is_current_gcc": source_info["candidate_is_current_gcc"],
            "source_nodes_json": json.dumps(sorted(sources, key=str), ensure_ascii=False),
        }
        source_rows.append(source_row)

        if step in checkpoint_by_step:
            exact_scores = exact_m5_scores(h_graph, use_igraph=args.use_igraph)
            ranking = ranking_metrics(h_graph, sampled_scores, exact_scores, removed_node)
            ranking.update(
                {
                    "dataset_group": dataset_group,
                    "graph_id": graph_id,
                    "graph_name": meta.get("graph_name", graph_id),
                    "method": method,
                    "seed": int(seed),
                    "source_budget": SOURCE_BUDGET,
                    "checkpoint_target_ratio": checkpoint_by_step[step],
                    "checkpoint_step": int(step),
                    "actual_remove_ratio": step / float(max(1, original_n)),
                    "current_gcc_node_count": int(h_graph.number_of_nodes()),
                    "source_set_hash": source_info["source_set_hash"],
                    "active_source_count": int(source_info["active_source_count"]),
                    "removed_node": removed_node,
                }
            )
            ranking_rows.append(ranking)

        previous_sources = source_set
        if removed_node is None or removed_node not in graph:
            status = "failed"
            break
        graph.remove_node(removed_node)
        step += 1
        if step >= original_n:
            break

    source_frame = pd.DataFrame(source_rows)
    ranking_frame = pd.DataFrame(ranking_rows)
    if source_frame.empty or ranking_frame.empty:
        status = "failed"
    runtime = time.perf_counter() - started
    normalized_auc = np.nan
    if not source_frame.empty:
        observed = float(source_frame["remove_ratio"].iloc[-1])
        normalized_auc = node.trapezoid_auc(
            source_frame["gcc_ratio"].astype(float).values,
            source_frame["remove_ratio"].astype(float).values,
        ) / observed if observed > 0 else np.nan
    summary = {
        "dataset_group": dataset_group,
        "graph_id": graph_id,
        "method": method,
        "seed": int(seed),
        "source_budget": SOURCE_BUDGET,
        "status": status,
        "runtime_seconds": runtime,
        "normalized_auc": normalized_auc,
        "source_step_count": int(len(source_frame)),
        "ranking_checkpoint_count": int(len(ranking_frame)),
    }
    write_json(summary, summary_path)
    write_csv(source_frame, source_path)
    write_csv(ranking_frame, ranking_path)
    return summary, source_frame, ranking_frame


def run_all(args, config, smoke=False):
    graphs = load_graphs(config, smoke=smoke)
    summaries = []
    source_frames = []
    ranking_frames = []
    total = len(graphs) * len(SOURCE_METHODS) * len(SEEDS)
    completed = 0
    for dataset_group, meta, graph in graphs:
        for method in SOURCE_METHODS:
            for seed in SEEDS:
                print(
                    "mechanism {} {}/{} {} {} seed={}".format(
                        "smoke" if smoke else "full", completed + 1, total, dataset_group, method, seed
                    ),
                    flush=True,
                )
                summary, source_frame, ranking_frame = run_diagnostic(
                    dataset_group, meta, graph, method, seed, args
                )
                summaries.append(summary)
                source_frames.append(source_frame)
                ranking_frames.append(ranking_frame)
                completed += 1
                print(
                    "mechanism-status {} {} auc={}".format(
                        summary["status"], summary["graph_id"], summary["normalized_auc"]
                    ),
                    flush=True,
                )
    prefix = "mechanism_smoke" if smoke else "mechanism"
    write_csv(pd.DataFrame(summaries), args.output_dir / "{}_run_summary.csv".format(prefix))
    write_csv(pd.concat(source_frames, ignore_index=True, sort=False), args.output_dir / "{}_source_step_metrics.csv".format(prefix))
    write_csv(pd.concat(ranking_frames, ignore_index=True, sort=False), args.output_dir / "{}_ranking_step_metrics.csv".format(prefix))
    return pd.DataFrame(summaries), pd.concat(source_frames, ignore_index=True, sort=False), pd.concat(ranking_frames, ignore_index=True, sort=False)


def coerce_graph_node(value, graph):
    if value in graph:
        return value
    if isinstance(value, float) and value.is_integer() and int(value) in graph:
        return int(value)
    text = str(value)
    if text in graph:
        return text
    return value


def recompute_rankings_from_saved_source(config, source):
    """Recompute ranking metrics from saved trajectories without rerunning attacks."""
    args = SimpleNamespace(datasets="synthetic45,realworld_completed", graph_ids="")
    graph_lookup = {}
    selected_ids = {row["graph_id"] for row in selected_networks(config, smoke=False)}
    for dataset_group, meta, graph in node.load_all_graphs(args):
        if meta["graph_id"] in selected_ids:
            graph_lookup[(dataset_group, meta["graph_id"])] = (meta, graph)

    rows = []
    grouped = source.groupby(["dataset_group", "graph_id", "method", "seed"], sort=False)
    for (dataset_group, graph_id, method, seed), group in grouped:
        meta, graph0 = graph_lookup[(dataset_group, graph_id)]
        graph = graph0.copy()
        original_n = graph.number_of_nodes()
        target_steps = checkpoint_steps(original_n)
        checkpoint_by_step = {step: target for target, step in target_steps.items()}
        for _, saved in group.sort_values("step").iterrows():
            step = int(saved["step"])
            h_graph = node.largest_cc_graph(graph)
            raw_sources = json.loads(saved["source_nodes_json"])
            sources = [coerce_graph_node(value, h_graph) for value in raw_sources]
            sources = [value for value in sources if value in h_graph]
            sampled_scores = node.shared_node_dependencies(h_graph, sources)
            removed_node = coerce_graph_node(saved["removed_node"], graph) if not pd.isna(saved["removed_node"]) else None
            if step in checkpoint_by_step:
                exact_scores = exact_m5_scores(h_graph, use_igraph=True)
                ranking = ranking_metrics(h_graph, sampled_scores, exact_scores, removed_node)
                ranking.update(
                    {
                        "dataset_group": dataset_group,
                        "graph_id": graph_id,
                        "graph_name": meta.get("graph_name", graph_id),
                        "method": method,
                        "seed": int(seed),
                        "source_budget": SOURCE_BUDGET,
                        "checkpoint_target_ratio": checkpoint_by_step[step],
                        "checkpoint_step": step,
                        "actual_remove_ratio": float(saved["remove_ratio"]),
                        "current_gcc_node_count": int(h_graph.number_of_nodes()),
                        "source_set_hash": saved["source_set_hash"],
                        "active_source_count": int(saved["active_source_count"]),
                        "removed_node": removed_node,
                    }
                )
                rows.append(ranking)
            if removed_node is None or removed_node not in graph:
                break
            graph.remove_node(removed_node)
    return pd.DataFrame(rows)


def validate_smoke(summaries, source, ranking):
    checks = {
        "run_count": len(summaries) == 80,
        "network_count": summaries[["dataset_group", "graph_id"]].drop_duplicates().shape[0] == 4,
        "method_count": summaries["method"].nunique() == 4,
        "seed_count": summaries["seed"].nunique() == 5,
        "all_finished": summaries["status"].eq("finished").all(),
        "source_rows_nonempty": len(source) > 0,
        "ranking_rows_nonempty": len(ranking) == 80 * len(CHECKPOINT_TARGETS),
        "source_budget_correct": source["source_budget"].eq(SOURCE_BUDGET).all(),
        "active_source_valid": (
            source["active_source_count"].between(0, SOURCE_BUDGET).all()
            and source.loc[source["method"].ne(node.METHOD_FROZEN_SOURCE), "active_source_count"].ge(1).all()
        ),
        "candidate_scope_valid": source["candidate_set_scope"].eq("current_gcc_all_nodes").all() and source["candidate_is_current_gcc"].all(),
        "no_nan_core_source_metrics": not source[["community_coverage", "community_entropy", "source_pairwise_distance_mean", "positive_dependency_node_fraction"]].isna().any().any(),
        "no_nan_core_ranking_metrics": not ranking[["spearman_rank_correlation", "top_5pct_overlap", "pearson_score_correlation"]].isna().any().any(),
    }
    checks = {key: bool(value) for key, value in checks.items()}
    checks["passed"] = bool(all(checks.values()))
    return checks


def load_existing_delta_policy():
    if not PILOT_RESULTS.exists():
        return pd.DataFrame(columns=["dataset_group", "graph_id", "delta_policy"])
    per = pd.read_csv(PILOT_RESULTS, encoding="utf-8-sig")
    per = per[(per["source_budget"].eq(SOURCE_BUDGET)) & per["method"].isin([node.METHOD_STRUCTURED, node.METHOD_RANDOM_SOURCE])].copy()
    grouped = per.groupby(["dataset_group", "graph_id", "method"], as_index=False)["normalized_auc"].mean()
    pivot = grouped.pivot_table(index=["dataset_group", "graph_id"], columns="method", values="normalized_auc").reset_index()
    pivot["delta_policy"] = pivot[node.METHOD_STRUCTURED] - pivot[node.METHOD_RANDOM_SOURCE]
    return pivot[["dataset_group", "graph_id", "delta_policy"]]


def summary_stats(source, ranking):
    source_numeric = [
        "community_coverage", "community_entropy", "source_pairwise_distance_mean",
        "source_pairwise_distance_median", "boundary_source_fraction",
        "cross_community_source_pair_fraction", "positive_dependency_node_fraction",
        "source_node_degree_mean", "source_node_degree_median",
        "source_betweenness_proxy_mean", "source_set_size_over_current_gcc",
        "source_set_jaccard_previous_step",
    ]
    rows = []
    for (dataset, method), group in source.groupby(["dataset_group", "method"]):
        row = {"dataset_group": dataset, "method": method, "run_count": group[["graph_id", "seed"]].drop_duplicates().shape[0], "step_count": len(group)}
        for column in source_numeric:
            row["mean_" + column] = pd.to_numeric(group[column], errors="coerce").mean()
            row["std_" + column] = pd.to_numeric(group[column], errors="coerce").std()
        rows.append(row)
    return pd.DataFrame(rows)


def initial_overlap(source):
    initial = source[source["step"].eq(0)].copy()
    rows = []
    for (dataset, graph_id, seed), group in initial.groupby(["dataset_group", "graph_id", "seed"]):
        sets = {}
        for _, row in group.iterrows():
            try:
                sets[row["method"]] = set(json.loads(row["source_nodes_json"]))
            except Exception:
                sets[row["method"]] = set()
        for left, right in itertools.combinations(SOURCE_METHODS, 2):
            left_set = sets.get(left, set())
            right_set = sets.get(right, set())
            union = left_set | right_set
            rows.append(
                {
                    "dataset_group": dataset,
                    "graph_id": graph_id,
                    "seed": int(seed),
                    "left_method": left,
                    "right_method": right,
                    "left_label": METHOD_LABELS[left],
                    "right_label": METHOD_LABELS[right],
                    "left_source_count": len(left_set),
                    "right_source_count": len(right_set),
                    "initial_source_jaccard": len(left_set & right_set) / float(len(union)) if union else np.nan,
                }
            )
    return pd.DataFrame(rows)


def ranking_summary(ranking):
    metrics = [
        "spearman_rank_correlation", "kendall_rank_correlation", "pearson_score_correlation",
        "top_1pct_overlap", "top_5pct_overlap", "top_10pct_overlap",
        "removed_node_m5_rank_percentile", "removed_node_m5_top_1pct",
        "removed_node_m5_top_5pct", "removed_node_m5_top_10pct",
    ]
    rows = []
    for (dataset, method, target), group in ranking.groupby(["dataset_group", "method", "checkpoint_target_ratio"]):
        row = {"dataset_group": dataset, "method": method, "checkpoint_target_ratio": target, "run_count": group[["graph_id", "seed"]].drop_duplicates().shape[0], "checkpoint_count": len(group)}
        for column in metrics:
            values = pd.to_numeric(group[column], errors="coerce")
            row["mean_" + column] = values.mean()
            row["std_" + column] = values.std()
        rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_ci(values, seed=20260513, iterations=2000):
    values = np.asarray([value for value in values if not pd.isna(value)], dtype=float)
    if len(values) == 0:
        return np.nan, np.nan
    rng = np.random.RandomState(seed)
    means = [np.mean(rng.choice(values, size=len(values), replace=True)) for _ in range(iterations)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired_test(left, right, dataset, comparison, metric, level):
    merged = left.merge(right, on=["dataset_group", "graph_id", "seed"] + (["checkpoint_target_ratio"] if level == "ranking" else []), suffixes=("_left", "_right"))
    delta = pd.to_numeric(merged[metric + "_left"], errors="coerce") - pd.to_numeric(merged[metric + "_right"], errors="coerce")
    delta = delta.dropna()
    p_value = np.nan
    if node.scipy_stats is not None and len(delta):
        try:
            p_value = float(node.scipy_stats.wilcoxon(delta).pvalue)
        except Exception:
            p_value = np.nan
    ci_low, ci_high = bootstrap_ci(delta)
    return {
        "dataset_group": dataset,
        "level": level,
        "comparison": comparison,
        "metric": metric,
        "n_pairs": int(len(delta)),
        "mean_delta_left_minus_right": float(delta.mean()) if len(delta) else np.nan,
        "median_delta_left_minus_right": float(delta.median()) if len(delta) else np.nan,
        "wins_left_lower": int((delta < 0).sum()),
        "ties": int((delta.abs() <= 1e-12).sum()),
        "losses_left_higher": int((delta > 0).sum()),
        "wilcoxon_p": p_value,
        "bootstrap_ci95_low": ci_low,
        "bootstrap_ci95_high": ci_high,
    }


def statistical_tests(source, ranking):
    rows = []
    initial = source[source["step"].eq(0)].copy()
    comparisons = [
        (node.METHOD_STRUCTURED, node.METHOD_RANDOM_SOURCE),
        (node.METHOD_STRUCTURED, node.METHOD_DEGREE_SOURCE),
        (node.METHOD_STRUCTURED, node.METHOD_FROZEN_SOURCE),
    ]
    initial_metrics = ["community_coverage", "community_entropy", "source_pairwise_distance_mean", "boundary_source_fraction", "positive_dependency_node_fraction"]
    for dataset in sorted(initial["dataset_group"].unique()):
        group = initial[initial["dataset_group"].eq(dataset)]
        for left, right in comparisons:
            for metric in initial_metrics:
                left_frame = group[group["method"].eq(left)][["dataset_group", "graph_id", "seed", metric]]
                right_frame = group[group["method"].eq(right)][["dataset_group", "graph_id", "seed", metric]]
                row = paired_test(left_frame, right_frame, dataset, METHOD_LABELS[left] + " vs " + METHOD_LABELS[right], metric, "initial_source")
                rows.append(row)
    ranking_metrics_to_test = ["spearman_rank_correlation", "kendall_rank_correlation", "top_5pct_overlap", "top_10pct_overlap", "removed_node_m5_rank_percentile"]
    for dataset in sorted(ranking["dataset_group"].unique()):
        group = ranking[ranking["dataset_group"].eq(dataset)]
        for left, right in comparisons:
            for metric in ranking_metrics_to_test:
                left_frame = group[group["method"].eq(left)][["dataset_group", "graph_id", "seed", "checkpoint_target_ratio", metric]]
                right_frame = group[group["method"].eq(right)][["dataset_group", "graph_id", "seed", "checkpoint_target_ratio", metric]]
                rows.append(paired_test(left_frame, right_frame, dataset, METHOD_LABELS[left] + " vs " + METHOD_LABELS[right], metric, "ranking_checkpoint"))
    return pd.DataFrame(rows)


def associations(source, ranking):
    delta = load_existing_delta_policy()
    rows = []
    source_avg = source.groupby(["dataset_group", "graph_id", "method"], as_index=False)[[
        "community_coverage", "community_entropy", "source_pairwise_distance_mean", "boundary_source_fraction", "positive_dependency_node_fraction", "source_set_jaccard_previous_step"
    ]].mean()
    rank_avg = ranking.groupby(["dataset_group", "graph_id", "method"], as_index=False)[[
        "spearman_rank_correlation", "kendall_rank_correlation", "top_5pct_overlap", "removed_node_m5_rank_percentile"
    ]].mean()
    for frame, metrics, level in [(source_avg, ["community_coverage", "community_entropy", "source_pairwise_distance_mean", "boundary_source_fraction", "positive_dependency_node_fraction", "source_set_jaccard_previous_step"], "source_diversity"), (rank_avg, ["spearman_rank_correlation", "kendall_rank_correlation", "top_5pct_overlap", "removed_node_m5_rank_percentile"], "ranking")]:
        merged = frame.merge(delta, on=["dataset_group", "graph_id"], how="inner")
        for method in SOURCE_METHODS:
            subset = merged[merged["method"].eq(method)]
            for metric in metrics:
                x = pd.to_numeric(subset[metric], errors="coerce")
                y = pd.to_numeric(subset["delta_policy"], errors="coerce")
                valid = x.notna() & y.notna()
                x = x[valid]
                y = y[valid]
                rows.append({
                    "dataset_group": subset["dataset_group"].iloc[0] if not subset.empty else "",
                    "method": method,
                    "level": level,
                    "metric": metric,
                    "n_networks": int(len(x)),
                    "delta_policy_definition": "AUC_structured - AUC_random_source",
                    "spearman_with_delta_policy": scipy_metric("spearmanr", list(x), list(y)) if len(x) >= 3 else np.nan,
                    "pearson_with_delta_policy": float(np.corrcoef(x, y)[0, 1]) if len(x) >= 3 and len(set(x)) > 1 and len(set(y)) > 1 else np.nan,
                })
    return pd.DataFrame(rows)


def plot_metric(source, column, ylabel, filename):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for axis, dataset in zip(axes, ["synthetic45", "realworld_completed"]):
        group = source[source["dataset_group"].eq(dataset)]
        values = group.groupby("method")[column].agg(["mean", "std"]).reindex(SOURCE_METHODS)
        axis.bar([METHOD_LABELS[m] for m in SOURCE_METHODS], values["mean"], yerr=values["std"], color=[COLORS[m] for m in SOURCE_METHODS], alpha=0.85, capsize=3)
        axis.set_title(dataset)
        axis.set_ylabel(ylabel)
        axis.tick_params(axis="x", rotation=25)
        axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "plots" / filename, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_source_delta(source):
    delta = load_existing_delta_policy()
    averaged = source.groupby(["dataset_group", "graph_id", "method"], as_index=False)[["community_entropy", "source_pairwise_distance_mean", "boundary_source_fraction", "positive_dependency_node_fraction"]].mean()
    frame = averaged.merge(delta, on=["dataset_group", "graph_id"], how="inner")
    fig, axes = plt.subplots(2, 2, figsize=(11, 9), sharex=False)
    metrics = [("community_entropy", "Mean source community entropy"), ("source_pairwise_distance_mean", "Mean source pair distance"), ("boundary_source_fraction", "Mean boundary source fraction"), ("positive_dependency_node_fraction", "Mean positive dependency node fraction")]
    for axis, (metric, label) in zip(axes.ravel(), metrics):
        for method in SOURCE_METHODS:
            group = frame[frame["method"].eq(method)]
            axis.scatter(group[metric], group["delta_policy"], s=28, alpha=0.75, color=COLORS[method], label=METHOD_LABELS[method])
        axis.axhline(0, color="black", linewidth=0.8)
        axis.set_xlabel(label)
        axis.set_ylabel("delta_policy")
        axis.grid(alpha=0.2)
    handles, labels = axes.ravel()[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT_DIR / "plots" / "source_diversity_vs_delta_policy.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_ranking_metric(ranking, column, ylabel, filename):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for axis, dataset in zip(axes, ["synthetic45", "realworld_completed"]):
        group = ranking[ranking["dataset_group"].eq(dataset)]
        for method in SOURCE_METHODS:
            values = group[group["method"].eq(method)].groupby("checkpoint_target_ratio")[column].mean()
            axis.plot(values.index, values.values, marker="o", linewidth=2, color=COLORS[method], label=METHOD_LABELS[method])
        axis.set_title(dataset)
        axis.set_xlabel("Checkpoint remove ratio")
        axis.set_ylabel(ylabel)
        axis.set_xticks(CHECKPOINT_TARGETS)
        axis.grid(alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT_DIR / "plots" / filename, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_ranking_auc(ranking):
    delta = load_existing_delta_policy()
    auc = pd.read_csv(PILOT_RESULTS, encoding="utf-8-sig")
    auc = auc[(auc["source_budget"].eq(SOURCE_BUDGET)) & auc["method"].isin(SOURCE_METHODS)].groupby(["dataset_group", "graph_id", "method"], as_index=False)["normalized_auc"].mean()
    corr = ranking.groupby(["dataset_group", "graph_id", "method"], as_index=False)["spearman_rank_correlation"].mean().merge(auc, on=["dataset_group", "graph_id", "method"], how="inner")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for axis, dataset in zip(axes, ["synthetic45", "realworld_completed"]):
        group = corr[corr["dataset_group"].eq(dataset)]
        for method in SOURCE_METHODS:
            subset = group[group["method"].eq(method)]
            axis.scatter(subset["spearman_rank_correlation"], subset["normalized_auc"], color=COLORS[method], s=32, label=METHOD_LABELS[method])
        axis.set_title(dataset)
        axis.set_xlabel("Mean Spearman correlation with M5")
        axis.set_ylabel("Existing pilot normalized AUC, B=64")
        axis.grid(alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT_DIR / "plots" / "ranking_correlation_vs_auc.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_cases(source):
    delta = load_existing_delta_policy()
    graph_delta = delta.sort_values(["delta_policy", "dataset_group", "graph_id"])
    failure = graph_delta.iloc[-1]
    success = graph_delta.iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for axis, case, title in [(axes[0], failure, "Structured failure case"), (axes[1], success, "Random-source success case")]:
        group = source[(source["dataset_group"].eq(case["dataset_group"])) & (source["graph_id"].eq(case["graph_id"]))]
        for method in SOURCE_METHODS:
            values = group[group["method"].eq(method)].groupby("remove_ratio")["gcc_ratio"].mean().sort_index()
            axis.plot(values.index, values.values, color=COLORS[method], linewidth=2, label=METHOD_LABELS[method])
        axis.set_title("{}\n{} / {}\ndelta_policy={:.4f}".format(title, case["dataset_group"], case["graph_id"], case["delta_policy"]))
        axis.set_xlabel("Removed-node ratio")
        axis.set_ylabel("GCC node ratio")
        axis.grid(alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT_DIR / "plots" / "structured_failure_random_success_cases.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    return {"structured_failure": failure.to_dict(), "random_source_success": success.to_dict()}


def write_report(config, summaries, source, ranking, source_summary, ranking_summary_frame, tests, assoc, cases, smoke_checks, runtime_seconds):
    runtime_seconds = float(pd.to_numeric(summaries["runtime_seconds"], errors="coerce").sum())
    auc_delta = load_existing_delta_policy()
    auc = pd.read_csv(PILOT_RESULTS, encoding="utf-8-sig")
    auc = auc[(auc["source_budget"].eq(SOURCE_BUDGET)) & auc["method"].isin(SOURCE_METHODS)]
    auc_means = auc.groupby(["dataset_group", "method"], as_index=False)["normalized_auc"].mean()
    policy_rows = []
    for dataset, group in auc_delta.groupby("dataset_group"):
        delta = pd.to_numeric(group["delta_policy"], errors="coerce").dropna()
        policy_rows.append({
            "dataset_group": dataset,
            "mean_delta_structured_minus_random": delta.mean(),
            "median_delta_structured_minus_random": delta.median(),
            "structured_better": int((delta < 0).sum()),
            "ties": int((delta.abs() <= 1e-12).sum()),
            "structured_worse": int((delta > 0).sum()),
        })
    policy_summary = pd.DataFrame(policy_rows)
    ranking_means = ranking.groupby(["dataset_group", "method"], as_index=False)[[
        "spearman_rank_correlation", "kendall_rank_correlation", "top_5pct_overlap"
    ]].mean()
    rank_policy_rows = []
    for dataset in sorted(ranking["dataset_group"].unique()):
        group = ranking[ranking["dataset_group"].eq(dataset)]
        pivot = group.pivot_table(index=["graph_id", "seed", "checkpoint_target_ratio"], columns="method", values="spearman_rank_correlation")
        delta = (pivot["SASB-N-structured"] - pivot["SASB-N-random-source"]).dropna()
        rank_policy_rows.append({"dataset_group": dataset, "mean_spearman_delta": delta.mean(), "median_spearman_delta": delta.median()})
    source_means = source.groupby(["dataset_group", "method"], as_index=False)[[
        "community_coverage", "community_entropy", "source_pairwise_distance_mean", "boundary_source_fraction"
    ]].mean()
    source_policy_rows = []
    for dataset in sorted(source["dataset_group"].unique()):
        group = source_means[source_means["dataset_group"].eq(dataset)].set_index("method")
        source_policy_rows.append({
            "dataset_group": dataset,
            "delta_community_coverage": group.loc["SASB-N-structured", "community_coverage"] - group.loc["SASB-N-random-source", "community_coverage"],
            "delta_community_entropy": group.loc["SASB-N-structured", "community_entropy"] - group.loc["SASB-N-random-source", "community_entropy"],
            "delta_source_pairwise_distance": group.loc["SASB-N-structured", "source_pairwise_distance_mean"] - group.loc["SASB-N-random-source", "source_pairwise_distance_mean"],
            "delta_boundary_fraction": group.loc["SASB-N-structured", "boundary_source_fraction"] - group.loc["SASB-N-random-source", "boundary_source_fraction"],
        })
    lines = [
        "# SASB-N Mechanism Diagnostic Report",
        "",
        "## 1. 实验目的",
        "",
        "本实验只诊断两个问题：structured source policy 为什么可能不如 random-source，以及四种 source policy 的节点排序谁更接近精确 M5 node betweenness。它不重新分析其他 pilot budget，也不运行 73 网络正式实验。",
        "",
        "## 2. 实验定义",
        "",
        "源点多样性指标在每种策略自己的动态攻击轨迹中逐步计算。不同策略的逐步轨迹不同，因此不做逐步 source-set Jaccard 横向比较；跨策略 source-set overlap 只在相同初始图状态下计算。",
        "",
        "排序指标在每种策略自己的当前 GCC 上计算：先用该策略当前源点集合得到 sampled dependency，再在同一个当前 GCC 上计算精确 M5 node betweenness。checkpoint 为 remove ratio 最接近 0、0.1、0.2、0.3、0.5 的 step。",
        "",
        "## 3. 数据和实验设置",
        "",
        "- 网络：pilot 中 24 个网络，synthetic45 12 个、realworld_completed 12 个。",
        "- 方法：SASB-N-structured、SASB-N-random-source、SASB-N-degree-source、SASB-N-frozen-source。",
        "- source budget：固定为 B=64。",
        "- seeds：20260513--20260517。",
        "- 源点距离：源点对不超过 64 对时使用全部源点对，否则使用由 `stable_seed(seed, graph_id, method, step, source-distance-pairs)` 固定抽取的 64 对。",
        "- source betweenness proxy：当前 sampled dependency score 在源点上的均值，不是精确 M5 betweenness。",
        "",
        "## 4. Smoke 验证",
        "",
        "```json",
        json.dumps(smoke_checks, indent=2, ensure_ascii=False),
        "```",
        "",
        "## 5. 源点多样性结果",
        "",
        "下表是按 dataset 和 strategy 汇总的逐步结果。不同策略的均值用于描述策略行为，不表示它们在同一图状态上逐步配对。",
        "",
    ]
    diversity_columns = ["dataset_group", "method", "step_count", "mean_community_coverage", "mean_community_entropy", "mean_source_pairwise_distance_mean", "mean_boundary_source_fraction", "mean_positive_dependency_node_fraction", "mean_source_set_jaccard_previous_step"]
    lines.append(markdown_table(source_summary, diversity_columns))
    lines += [
        "",
        "## 6. 节点排序相关性结果",
        "",
        "排序结果按 checkpoint 汇总；正相关表示 sampled dependency 排序更接近精确 M5 排序。",
        "",
    ]
    rank_columns = ["dataset_group", "method", "checkpoint_target_ratio", "mean_spearman_rank_correlation", "mean_kendall_rank_correlation", "mean_top_5pct_overlap", "mean_removed_node_m5_rank_percentile"]
    lines.append(markdown_table(ranking_summary_frame, rank_columns))
    lines += [
        "",
        "## Numeric comparison for the mechanism question",
        "",
        "The following tables make the structured versus random-source comparison explicit. Negative AUC delta means structured is better; positive means structured is worse.",
        "",
    ]
    lines.append(markdown_table(policy_summary, ["dataset_group", "mean_delta_structured_minus_random", "median_delta_structured_minus_random", "structured_better", "ties", "structured_worse"]))
    lines += ["", "Mean B=64 normalized AUC by source policy:", ""]
    lines.append(markdown_table(auc_means, ["dataset_group", "method", "normalized_auc"]))
    lines += [
        "",
        "## Structured versus M5 ranking correlation",
        "",
        "Each value compares sampled dependency with exact M5 node betweenness on the same policy-specific current GCC; ranking correlation is not equivalent to dismantling AUC.",
        "",
    ]
    lines.append(markdown_table(ranking_means, ["dataset_group", "method", "spearman_rank_correlation", "kendall_rank_correlation", "top_5pct_overlap"]))
    lines += ["", "Structured minus random-source mean Spearman correlation:", ""]
    lines.append(markdown_table(pd.DataFrame(rank_policy_rows), ["dataset_group", "mean_spearman_delta", "median_spearman_delta"]))
    lines += [
        "",
        "## Structured versus random-source source diversity",
        "",
        "These are trajectory-level mean differences, not stepwise paired comparisons across policies.",
        "",
    ]
    lines.append(markdown_table(pd.DataFrame(source_policy_rows), ["dataset_group", "delta_community_coverage", "delta_community_entropy", "delta_source_pairwise_distance", "delta_boundary_fraction"]))
    lines += [
        "",
        "## 7. Structured 与 random-source",
        "",
        "初始 source-set overlap 见 `source_policy_initial_overlap.csv`。source diversity 和 ranking 的 paired tests 见 `mechanism_statistical_tests.csv`。delta_policy 使用已有 pilot 的 B=64 结果定义为 `AUC_structured - AUC_random_source`，本诊断不重新运行其他 budget。",
        "",
        "## 8. 机制解释和证据边界",
        "",
        "本报告不直接声称结构化偏差有益。若 structured 的 boundary fraction 较高、community entropy 或 source distance 较低，同时排序相关性和 AUC 较差，则更符合当前 boundary-first 规则引入不利偏差的解释；若排序相关性较低但 AUC 较好，则说明瓦解目标不要求完全恢复 M5 排序；若 random-source 的排序相关性和 AUC 都更好，则当前结构化规则没有显示优势；若 structured 社区覆盖更好但 AUC 更差，则社区覆盖本身不能保证覆盖真正的高介数路径。",
        "",
        "## 9. 案例",
        "",
        "案例图按已有 B=64 pilot 的 delta_policy 选择极端网络，仅用于机制展示，不作为主要证据，也不删除任何负结果。",
        "",
        "- structured failure case：`{}/{}; delta_policy={:.4f}`。".format(cases["structured_failure"]["dataset_group"], cases["structured_failure"]["graph_id"], cases["structured_failure"]["delta_policy"]),
        "- random-source success case：`{}/{}; delta_policy={:.4f}`。".format(cases["random_source_success"]["dataset_group"], cases["random_source_success"]["graph_id"], cases["random_source_success"]["delta_policy"]),
        "",
        "## 10. 运行和输出",
        "",
        "- 诊断运行数：{}。".format(len(summaries)),
        "- 完成数：{}；失败数：{}。".format(int(summaries["status"].eq("finished").sum()), int((~summaries["status"].eq("finished")).sum())),
        "- source step rows：{}；ranking checkpoint rows：{}。".format(len(source), len(ranking)),
        "- 累计运行时间：{:.2f} 秒。".format(runtime_seconds),
        "",
        "## 11. 下一步建议",
        "",
        "下一版应根据本诊断中 source diversity、排序相关性和 AUC 的共同证据决定：继续改进 structured 的 boundary-first 规则，还是将 random-source 作为更稳健的采样基线。仅凭单一 AUC 或单一排序相关性不能做出主方法决策。",
    ]
    (OUT_DIR / "mechanism_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def aggregate_and_write(config, summaries, source, ranking, smoke_checks, runtime_seconds):
    source = source.copy()
    for column in ["community_coverage", "cross_community_source_pair_fraction", "boundary_source_fraction"]:
        if column in source.columns:
            source[column] = pd.to_numeric(source[column], errors="coerce").fillna(0.0)
    required_ranking = {"spearman_rank_correlation", "kendall_rank_correlation", "pearson_score_correlation"}
    if ranking.empty or not required_ranking.issubset(set(ranking.columns)):
        ranking = recompute_rankings_from_saved_source(config, source)
        write_csv(ranking, OUT_DIR / "mechanism_ranking_step_metrics.csv")
    write_csv(source, OUT_DIR / "source_diversity_step_metrics.csv")
    write_csv(source, OUT_DIR / "mechanism_source_step_metrics.csv")
    write_csv(ranking, OUT_DIR / "ranking_correlation_step_metrics.csv")
    source_summary = summary_stats(source, ranking)
    overlap = initial_overlap(source)
    rank_summary = ranking_summary(ranking)
    tests = statistical_tests(source, ranking)
    assoc = associations(source, ranking)
    write_csv(source_summary, OUT_DIR / "source_diversity_summary.csv")
    write_csv(overlap, OUT_DIR / "source_policy_initial_overlap.csv")
    write_csv(rank_summary, OUT_DIR / "ranking_correlation_summary.csv")
    write_csv(pd.concat([tests, assoc.assign(level="association")], ignore_index=True, sort=False), OUT_DIR / "mechanism_statistical_tests.csv")
    plot_metric(source, "community_coverage", "Source community coverage", "community_coverage_by_policy.png")
    plot_metric(source, "community_entropy", "Source community entropy", "community_entropy_by_policy.png")
    plot_metric(source, "source_pairwise_distance_mean", "Mean source pairwise distance", "source_pairwise_distance_by_policy.png")
    plot_metric(source, "boundary_source_fraction", "Boundary source fraction", "boundary_source_fraction_by_policy.png")
    plot_metric(source, "positive_dependency_node_fraction", "Positive dependency node fraction", "positive_dependency_fraction_by_policy.png")
    plot_source_delta(source)
    plot_ranking_metric(ranking, "spearman_rank_correlation", "Spearman correlation with M5", "ranking_spearman_by_checkpoint.png")
    plot_ranking_metric(ranking, "top_5pct_overlap", "Top-5% overlap with M5", "ranking_top5_overlap_by_checkpoint.png")
    plot_ranking_auc(ranking)
    cases = plot_cases(source)
    write_report(config, summaries, source, ranking, source_summary, rank_summary, tests, assoc, cases, smoke_checks, runtime_seconds)
    return source_summary, overlap, rank_summary, tests, assoc, cases


def parse_args():
    parser = argparse.ArgumentParser(description="Run SASB-N mechanism diagnostics.")
    parser.add_argument("--stage", choices=["smoke", "full", "aggregate", "all"], default="all")
    parser.add_argument("--pilot-config", type=Path, default=PILOT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--use-igraph", action="store_true", default=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    args.output_dir = Path(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "plots").mkdir(parents=True, exist_ok=True)
    config = load_pilot_config(args.pilot_config)
    mechanism_config = {
        "experiment_name": "SASB-N formal mechanism diagnostic",
        "formal_algorithm_name": "SASB-N",
        "source_budget": SOURCE_BUDGET,
        "seeds": SEEDS,
        "methods": SOURCE_METHODS,
        "checkpoints": CHECKPOINT_TARGETS,
        "pilot_config": display_path(args.pilot_config),
        "selected_network_count": len(selected_networks(config, smoke=False)),
        "selected_networks": selected_networks(config, smoke=False),
        "smoke_networks": selected_networks(config, smoke=True),
        "source_distance_sampling": {
            "pair_limit": DISTANCE_PAIR_LIMIT,
            "rule": "all source pairs if <=64; otherwise fixed 64 pairs sampled with stable_seed(seed, graph_id, method, step, source-distance-pairs)",
        },
        "ranking_reference": "Exact M5 node betweenness is recomputed on each policy's own current GCC at each checkpoint.",
        "delta_policy_source": display_path(PILOT_RESULTS),
        "do_not_rerun_other_budgets": True,
        "do_not_run_full_73_network_experiment": True,
    }
    write_json(mechanism_config, args.output_dir / "mechanism_config.json")
    if args.stage == "smoke":
        started = time.perf_counter()
        summaries, source, ranking = run_all(args, config, smoke=True)
        checks = validate_smoke(summaries, source, ranking)
        write_json(checks, args.output_dir / "mechanism_smoke_validation.json")
        print("mechanism smoke validation: {}".format("passed" if checks["passed"] else "failed"), flush=True)
        if not checks["passed"]:
            raise RuntimeError("Mechanism smoke validation failed: {}".format(checks))
        aggregate_and_write(config, summaries, source, ranking, checks, time.perf_counter() - started)
        return
    if args.stage == "full":
        started = time.perf_counter()
        summaries, source, ranking = run_all(args, config, smoke=False)
        checks = {"passed": True, "mode": "full_only"}
        aggregate_and_write(config, summaries, source, ranking, checks, time.perf_counter() - started)
        return
    if args.stage == "aggregate":
        started = time.perf_counter()
        summary_path = args.output_dir / "mechanism_run_summary.csv"
        source_path = args.output_dir / "mechanism_source_step_metrics.csv"
        ranking_path = args.output_dir / "mechanism_ranking_step_metrics.csv"
        summaries = pd.read_csv(summary_path)
        source = pd.read_csv(source_path)
        ranking = pd.read_csv(ranking_path) if ranking_path.exists() else pd.DataFrame()
        smoke_path = args.output_dir / "mechanism_smoke_validation.json"
        checks = json.loads(smoke_path.read_text(encoding="utf-8")) if smoke_path.exists() else {"passed": True, "mode": "aggregate_only"}
        aggregate_and_write(config, summaries, source, ranking, checks, time.perf_counter() - started)
        print("mechanism diagnostics aggregate complete: {}".format(args.output_dir), flush=True)
        return
    started = time.perf_counter()
    smoke_summaries, smoke_source, smoke_ranking = run_all(args, config, smoke=True)
    checks = validate_smoke(smoke_summaries, smoke_source, smoke_ranking)
    write_json(checks, args.output_dir / "mechanism_smoke_validation.json")
    print("mechanism smoke validation: {}".format("passed" if checks["passed"] else "failed"), flush=True)
    if not checks["passed"]:
        raise RuntimeError("Mechanism smoke validation failed: {}".format(checks))
    full_summaries, full_source, full_ranking = run_all(args, config, smoke=False)
    aggregate_and_write(config, full_summaries, full_source, full_ranking, checks, time.perf_counter() - started)
    print("mechanism diagnostics complete: {}".format(args.output_dir), flush=True)


if __name__ == "__main__":
    main()
