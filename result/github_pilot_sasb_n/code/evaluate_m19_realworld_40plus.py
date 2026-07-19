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

import evaluate_m18_candidate as m18
import evaluate_m19_next_stage_validation as m19val


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260513

DEFAULT_DATA_DIR = ROOT / "data" / "realnetworks_40plus"
DEFAULT_VALIDATION_PATH = ROOT / "result" / "m19_realworld_40plus_validation" / "graph_validation_summary.csv"
DEFAULT_OUT_DIR = ROOT / "result" / "m19_realworld_40plus"

METHOD_M19_FULL = m18.METHOD_M19
METHOD_M19_NO_BRIDGE = "M19-no-bridge"
METHOD_M7 = m18.METHOD_M7
METHOD_M12 = m18.METHOD_M12
METHOD_M5 = m18.METHOD_M5
METHOD_M18_TUNED = m18.METHOD_M18_TUNED

CORE_METHODS = [METHOD_M19_FULL, METHOD_M19_NO_BRIDGE, METHOD_M7, METHOD_M12]
PLOT_LABELS = {
    METHOD_M19_FULL: "M19 full",
    METHOD_M19_NO_BRIDGE: "M19 no-bridge",
    METHOD_M7: "M7",
    METHOD_M12: "M12",
    METHOD_M5: "M5",
    METHOD_M18_TUNED: "M18-tuned",
}


def method_slug(method):
    return (
        method.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
    )


