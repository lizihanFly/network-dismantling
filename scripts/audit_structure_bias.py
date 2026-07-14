from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "result" / "structure_bias_audit"
PLOT_DIR = OUT_DIR / "plots"

SYN_DIR = ROOT / "result" / "sasb_m5_edge_diagnostics" / "full_synthetic45"
REAL_DIR = ROOT / "result" / "sasb_m5_edge_diagnostics" / "full_real_completed_edges_le1305"
WHY_DIR = ROOT / "result" / "sasb_m5_edge_diagnostics" / "why_sasb_wins_or_loses"
BASELINE_DIR = ROOT / "result" / "paper_experiments" / "baselines"

DATASETS = {
    "synthetic45": SYN_DIR,
    "realworld_completed_24of28": REAL_DIR,
}

REQUIRED_INPUTS = [
    SYN_DIR / "edge_step_diagnostics.csv",
    SYN_DIR / "graph_method_summary.csv",
    REAL_DIR / "edge_step_diagnostics.csv",
    REAL_DIR / "graph_method_summary.csv",
    WHY_DIR / "graph_structure_by_outcome.csv",
    WHY_DIR / "selected_edge_summary_by_outcome_method.csv",
    WHY_DIR / "phase_auc_summary_by_outcome_method.csv",
    BASELINE_DIR / "baseline_synthetic45_summary.csv",
    BASELINE_DIR / "baseline_realworld_m5_completed_per_graph.csv",
    ROOT / "result" / "paper_experiments" / "interim_completed_subset_summary.md",
    ROOT / "RESEARCH_PROGRESS_ALGORITHM_SUMMARY.md",
    ROOT / "FIXED_K32_METHOD_DETAILED_SUMMARY_CN.md",
]

CANONICAL_FIELDS = {
    "graph_id": ["graph_id", "graph", "network_id"],
    "step": ["step", "removed_edges_after_step"],
    "method": ["method", "attack_method"],
    "selected_edge": ["selected_edge"],
    "gcc_before": ["gcc_before", "gcc_size_before"],
    "gcc_after": ["gcc_after", "gcc_size_after"],
    "delta_gcc": ["delta_gcc"],
    "num_components_before": ["num_components_before", "components_before"],
    "num_components_after": ["num_components_after", "components_after"],
    "is_bridge_before_removal": ["is_bridge_before_removal", "is_bridge"],
    "is_inter_community_edge": ["is_inter_community_edge", "is_inter_community"],
    "degree_u": ["degree_u", "selected_edge_u_degree"],
    "degree_v": ["degree_v", "selected_edge_v_degree"],
    "degree_product": ["degree_product"],
    "common_neighbors": ["common_neighbors"],
    "edge_embeddedness": ["edge_embeddedness", "embeddedness"],
    "full_edge_betweenness_score": ["full_edge_betweenness_score", "full_edge_betweenness"],
    "sampled_betweenness_score": ["sampled_betweenness_score", "sampled_betweenness"],
    "attack_phase": ["attack_phase", "phase"],
}

INVENTORY_EXPECTED = {
    "edge_step_diagnostics.csv": list(CANONICAL_FIELDS),
    "graph_method_summary.csv": ["dataset", "graph_id", "method", "normalized_auc", "runtime_seconds"],
    "graph_structure_by_outcome.csv": [
        "dataset",
        "graph_id",
        "outcome_class",
        "sasb_minus_m5_normalized_auc",
        "bridge_ratio",
        "core2_size_ratio",
        "degree_cv",
    ],
    "selected_edge_summary_by_outcome_method.csv": ["outcome_class", "method", "selected_edges"],
    "phase_auc_summary_by_outcome_method.csv": ["outcome_class", "method", "attack_phase"],
    "baseline_synthetic45_summary.csv": ["dataset", "method", "mean_normalized_auc"],
    "baseline_realworld_m5_completed_per_graph.csv": ["dataset", "graph_id", "method", "normalized_auc"],
}

METHOD_ORDER = ["M5", "SASB"]
PHASE_ORDER = ["early", "middle", "late"]
PHASE_COLORS = {"early": "#4C78A8", "middle": "#F58518", "late": "#54A24B"}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def line_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return sum(1 for _ in handle)


def file_type_for(path: Path) -> str:
    text = rel(path)
    if "sasb_m5_edge_diagnostics" in text:
        if "why_sasb_wins_or_loses" in text:
            return "mechanism diagnostic outcome analysis"
        return "mechanism diagnostic result"
    if "paper_experiments/baselines" in text:
        return "baseline result"
    if path.suffix.lower() == ".md":
        return "documentation/report"
    return "other"


