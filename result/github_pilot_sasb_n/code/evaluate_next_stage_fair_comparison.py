from pathlib import Path
import argparse
import json
import math
import time

import community as community_louvain
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

import evaluate_heuristic_attacks as heur
import evaluate_m18_candidate as m18
import evaluate_m19_next_stage_validation as m19val
import evaluate_m19_realworld_40plus as real40


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260513

DEFAULT_OUT_DIR = ROOT / "result" / "next_stage_fair_comparison"
SYNTHETIC_DATA_DIR = ROOT / "data" / "ml_attack_dataset_large300"
SYNTHETIC_SPLIT = "synthetic_test"
REAL_DATA_DIR = ROOT / "data" / "realnetworks_40plus"
REAL_VALIDATION = ROOT / "result" / "m19_realworld_40plus_validation" / "graph_validation_summary.csv"

METHOD_M4 = "M4 dynamic community internal / pair"
METHOD_M5 = m18.METHOD_M5
METHOD_M7 = m18.METHOD_M7
METHOD_M12 = m18.METHOD_M12
METHOD_M18_TUNED = m18.METHOD_M18_TUNED
METHOD_M19 = m18.METHOD_M19
METHOD_M19_NO_BRIDGE = m19val.METHOD_M19_NO_BRIDGE
METHOD_M19_SAMPLE_ONLY = "M19-sample-only"
METHOD_M19_CANDIDATE_ONLY = "M19-candidate-only"
METHOD_M19_SAMPLE_16 = "M19-sample-16"
METHOD_M19_SAMPLE_32 = "M19-sample-32"
METHOD_M19_SAMPLE_64 = "M19-sample-64"

TARGET_METHODS = [
    METHOD_M4,
    METHOD_M5,
    METHOD_M7,
    METHOD_M12,
    METHOD_M18_TUNED,
    METHOD_M19,
    METHOD_M19_NO_BRIDGE,
]

ABLATION_METHODS = [
    METHOD_M19,
    METHOD_M19_NO_BRIDGE,
    METHOD_M19_SAMPLE_ONLY,
    METHOD_M19_CANDIDATE_ONLY,
    METHOD_M19_SAMPLE_16,
    METHOD_M19_SAMPLE_32,
    METHOD_M19_SAMPLE_64,
]

SHORT_LABELS = {
    METHOD_M4: "M4",
    METHOD_M5: "M5",
    METHOD_M7: "M7",
    METHOD_M12: "M12",
    METHOD_M18_TUNED: "M18-tuned",
    METHOD_M19: "M19",
    METHOD_M19_NO_BRIDGE: "M19-no-bridge",
    METHOD_M19_SAMPLE_ONLY: "M19-sample-only",
    METHOD_M19_CANDIDATE_ONLY: "M19-candidate-only",
    METHOD_M19_SAMPLE_16: "M19-sample-16",
    METHOD_M19_SAMPLE_32: "M19-sample-32",
    METHOD_M19_SAMPLE_64: "M19-sample-64",
}


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def parse_list(text):
    return [part.strip() for part in str(text).split(",") if part.strip()]


def method_slug(method):
    return (
        method.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
    )


def edge_sort_key(edge):
    u, v = edge
    return (min(int(u), int(v)), max(int(u), int(v)))


def first_remove_ratio_at_or_below(curve_df, threshold):
    hit = curve_df[curve_df["gcc_ratio"] <= threshold]
    if hit.empty:
        return np.nan
    return float(hit["remove_ratio"].iloc[0])


def make_run_args(args):
    return argparse.Namespace(
        max_remove_ratio=args.max_remove_ratio,
        m12_louvain_interval=args.m12_louvain_interval,
        m16_candidate_k=30,
        m16_min_drop_ratio=0.05,
        m17_louvain_interval=5,
        m17_candidate_k=100,
        m17_cross_k=60,
        m17_local_k=40,
        m17_bridge_k=30,
        m17_min_drop_ratio=0.0,
        m18_sample_sources=32,
        m18_candidate_k=128,
        m18_m7_k=40,
        m18_m12_k=40,
        m18_local_k=40,
        m18_degree_k=30,
        m18_bridge_k=30,
        m18_louvain_interval=5,
        m18_alpha_sampled_path=5.0,
        m18_beta_community=2.0,
        m18_beta_m12=1.0,
        m18_gamma_local_bridge=0.4,
        m18_delta_degree_product=0.1,
        m18_eta_bridge_bonus=0.3,
        m19_candidate_topk=args.candidate_topk,
        m19_sample_sources=args.sample_sources,
        m19_tau_bridge=args.tau_bridge,
        m19_alpha=args.alpha,
        m19_beta=args.beta,
        m19_gamma=args.gamma,
        m19_delta=args.delta,
        m19_louvain_interval=args.m19_louvain_interval,
        m19_louvain_drop_threshold=args.m19_louvain_drop_threshold,
    )


def choose_edge(graph, method, step, state, run_args):
    if method == METHOD_M4:
        return heur.choose_community_edge(graph, "m4")
    if method == METHOD_M19_NO_BRIDGE:
        return m19val.choose_m19_ablation_edge(graph, METHOD_M19_NO_BRIDGE, step, state, run_args)
    if method == METHOD_M19_CANDIDATE_ONLY:
        return m19val.choose_m19_ablation_edge(graph, m19val.METHOD_M19_NO_SAMPLED, step, state, run_args)
    if method == METHOD_M19_SAMPLE_ONLY:
        sample_args = argparse.Namespace(**vars(run_args))
        sample_args.m19_beta = 0.0
        sample_args.m19_gamma = 0.0
        sample_args.m19_delta = 0.0
        return m18.choose_m19_edge(graph, step, state, sample_args)
    if method in {METHOD_M19_SAMPLE_16, METHOD_M19_SAMPLE_32, METHOD_M19_SAMPLE_64}:
        sample_args = argparse.Namespace(**vars(run_args))
        sample_args.m19_sample_sources = int(method.rsplit("-", 1)[1])
        return m18.choose_m19_edge(graph, step, state, sample_args)
    if method == METHOD_M18_TUNED:
        return m18.choose_edge(graph, method, step, state, m18.m18_tuned_args(run_args))
    return m18.choose_edge(graph, method, step, state, run_args)


def graph_gcc_ratio(graph, original_n):
    if original_n <= 0 or graph.number_of_nodes() == 0:
        return 0.0
    if graph.number_of_edges() == 0:
        return 1.0 / float(original_n)
    return len(max(nx.connected_components(graph), key=len)) / float(original_n)


def curve_row(dataset, meta, method, step, original_m, ratio):
    return {
        "dataset": dataset,
        "graph_id": meta["graph_id"],
        "graph_name": meta.get("graph_name", meta["graph_id"]),
        "graph_type": meta.get("graph_type", "unknown"),
        "community_strength": meta.get("community_strength", "unknown"),
        "method": method,
        "removed_edges": step,
        "remove_ratio": step / float(max(1, original_m)),
        "gcc_ratio": ratio,
    }


def summarize_curve(curve_df, elapsed_seconds, timings, status):
    if curve_df.empty:
        return {}
    x = curve_df["remove_ratio"].values
    y = curve_df["gcc_ratio"].values
    observed_remove_ratio = float(x[-1]) if len(x) else 0.0
    auc = float(np.trapz(y, x)) if len(x) else np.nan
    row = {
        "dataset": curve_df["dataset"].iloc[0],
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_name": curve_df["graph_name"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "community_strength": curve_df["community_strength"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "status": status,
        "auc": auc,
        "normalized_auc": auc / observed_remove_ratio if observed_remove_ratio > 0 else np.nan,
        "observed_remove_ratio": observed_remove_ratio,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "runtime_seconds": float(elapsed_seconds),
        "elapsed_seconds": float(elapsed_seconds),
        "removed_edges": int(curve_df["removed_edges"].max()) if len(curve_df) else 0,
        "remove_ratio_gcc_le_0.5": first_remove_ratio_at_or_below(curve_df, 0.5),
        "remove_ratio_gcc_le_0.2": first_remove_ratio_at_or_below(curve_df, 0.2),
        "remove_ratio_gcc_le_0.1": first_remove_ratio_at_or_below(curve_df, 0.1),
    }
    row.update(timings)
    return row


def simulate_attack(dataset, meta, graph0, method, run_args, timeout_seconds):
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    rows = [curve_row(dataset, meta, method, 0, original_m, graph_gcc_ratio(graph, original_n))]
    state = {"original_n": original_n}
    step = 0
    start = time.perf_counter()
    timed_out = False
    while graph.number_of_edges() > 0 and step / float(max(1, original_m)) < run_args.max_remove_ratio:
        if timeout_seconds > 0 and time.perf_counter() - start > timeout_seconds:
            timed_out = True
            break
        edge = choose_edge(graph, method, step, state, run_args)
        if edge is None or not graph.has_edge(*edge):
            break
        graph.remove_edge(*edge)
        step += 1
        rows.append(curve_row(dataset, meta, method, step, original_m, graph_gcc_ratio(graph, original_n)))
    elapsed = time.perf_counter() - start
    for row in rows:
        row["elapsed_seconds"] = elapsed
    timings = {}
    if method in {METHOD_M19, METHOD_M19_SAMPLE_ONLY, METHOD_M19_SAMPLE_16, METHOD_M19_SAMPLE_32, METHOD_M19_SAMPLE_64}:
        timings = state.get("m19_timings", {}).copy()
        timings["louvain_recomputes"] = state.get("m19_louvain_recomputes", 0)
    elif method in {METHOD_M19_NO_BRIDGE, METHOD_M19_CANDIDATE_ONLY}:
        timings = state.get("m19_ablation_timings", {}).copy()
        timings["louvain_recomputes"] = state.get("m19_ablation_louvain_recomputes", 0)
    elif method == METHOD_M18_TUNED:
        timings = state.get("m18_timings", {}).copy()
    return pd.DataFrame(rows), elapsed, timings, timed_out