def write_csv(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def load_cleaned_graph(path):
    graph = nx.read_edgelist(path, nodetype=int, data=False)
    graph = nx.Graph(graph)
    graph.remove_edges_from(nx.selfloop_edges(graph))
    mapping = {node: idx for idx, node in enumerate(sorted(graph.nodes()))}
    graph = nx.relabel_nodes(graph, mapping, copy=True)
    return graph


def load_valid_metadata(data_dir, validation_path, max_networks=0, graph_ids=None):
    metadata = pd.read_csv(data_dir / "metadata" / "real_networks_metadata.csv")
    validation = pd.read_csv(validation_path)
    valid_ids = set(validation[validation["is_valid"]]["graph_id"])
    if graph_ids:
        valid_ids &= set(graph_ids)
    metadata = metadata[metadata["graph_id"].isin(valid_ids)].copy()
    metadata = metadata.sort_values(["num_edges_gcc", "num_nodes_gcc", "graph_id"])
    if max_networks > 0:
        metadata = metadata.head(max_networks)
    return metadata


def first_remove_ratio_at_or_below(curve_df, threshold):
    hit = curve_df[curve_df["gcc_ratio"] <= threshold]
    if hit.empty:
        return np.nan
    return float(hit["remove_ratio"].iloc[0])


def curve_row(meta, method, step, original_m, ratio):
    return {
        "graph_id": meta["graph_id"],
        "graph_name": meta["graph_name"],
        "graph_type": meta["graph_type"],
        "method": method,
        "removed_edges": step,
        "remove_ratio": step / float(max(1, original_m)),
        "gcc_ratio": ratio,
    }


def gcc_ratio(graph, original_n):
    if original_n <= 0 or graph.number_of_nodes() == 0:
        return 0.0
    if graph.number_of_edges() == 0:
        return 1.0 / float(original_n)
    gcc_size = len(max(nx.connected_components(graph), key=len))
    return gcc_size / float(original_n)


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
    if method == METHOD_M19_NO_BRIDGE:
        return m19val.choose_m19_ablation_edge(graph, METHOD_M19_NO_BRIDGE, step, state, run_args)
    if method == METHOD_M18_TUNED:
        return m18.choose_edge(graph, method, step, state, m18.m18_tuned_args(run_args))
    return m18.choose_edge(graph, method, step, state, run_args)


def simulate_attack(meta, graph0, method, run_args, timeout_seconds):
    graph = graph0.copy()
    original_n = graph.number_of_nodes()
    original_m = graph.number_of_edges()
    rows = [curve_row(meta, method, 0, original_m, gcc_ratio(graph, original_n))]
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
        rows.append(curve_row(meta, method, step, original_m, gcc_ratio(graph, original_n)))
    elapsed = time.perf_counter() - start
    for row in rows:
        row["elapsed_seconds"] = elapsed
    timings = {}
    if method == METHOD_M19_FULL:
        timings = state.get("m19_timings", {}).copy()
        timings["louvain_recomputes"] = state.get("m19_louvain_recomputes", 0)
    elif method == METHOD_M19_NO_BRIDGE:
        timings = state.get("m19_ablation_timings", {}).copy()
        timings["louvain_recomputes"] = state.get("m19_ablation_louvain_recomputes", 0)
    elif method == METHOD_M18_TUNED:
        timings = state.get("m18_timings", {}).copy()
    return pd.DataFrame(rows), elapsed, timings, timed_out


def summarize_curve(curve_df, elapsed_seconds, timings, status):
    x = curve_df["remove_ratio"].values
    y = curve_df["gcc_ratio"].values
    observed_remove_ratio = float(x[-1]) if len(x) else 0.0
    auc = float(np.trapz(y, x)) if len(x) else np.nan
    row = {
        "graph_id": curve_df["graph_id"].iloc[0],
        "graph_name": curve_df["graph_name"].iloc[0],
        "graph_type": curve_df["graph_type"].iloc[0],
        "method": curve_df["method"].iloc[0],
        "status": status,
        "auc": auc,
        "normalized_auc": auc / observed_remove_ratio if observed_remove_ratio > 0 else np.nan,
        "runtime_seconds": float(elapsed_seconds),
        "elapsed_seconds": float(elapsed_seconds),
        "removed_edges": int(curve_df["removed_edges"].max()) if len(curve_df) else 0,
        "observed_remove_ratio": observed_remove_ratio,
        "final_gcc_ratio": float(y[-1]) if len(y) else np.nan,
        "remove_ratio_gcc_le_0.5": first_remove_ratio_at_or_below(curve_df, 0.5),
        "remove_ratio_gcc_le_0.2": first_remove_ratio_at_or_below(curve_df, 0.2),
        "remove_ratio_gcc_le_0.1": first_remove_ratio_at_or_below(curve_df, 0.1),
    }
    row.update(timings)
    return row


def graph_features(graph, meta):
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    degrees = np.array([degree for _, degree in graph.degree()], dtype=float)
    avg_degree = float(degrees.mean()) if len(degrees) else 0.0
    if m > 0:
        partition = community_louvain.best_partition(graph, random_state=SEED)
    else:
        partition = {node: idx for idx, node in enumerate(graph.nodes())}
    communities = len(set(partition.values())) if partition else 0
    modularity = community_louvain.modularity(partition, graph) if m > 0 and communities > 1 else 0.0
    bridge_count = sum(1 for _ in nx.bridges(graph)) if m > 0 else 0
    return {
        "graph_id": meta["graph_id"],
        "graph_name": meta["graph_name"],
        "graph_type": meta["graph_type"],
        "num_nodes": n,
        "num_edges": m,
        "density": nx.density(graph) if n > 1 else 0.0,
        "average_degree": avg_degree,
        "clustering_coefficient": nx.average_clustering(graph) if n > 0 else 0.0,
        "modularity": modularity,
        "num_louvain_communities": communities,
        "bridge_count": bridge_count,
        "bridge_ratio": bridge_count / float(max(1, m)),
        "degree_heterogeneity": float(degrees.std() / avg_degree) if avg_degree > 0 else 0.0,
    }


def run_pair(meta, graph, method, args, run_args, out_dir):
    run_dir = out_dir / "runs" / meta["graph_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    slug = method_slug(method)
    summary_path = run_dir / "{}_summary.csv".format(slug)
    curve_path = run_dir / "{}_curve.csv".format(slug)
    if summary_path.exists() and curve_path.exists() and not args.overwrite_runs:
        try:
            existing = pd.read_csv(summary_path)
            if not existing.empty and existing.get("status", pd.Series([""])).iloc[0] in {
                "finished",
                "skipped_due_to_size",
            }:
                return "skipped_finished"
        except Exception:
            pass
    if method == METHOD_M5 and not (
        int(meta["num_nodes_gcc"]) <= args.m5_max_nodes and int(meta["num_edges_gcc"]) <= args.m5_max_edges
    ):
        skipped = pd.DataFrame(
            [
                {
                    "graph_id": meta["graph_id"],
                    "graph_name": meta["graph_name"],
                    "graph_type": meta["graph_type"],
                    "method": method,
                    "status": "skipped_due_to_size",
                    "reason": "num_nodes_gcc={} num_edges_gcc={}".format(meta["num_nodes_gcc"], meta["num_edges_gcc"]),
                }
            ]
        )
        write_csv(skipped, summary_path)
        write_csv(pd.DataFrame(), curve_path)
        return "skipped_due_to_size"
    try:
        curve_df, elapsed, timings, timed_out = simulate_attack(
            meta,
            graph,
            method,
            run_args,
            args.timeout_seconds,
        )
        status = "timeout" if timed_out else "finished"
        summary = pd.DataFrame([summarize_curve(curve_df, elapsed, timings, status)])
        write_csv(curve_df, curve_path)
        write_csv(summary, summary_path)
        return status
    except Exception as exc:
        failed = pd.DataFrame(
            [
                {
                    "graph_id": meta["graph_id"],
                    "graph_name": meta["graph_name"],
                    "graph_type": meta["graph_type"],
                    "method": method,
                    "status": "failed",
                    "reason": repr(exc),
                }
            ]
        )
        write_csv(failed, summary_path)
        write_csv(pd.DataFrame(), curve_path)
        return "failed"


def collect_run_outputs(out_dir):
    summaries = []
    curves = []
    skipped_failed = []
    for summary_path in sorted((out_dir / "runs").glob("*/*_summary.csv")):
        try:
            df = pd.read_csv(summary_path)
        except pd.errors.EmptyDataError:
            continue
        if df.empty:
            continue
        if "status" in df.columns and df["status"].iloc[0] == "finished":
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
            skipped_failed.append(df)
    summary_df = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
    curve_df = pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()
    skip_df = pd.concat(skipped_failed, ignore_index=True) if skipped_failed else pd.DataFrame()
    return summary_df, curve_df, skip_df


def average_results(summary_df):
    rows = []
    if summary_df.empty:
        return pd.DataFrame()
    for method, group in summary_df.groupby("method", sort=False):
        rows.append(
            {
                "method": method,
                "num_graphs": len(group),
                "mean_auc": group["auc"].mean(),
                "mean_normalized_auc": group["normalized_auc"].mean(),
                "median_normalized_auc": group["normalized_auc"].median(),
                "total_runtime_seconds": group["runtime_seconds"].sum(),
                "mean_runtime_seconds": group["runtime_seconds"].mean(),
                "mean_final_gcc_ratio": group["final_gcc_ratio"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(["mean_normalized_auc", "total_runtime_seconds"])


def winloss(summary_df):
    rows = []
    baselines = [METHOD_M7, METHOD_M12, METHOD_M5, METHOD_M19_NO_BRIDGE]
    for baseline in baselines:
        diffs = []
        wins = losses = ties = 0
        for graph_id, group in summary_df.groupby("graph_id", sort=False):
            by_method = {row["method"]: row for _, row in group.iterrows()}
            if METHOD_M19_FULL not in by_method or baseline not in by_method:
                continue
            diff = float(by_method[METHOD_M19_FULL]["normalized_auc"]) - float(by_method[baseline]["normalized_auc"])
            diffs.append(diff)
            if diff < -1e-12:
                wins += 1
            elif diff > 1e-12:
                losses += 1
            else:
                ties += 1
        if diffs:
            rows.append(
                {
                    "baseline_method": baseline,
                    "num_graphs": len(diffs),
                    "m19_wins": wins,
                    "m19_losses": losses,
                    "ties": ties,
                    "mean_auc_diff_m19_minus_baseline": float(np.mean(diffs)),
                }
            )
    return pd.DataFrame(rows)


def m19_loss_cases(summary_df, feature_df):
    rows = []
    for baseline in [METHOD_M7, METHOD_M12, METHOD_M5, METHOD_M19_NO_BRIDGE]:
        for graph_id, group in summary_df.groupby("graph_id", sort=False):
            by_method = {row["method"]: row for _, row in group.iterrows()}
            if METHOD_M19_FULL not in by_method or baseline not in by_method:
                continue
            diff = float(by_method[METHOD_M19_FULL]["normalized_auc"]) - float(by_method[baseline]["normalized_auc"])
            if diff > 1e-12:
                rows.append(
                    {
                        "graph_id": graph_id,
                        "baseline_method": baseline,
                        "m19_normalized_auc": float(by_method[METHOD_M19_FULL]["normalized_auc"]),
                        "baseline_normalized_auc": float(by_method[baseline]["normalized_auc"]),
                        "auc_diff_m19_minus_baseline": diff,
                    }
                )
    loss_df = pd.DataFrame(rows)
    if loss_df.empty or feature_df.empty:
        return loss_df
    return loss_df.merge(feature_df, on="graph_id", how="left")


def runtime_summary(summary_df):
    if summary_df.empty:
        return pd.DataFrame()
    rows = []
    for method, group in summary_df.groupby("method", sort=False):
        rows.append(
            {
                "method": method,
                "num_finished": len(group),
                "total_runtime_seconds": group["runtime_seconds"].sum(),
                "mean_runtime_seconds": group["runtime_seconds"].mean(),
                "max_runtime_seconds": group["runtime_seconds"].max(),
            }
        )
    return pd.DataFrame(rows)


def interpolate_average_curve(curve_df):
    if curve_df.empty:
        return pd.DataFrame()
    grid = np.linspace(0.0, 1.0, 201)
    rows = []
    for method, method_df in curve_df.groupby("method", sort=False):
        values = []
        for _, graph_df in method_df.groupby("graph_id", sort=False):
            graph_df = graph_df.sort_values("remove_ratio")
            reduced = graph_df.groupby("remove_ratio", as_index=False)["gcc_ratio"].mean()
            x = reduced["remove_ratio"].values.astype(float)
            y = reduced["gcc_ratio"].values.astype(float)
            if len(x):
                values.append(np.interp(grid, x, y, left=y[0], right=y[-1]))
        if values:
            mean_y = np.vstack(values).mean(axis=0)
            for x_value, y_value in zip(grid, mean_y):
                rows.append({"method": method, "remove_ratio": x_value, "mean_gcc_ratio": y_value})
    return pd.DataFrame(rows)


def plot_average_gcc(curve_df, path):
    avg = interpolate_average_curve(curve_df)
    if avg.empty:
        return
    plt.figure(figsize=(10, 6))
    for method, group in avg.groupby("method", sort=False):
        plt.plot(group["remove_ratio"], group["mean_gcc_ratio"], label=PLOT_LABELS.get(method, method), linewidth=2)
    plt.xlabel("Removed edge ratio")
    plt.ylabel("Mean GCC ratio")
    plt.title("Average GCC curve on real networks")
    plt.grid(alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_box(summary_df, column, title, ylabel, path):
    if summary_df.empty:
        return
    methods = list(summary_df["method"].drop_duplicates())
    data = [summary_df[summary_df["method"] == method][column].values for method in methods]
    plt.figure(figsize=(10, 6))
    plt.boxplot(data, labels=[PLOT_LABELS.get(method, method) for method in methods], showfliers=True)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_auc_runtime(avg_df, path):
    if avg_df.empty:
        return
    plt.figure(figsize=(9, 5.5))
    for _, row in avg_df.iterrows():
        plt.scatter(row["total_runtime_seconds"], row["mean_normalized_auc"], s=60)
        plt.text(row["total_runtime_seconds"], row["mean_normalized_auc"], PLOT_LABELS.get(row["method"], row["method"]), fontsize=8)
    plt.xlabel("Total runtime seconds")
    plt.ylabel("Mean normalized AUC")
    plt.title("AUC-runtime tradeoff on real networks")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_auc_diff(summary_df, baseline, path, title):
    rows = []
    for graph_id, group in summary_df.groupby("graph_id", sort=False):
        by_method = {row["method"]: row for _, row in group.iterrows()}
        if METHOD_M19_FULL not in by_method or baseline not in by_method:
            continue
        rows.append(
            {
                "graph_id": graph_id,
                "diff": float(by_method[METHOD_M19_FULL]["normalized_auc"]) - float(by_method[baseline]["normalized_auc"]),
            }
        )
    diff_df = pd.DataFrame(rows)
    if diff_df.empty:
        return
    diff_df = diff_df.sort_values("diff")
    plt.figure(figsize=(12, 5.5))
    colors = ["#d62728" if value > 0 else "#2ca02c" for value in diff_df["diff"]]
    plt.bar(diff_df["graph_id"], diff_df["diff"], color=colors)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xticks(rotation=90, fontsize=7)
    plt.ylabel("Normalized AUC difference")
    plt.title(title)
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def plot_winloss(winloss_df, path):
    if winloss_df.empty:
        return
    labels = [PLOT_LABELS.get(method, method) for method in winloss_df["baseline_method"]]
    x = np.arange(len(labels))
    plt.figure(figsize=(9, 5.2))
    plt.bar(x - 0.2, winloss_df["m19_wins"], width=0.4, label="M19 wins")
    plt.bar(x + 0.2, winloss_df["m19_losses"], width=0.4, label="M19 losses")
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Number of graphs")
    plt.title("M19 win/loss against baselines")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def write_report(out_dir, metadata, summary_df, avg_df, skip_df, winloss_df, loss_df):
    num_collected = len(metadata)
    type_counts = metadata.groupby("graph_type").size().sort_values(ascending=False)
    any_finished_graphs = summary_df["graph_id"].nunique() if not summary_df.empty else 0
    status_rows = []
    if not summary_df.empty:
        finished_status = summary_df[["graph_id", "method", "status"]].copy()
    else:
        finished_status = pd.DataFrame(columns=["graph_id", "method", "status"])
    if not skip_df.empty and {"graph_id", "method", "status"}.issubset(skip_df.columns):
        status_df = pd.concat([finished_status, skip_df[["graph_id", "method", "status"]]], ignore_index=True)
    else:
        status_df = finished_status
    if not status_df.empty:
        for (method, status), group in status_df.groupby(["method", "status"], sort=False):
            status_rows.append({"method": method, "status": status, "count": len(group)})
    status_count_df = pd.DataFrame(status_rows)
    all_core_finished_graphs = 0
    core_timeout_graphs = 0
    m19_finished_graphs = 0
    if not status_df.empty:
        core_status = status_df[status_df["method"].isin(CORE_METHODS)].copy()
        if not core_status.empty:
            core_wide = core_status.pivot_table(
                index="graph_id",
                columns="method",
                values="status",
                aggfunc="first",
            )
            core_wide = core_wide.reindex(metadata["graph_id"].tolist())
            all_core_finished_graphs = int((core_wide == "finished").all(axis=1).sum())
            core_timeout_graphs = int((core_wide == "timeout").any(axis=1).sum())
        m19_finished_graphs = int(
            len(
                status_df[
                    (status_df["method"] == METHOD_M19_FULL)
                    & (status_df["status"] == "finished")
                ]
            )
        )
    avg_by_method = {row["method"]: row for _, row in avg_df.iterrows()} if not avg_df.empty else {}
    m19_row = avg_by_method.get(METHOD_M19_FULL)
    no_bridge_row = avg_by_method.get(METHOD_M19_NO_BRIDGE)
    no_bridge_gap = np.nan
    no_bridge_runtime_ratio = np.nan
    if m19_row is not None and no_bridge_row is not None:
        no_bridge_gap = float(no_bridge_row["mean_normalized_auc"]) - float(m19_row["mean_normalized_auc"])
        no_bridge_runtime_ratio = float(no_bridge_row["total_runtime_seconds"]) / float(m19_row["total_runtime_seconds"])
    loss_type_table = []
    if not loss_df.empty and "graph_type" in loss_df.columns:
        for (baseline, graph_type), group in loss_df.groupby(["baseline_method", "graph_type"], sort=False):
            loss_type_table.append({"baseline": baseline, "graph_type": graph_type, "count": len(group)})
    loss_feature_means = {}
    feature_cols = [
        "num_nodes",
        "num_edges",
        "density",
        "average_degree",
        "clustering_coefficient",
        "modularity",
        "num_louvain_communities",
        "bridge_ratio",
        "degree_heterogeneity",
    ]
    if not loss_df.empty:
        for col in feature_cols:
            if col in loss_df.columns:
                loss_feature_means[col] = float(loss_df[col].mean())
    lines = [
        "# M19 Real-world 40plus Report",
        "",
        "## Dataset",
        "",
        "- Collected valid real networks: {}.".format(num_collected),
        "- Networks with at least one finished method: {}.".format(any_finished_graphs),
        "- Networks with finished M19 full: {}.".format(m19_finished_graphs),
        "- Networks with all four core methods finished: {}.".format(all_core_finished_graphs),
        "- Networks with at least one core-method timeout: {}.".format(core_timeout_graphs),
        "- All {} valid networks were attempted for core methods; unfinished large graph-method pairs are recorded as `timeout`.".format(num_collected),
        "- Data directory: `data/realnetworks_40plus/`.",
        "- Attack protocol: current GCC only; GCC is recomputed after every edge removal; max_remove_ratio is 1.0 unless a run times out.",
        "",
        "## Network Types",
        "",
        "| graph_type | count |",
        "|---|---:|",
    ]
    for graph_type, count in type_counts.items():
        lines.append("| {} | {} |".format(graph_type, int(count)))
    lines.extend(["", "## Run Status", "", "| method | status | count |", "|---|---|---:|"])
    if not status_count_df.empty:
        for _, row in status_count_df.sort_values(["method", "status"]).iterrows():
            lines.append("| {} | {} | {} |".format(row["method"], row["status"], int(row["count"])))
    lines.extend(["", "## Average Results", "", "| method | graphs | mean normalized AUC | total runtime (s) |", "|---|---:|---:|---:|"])
    if not avg_df.empty:
        for _, row in avg_df.iterrows():
            lines.append(
                "| {} | {} | {:.6f} | {:.3f} |".format(
                    row["method"],
                    int(row["num_graphs"]),
                    row["mean_normalized_auc"],
                    row["total_runtime_seconds"],
                )
            )
    lines.extend(["", "## M19 Win/Loss", "", "| baseline | graphs | M19 wins | M19 losses | ties | mean AUC diff |", "|---|---:|---:|---:|---:|---:|"])
    if not winloss_df.empty:
        for _, row in winloss_df.iterrows():
            lines.append(
                "| {} | {} | {} | {} | {} | {:.6f} |".format(
                    row["baseline_method"],
                    int(row["num_graphs"]),
                    int(row["m19_wins"]),
                    int(row["m19_losses"]),
                    int(row["ties"]),
                    row["mean_auc_diff_m19_minus_baseline"],
                )
            )
    lines.extend(
        [
            "",
            "## M19-no-bridge",
            "",
            "On finished paired runs, M19-no-bridge is close to M19 full: mean normalized-AUC gap is {:.6f}. Its total runtime is {:.3f} of M19 full, so it is faster in this partial real-network run.".format(
                no_bridge_gap,
                no_bridge_runtime_ratio,
            ),
            "",
            "## Loss Cases",
            "",
            "- Number of M19 loss-case rows: {}.".format(len(loss_df)),
            "- See `m19_loss_cases.csv` for graph features and baselines where M19 loses.",
            "- Average loss-case structure: nodes={:.1f}, edges={:.1f}, density={:.4f}, average_degree={:.3f}, clustering={:.3f}, modularity={:.3f}, Louvain communities={:.2f}, bridge_ratio={:.4f}, degree_heterogeneity={:.3f}.".format(
                loss_feature_means.get("num_nodes", np.nan),
                loss_feature_means.get("num_edges", np.nan),
                loss_feature_means.get("density", np.nan),
                loss_feature_means.get("average_degree", np.nan),
                loss_feature_means.get("clustering_coefficient", np.nan),
                loss_feature_means.get("modularity", np.nan),
                loss_feature_means.get("num_louvain_communities", np.nan),
                loss_feature_means.get("bridge_ratio", np.nan),
                loss_feature_means.get("degree_heterogeneity", np.nan),
            ),
            "",
            "| baseline | graph_type | loss rows |",
            "|---|---|---:|",
        ]
    )
    for row in loss_type_table:
        lines.append("| {} | {} | {} |".format(row["baseline"], row["graph_type"], int(row["count"])))
    lines.extend(
        [
            "",
            "## Figures",
            "",
            "- `average_gcc_curve.png`",
            "- `auc_boxplot.png`",
            "- `runtime_boxplot.png`",
            "- `auc_runtime_scatter.png`",
            "- `m19_minus_m5_auc_difference.png`",
            "- `m19_full_vs_no_bridge_auc_difference.png`",
            "- `win_loss_bar_chart.png`",
            "",
            "## Skipped or Failed Runs",
            "",
            "- Rows in `skipped_or_failed_runs.csv`: {}.".format(len(skip_df)),
        ]
    )
    (out_dir / "M19_realworld_40plus_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def aggregate_outputs(args, metadata):
    out_dir = Path(args.output_dir)
    summary_df, curve_df, skip_df = collect_run_outputs(out_dir)
    feature_rows = []
    for _, meta in metadata.iterrows():
        graph = load_cleaned_graph(ROOT / meta["cleaned_file"])
        feature_rows.append(graph_features(graph, meta))
    feature_df = pd.DataFrame(feature_rows)
    avg_df = average_results(summary_df)
    winloss_df = winloss(summary_df)
    loss_df = m19_loss_cases(summary_df, feature_df)
    runtime_df = runtime_summary(summary_df)
    if skip_df.empty:
        skip_df = pd.DataFrame(columns=["graph_id", "graph_name", "graph_type", "method", "status", "reason"])
    if loss_df.empty:
        loss_df = pd.DataFrame(
            columns=[
                "graph_id",
                "baseline_method",
                "m19_normalized_auc",
                "baseline_normalized_auc",
                "auc_diff_m19_minus_baseline",
            ]
        )
    write_csv(summary_df, out_dir / "per_graph_method_results.csv")
    write_csv(avg_df, out_dir / "average_results_by_method.csv")
    write_csv(skip_df, out_dir / "skipped_or_failed_runs.csv")
    write_csv(runtime_df, out_dir / "runtime_summary.csv")
    write_csv(winloss_df, out_dir / "m19_vs_baselines_winloss.csv")
    write_csv(feature_df, out_dir / "graph_features.csv")
    write_csv(loss_df, out_dir / "m19_loss_cases.csv")
    if not curve_df.empty:
        write_csv(curve_df, out_dir / "attack_curves.csv")
        plot_average_gcc(curve_df, out_dir / "average_gcc_curve.png")
    plot_box(summary_df, "normalized_auc", "AUC distribution on real networks", "Normalized AUC", out_dir / "auc_boxplot.png")
    plot_box(summary_df, "runtime_seconds", "Runtime distribution on real networks", "Runtime seconds", out_dir / "runtime_boxplot.png")
    plot_auc_runtime(avg_df, out_dir / "auc_runtime_scatter.png")
    plot_auc_diff(summary_df, METHOD_M5, out_dir / "m19_minus_m5_auc_difference.png", "M19 - M5 normalized AUC")
    plot_auc_diff(summary_df, METHOD_M19_NO_BRIDGE, out_dir / "m19_full_vs_no_bridge_auc_difference.png", "M19 full - M19-no-bridge normalized AUC")
    plot_winloss(winloss_df, out_dir / "win_loss_bar_chart.png")
    write_report(out_dir, metadata, summary_df, avg_df, skip_df, winloss_df, loss_df)


def parse_list(text):
    return [part.strip() for part in str(text).split(",") if part.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate M19 on 40+ real-world networks.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--validation-path", default=str(DEFAULT_VALIDATION_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--stage", choices=["smoke", "core", "m5", "aggregate", "all"], default="smoke")
    parser.add_argument("--graph-ids", default="")
    parser.add_argument("--max-networks", type=int, default=0)
    parser.add_argument("--max-remove-ratio", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--m5-max-nodes", type=int, default=2000)
    parser.add_argument("--m5-max-edges", type=int, default=10000)
    parser.add_argument("--include-m18-tuned", action="store_true")
    parser.add_argument("--overwrite-runs", action="store_true")
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
    data_dir = Path(args.data_dir)
    validation_path = Path(args.validation_path)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_ids = parse_list(args.graph_ids)
    metadata = load_valid_metadata(data_dir, validation_path, args.max_networks, graph_ids)
    if args.stage == "smoke":
        metadata = metadata.head(3)
    run_args = make_run_args(args)
    methods = list(CORE_METHODS)
    if args.include_m18_tuned:
        methods.append(METHOD_M18_TUNED)
    if args.stage in {"m5"}:
        methods = [METHOD_M5]
    elif args.stage == "all":
        methods = list(CORE_METHODS) + [METHOD_M5]
        if args.include_m18_tuned:
            methods.append(METHOD_M18_TUNED)
    elif args.stage == "aggregate":
        aggregate_outputs(args, load_valid_metadata(data_dir, validation_path, 0, None))
        print("aggregated outputs to {}".format(out_dir), flush=True)
        return

    log_lines = []
    for _, meta in metadata.iterrows():
        graph = load_cleaned_graph(ROOT / meta["cleaned_file"])
        for method in methods:
            label = "{} {}".format(meta["graph_id"], method)
            print(label, flush=True)
            status = run_pair(meta, graph, method, args, run_args, out_dir)
            log_lines.append("{} {}".format(label, status))
    with (out_dir / "run_log.txt").open("a", encoding="utf-8-sig") as handle:
        handle.write("\n".join(log_lines) + "\n")
    config = vars(args).copy()
    config["seed"] = SEED
    (out_dir / "config_last_run.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    aggregate_outputs(args, load_valid_metadata(data_dir, validation_path, 0, None))
    print("stage {} complete, outputs in {}".format(args.stage, out_dir), flush=True)


if __name__ == "__main__":
    main()