def find_col(df: pd.DataFrame, names: Iterable[str]) -> str | None:
    lowered = {c.lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def canonicalize_edge_df(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str | None]]:
    mapping: dict[str, str | None] = {}
    out = pd.DataFrame(index=df.index)
    for canonical, candidates in CANONICAL_FIELDS.items():
        col = find_col(df, candidates)
        mapping[canonical] = col
        out[canonical] = df[col] if col else np.nan
    if "dataset" in df.columns:
        out["dataset"] = df["dataset"]
    if "graph_name" in df.columns:
        out["graph_name"] = df["graph_name"]
    if "graph_type" in df.columns:
        out["graph_type"] = df["graph_type"]
    if "community_strength" in df.columns:
        out["community_strength"] = df["community_strength"]
    return out, mapping


def missing_canonical(df: pd.DataFrame, expected: Iterable[str]) -> list[str]:
    missing = []
    for field in expected:
        candidates = CANONICAL_FIELDS.get(field, [field])
        if find_col(df, candidates) is None:
            missing.append(field)
    return missing


def build_file_inventory() -> pd.DataFrame:
    rows = []
    for path in REQUIRED_INPUTS:
        exists = path.exists()
        columns: list[str] = []
        rows_count: int | float = np.nan
        graphs: int | float = np.nan
        methods: int | float = np.nan
        missing = []
        notes = []
        if exists and path.suffix.lower() == ".csv":
            df = read_csv(path)
            rows_count = len(df)
            columns = list(df.columns)
            graph_col = find_col(df, ["graph_id", "graph", "network_id"])
            method_col = find_col(df, ["method", "attack_method"])
            if graph_col:
                graphs = int(df[graph_col].nunique(dropna=True))
            if method_col:
                methods = int(df[method_col].nunique(dropna=True))
            expected = INVENTORY_EXPECTED.get(path.name, [])
            missing = missing_canonical(df, expected)
            missing_values = int(df.isna().sum().sum())
            notes.append(f"missing_values={missing_values}")
        elif exists and path.suffix.lower() == ".md":
            rows_count = line_count(path)
            notes.append("markdown file; columns/graphs/methods not applicable")
        elif not exists:
            missing = INVENTORY_EXPECTED.get(path.name, [])
        if exists:
            notes.append(f"last_write_time={pd.Timestamp(path.stat().st_mtime, unit='s').isoformat()}")
        rows.append(
            {
                "file_path": rel(path),
                "exists": bool(exists),
                "rows": rows_count,
                "columns": json.dumps(columns, ensure_ascii=False),
                "graphs": graphs,
                "methods": methods,
                "missing_columns": ";".join(missing),
                "file_type": file_type_for(path),
                "notes": "; ".join(notes),
            }
        )
    inv = pd.DataFrame(rows)
    inv.to_csv(OUT_DIR / "file_inventory.csv", index=False, encoding="utf-8-sig")
    return inv


def bool_mean(series: pd.Series) -> float:
    if series.notna().sum() == 0:
        return np.nan
    return pd.to_numeric(series, errors="coerce").mean()


def conditional_positive_mean(series: pd.Series) -> float:
    vals = pd.to_numeric(series, errors="coerce")
    pos = vals[vals > 0]
    if pos.empty:
        return np.nan
    return float(pos.mean())


def summarize_group(group: pd.DataFrame) -> pd.Series:
    degree_u = pd.to_numeric(group["degree_u"], errors="coerce")
    degree_v = pd.to_numeric(group["degree_v"], errors="coerce")
    min_degree = pd.concat([degree_u, degree_v], axis=1).min(axis=1)
    delta = pd.to_numeric(group["delta_gcc"], errors="coerce")
    comp_before = pd.to_numeric(group["num_components_before"], errors="coerce")
    comp_after = pd.to_numeric(group["num_components_after"], errors="coerce")
    component_increase = comp_after - comp_before
    return pd.Series(
        {
            "selected_edges": int(len(group)),
            "inter_community_ratio": bool_mean(group["is_inter_community_edge"]),
            "bridge_ratio": bool_mean(group["is_bridge_before_removal"]),
            "mean_common_neighbors": pd.to_numeric(group["common_neighbors"], errors="coerce").mean(),
            "median_common_neighbors": pd.to_numeric(group["common_neighbors"], errors="coerce").median(),
            "mean_edge_embeddedness": pd.to_numeric(group["edge_embeddedness"], errors="coerce").mean(),
            "median_edge_embeddedness": pd.to_numeric(group["edge_embeddedness"], errors="coerce").median(),
            "mean_degree_product": pd.to_numeric(group["degree_product"], errors="coerce").mean(),
            "mean_min_endpoint_degree": min_degree.mean(),
            "fraction_min_degree_1": (min_degree == 1).mean() if min_degree.notna().any() else np.nan,
            "fraction_min_degree_2": (min_degree == 2).mean() if min_degree.notna().any() else np.nan,
            "mean_delta_gcc": delta.mean(),
            "median_delta_gcc": delta.median(),
            "positive_delta_gcc_rate": (delta > 0).mean() if delta.notna().any() else np.nan,
            "conditional_mean_delta_gcc": conditional_positive_mean(delta),
            "mean_num_components_after": comp_after.mean(),
            "mean_component_increase": component_increase.mean(),
            "mean_full_edge_betweenness_score": pd.to_numeric(
                group["full_edge_betweenness_score"], errors="coerce"
            ).mean(),
            "mean_sampled_betweenness_score": pd.to_numeric(
                group["sampled_betweenness_score"], errors="coerce"
            ).mean(),
        }
    )