def load_synthetic_groups(graph_ids=None, max_graphs=0):
    df = pd.read_csv(SYNTHETIC_DATA_DIR / "edge_features_{}.csv".format(SYNTHETIC_SPLIT))
    if graph_ids:
        df = df[df["graph_id"].isin(set(graph_ids))].copy()
    groups = [(graph_id, group.copy()) for graph_id, group in df.groupby("graph_id", sort=True)]
    if max_graphs > 0:
        groups = groups[:max_graphs]
    return groups


def reconstruct_synthetic_graph(group):
    return heur.reconstruct_graph(group)


def synthetic_meta(group):
    return {
        "graph_id": group["graph_id"].iloc[0],
        "graph_name": group["graph_id"].iloc[0],
        "graph_type": group["graph_type"].iloc[0],
        "community_strength": group["community_strength"].iloc[0] if "community_strength" in group.columns else "unknown",
    }


def load_real_metadata(graph_ids=None, max_networks=0):
    metadata = real40.load_valid_metadata(REAL_DATA_DIR, REAL_VALIDATION, max_networks, graph_ids or [])
    return metadata


def load_real_graph(meta):
    return real40.load_cleaned_graph(ROOT / meta["cleaned_file"])


def normalize_existing_summary(df, dataset):
    result = df.copy()
    if result.empty:
        return result
    result["dataset"] = dataset
    if "graph_name" not in result.columns:
        result["graph_name"] = result["graph_id"]
    if "community_strength" not in result.columns:
        result["community_strength"] = "unknown"
    if "runtime_seconds" not in result.columns:
        if "elapsed_seconds" in result.columns:
            result["runtime_seconds"] = result["elapsed_seconds"]
        else:
            result["runtime_seconds"] = np.nan
    if "elapsed_seconds" not in result.columns:
        result["elapsed_seconds"] = result["runtime_seconds"]
    if "final_gcc_ratio" not in result.columns and "gcc_at_budget" in result.columns:
        result["final_gcc_ratio"] = result["gcc_at_budget"]
    if "status" not in result.columns:
        result["status"] = "finished"
    return result


def normalize_existing_curves(df, dataset):
    result = df.copy()
    if result.empty:
        return result
    result["dataset"] = dataset
    if "graph_name" not in result.columns:
        result["graph_name"] = result["graph_id"]
    if "community_strength" not in result.columns:
        result["community_strength"] = "unknown"
    return result


def load_existing_synthetic_results():
    frames = []
    curve_frames = []
    full_dir = ROOT / "result" / "m19_full_100pct_compare"
    next_dir = ROOT / "result" / "m19_next_stage_validation"
    full_summary = full_dir / "per_graph_results.csv"
    full_curves = full_dir / "attack_curves.csv"
    if full_summary.exists():
        df = normalize_existing_summary(pd.read_csv(full_summary), "synthetic")
        df = df[df["method"].isin({METHOD_M5, METHOD_M7, METHOD_M12, METHOD_M18_TUNED, METHOD_M19})].copy()
        frames.append(df)
    if full_curves.exists():
        curves = normalize_existing_curves(pd.read_csv(full_curves), "synthetic")
        curves = curves[curves["method"].isin({METHOD_M5, METHOD_M7, METHOD_M12, METHOD_M18_TUNED, METHOD_M19})].copy()
        curve_frames.append(curves)
    ns_summary = next_dir / "attack_summary_by_graph.csv"
    ns_curves = next_dir / "attack_curves.csv"
    if ns_summary.exists():
        df = normalize_existing_summary(pd.read_csv(ns_summary), "synthetic")
        df = df[df["method"] == METHOD_M19_NO_BRIDGE].copy()
        frames.append(df)
    if ns_curves.exists():
        curves = normalize_existing_curves(pd.read_csv(ns_curves), "synthetic")
        curves = curves[curves["method"] == METHOD_M19_NO_BRIDGE].copy()
        curve_frames.append(curves)
    summary = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    curves = pd.concat(curve_frames, ignore_index=True, sort=False) if curve_frames else pd.DataFrame()
    return summary, curves


def load_existing_real_results():
    base = ROOT / "result" / "m19_realworld_40plus"
    summary = pd.DataFrame()
    curves = pd.DataFrame()
    skipped = pd.DataFrame()
    if (base / "per_graph_method_results.csv").exists():
        summary = normalize_existing_summary(pd.read_csv(base / "per_graph_method_results.csv"), "realworld")
        summary = summary[summary["method"].isin({METHOD_M5, METHOD_M7, METHOD_M12, METHOD_M19, METHOD_M19_NO_BRIDGE})].copy()
    if (base / "attack_curves.csv").exists():
        curves = normalize_existing_curves(pd.read_csv(base / "attack_curves.csv"), "realworld")
        curves = curves[curves["method"].isin({METHOD_M5, METHOD_M7, METHOD_M12, METHOD_M19, METHOD_M19_NO_BRIDGE})].copy()
    if (base / "skipped_or_failed_runs.csv").exists():
        skipped = normalize_existing_summary(pd.read_csv(base / "skipped_or_failed_runs.csv"), "realworld")
        skipped = skipped[skipped["method"].isin({METHOD_M5, METHOD_M7, METHOD_M12, METHOD_M19, METHOD_M19_NO_BRIDGE})].copy()
    return summary, curves, skipped


def run_dir(out_dir, stage):
    return out_dir / ("smoke_runs" if stage == "smoke" else "runs")


def run_pair(out_dir, stage, dataset, meta, graph, method, args, run_args):
    root = run_dir(out_dir, stage) / dataset / meta["graph_id"]
    root.mkdir(parents=True, exist_ok=True)
    slug = method_slug(method)
    summary_path = root / "{}_summary.csv".format(slug)
    curve_path = root / "{}_curve.csv".format(slug)
    if summary_path.exists() and curve_path.exists() and not args.overwrite_runs:
        return "skipped_existing"
    if dataset == "realworld" and method == METHOD_M5 and not (
        int(meta.get("num_nodes_gcc", graph.number_of_nodes())) <= args.m5_max_nodes
        and int(meta.get("num_edges_gcc", graph.number_of_edges())) <= args.m5_max_edges
    ):
        row = dict(meta)
        row.update(
            {
                "dataset": dataset,
                "method": method,
                "status": "skipped_due_to_size",
                "reason": "num_nodes_gcc={} num_edges_gcc={}".format(
                    meta.get("num_nodes_gcc", graph.number_of_nodes()),
                    meta.get("num_edges_gcc", graph.number_of_edges()),
                ),
            }
        )
        write_csv(pd.DataFrame([row]), summary_path)
        write_csv(pd.DataFrame(), curve_path)
        return "skipped_due_to_size"
    try:
        curve_df, elapsed, timings, timed_out = simulate_attack(
            dataset, meta, graph, method, run_args, args.timeout_seconds
        )
        status = "timeout" if timed_out else "finished"
        summary = pd.DataFrame([summarize_curve(curve_df, elapsed, timings, status)])
        write_csv(summary, summary_path)
        write_csv(curve_df, curve_path)
        return status
    except Exception as exc:
        row = dict(meta)
        row.update({"dataset": dataset, "method": method, "status": "failed", "reason": repr(exc)})
        write_csv(pd.DataFrame([row]), summary_path)
        write_csv(pd.DataFrame(), curve_path)
        return "failed"


def collect_new_runs(out_dir, stage="full"):
    roots = [out_dir / "runs"]
    if stage == "smoke":
        roots = [out_dir / "smoke_runs"]
    summaries = []
    curves = []
    skipped = []
    for root in roots:
        if not root.exists():
            continue
        for summary_path in sorted(root.glob("*/*/*_summary.csv")):
            try:
                df = pd.read_csv(summary_path)
            except pd.errors.EmptyDataError:
                continue
            if df.empty:
                continue
            status = df["status"].iloc[0] if "status" in df.columns else "finished"
            if status == "finished":
                summaries.append(df)
                curve_path = summary_path.with_name(summary_path.name.replace("_summary.csv", "_curve.csv"))
                if curve_path.exists():
                    try:
                        curve_df = pd.read_csv(curve_path)
                        if not curve_df.empty:
                            curves.append(curve_df)
                    except pd.errors.EmptyDataError:
                        pass
            else:
                skipped.append(df)
    summary_df = pd.concat(summaries, ignore_index=True, sort=False) if summaries else pd.DataFrame()
    curve_df = pd.concat(curves, ignore_index=True, sort=False) if curves else pd.DataFrame()
    skipped_df = pd.concat(skipped, ignore_index=True, sort=False) if skipped else pd.DataFrame()
    return summary_df, curve_df, skipped_df