def load_edge_diagnostics() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    availability_rows = []
    for label, directory in DATASETS.items():
        path = directory / "edge_step_diagnostics.csv"
        raw = read_csv(path)
        canon, mapping = canonicalize_edge_df(raw)
        canon["dataset_scope"] = label
        frames.append(canon)
        for field, source in mapping.items():
            availability_rows.append(
                {
                    "dataset": label,
                    "canonical_field": field,
                    "source_column": source if source is not None else "missing",
                    "status": "present" if source is not None else "missing",
                }
            )
    availability = pd.DataFrame(availability_rows)
    availability.to_csv(OUT_DIR / "field_availability.csv", index=False, encoding="utf-8-sig")
    return pd.concat(frames, ignore_index=True), availability


def build_structure_bias_summary(edges: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        edges.groupby(["dataset_scope", "dataset", "graph_id", "method"], dropna=False)
        .apply(summarize_group, include_groups=False)
        .reset_index()
        .rename(columns={"dataset_scope": "dataset_label"})
    )
    grouped.to_csv(OUT_DIR / "structure_bias_summary.csv", index=False, encoding="utf-8-sig")
    return grouped


def build_phase_bias_summary(edges: pd.DataFrame) -> pd.DataFrame:
    graph_phase = (
        edges.groupby(["dataset_scope", "dataset", "graph_id", "method", "attack_phase"], dropna=False)
        .apply(summarize_group, include_groups=False)
        .reset_index()
    )
    aggregate = (
        graph_phase.groupby(["dataset_scope", "dataset", "method", "attack_phase"], dropna=False)
        .agg(
            graph_count=("graph_id", "nunique"),
            selected_edges=("selected_edges", "sum"),
            inter_community_ratio=("inter_community_ratio", "mean"),
            bridge_ratio=("bridge_ratio", "mean"),
            mean_common_neighbors=("mean_common_neighbors", "mean"),
            mean_edge_embeddedness=("mean_edge_embeddedness", "mean"),
            mean_min_endpoint_degree=("mean_min_endpoint_degree", "mean"),
            positive_delta_gcc_rate=("positive_delta_gcc_rate", "mean"),
            conditional_mean_delta_gcc=("conditional_mean_delta_gcc", "mean"),
            mean_num_components_after=("mean_num_components_after", "mean"),
        )
        .reset_index()
        .rename(columns={"dataset_scope": "dataset_label"})
    )
    graph_phase.rename(columns={"dataset_scope": "dataset_label"}).to_csv(
        OUT_DIR / "phase_bias_by_graph.csv", index=False, encoding="utf-8-sig"
    )
    aggregate.to_csv(OUT_DIR / "phase_bias_summary.csv", index=False, encoding="utf-8-sig")
    return aggregate


def load_graph_summaries() -> pd.DataFrame:
    frames = []
    for label, directory in DATASETS.items():
        df = read_csv(directory / "graph_method_summary.csv")
        df["dataset_label"] = label
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def build_curve_budget_summary() -> pd.DataFrame:
    rows = []
    budgets = [0.05, 0.10, 0.20, 0.40]
    for label, directory in DATASETS.items():
        curves = read_csv(directory / "attack_curves.csv")
        for (dataset, graph_id, method), group in curves.groupby(["dataset", "graph_id", "method"], dropna=False):
            group = group.sort_values("remove_ratio")
            row = {"dataset_label": label, "dataset": dataset, "graph_id": graph_id, "method": method}
            for budget in budgets:
                eligible = group[group["remove_ratio"] <= budget]
                if eligible.empty:
                    row[f"gcc_at_{int(budget * 100)}pct"] = np.nan
                else:
                    row[f"gcc_at_{int(budget * 100)}pct"] = float(eligible.iloc[-1]["gcc_ratio"])
            drops = group.sort_values("step")["gcc_ratio"].diff()
            positive_drop = group.loc[drops < 0]
            row["first_positive_drop_step"] = (
                int(positive_drop.iloc[0]["step"]) if not positive_drop.empty else np.nan
            )
            rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "budget_gcc_summary.csv", index=False, encoding="utf-8-sig")
    return summary


def build_outcome_structure_summary() -> pd.DataFrame:
    path = WHY_DIR / "graph_structure_by_outcome.csv"
    df = read_csv(path)
    rename = {"n": "num_nodes", "m": "num_edges"}
    df = df.rename(columns=rename)
    variables = [
        "bridge_ratio",
        "core2_size_ratio",
        "degree_cv",
        "modularity",
        "clustering_coefficient",
        "average_edge_embeddedness",
        "inter_community_edge_ratio",
        "average_degree",
        "num_nodes",
        "num_edges",
    ]
    delta_col = "sasb_minus_m5_normalized_auc"
    rows = []
    for outcome, group in df.groupby("outcome_class", dropna=False):
        row = {"row_type": "outcome_group", "outcome_class": outcome, "metric": "graph_count", "value": len(group)}
        rows.append(row)
        for var in variables:
            if var in group.columns:
                rows.append(
                    {
                        "row_type": "outcome_group",
                        "outcome_class": outcome,
                        "metric": var,
                        "value": pd.to_numeric(group[var], errors="coerce").mean(),
                    }
                )
    for var in variables:
        if var in df.columns and delta_col in df.columns:
            vals = df[[var, delta_col]].apply(pd.to_numeric, errors="coerce").dropna()
            corr = vals[var].rank().corr(vals[delta_col].rank()) if len(vals) >= 3 else np.nan
            rows.append(
                {
                    "row_type": "spearman_correlation",
                    "outcome_class": "all",
                    "metric": f"{var}_vs_sasb_minus_m5_normalized_auc",
                    "value": corr,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "outcome_structure_summary.csv", index=False, encoding="utf-8-sig")
    return out


def pivot_method_delta(df: pd.DataFrame, value: str, group_cols: list[str]) -> pd.DataFrame:
    pivot = df.pivot_table(index=group_cols, columns="method", values=value, aggfunc="mean").reset_index()
    if "SASB" in pivot.columns and "M5" in pivot.columns:
        pivot[f"sasb_minus_m5_{value}"] = pivot["SASB"] - pivot["M5"]
    return pivot


def plot_phase_metric(phase: pd.DataFrame, metric: str, filename: str, ylabel: str, higher_note: str) -> None:
    datasets = list(phase["dataset_label"].dropna().unique())
    fig, axes = plt.subplots(1, len(datasets), figsize=(7 * len(datasets), 4.8), sharey=True)
    if len(datasets) == 1:
        axes = [axes]
    for ax, dataset in zip(axes, datasets):
        sub = phase[phase["dataset_label"] == dataset].copy()
        x = np.arange(len(PHASE_ORDER))
        width = 0.34
        for offset, method, hatch in [(-width / 2, "M5", ""), (width / 2, "SASB", "//")]:
            vals = []
            colors = []
            for ph in PHASE_ORDER:
                match = sub[(sub["method"] == method) & (sub["attack_phase"] == ph)]
                vals.append(match[metric].mean() if not match.empty else np.nan)
                colors.append(PHASE_COLORS[ph])
            ax.bar(
                x + offset,
                vals,
                width=width,
                label=method,
                color=colors,
                edgecolor="black",
                linewidth=0.6,
                hatch=hatch,
            )
        n_graphs = sub["graph_count"].max()
        coverage = "24/28 completed subset" if "realworld" in dataset else "45/45 synthetic"
        ax.set_title(f"{dataset} ({coverage}, n={int(n_graphs) if pd.notna(n_graphs) else 'NA'})")
        ax.set_xticks(x)
        ax.set_xticklabels(PHASE_ORDER)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
    method_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="black", label="M5"),
        plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="black", hatch="//", label="SASB"),
    ]
    phase_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=PHASE_COLORS[p], edgecolor="black", label=p)
        for p in PHASE_ORDER
    ]
    axes[0].legend(handles=method_handles + phase_handles, ncol=2, fontsize=8)
    fig.suptitle(f"{ylabel} by method and phase ({higher_note})")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / filename, dpi=220)
    plt.close(fig)