def compute_graph_features(graph, meta, dataset):
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    degrees = np.array([degree for _, degree in graph.degree()], dtype=float)
    avg_degree = float(degrees.mean()) if len(degrees) else 0.0
    max_degree = float(degrees.max()) if len(degrees) else 0.0
    if m > 0:
        partition = community_louvain.best_partition(graph, random_state=SEED)
    else:
        partition = {node: idx for idx, node in enumerate(graph.nodes())}
    communities = {}
    for node, cid in partition.items():
        communities.setdefault(cid, 0)
        communities[cid] += 1
    inter_edges = 0
    for u, v in graph.edges():
        if partition.get(u) != partition.get(v):
            inter_edges += 1
    num_communities = len(communities)
    path_reason = "computed"
    average_shortest_path_length = np.nan
    diameter = np.nan
    if n == 0:
        path_reason = "empty_graph"
    elif n > 800:
        path_reason = "skipped_large_n"
    elif m == 0:
        path_reason = "no_edges"
        average_shortest_path_length = 0.0
        diameter = 0.0
    else:
        try:
            component = graph
            if not nx.is_connected(component):
                nodes = max(nx.connected_components(component), key=len)
                component = component.subgraph(nodes).copy()
                path_reason = "computed_on_lcc"
            average_shortest_path_length = nx.average_shortest_path_length(component)
            diameter = nx.diameter(component)
        except Exception as exc:
            path_reason = "failed:{}".format(type(exc).__name__)
    return {
        "dataset": dataset,
        "graph_id": meta["graph_id"],
        "graph_name": meta.get("graph_name", meta["graph_id"]),
        "network_name": meta.get("graph_name", meta["graph_id"]),
        "graph_type": meta.get("graph_type", "unknown"),
        "network_type": meta.get("graph_type", "unknown"),
        "community_strength": meta.get("community_strength", "unknown"),
        "n": n,
        "m": m,
        "num_nodes": n,
        "num_edges": m,
        "density": nx.density(graph) if n > 1 else 0.0,
        "average_degree": avg_degree,
        "max_degree": max_degree,
        "degree_heterogeneity": float(degrees.std() / avg_degree) if avg_degree > 0 else 0.0,
        "clustering_coefficient": nx.average_clustering(graph) if n > 0 else 0.0,
        "num_louvain_communities": num_communities,
        "modularity": community_louvain.modularity(partition, graph) if m > 0 and num_communities > 1 else 0.0,
        "inter_community_edge_ratio": inter_edges / float(max(1, m)),
        "largest_community_ratio": max(communities.values()) / float(max(1, n)) if communities else 0.0,
        "average_shortest_path_length": average_shortest_path_length,
        "diameter": diameter,
        "path_metric_reason": path_reason,
    }


def build_feature_table(out_dir, args):
    rows = []
    for _, group in load_synthetic_groups():
        meta = synthetic_meta(group)
        rows.append(compute_graph_features(reconstruct_synthetic_graph(group), meta, "synthetic"))
    for _, meta_row in load_real_metadata().iterrows():
        meta = meta_row.to_dict()
        rows.append(compute_graph_features(load_real_graph(meta), meta, "realworld"))
    df = pd.DataFrame(rows)
    write_csv(df, out_dir / "graph_features_next_stage.csv")
    return df


def add_ranks_and_speedups(summary_df):
    result = summary_df.copy()
    if result.empty:
        return result
    result["runtime_seconds"] = pd.to_numeric(result["runtime_seconds"], errors="coerce")
    result["normalized_auc"] = pd.to_numeric(result["normalized_auc"], errors="coerce")
    result["per_graph_auc_rank"] = np.nan
    result["speedup_vs_m5"] = np.nan
    result["speedup_vs_m7"] = np.nan
    for (_, graph_id), group in result.groupby(["dataset", "graph_id"], sort=False):
        idxs = group.index
        result.loc[idxs, "per_graph_auc_rank"] = group["normalized_auc"].rank(method="min", ascending=True)
        m5 = group[group["method"] == METHOD_M5]
        m7 = group[group["method"] == METHOD_M7]
        m5_time = float(m5["runtime_seconds"].iloc[0]) if len(m5) else np.nan
        m7_time = float(m7["runtime_seconds"].iloc[0]) if len(m7) else np.nan
        if m5_time > 0:
            result.loc[idxs, "speedup_vs_m5"] = m5_time / group["runtime_seconds"]
        if m7_time > 0:
            result.loc[idxs, "speedup_vs_m7"] = m7_time / group["runtime_seconds"]
    result["network_name"] = result["graph_name"]
    result["network_type"] = result["graph_type"]
    result["runtime"] = result["runtime_seconds"]
    result["removed_budget"] = result["observed_remove_ratio"]
    return result


def method_summary(per_graph_df):
    rows = []
    if per_graph_df.empty:
        return pd.DataFrame()
    for (dataset, method), group in per_graph_df.groupby(["dataset", "method"], sort=False):
        rows.append(
            {
                "dataset": dataset,
                "method": method,
                "method_label": SHORT_LABELS.get(method, method),
                "num_graphs": len(group),
                "mean_normalized_auc": group["normalized_auc"].mean(),
                "median_normalized_auc": group["normalized_auc"].median(),
                "mean_remove_ratio_gcc_le_0.5": group["remove_ratio_gcc_le_0.5"].mean(),
                "mean_remove_ratio_gcc_le_0.2": group["remove_ratio_gcc_le_0.2"].mean(),
                "mean_remove_ratio_gcc_le_0.1": group["remove_ratio_gcc_le_0.1"].mean(),
                "mean_final_gcc_ratio": group["final_gcc_ratio"].mean(),
                "total_runtime_seconds": group["runtime_seconds"].sum(),
                "mean_runtime_seconds": group["runtime_seconds"].mean(),
                "mean_auc_rank": group["per_graph_auc_rank"].mean(),
                "mean_speedup_vs_m5": group["speedup_vs_m5"].mean(),
                "mean_speedup_vs_m7": group["speedup_vs_m7"].mean(),
            }
        )
    return pd.DataFrame(rows)


def winloss_summary(per_graph_df):
    baselines = [METHOD_M5, METHOD_M7, METHOD_M12, METHOD_M19_NO_BRIDGE]
    rows = []
    for dataset, df in per_graph_df.groupby("dataset", sort=False):
        for baseline in baselines:
            wins = losses = ties = 0
            diffs = []
            graphs = 0
            for graph_id, group in df.groupby("graph_id", sort=False):
                by_method = {row["method"]: row for _, row in group.iterrows()}
                if METHOD_M19 not in by_method or baseline not in by_method:
                    continue
                diff = float(by_method[METHOD_M19]["normalized_auc"]) - float(by_method[baseline]["normalized_auc"])
                diffs.append(diff)
                graphs += 1
                if abs(diff) <= 1e-12:
                    ties += 1
                elif diff < 0:
                    wins += 1
                else:
                    losses += 1
            rows.append(
                {
                    "dataset": dataset,
                    "comparison": "M19 vs {}".format(SHORT_LABELS.get(baseline, baseline)),
                    "baseline_method": baseline,
                    "num_graphs": graphs,
                    "m19_wins": wins,
                    "m19_losses": losses,
                    "ties": ties,
                    "mean_auc_diff_m19_minus_baseline": float(np.mean(diffs)) if diffs else np.nan,
                }
            )
    return pd.DataFrame(rows)


def timeout_skipped_summary(per_graph_df, skipped_df, valid_real_graphs):
    finished = per_graph_df[["dataset", "graph_id", "graph_name", "graph_type", "method"]].copy()
    finished["status"] = "finished"
    finished["reason"] = ""
    frames = [finished]
    if not skipped_df.empty:
        keep = [col for col in ["dataset", "graph_id", "graph_name", "graph_type", "method", "status", "reason"] if col in skipped_df.columns]
        frames.append(skipped_df[keep].copy())
    status_rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    rows = []
    if not status_rows.empty:
        for (dataset, method, status), group in status_rows.groupby(["dataset", "method", "status"], sort=False):
            rows.append({"dataset": dataset, "method": method, "status": status, "count": len(group)})
    counts = pd.DataFrame(rows)
    if valid_real_graphs:
        existing = set()
        for _, row in counts.iterrows():
            existing.add((row["dataset"], row["method"], row["status"]))
        for method in TARGET_METHODS:
            attempted = status_rows[(status_rows["dataset"] == "realworld") & (status_rows["method"] == method)]["graph_id"].nunique()
            missing = max(0, valid_real_graphs - attempted)
            if missing and ("realworld", method, "not_attempted") not in existing:
                counts = pd.concat(
                    [counts, pd.DataFrame([{"dataset": "realworld", "method": method, "status": "not_attempted", "count": missing}])],
                    ignore_index=True,
                    sort=False,
                )
    return counts