def plot_auc_scatter(outcome_csv: Path, x_col: str, filename: str, xlabel: str) -> None:
    df = read_csv(outcome_csv).rename(columns={"n": "num_nodes", "m": "num_edges"})
    if x_col not in df.columns or "sasb_minus_m5_normalized_auc" not in df.columns:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, f"Missing column: {x_col}", ha="center", va="center")
        ax.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(6.5, 4.8))
        colors = {"SASB_better": "#4C78A8", "SASB_worse": "#E45756", "tie_close": "#72B7B2"}
        for outcome, group in df.groupby("outcome_class", dropna=False):
            ax.scatter(
                pd.to_numeric(group[x_col], errors="coerce"),
                pd.to_numeric(group["sasb_minus_m5_normalized_auc"], errors="coerce"),
                label=str(outcome),
                alpha=0.8,
                color=colors.get(str(outcome), None),
            )
        ax.axhline(0, color="black", linewidth=1, alpha=0.6)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("SASB normalized AUC - M5 normalized AUC (lower favors SASB)")
        ax.set_title(f"AUC difference vs {xlabel} (realworld 24/28, lower AUC is better)")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT_DIR / filename, dpi=220)
    plt.close(fig)


def plot_phase_auc() -> None:
    frames = []
    for label, directory in DATASETS.items():
        df = read_csv(directory / "phase_auc_by_graph.csv")
        df["dataset_label"] = label
        frames.append(df)
    data = pd.concat(frames, ignore_index=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, dataset in zip(axes, ["synthetic45", "realworld_completed_24of28"]):
        sub = data[data["dataset_label"] == dataset]
        x = np.arange(len(PHASE_ORDER))
        width = 0.34
        for offset, method, hatch in [(-width / 2, "M5", ""), (width / 2, "SASB", "//")]:
            vals = [
                sub[(sub["method"] == method) & (sub["attack_phase"] == ph)]["phase_normalized_auc"].mean()
                for ph in PHASE_ORDER
            ]
            ax.bar(
                x + offset,
                vals,
                width=width,
                label=method,
                color=[PHASE_COLORS[p] for p in PHASE_ORDER],
                edgecolor="black",
                linewidth=0.6,
                hatch=hatch,
            )
        n = sub["graph_id"].nunique()
        coverage = "24/28 completed subset" if "realworld" in dataset else "45/45 synthetic"
        ax.set_title(f"{dataset} ({coverage}, n={n})")
        ax.set_xticks(x)
        ax.set_xticklabels(PHASE_ORDER)
        ax.set_ylabel("Mean phase normalized GCC-AUC")
        ax.grid(axis="y", alpha=0.25)
    method_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="black", label="M5"),
        plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="black", hatch="//", label="SASB"),
    ]
    phase_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=PHASE_COLORS[p], edgecolor="black", label=p)
        for p in PHASE_ORDER
    ]
    axes[0].legend(handles=method_handles + phase_handles, ncol=2, fontsize=8)
    fig.suptitle("Phase AUC comparison (lower is better)")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "phase_auc_comparison.png", dpi=220)
    plt.close(fig)


def build_plots(phase: pd.DataFrame) -> None:
    plot_phase_metric(
        phase,
        "inter_community_ratio",
        "inter_community_ratio_by_method_phase.png",
        "Inter-community selection ratio",
        "higher means stronger boundary-edge bias",
    )
    plot_phase_metric(
        phase,
        "mean_edge_embeddedness",
        "embeddedness_by_method_phase.png",
        "Mean selected-edge embeddedness",
        "lower means less locally embedded",
    )
    plot_phase_metric(
        phase,
        "mean_common_neighbors",
        "common_neighbors_by_method_phase.png",
        "Mean common neighbors",
        "lower means less locally embedded",
    )
    plot_phase_metric(
        phase,
        "mean_min_endpoint_degree",
        "min_endpoint_degree_by_method_phase.png",
        "Mean min endpoint degree",
        "lower means more peripheral endpoint bias",
    )
    plot_phase_metric(
        phase,
        "positive_delta_gcc_rate",
        "positive_gcc_drop_probability.png",
        "P(delta_gcc > 0)",
        "higher means selected edge more often reduces GCC immediately",
    )
    plot_auc_scatter(
        WHY_DIR / "graph_structure_by_outcome.csv",
        "bridge_ratio",
        "sasb_m5_auc_difference_vs_bridge_ratio.png",
        "Graph bridge ratio",
    )
    plot_auc_scatter(
        WHY_DIR / "graph_structure_by_outcome.csv",
        "core2_size_ratio",
        "sasb_m5_auc_difference_vs_core2_ratio.png",
        "2-core size ratio",
    )
    plot_auc_scatter(
        WHY_DIR / "graph_structure_by_outcome.csv",
        "degree_cv",
        "sasb_m5_auc_difference_vs_degree_cv.png",
        "Degree coefficient of variation",
    )
    plot_phase_auc()