def realworld_status_detail(per_graph_df, skipped_df, feature_df, valid_real_graphs):
    metadata = load_real_metadata()
    rows = []
    feature_lookup = {}
    if not feature_df.empty:
        for _, row in feature_df[feature_df["dataset"] == "realworld"].iterrows():
            feature_lookup[row["graph_id"]] = row.to_dict()
    finished_lookup = {}
    if not per_graph_df.empty:
        real_finished = per_graph_df[per_graph_df["dataset"] == "realworld"].copy()
        for _, row in real_finished.iterrows():
            finished_lookup[(row["graph_id"], row["method"])] = row.to_dict()
    skipped_lookup = {}
    if not skipped_df.empty:
        real_skipped = skipped_df[skipped_df["dataset"] == "realworld"].copy()
        for _, row in real_skipped.iterrows():
            skipped_lookup[(row["graph_id"], row["method"])] = row.to_dict()
    for _, meta_row in metadata.iterrows():
        meta = meta_row.to_dict()
        graph_id = meta["graph_id"]
        feature = feature_lookup.get(graph_id, {})
        for method in TARGET_METHODS:
            key = (graph_id, method)
            source = finished_lookup.get(key) or skipped_lookup.get(key) or {}
            status = source.get("status", "not_attempted")
            row = {
                "dataset": "realworld",
                "network_name": meta.get("graph_name", graph_id),
                "network_type": meta.get("graph_type", "realworld"),
                "graph_id": graph_id,
                "graph_name": meta.get("graph_name", graph_id),
                "graph_type": meta.get("graph_type", "realworld"),
                "method": method,
                "method_label": SHORT_LABELS.get(method, method),
                "status": status,
                "reason": source.get("reason", ""),
                "normalized_auc": source.get("normalized_auc", np.nan),
                "runtime": source.get("runtime_seconds", source.get("elapsed_seconds", np.nan)),
                "runtime_seconds": source.get("runtime_seconds", source.get("elapsed_seconds", np.nan)),
                "removed_budget": source.get("observed_remove_ratio", np.nan),
                "observed_remove_ratio": source.get("observed_remove_ratio", np.nan),
                "final_gcc_ratio": source.get("final_gcc_ratio", np.nan),
                "num_nodes": feature.get("num_nodes", meta.get("num_nodes_gcc", np.nan)),
                "num_edges": feature.get("num_edges", meta.get("num_edges_gcc", np.nan)),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def fair_subset_tables(per_graph_df, real_status_df):
    per_rows = []
    if per_graph_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    target_no_m5 = [METHOD_M19, METHOD_M19_NO_BRIDGE, METHOD_M7, METHOD_M12, METHOD_M4, METHOD_M18_TUNED]

    synthetic = per_graph_df[
        (per_graph_df["dataset"] == "synthetic") & (per_graph_df["method"].isin(TARGET_METHODS))
    ].copy()
    if not synthetic.empty:
        synthetic["fair_subset"] = "synthetic-full"
        per_rows.append(synthetic)

    real_full = per_graph_df[
        (per_graph_df["dataset"] == "realworld") & (per_graph_df["method"].isin(target_no_m5))
    ].copy()
    if not real_full.empty:
        real_full["fair_subset"] = "realworld-full"
        per_rows.append(real_full)

    m5_graphs = set(
        per_graph_df[(per_graph_df["dataset"] == "realworld") & (per_graph_df["method"] == METHOD_M5)]["graph_id"]
    )
    m5_subset = per_graph_df[
        (per_graph_df["dataset"] == "realworld")
        & (per_graph_df["graph_id"].isin(m5_graphs))
        & (per_graph_df["method"].isin(TARGET_METHODS))
    ].copy()
    if not m5_subset.empty:
        m5_subset["fair_subset"] = "M5-finished-subset"
        per_rows.append(m5_subset)

    fair_per = pd.concat(per_rows, ignore_index=True, sort=False) if per_rows else pd.DataFrame()
    summary_rows = []
    if not fair_per.empty:
        for (subset, method), group in fair_per.groupby(["fair_subset", "method"], sort=False):
            summary_rows.append(
                {
                    "fair_subset": subset,
                    "method": method,
                    "method_label": SHORT_LABELS.get(method, method),
                    "num_finished_graphs": group["graph_id"].nunique(),
                    "mean_normalized_auc": group["normalized_auc"].mean(),
                    "median_normalized_auc": group["normalized_auc"].median(),
                    "mean_final_gcc_ratio": group["final_gcc_ratio"].mean(),
                    "total_runtime_seconds": group["runtime_seconds"].sum(),
                    "mean_runtime_seconds": group["runtime_seconds"].mean(),
                    "mean_auc_rank": group["per_graph_auc_rank"].mean() if "per_graph_auc_rank" in group.columns else np.nan,
                }
            )
    if real_status_df is not None and not real_status_df.empty:
        for method, group in real_status_df[real_status_df["method"].isin(target_no_m5)].groupby("method", sort=False):
            counts = group["status"].value_counts().to_dict()
            summary_rows.append(
                {
                    "fair_subset": "realworld-full-status",
                    "method": method,
                    "method_label": SHORT_LABELS.get(method, method),
                    "num_finished_graphs": int(counts.get("finished", 0)),
                    "mean_normalized_auc": np.nan,
                    "median_normalized_auc": np.nan,
                    "mean_final_gcc_ratio": np.nan,
                    "total_runtime_seconds": np.nan,
                    "mean_runtime_seconds": np.nan,
                    "mean_auc_rank": np.nan,
                    "finished": int(counts.get("finished", 0)),
                    "timeout": int(counts.get("timeout", 0)),
                    "failed": int(counts.get("failed", 0)),
                    "skipped_due_to_size": int(counts.get("skipped_due_to_size", 0)),
                    "not_attempted": int(counts.get("not_attempted", 0)),
                }
            )
    return fair_per, pd.DataFrame(summary_rows)


def loss_cases(per_graph_df, feature_df):
    rows = []
    for (dataset, graph_id), group in per_graph_df.groupby(["dataset", "graph_id"], sort=False):
        by_method = {row["method"]: row for _, row in group.iterrows()}
        if METHOD_M19 not in by_method:
            continue
        m19_auc = float(by_method[METHOD_M19]["normalized_auc"])
        m5_auc = float(by_method[METHOD_M5]["normalized_auc"]) if METHOD_M5 in by_method else np.nan
        m7_auc = float(by_method[METHOD_M7]["normalized_auc"]) if METHOD_M7 in by_method else np.nan
        loss_to_m5 = bool(not np.isnan(m5_auc) and m19_auc > m5_auc)
        loss_to_m7 = bool(not np.isnan(m7_auc) and m19_auc > m7_auc)
        if not (loss_to_m5 or loss_to_m7):
            continue
        loss_type = []
        if loss_to_m5:
            loss_type.append("M5")
        if loss_to_m7:
            loss_type.append("M7")
        rows.append(
            {
                "dataset": dataset,
                "graph_id": graph_id,
                "graph_name": by_method[METHOD_M19].get("graph_name", graph_id),
                "graph_type": by_method[METHOD_M19].get("graph_type", "unknown"),
                "community_strength": by_method[METHOD_M19].get("community_strength", "unknown"),
                "m19_normalized_auc": m19_auc,
                "m5_normalized_auc": m5_auc,
                "m7_normalized_auc": m7_auc,
                "loss_to_m5": loss_to_m5,
                "loss_to_m7": loss_to_m7,
                "loss_type": "+".join(loss_type),
                "auc_diff_m19_minus_m5": m19_auc - m5_auc if not np.isnan(m5_auc) else np.nan,
                "auc_diff_m19_minus_m7": m19_auc - m7_auc if not np.isnan(m7_auc) else np.nan,
            }
        )
    loss_df = pd.DataFrame(rows)
    if loss_df.empty:
        return loss_df
    return loss_df.merge(feature_df, on=["dataset", "graph_id", "graph_name", "graph_type", "community_strength"], how="left")


def average_curves(curve_df):
    rows = []
    if curve_df.empty:
        return pd.DataFrame()
    grid = np.linspace(0.0, 1.0, 101)
    for (dataset, method), group in curve_df.groupby(["dataset", "method"], sort=False):
        vals = []
        for graph_id, g in group.groupby("graph_id"):
            g = g.sort_values("remove_ratio")
            if g.empty:
                continue
            vals.append(np.interp(grid, g["remove_ratio"].values, g["gcc_ratio"].values, left=g["gcc_ratio"].iloc[0], right=g["gcc_ratio"].iloc[-1]))
        if not vals:
            continue
        mean_vals = np.vstack(vals).mean(axis=0)
        for x, y in zip(grid, mean_vals):
            rows.append({"dataset": dataset, "method": method, "remove_ratio": x, "mean_gcc_ratio": y})
    return pd.DataFrame(rows)


def setup_plot():
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10})


def plot_average_gcc(curve_df, path):
    setup_plot()
    avg = average_curves(curve_df)
    if avg.empty:
        return
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for method in TARGET_METHODS:
        g = avg[(avg["dataset"] == "synthetic") & (avg["method"] == method)]
        if g.empty:
            continue
        ax.plot(g["remove_ratio"], g["mean_gcc_ratio"], label="synthetic {}".format(SHORT_LABELS.get(method, method)), linewidth=2)
    for method in [METHOD_M19, METHOD_M19_NO_BRIDGE, METHOD_M7, METHOD_M12, METHOD_M5, METHOD_M4, METHOD_M18_TUNED]:
        g = avg[(avg["dataset"] == "realworld") & (avg["method"] == method)]
        if g.empty:
            continue
        ax.plot(g["remove_ratio"], g["mean_gcc_ratio"], linestyle="--", label="real {}".format(SHORT_LABELS.get(method, method)), linewidth=1.8)
    ax.set_title("Average GCC curve by edge removal ratio")
    ax.set_xlabel("Removed edge ratio")
    ax.set_ylabel("Mean GCC ratio")
    ax.grid(alpha=0.25)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    write_csv(avg, path.with_suffix(".csv"))


def plot_real_heatmap(per_graph_df, path):
    setup_plot()
    real = per_graph_df[per_graph_df["dataset"] == "realworld"].copy()
    if real.empty:
        return
    pivot = real.pivot_table(index="graph_id", columns="method", values="normalized_auc", aggfunc="mean")
    order = [m for m in TARGET_METHODS if m in pivot.columns]
    pivot = pivot[order].sort_index()
    fig_h = max(6, 0.22 * len(pivot) + 2)
    fig, ax = plt.subplots(figsize=(10, fig_h))
    im = ax.imshow(pivot.values, aspect="auto", cmap="viridis_r")
    ax.set_title("Realworld normalized AUC heatmap (lower is better)")
    ax.set_xlabel("Method")
    ax.set_ylabel("Network")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([SHORT_LABELS.get(m, m) for m in order], rotation=35, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=7)
    fig.colorbar(im, ax=ax, label="Normalized AUC")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_method_rank(method_df, path):
    setup_plot()
    if method_df.empty:
        return
    df = method_df.copy()
    df = df.sort_values(["dataset", "mean_auc_rank"])
    labels = ["{} {}".format(row["dataset"], SHORT_LABELS.get(row["method"], row["method"])) for _, row in df.iterrows()]
    fig, ax = plt.subplots(figsize=(10, max(4, 0.28 * len(df))))
    ax.barh(labels, df["mean_auc_rank"])
    ax.invert_yaxis()
    ax.set_title("Average per-graph AUC rank (lower is better)")
    ax.set_xlabel("Mean rank")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_auc_runtime(method_df, path):
    setup_plot()
    if method_df.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for dataset, marker in [("synthetic", "o"), ("realworld", "s")]:
        df = method_df[method_df["dataset"] == dataset]
        if df.empty:
            continue
        ax.scatter(df["total_runtime_seconds"], df["mean_normalized_auc"], label=dataset, marker=marker, s=70)
        for _, row in df.iterrows():
            ax.annotate(SHORT_LABELS.get(row["method"], row["method"]), (row["total_runtime_seconds"], row["mean_normalized_auc"]), fontsize=8)
    ax.set_title("AUC-runtime tradeoff")
    ax.set_xlabel("Total runtime seconds")
    ax.set_ylabel("Mean normalized AUC")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_auc_diff(per_graph_df, baseline, path, title):
    setup_plot()
    rows = []
    for dataset, df in per_graph_df.groupby("dataset", sort=False):
        for graph_id, group in df.groupby("graph_id", sort=False):
            by = {row["method"]: row for _, row in group.iterrows()}
            if METHOD_M19 not in by or baseline not in by:
                continue
            rows.append(
                {
                    "dataset": dataset,
                    "graph_id": graph_id,
                    "diff": float(by[METHOD_M19]["normalized_auc"]) - float(by[baseline]["normalized_auc"]),
                }
            )
    diff_df = pd.DataFrame(rows)
    if diff_df.empty:
        return
    diff_df = diff_df.sort_values("diff")
    colors = diff_df["diff"].apply(lambda v: "#2ca02c" if v < 0 else "#d62728")
    fig, ax = plt.subplots(figsize=(10, max(4, 0.18 * len(diff_df) + 2)))
    ax.barh(diff_df["dataset"] + ":" + diff_df["graph_id"], diff_df["diff"], color=colors)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel("Normalized AUC difference (M19 - baseline)")
    ax.set_ylabel("Graph")
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    write_csv(diff_df, path.with_suffix(".csv"))