def fmt(x: float | int | str, digits: int = 4) -> str:
    if isinstance(x, str):
        return x
    if pd.isna(x):
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{float(x):.{digits}f}"


def compare_methods(df: pd.DataFrame, metric: str, dataset_label: str, phase: str | None = None) -> dict[str, float]:
    sub = df[df["dataset_label"] == dataset_label]
    if phase is not None:
        sub = sub[sub["attack_phase"] == phase]
    means = sub.groupby("method")[metric].mean()
    return {
        "m5": float(means.get("M5", np.nan)),
        "sasb": float(means.get("SASB", np.nan)),
        "sasb_minus_m5": float(means.get("SASB", np.nan) - means.get("M5", np.nan)),
    }


def build_report(
    inventory: pd.DataFrame,
    availability: pd.DataFrame,
    structure: pd.DataFrame,
    phase: pd.DataFrame,
    graph_summary: pd.DataFrame,
    outcome: pd.DataFrame,
    budget: pd.DataFrame,
) -> None:
    missing_files = inventory[~inventory["exists"]]
    missing_fields = availability[availability["status"] == "missing"]
    auc_pivot = pivot_method_delta(
        graph_summary, "normalized_auc", ["dataset_label", "dataset", "graph_id"]
    )
    auc_by_dataset = auc_pivot.groupby("dataset_label")["sasb_minus_m5_normalized_auc"].agg(
        ["count", "mean", lambda s: (s < 0).sum(), lambda s: (s > 0).sum()]
    )
    auc_by_dataset.columns = ["graphs", "mean_sasb_minus_m5_auc", "sasb_better_graphs", "sasb_worse_graphs"]

    lines: list[str] = []
    lines.append("# 结构化少源点采样偏差审计报告")
    lines.append("")
    lines.append("## 1. 研究问题")
    lines.append(
        "本审计只分析已有结果，检验 SASB / M19-sampled-BE-fast 是否相对 M5 产生系统性结构选边偏差，"
        "以及这种偏差是否在部分网络结构和攻击阶段与更快 GCC 瓦解相对应。"
    )
    lines.append("")
    lines.append("## 2. 方法定义")
    lines.append("- SASB / M19-sampled-BE-fast: 结构候选边集合 + k=32 结构化源点采样 + sampled dependency 排序。")
    lines.append("- fixed_k32: 每一步固定 32 个源点的少源点动态基线；本报告只引用已有 baseline，不新增实验。")
    lines.append("- M5: 完整动态 edge betweenness，是强效果和高成本参考基线。")
    lines.append("- ACES: 仅作为静态排序相似度参考，不作为本次动态瓦解主方法。")
    lines.append("")
    lines.append("## 3. 数据和文件范围")
    lines.append("- synthetic45: full diagnostic 覆盖 45/45 张图，M5 与 SASB 均完成。")
    lines.append("- realworld_completed: 当前 full diagnostic 覆盖 24/28 张真实图，M5 与 SASB 均完成。")
    lines.append("- 剩余未进入当前 full diagnostic 的真实网络: ia_fb_messages, bio_grid_worm, econ_mahindas, ca_grqc。")
    lines.append("- 本次未运行任何大规模新实验；所有统计来自现有 CSV 和曲线文件。")
    if missing_files.empty:
        lines.append("- 任务指定输入文件均存在。")
    else:
        lines.append("- 缺失输入文件: " + ", ".join(missing_files["file_path"].tolist()))
    lines.append("")
    lines.append("## 4. synthetic45 结果")
    syn_auc = auc_by_dataset.loc["synthetic45"]
    syn_inter = compare_methods(structure, "inter_community_ratio", "synthetic45")
    syn_embed = compare_methods(structure, "mean_edge_embeddedness", "synthetic45")
    syn_pos = compare_methods(structure, "positive_delta_gcc_rate", "synthetic45")
    lines.append(
        f"- normalized GCC-AUC: SASB-M5 均值差 {fmt(syn_auc['mean_sasb_minus_m5_auc'])}; "
        f"SASB better {int(syn_auc['sasb_better_graphs'])}/{int(syn_auc['graphs'])}, "
        f"worse {int(syn_auc['sasb_worse_graphs'])}/{int(syn_auc['graphs'])}。"
    )
    lines.append(
        f"- inter-community ratio: M5 {fmt(syn_inter['m5'])}, SASB {fmt(syn_inter['sasb'])}, "
        f"差值 {fmt(syn_inter['sasb_minus_m5'])}。"
    )
    lines.append(
        f"- mean embeddedness: M5 {fmt(syn_embed['m5'])}, SASB {fmt(syn_embed['sasb'])}, "
        f"差值 {fmt(syn_embed['sasb_minus_m5'])}。"
    )
    lines.append(
        f"- P(delta_gcc > 0): M5 {fmt(syn_pos['m5'])}, SASB {fmt(syn_pos['sasb'])}, "
        f"差值 {fmt(syn_pos['sasb_minus_m5'])}。"
    )
    lines.append("")
    lines.append("## 5. realworld 24 图结果")
    real_auc = auc_by_dataset.loc["realworld_completed_24of28"]
    real_inter = compare_methods(structure, "inter_community_ratio", "realworld_completed_24of28")
    real_embed = compare_methods(structure, "mean_edge_embeddedness", "realworld_completed_24of28")
    real_pos = compare_methods(structure, "positive_delta_gcc_rate", "realworld_completed_24of28")
    lines.append(
        f"- normalized GCC-AUC: SASB-M5 均值差 {fmt(real_auc['mean_sasb_minus_m5_auc'])}; "
        f"SASB better {int(real_auc['sasb_better_graphs'])}/{int(real_auc['graphs'])}, "
        f"worse {int(real_auc['sasb_worse_graphs'])}/{int(real_auc['graphs'])}。"
    )
    lines.append(
        f"- inter-community ratio: M5 {fmt(real_inter['m5'])}, SASB {fmt(real_inter['sasb'])}, "
        f"差值 {fmt(real_inter['sasb_minus_m5'])}。"
    )
    lines.append(
        f"- mean embeddedness: M5 {fmt(real_embed['m5'])}, SASB {fmt(real_embed['sasb'])}, "
        f"差值 {fmt(real_embed['sasb_minus_m5'])}。"
    )
    lines.append(
        f"- P(delta_gcc > 0): M5 {fmt(real_pos['m5'])}, SASB {fmt(real_pos['sasb'])}, "
        f"差值 {fmt(real_pos['sasb_minus_m5'])}。"
    )
    lines.append("")
    lines.append("## 6. SASB 与 M5 的结构选边差异")
    lines.append(
        "全程 bridge ratio 只作为一致性检查，因为完整删边过程中 bridge 选择总量可能受边集合和删除顺序的共同约束，"
        "不能单独证明 M5 与 SASB 的机制差异；正式比较应看 early/middle/late 分阶段指标。"
    )
    for dataset in ["synthetic45", "realworld_completed_24of28"]:
        bridge = compare_methods(structure, "bridge_ratio", dataset)
        cn = compare_methods(structure, "mean_common_neighbors", dataset)
        mind = compare_methods(structure, "mean_min_endpoint_degree", dataset)
        lines.append(
            f"- {dataset}: bridge ratio 差值 {fmt(bridge['sasb_minus_m5'])}; "
            f"common neighbors 差值 {fmt(cn['sasb_minus_m5'])}; "
            f"min endpoint degree 差值 {fmt(mind['sasb_minus_m5'])}。"
        )
    lines.append("")
    lines.append("## 7. early/middle/late 阶段差异")
    for dataset in ["synthetic45", "realworld_completed_24of28"]:
        lines.append(f"- {dataset}:")
        for ph in PHASE_ORDER:
            auc_phase = compare_methods(
                pd.concat(
                    [
                        read_csv(SYN_DIR / "phase_auc_by_graph.csv").assign(dataset_label="synthetic45"),
                        read_csv(REAL_DIR / "phase_auc_by_graph.csv").assign(
                            dataset_label="realworld_completed_24of28"
                        ),
                    ],
                    ignore_index=True,
                ).rename(columns={"phase_normalized_auc": "metric"}),
                "metric",
                dataset,
                ph,
            )
            inter = compare_methods(phase, "inter_community_ratio", dataset, ph)
            pos = compare_methods(phase, "positive_delta_gcc_rate", dataset, ph)
            lines.append(
                f"  - {ph}: phase AUC SASB-M5 {fmt(auc_phase['sasb_minus_m5'])}; "
                f"inter-community 差值 {fmt(inter['sasb_minus_m5'])}; "
                f"P(delta_gcc>0) 差值 {fmt(pos['sasb_minus_m5'])}。"
            )
    lines.append("")
    lines.append("## 8. SASB better/worse 网络结构差异")
    corr_rows = outcome[outcome["row_type"] == "spearman_correlation"].copy()
    if not corr_rows.empty:
        top = corr_rows.assign(abs_value=lambda d: d["value"].abs()).sort_values("abs_value", ascending=False).head(5)
        for _, row in top.iterrows():
            lines.append(f"- Spearman {row['metric']}: {fmt(row['value'])}")
    lines.append(
        "这些相关性是探索性分析，不是因果证明；真实网络样本量只有 24 张，不能外推为完整 realworld 结论。"
    )
    lines.append("")
    lines.append("## 9. source bias 与 candidate bias 的可识别性")
    lines.append(
        "当前 SASB 同时包含结构化候选边集合和结构化源点采样。已有机制日志不能单独固定 candidate set 后只替换 source policy，"
        "因此不能证明全部收益主要来自源点选择，也不能把 SASB 整体效果完全归因于 source bias。"
    )
    lines.append("")
    lines.append("## 10. 关键数据缺失")
    if missing_fields.empty:
        lines.append("- edge-level 规范字段均能在当前 M5/SASB 机制诊断 CSV 中映射。")
    else:
        for dataset, group in missing_fields.groupby("dataset"):
            lines.append(f"- {dataset}: missing " + ", ".join(group["canonical_field"].tolist()))
    lines.append("- 当前没有完整候选边排序，因此不计算 top-1 recall、NDCG、Spearman 或完整 candidate rank。")
    lines.append("- selected edge 分数仅代表被选边的记录，不能当作完整候选边排序。")
    lines.append("- mechanism diagnostic runtime 含诊断记录开销，不能与普通 baseline runtime 直接混用。")
    lines.append("")
    lines.append("## 11. 当前证据边界")
    lines.append(
        "已有证据可以支持 SASB 存在结构偏差，并且这种偏差在部分网络和阶段与 GCC-AUC 或 immediate GCC drop 改善相伴。"
        "但真实网络只覆盖 24/28，且 candidate/source bias 尚未解耦，所以不能写成 SASB 在所有真实网络上优于 M5。"
    )
    lines.append("")
    lines.append("## 12. 下一阶段 P1 实验设计")
    lines.append("- 比较方法: M5, fixed_k32, SASB structured-source, SASB uniform-random-source, SASB degree-community-matched-source。")
    lines.append("- 固定 candidate set 相同、source budget=32、random seeds 相同、动态更新 GCC。")
    lines.append("- synthetic45 使用 remove_ratio=1.0；realworld 使用当前 24/28 completed subset。")
    lines.append(
        "- 只有 structured-source 同时优于 uniform-random-source 和 degree-community-matched-source，"
        "并改善 GCC-AUC、保持结构偏差方向稳定且 runtime 可接受，才支持核心源点采样假设。"
    )
    lines.append("- 如果只提高 top1 agreement、NDCG 或 Spearman 而不改善 GCC-AUC，只能说明更像 M5，不能说明更适合网络瓦解。")
    lines.append("")
    lines.append("## 明确结论")
    lines.append("结论 B：已有证据支持存在结构偏差，但目前不能证明收益主要来自源点选择。")
    lines.append("")
    lines.append("## 生成文件")
    for path in [
        OUT_DIR / "file_inventory.csv",
        OUT_DIR / "field_availability.csv",
        OUT_DIR / "structure_bias_summary.csv",
        OUT_DIR / "phase_bias_summary.csv",
        OUT_DIR / "phase_bias_by_graph.csv",
        OUT_DIR / "outcome_structure_summary.csv",
        OUT_DIR / "budget_gcc_summary.csv",
    ]:
        lines.append(f"- {rel(path)}")
    for plot in sorted(PLOT_DIR.glob("*.png")):
        lines.append(f"- {rel(plot)}")

    (OUT_DIR / "structure_bias_audit_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    ensure_dirs()
    inventory = build_file_inventory()
    edges, availability = load_edge_diagnostics()
    structure = build_structure_bias_summary(edges)
    phase = build_phase_bias_summary(edges)
    graph_summary = load_graph_summaries()
    budget = build_curve_budget_summary()
    outcome = build_outcome_structure_summary()
    build_plots(phase)
    build_report(inventory, availability, structure, phase, graph_summary, outcome, budget)
    print(f"Wrote audit outputs to {rel(OUT_DIR)}")


if __name__ == "__main__":
    main()