def plot_timeout_skipped(status_df, path):
    setup_plot()
    if status_df.empty:
        return
    real = status_df[status_df["dataset"] == "realworld"].copy()
    if real.empty:
        return
    pivot = real.pivot_table(index="method", columns="status", values="count", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex([m for m in TARGET_METHODS if m in pivot.index])
    fig, ax = plt.subplots(figsize=(9, 5.5))
    pivot.plot(kind="bar", stacked=True, ax=ax)
    ax.set_title("Realworld run status by method")
    ax.set_xlabel("Method")
    ax.set_ylabel("Graph-method count")
    ax.set_xticklabels([SHORT_LABELS.get(m, m) for m in pivot.index], rotation=35, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_loss_features(loss_df, out_dir):
    setup_plot()
    if loss_df.empty:
        return
    feature_cols = [
        "n",
        "m",
        "density",
        "average_degree",
        "max_degree",
        "degree_heterogeneity",
        "clustering_coefficient",
        "num_louvain_communities",
        "modularity",
        "inter_community_edge_ratio",
        "largest_community_ratio",
        "average_shortest_path_length",
        "diameter",
    ]
    present = [col for col in feature_cols if col in loss_df.columns]
    data = loss_df[present].copy()
    data = data.apply(pd.to_numeric, errors="coerce")
    z = (data - data.mean()) / data.std(ddof=0).replace(0, np.nan)
    z = z.fillna(0.0)
    fig, ax = plt.subplots(figsize=(11, max(4, 0.26 * len(z) + 2)))
    im = ax.imshow(z.values, aspect="auto", cmap="coolwarm", vmin=-2.5, vmax=2.5)
    ax.set_title("M19 loss-case feature heatmap (z-score)")
    ax.set_xlabel("Feature")
    ax.set_ylabel("Loss case")
    labels = loss_df["dataset"].astype(str) + ":" + loss_df["graph_id"].astype(str) + " (" + loss_df["loss_type"].astype(str) + ")"
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xticks(range(len(present)))
    ax.set_xticklabels(present, rotation=35, ha="right")
    fig.colorbar(im, ax=ax, label="z-score")
    fig.tight_layout()
    fig.savefig(out_dir / "loss_case_feature_heatmap.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    for loss_type, group in loss_df.groupby("loss_type"):
        ax.scatter(group["modularity"], group["degree_heterogeneity"], label=loss_type, s=60)
    ax.set_title("M19 loss cases: modularity vs degree heterogeneity")
    ax.set_xlabel("Modularity")
    ax.set_ylabel("Degree heterogeneity")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "loss_case_scatter.png", dpi=220)
    plt.close(fig)


def ablation_run_dir(out_dir, stage):
    return out_dir / ("ablation_smoke_runs" if stage == "ablation_smoke" else "ablation_runs")


def run_ablation_pair(out_dir, stage, dataset, meta, graph, method, args, run_args):
    root = ablation_run_dir(out_dir, stage) / dataset / meta["graph_id"]
    root.mkdir(parents=True, exist_ok=True)
    slug = method_slug(method)
    summary_path = root / "{}_summary.csv".format(slug)
    curve_path = root / "{}_curve.csv".format(slug)
    if summary_path.exists() and curve_path.exists() and not args.overwrite_runs:
        return "skipped_existing"
    try:
        curve_df, elapsed, timings, timed_out = simulate_attack(
            dataset, meta, graph, method, run_args, args.timeout_seconds
        )
        status = "timeout" if timed_out else "finished"
        summary = pd.DataFrame([summarize_curve(curve_df, elapsed, timings, status)])
        write_csv(summary, summary_path)
        write_csv(curve_df, curve_path)
        return status
    except Exception as exc:
        row = dict(meta)
        row.update({"dataset": dataset, "method": method, "status": "failed", "reason": repr(exc)})
        write_csv(pd.DataFrame([row]), summary_path)
        write_csv(pd.DataFrame(), curve_path)
        return "failed"


def sample_size_for_variant(method):
    if method in {METHOD_M19, "M19-full", METHOD_M19_NO_BRIDGE, METHOD_M19_SAMPLE_ONLY, METHOD_M19_CANDIDATE_ONLY, METHOD_M19_SAMPLE_32}:
        return 32
    if method in {METHOD_M19_SAMPLE_16, METHOD_M19_SAMPLE_64}:
        return int(method.rsplit("-", 1)[1])
    return np.nan


def collect_ablation_runs(out_dir, include_smoke=False):
    frames = []
    curve_frames = []
    roots = [out_dir / "ablation_runs"]
    if include_smoke:
        roots.append(out_dir / "ablation_smoke_runs")
    for root in roots:
        if not root.exists():
            continue
        for summary_path in sorted(root.glob("*/*/*_summary.csv")):
            try:
                df = pd.read_csv(summary_path)
            except pd.errors.EmptyDataError:
                continue
            if df.empty:
                continue
            frames.append(df)
            curve_path = summary_path.with_name(summary_path.name.replace("_summary.csv", "_curve.csv"))
            if curve_path.exists():
                try:
                    curve_df = pd.read_csv(curve_path)
                    if not curve_df.empty:
                        curve_frames.append(curve_df)
                except pd.errors.EmptyDataError:
                    pass
    summary = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    curves = pd.concat(curve_frames, ignore_index=True, sort=False) if curve_frames else pd.DataFrame()
    return summary, curves


def load_existing_ablation_results(per_graph_df):
    frames = []
    if not per_graph_df.empty:
        full = per_graph_df[per_graph_df["method"].isin({METHOD_M19, METHOD_M19_NO_BRIDGE})].copy()
        if not full.empty:
            full["method_variant"] = full["method"].replace({METHOD_M19: "M19-full"})
            full["sample_size"] = full["method"].apply(sample_size_for_variant)
            full["notes"] = full["method"].map(
                {
                    METHOD_M19: "full M19, reused from main comparison",
                    METHOD_M19_NO_BRIDGE: "no significant-bridge bonus, reused from main comparison",
                }
            )
            frames.append(full)
        sample32 = per_graph_df[per_graph_df["method"] == METHOD_M19].copy()
        if not sample32.empty:
            sample32["method_variant"] = METHOD_M19_SAMPLE_32
            sample32["sample_size"] = 32
            sample32["notes"] = "full M19 with default sample_sources=32, reused as sample-size reference"
            frames.append(sample32)
    ns_summary = ROOT / "result" / "m19_next_stage_validation" / "attack_summary_by_graph.csv"
    if ns_summary.exists():
        df = normalize_existing_summary(pd.read_csv(ns_summary), "synthetic")
        df = df[df["method"] == m19val.METHOD_M19_NO_SAMPLED].copy()
        if not df.empty:
            df["method_variant"] = METHOD_M19_CANDIDATE_ONLY
            df["sample_size"] = 32
            df["notes"] = "existing no-sampled-dependency ablation, used as candidate-only evidence"
            frames.append(df)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def build_ablation_tables(out_dir, per_graph_df, include_smoke=False):
    existing = load_existing_ablation_results(per_graph_df)
    new_summary, _ = collect_ablation_runs(out_dir, include_smoke=include_smoke)
    frames = []
    if not existing.empty:
        frames.append(existing)
    if not new_summary.empty:
        if "graph_name" not in new_summary.columns:
            new_summary["graph_name"] = new_summary["graph_id"]
        if "community_strength" not in new_summary.columns:
            new_summary["community_strength"] = "unknown"
        if "runtime_seconds" not in new_summary.columns:
            new_summary["runtime_seconds"] = new_summary.get("elapsed_seconds", np.nan)
        if "elapsed_seconds" not in new_summary.columns:
            new_summary["elapsed_seconds"] = new_summary["runtime_seconds"]
        if "status" not in new_summary.columns:
            new_summary["status"] = "finished"
        new_summary["method_variant"] = new_summary["method"]
        new_summary["sample_size"] = new_summary["method"].apply(sample_size_for_variant)
        new_summary["notes"] = new_summary["method"].map(
            {
                METHOD_M19_SAMPLE_ONLY: "only sampled shortest-path dependency, M19 candidate pool retained",
                METHOD_M19_SAMPLE_16: "full M19 score with sample_sources=16",
                METHOD_M19_SAMPLE_64: "full M19 score with sample_sources=64",
            }
        ).fillna("")
        frames.append(new_summary)
    if not frames:
        return pd.DataFrame(), pd.DataFrame()
    per = pd.concat(frames, ignore_index=True, sort=False)
    if "graph_name" in per.columns:
        per["network_name"] = per["graph_name"]
    else:
        per["network_name"] = per["graph_id"]
    if "network_name" not in per.columns:
        per["network_name"] = per["graph_id"]
    if "runtime_seconds" not in per.columns and "runtime" in per.columns:
        per["runtime_seconds"] = per["runtime"]
    per["runtime"] = per["runtime_seconds"]
    per = per.drop_duplicates(["dataset", "graph_id", "method_variant"], keep="last")
    rows = []
    for (dataset, variant), group in per.groupby(["dataset", "method_variant"], sort=False):
        finished = group[group["status"] == "finished"] if "status" in group.columns else group
        rows.append(
            {
                "dataset": dataset,
                "method_variant": variant,
                "sample_size": sample_size_for_variant(variant),
                "num_finished_graphs": len(finished),
                "num_total_records": len(group),
                "mean_normalized_auc": finished["normalized_auc"].mean(),
                "median_normalized_auc": finished["normalized_auc"].median(),
                "total_runtime_seconds": finished["runtime_seconds"].sum(),
                "mean_runtime_seconds": finished["runtime_seconds"].mean(),
                "notes": "; ".join(sorted(set(str(v) for v in group.get("notes", pd.Series(dtype=str)).dropna() if str(v)))),
            }
        )
    return per, pd.DataFrame(rows)


def plot_ablation_auc_runtime(ablation_summary, path):
    setup_plot()
    if ablation_summary.empty:
        return
    df = ablation_summary.dropna(subset=["mean_normalized_auc", "total_runtime_seconds"]).copy()
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    for dataset, marker in [("synthetic", "o"), ("realworld", "s")]:
        g = df[df["dataset"] == dataset]
        if g.empty:
            continue
        ax.scatter(g["total_runtime_seconds"], g["mean_normalized_auc"], marker=marker, s=70, label=dataset)
        for _, row in g.iterrows():
            ax.annotate(SHORT_LABELS.get(row["method_variant"], row["method_variant"]), (row["total_runtime_seconds"], row["mean_normalized_auc"]), fontsize=8)
    ax.set_title("M19 ablation AUC-runtime tradeoff")
    ax.set_xlabel("Total runtime seconds")
    ax.set_ylabel("Mean normalized AUC")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_ablation_sample_size(ablation_summary, path):
    setup_plot()
    if ablation_summary.empty:
        return
    df = ablation_summary[
        ablation_summary["method_variant"].isin({METHOD_M19_SAMPLE_16, METHOD_M19_SAMPLE_32, METHOD_M19_SAMPLE_64})
    ].dropna(subset=["sample_size", "mean_normalized_auc"]).copy()
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for dataset, group in df.groupby("dataset"):
        group = group.sort_values("sample_size")
        ax.plot(group["sample_size"], group["mean_normalized_auc"], marker="o", linewidth=2, label=dataset)
    ax.set_title("M19 sample size sensitivity")
    ax.set_xlabel("sample_sources")
    ax.set_ylabel("Mean normalized AUC")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def write_loss_case_report(loss_df, out_dir):
    lines = ["# M19 loss-case feature summary", ""]
    if loss_df.empty:
        lines.append("No M19 loss cases were found in the finished comparable graph-method pairs.")
        (out_dir / "m19_loss_case_feature_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    lines.extend(
        [
            "Loss-case definition: M19 loses when its normalized AUC is higher than M5 or M7 on the same graph.",
            "",
            "## Counts",
            "",
            "- Total loss cases: {}.".format(len(loss_df)),
            "- Loss to M5: {}.".format(int(loss_df["loss_to_m5"].sum())),
            "- Loss to M7: {}.".format(int(loss_df["loss_to_m7"].sum())),
            "",
            "## By Dataset",
            "",
        ]
    )
    for dataset, group in loss_df.groupby("dataset"):
        lines.append("- {}: {} loss cases.".format(dataset, len(group)))
    lines.extend(["", "## By Graph Type", ""])
    for graph_type, group in loss_df.groupby("graph_type"):
        lines.append("- {}: {} loss cases.".format(graph_type, len(group)))
    if "community_strength" in loss_df.columns:
        lines.extend(["", "## By Community Strength", ""])
        for strength, group in loss_df.groupby("community_strength"):
            lines.append("- {}: {} loss cases.".format(strength, len(group)))
    numeric = [
        "n",
        "m",
        "density",
        "average_degree",
        "max_degree",
        "degree_heterogeneity",
        "clustering_coefficient",
        "num_louvain_communities",
        "modularity",
        "inter_community_edge_ratio",
        "largest_community_ratio",
        "average_shortest_path_length",
        "diameter",
    ]
    lines.extend(["", "## Feature Means", "", "| feature | mean | median |", "|---|---:|---:|"])
    for col in numeric:
        if col in loss_df.columns:
            vals = pd.to_numeric(loss_df[col], errors="coerce")
            lines.append("| {} | {:.6f} | {:.6f} |".format(col, vals.mean(), vals.median()))
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- M19 tends to win when sampled shortest-path dependency and community boundary candidates point to the same bottleneck edges.",
            "- M19 can lose to M5 when strong-community or high-modularity graphs require more exact shortest-path dependency than the sampled candidate set captures.",
            "- M19 can lose to M7 on some real networks when the simple dynamic community bottleneck is already stable and M19's extra candidate scoring adds little or slightly shifts edge choice.",
            "- M19-no-bridge remains a strong speed-first candidate if its paired AUC difference against M19 stays near zero on realworld finished pairs.",
        ]
    )
    (out_dir / "m19_loss_case_feature_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(df, columns=None, floatfmt=".6f"):
    if df is None or df.empty:
        return ""
    table = df.copy()
    if columns is not None:
        table = table[[col for col in columns if col in table.columns]].copy()
    headers = list(table.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in table.iterrows():
        cells = []
        for col in headers:
            value = row[col]
            if pd.isna(value):
                cells.append("")
            elif isinstance(value, (float, np.floating)):
                cells.append(format(float(value), floatfmt))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_research_summary(method_df, per_graph_df, winloss_df, status_df, loss_df, fair_summary, ablation_summary, out_dir):
    lines = [
        "# Next-stage Fair Comparison Summary",
        "",
        "This report is generated from `next_stage_method_summary.csv`, `next_stage_per_graph_results.csv`, `fair_subset_summary.csv`, `next_stage_winloss_summary.csv`, `next_stage_timeout_skipped_summary.csv`, `m19_ablation_summary.csv`, and `m19_loss_cases.csv`.",
        "",
        "## 1. Research Goal",
        "",
        "The current research goal is to build a network-collapse attack that approaches or exceeds dynamic edge betweenness attack M5 in destructive effect, while avoiding full edge betweenness recomputation and remaining feasible on larger synthetic and real-world networks.",
        "",
        "## 2. Method Family",
        "",
        "The next-stage fair comparison focuses on M4, M5, M7, M12, M18-tuned, M19, and M19-no-bridge. M5 is the strong but expensive dynamic edge-betweenness baseline. M19 is the current main line because it combines community bottlenecks, boundary priorities, local bridge candidates, and sampled shortest-path dependency on the current GCC.",
        "",
    ]
    if not method_df.empty:
        cols = [
            "dataset",
            "method_label",
            "num_graphs",
            "mean_normalized_auc",
            "mean_final_gcc_ratio",
            "total_runtime_seconds",
            "mean_auc_rank",
            "mean_speedup_vs_m5",
            "mean_speedup_vs_m7",
        ]
        lines.append(markdown_table(method_df, cols))
    lines.extend(["", "## 3. Main Method: M19", ""])
    lines.append("M19 scores only a candidate edge pool, not all edges. The score is:")
    lines.append("")
    lines.append("`S19(e)=alpha*norm(sampled_path)+beta*norm(community_bottleneck)+gamma*norm(boundary_local_score)+delta*bridge_bonus`")
    lines.append("")
    lines.append("Default parameters in this stage are `candidate_topk=128`, `sample_sources=32`, `tau_bridge=0.05`, `alpha=5.0`, `beta=2.0`, `gamma=1.0`, `delta=0.5`, with adaptive stale Louvain interval 10 and early refresh when GCC ratio drops by more than 0.05.")
    lines.extend(["", "## 4. Synthetic Benchmark Results", ""])
    syn = method_df[method_df["dataset"] == "synthetic"].sort_values("mean_normalized_auc")
    if not syn.empty:
        best = syn.iloc[0]
        lines.append(
            "On synthetic large300 45-graph, 100% removal-budget results, the lowest mean normalized AUC is `{:.6f}` from `{}`.".format(
                best["mean_normalized_auc"], SHORT_LABELS.get(best["method"], best["method"])
            )
        )
        lines.append("")
        lines.append(markdown_table(syn, ["method_label", "num_graphs", "mean_normalized_auc", "total_runtime_seconds", "mean_auc_rank"]))
    lines.extend(["", "## 5. Real-world Network Results", ""])
    real = method_df[method_df["dataset"] == "realworld"].sort_values("mean_normalized_auc") if not method_df.empty else pd.DataFrame()
    if not real.empty:
        lines.append(markdown_table(real, ["method_label", "num_graphs", "mean_normalized_auc", "total_runtime_seconds", "mean_auc_rank"]))
    lines.extend(["", "## 6. M5 Timeout and Fair Subset Comparison", ""])
    real_status = status_df[status_df["dataset"] == "realworld"] if not status_df.empty else pd.DataFrame()
    if not real_status.empty:
        lines.append(markdown_table(real_status, floatfmt=".0f"))
    lines.append("")
    lines.append("M5 is treated as a small-graph strong baseline on real networks. Large real graph-method pairs are not forced to run; they are recorded as `skipped_due_to_size` or `timeout`.")
    if fair_summary is not None and not fair_summary.empty:
        lines.append("")
        lines.append("Fair subsets are separated to avoid mixing synthetic-full, realworld-full, and the M5-finished real subset:")
        lines.append("")
        lines.append(markdown_table(fair_summary, ["fair_subset", "method_label", "num_finished_graphs", "mean_normalized_auc", "total_runtime_seconds", "finished", "timeout", "failed", "skipped_due_to_size", "not_attempted"]))
    lines.extend(["", "## 7. M19 vs M5 / M7 / M12 / M19-no-bridge", ""])
    if not winloss_df.empty:
        lines.append(markdown_table(winloss_df))
    lines.extend(["", "## 8. Ablation Study", ""])
    if ablation_summary is not None and not ablation_summary.empty:
        lines.append("Ablation evidence separates full M19, no-bridge, candidate-only/no-sampled-dependency, sample-only, and sample-size variants.")
        lines.append("")
        lines.append(markdown_table(ablation_summary, ["dataset", "method_variant", "sample_size", "num_finished_graphs", "mean_normalized_auc", "total_runtime_seconds", "mean_runtime_seconds"]))
    else:
        lines.append("Ablation CSV is not available yet; run `--stage ablation_smoke` then `--stage ablation` to populate sample-only and sample-size variants.")
    lines.extend(["", "## 9. Loss-case Analysis", ""])
    lines.append("- Loss-case CSV: `result/next_stage_fair_comparison/m19_loss_cases.csv`.")
    lines.append("- Extended feature table: `result/next_stage_fair_comparison/m19_loss_case_feature_table.csv`.")
    lines.append("- Feature report: `result/next_stage_fair_comparison/m19_loss_case_feature_summary.md`.")
    if not loss_df.empty:
        lines.append("- Total M19 loss cases found: {}.".format(len(loss_df)))
        lines.append("- Loss to M5: {}; loss to M7: {}.".format(int(loss_df["loss_to_m5"].sum()), int(loss_df["loss_to_m7"].sum())))
    lines.extend(
        [
            "",
            "M19 tends to lose when exact shortest-path dependency matters more than the sampled candidate set can capture, or when a simple community bottleneck score such as M7 is already very stable on a real network. Strong community structure can also make a small number of exact high-betweenness inter-community edges decisive, which helps M5.",
            "",
            "## 10. Figures and Result Files",
            "",
            "| Figure | Use in presentation |",
            "|---|---|",
            "| `result/next_stage_fair_comparison/average_gcc_curve.png` | Overall GCC collapse curves. |",
            "| `result/next_stage_fair_comparison/auc_heatmap_realworld.png` | Real network x method AUC overview. |",
            "| `result/next_stage_fair_comparison/method_average_rank.png` | Average rank comparison. |",
            "| `result/next_stage_fair_comparison/auc_runtime_scatter.png` | AUC-runtime tradeoff. |",
            "| `result/next_stage_fair_comparison/m19_minus_m7_auc_difference.png` | Per-graph M19 vs M7 differences. |",
            "| `result/next_stage_fair_comparison/m19_minus_m5_auc_difference.png` | Per-graph M19 vs M5 differences on finished M5 pairs. |",
            "| `result/next_stage_fair_comparison/m19_full_vs_no_bridge_difference.png` | Whether no-bridge can be a faster M19 version. |",
            "| `result/next_stage_fair_comparison/timeout_skipped_bar.png` | Why M5 is not a full large-real-network baseline. |",
            "| `result/next_stage_fair_comparison/loss_case_feature_heatmap.png` | Structural features of M19 loss cases. |",
            "| `result/next_stage_fair_comparison/ablation_auc_runtime_scatter.png` | M19 ablation AUC-runtime tradeoff. |",
            "| `result/next_stage_fair_comparison/ablation_sample_size_curve.png` | M19 sample-size sensitivity. |",
            "",
            "Core CSV files: `next_stage_method_summary.csv`, `next_stage_per_graph_results.csv`, `fair_subset_summary.csv`, `fair_subset_per_graph_results.csv`, `realworld_method_status_detail.csv`, `m19_ablation_summary.csv`, `m19_ablation_per_graph_results.csv`, `m19_loss_case_feature_table.csv`.",
            "",
            "## 11. Current Conclusion",
            "",
            "M19 remains the strongest paper-candidate method in the current evidence chain: it improves synthetic normalized AUC over M5 while avoiding full edge betweenness, and on real networks it is close to M7 and consistently stronger than M12 on the finished set. M19-no-bridge remains a credible faster variant because its paired AUC gap against M19 is small in existing outputs.",
            "",
            "## 12. Next Steps",
            "",
            "Do not introduce M20-style new methods as the main line yet. First use this fair-comparison package for advisor reporting and paper framing. If optimization continues, prioritize M19-no-bridge and strong-community loss-case tuning.",
        ]
    )
    (out_dir / "next_stage_research_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def aggregate(out_dir, args, stage="full"):
    syn_summary, syn_curves = load_existing_synthetic_results()
    real_summary, real_curves, real_skipped = load_existing_real_results()
    new_summary, new_curves, new_skipped = collect_new_runs(out_dir, "smoke" if stage == "smoke" else "full")
    summary_frames = [df for df in [syn_summary, real_summary, new_summary] if not df.empty]
    curve_frames = [df for df in [syn_curves, real_curves, new_curves] if not df.empty]
    skipped_frames = [df for df in [real_skipped, new_skipped] if not df.empty]
    per_graph = pd.concat(summary_frames, ignore_index=True, sort=False) if summary_frames else pd.DataFrame()
    curves = pd.concat(curve_frames, ignore_index=True, sort=False) if curve_frames else pd.DataFrame()
    skipped = pd.concat(skipped_frames, ignore_index=True, sort=False) if skipped_frames else pd.DataFrame()
    if not per_graph.empty:
        per_graph = per_graph[per_graph["method"].isin(TARGET_METHODS)].copy()
        per_graph = per_graph.sort_values(["dataset", "graph_id", "method"])
        per_graph = per_graph.drop_duplicates(["dataset", "graph_id", "method"], keep="last")
        per_graph = add_ranks_and_speedups(per_graph)
    if not curves.empty:
        curves = curves[curves["method"].isin(TARGET_METHODS)].copy()
    feature_df = build_feature_table(out_dir, args)
    if not per_graph.empty and not feature_df.empty:
        feature_cols = [
            "dataset",
            "graph_id",
            "num_nodes",
            "num_edges",
            "n",
            "m",
            "density",
            "average_degree",
            "max_degree",
            "degree_heterogeneity",
            "clustering_coefficient",
            "num_louvain_communities",
            "modularity",
            "inter_community_edge_ratio",
            "largest_community_ratio",
        ]
        per_graph = per_graph.merge(feature_df[[col for col in feature_cols if col in feature_df.columns]], on=["dataset", "graph_id"], how="left")
    method_df = method_summary(per_graph)
    winloss_df = winloss_summary(per_graph)
    valid_real_graphs = len(load_real_metadata())
    status_df = timeout_skipped_summary(per_graph, skipped, valid_real_graphs)
    real_status_detail = realworld_status_detail(per_graph, skipped, feature_df, valid_real_graphs)
    fair_per, fair_summary = fair_subset_tables(per_graph, real_status_detail)
    loss_df = loss_cases(per_graph, feature_df)
    ablation_per, ablation_summary = build_ablation_tables(out_dir, per_graph, include_smoke=True)

    write_csv(per_graph, out_dir / "next_stage_per_graph_results.csv")
    write_csv(method_df, out_dir / "next_stage_method_summary.csv")
    write_csv(winloss_df, out_dir / "next_stage_winloss_summary.csv")
    write_csv(status_df, out_dir / "next_stage_timeout_skipped_summary.csv")
    write_csv(real_status_detail, out_dir / "realworld_method_status_detail.csv")
    write_csv(fair_per, out_dir / "fair_subset_per_graph_results.csv")
    write_csv(fair_summary, out_dir / "fair_subset_summary.csv")
    write_csv(loss_df, out_dir / "m19_loss_cases.csv")
    write_csv(loss_df, out_dir / "m19_loss_case_feature_table.csv")
    write_csv(ablation_per, out_dir / "m19_ablation_per_graph_results.csv")
    write_csv(ablation_summary, out_dir / "m19_ablation_summary.csv")
    if not curves.empty:
        write_csv(curves, out_dir / "next_stage_attack_curves.csv")
    plot_average_gcc(curves, out_dir / "average_gcc_curve.png")
    plot_real_heatmap(per_graph, out_dir / "auc_heatmap_realworld.png")
    plot_method_rank(method_df, out_dir / "method_average_rank.png")
    plot_auc_runtime(method_df, out_dir / "auc_runtime_scatter.png")
    plot_auc_diff(per_graph, METHOD_M7, out_dir / "m19_minus_m7_auc_difference.png", "M19 - M7 normalized AUC")
    plot_auc_diff(per_graph, METHOD_M5, out_dir / "m19_minus_m5_auc_difference.png", "M19 - M5 normalized AUC")
    plot_auc_diff(per_graph, METHOD_M19_NO_BRIDGE, out_dir / "m19_full_vs_no_bridge_difference.png", "M19 full - M19-no-bridge normalized AUC")
    plot_timeout_skipped(status_df, out_dir / "timeout_skipped_bar.png")
    plot_loss_features(loss_df, out_dir)
    plot_ablation_auc_runtime(ablation_summary, out_dir / "ablation_auc_runtime_scatter.png")
    plot_ablation_sample_size(ablation_summary, out_dir / "ablation_sample_size_curve.png")
    write_loss_case_report(loss_df, out_dir)
    write_research_summary(method_df, per_graph, winloss_df, status_df, loss_df, fair_summary, ablation_summary, out_dir)


def run_smoke(out_dir, args):
    run_args = make_run_args(args)
    log = []
    for graph_id, group in load_synthetic_groups(max_graphs=2):
        meta = synthetic_meta(group)
        graph = reconstruct_synthetic_graph(group)
        for method in [METHOD_M4, METHOD_M19_NO_BRIDGE]:
            status = run_pair(out_dir, "smoke", "synthetic", meta, graph, method, args, run_args)
            log.append("synthetic {} {} {}".format(graph_id, method, status))
            print(log[-1], flush=True)
    metadata = load_real_metadata(max_networks=3)
    for _, row in metadata.iterrows():
        meta = row.to_dict()
        graph = load_real_graph(meta)
        for method in [METHOD_M4, METHOD_M18_TUNED, METHOD_M19_NO_BRIDGE]:
            status = run_pair(out_dir, "smoke", "realworld", meta, graph, method, args, run_args)
            log.append("realworld {} {} {}".format(meta["graph_id"], method, status))
            print(log[-1], flush=True)
    (out_dir / "smoke_run_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    aggregate(out_dir, args, stage="smoke")


def run_missing(out_dir, args):
    run_args = make_run_args(args)
    log = []
    datasets = set(parse_list(args.missing_datasets))
    requested_methods = {part.lower() for part in parse_list(args.missing_methods)}
    if not datasets:
        datasets = {"synthetic", "realworld"}
    if "synthetic" in datasets:
        for graph_id, group in load_synthetic_groups(max_graphs=args.max_synthetic_missing):
            meta = synthetic_meta(group)
            graph = reconstruct_synthetic_graph(group)
            synthetic_methods = [METHOD_M4]
            for method in synthetic_methods:
                method_keys = {method_slug(method).lower(), SHORT_LABELS.get(method, method).lower(), method.lower()}
                if requested_methods and not (requested_methods & method_keys):
                    continue
                status = run_pair(out_dir, "missing", "synthetic", meta, graph, method, args, run_args)
                log.append("synthetic {} {} {}".format(graph_id, method, status))
                print(log[-1], flush=True)
    if "realworld" in datasets:
        metadata = load_real_metadata(max_networks=args.max_real_missing)
        for _, row in metadata.iterrows():
            meta = row.to_dict()
            graph = load_real_graph(meta)
            for method in [METHOD_M4, METHOD_M18_TUNED]:
                method_keys = {method_slug(method).lower(), SHORT_LABELS.get(method, method).lower(), method.lower()}
                if requested_methods and not (requested_methods & method_keys):
                    continue
                status = run_pair(out_dir, "missing", "realworld", meta, graph, method, args, run_args)
                log.append("realworld {} {} {}".format(meta["graph_id"], method, status))
                print(log[-1], flush=True)
    with (out_dir / "missing_run_log.txt").open("a", encoding="utf-8") as handle:
        handle.write("\n".join(log) + "\n")
    aggregate(out_dir, args, stage="full")


def run_ablation(out_dir, args, smoke=False):
    run_args = make_run_args(args)
    stage = "ablation_smoke" if smoke else "ablation"
    log = []
    synthetic_limit = 2 if smoke else args.max_ablation_synthetic
    if synthetic_limit == 0 and not smoke:
        synthetic_limit = 0
    synthetic_methods = [METHOD_M19_SAMPLE_ONLY, METHOD_M19_SAMPLE_16, METHOD_M19_SAMPLE_64]
    for graph_id, group in load_synthetic_groups(max_graphs=synthetic_limit):
        meta = synthetic_meta(group)
        graph = reconstruct_synthetic_graph(group)
        for method in synthetic_methods:
            status = run_ablation_pair(out_dir, stage, "synthetic", meta, graph, method, args, run_args)
            log.append("synthetic {} {} {}".format(graph_id, method, status))
            print(log[-1], flush=True)

    real_limit = 2 if smoke else args.max_ablation_real
    if real_limit > 0:
        m5_subset_path = out_dir / "next_stage_per_graph_results.csv"
        graph_ids = []
        if m5_subset_path.exists():
            try:
                per = pd.read_csv(m5_subset_path)
                graph_ids = list(
                    per[(per["dataset"] == "realworld") & (per["method"] == METHOD_M5)]["graph_id"].drop_duplicates()
                )[:real_limit]
            except pd.errors.EmptyDataError:
                graph_ids = []
        metadata = load_real_metadata(graph_ids=graph_ids, max_networks=real_limit if not graph_ids else 0)
        for _, row in metadata.iterrows():
            meta = row.to_dict()
            graph = load_real_graph(meta)
            for method in [METHOD_M19_SAMPLE_ONLY, METHOD_M19_SAMPLE_16, METHOD_M19_SAMPLE_64]:
                status = run_ablation_pair(out_dir, stage, "realworld", meta, graph, method, args, run_args)
                log.append("realworld {} {} {}".format(meta["graph_id"], method, status))
                print(log[-1], flush=True)
    with (out_dir / ("ablation_smoke_log.txt" if smoke else "ablation_run_log.txt")).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(log) + "\n")
    aggregate(out_dir, args, stage="smoke" if smoke else "full")


def parse_args():
    parser = argparse.ArgumentParser(description="Next-stage fair comparison and M19 loss-case analysis.")
    parser.add_argument("--stage", choices=["smoke", "missing", "ablation_smoke", "ablation", "aggregate"], default="smoke")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--max-remove-ratio", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--m5-max-nodes", type=int, default=2000)
    parser.add_argument("--m5-max-edges", type=int, default=10000)
    parser.add_argument("--overwrite-runs", action="store_true")
    parser.add_argument("--missing-datasets", default="synthetic,realworld")
    parser.add_argument("--missing-methods", default="")
    parser.add_argument("--max-synthetic-missing", type=int, default=0)
    parser.add_argument("--max-real-missing", type=int, default=0)
    parser.add_argument("--max-ablation-synthetic", type=int, default=0)
    parser.add_argument("--max-ablation-real", type=int, default=0)
    parser.add_argument("--candidate-topk", type=int, default=128)
    parser.add_argument("--sample-sources", type=int, default=32)
    parser.add_argument("--tau-bridge", type=float, default=0.05)
    parser.add_argument("--alpha", type=float, default=5.0)
    parser.add_argument("--beta", type=float, default=2.0)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--delta", type=float, default=0.5)
    parser.add_argument("--m19-louvain-interval", type=int, default=10)
    parser.add_argument("--m19-louvain-drop-threshold", type=float, default=0.05)
    parser.add_argument("--m12-louvain-interval", type=int, default=10)
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    config = vars(args).copy()
    config["seed"] = SEED
    (out_dir / "config_last_run.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.stage == "smoke":
        run_smoke(out_dir, args)
    elif args.stage == "missing":
        run_missing(out_dir, args)
    elif args.stage == "ablation_smoke":
        run_ablation(out_dir, args, smoke=True)
    elif args.stage == "ablation":
        run_ablation(out_dir, args, smoke=False)
    else:
        aggregate(out_dir, args, stage="full")
    print("stage {} complete, outputs in {}".format(args.stage, out_dir), flush=True)


if __name__ == "__main__":
    main()
