from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "result" / "source_policy_ablation_p1"
FORMAL_RUNS = OUT_DIR / "formal_runs"
PLOTS_DIR = OUT_DIR / "plots"

METHOD_ORDER = ["SASB-structured", "SASB-matched", "SASB-random"]
COMPARISONS = [
    ("SASB-structured", "SASB-matched"),
    ("SASB-structured", "SASB-random"),
    ("SASB-matched", "SASB-random"),
]
PRIMARY = "normalized_auc"
MECHANISM_METRICS = [
    "first_positive_drop_step",
    "positive_delta_gcc_rate",
    "conditional_mean_delta_gcc",
    "inter_community_ratio",
    "mean_edge_embeddedness",
    "mean_common_neighbors",
]
SECONDARY_METRICS = ["gcc_at_5pct", "gcc_at_10pct", "gcc_at_20pct", "gcc_at_40pct"]
COST_METRICS = [
    "runtime_seconds",
    "true_source_traversal_count",
    "candidate_generation_seconds",
    "sampled_path_scoring_seconds",
    "model_scoring_seconds",
    "louvain_recomputes",
]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_formal_results() -> pd.DataFrame:
    path = FORMAL_RUNS / "p1_source_policy_ablation_summary.csv"
    df = pd.read_csv(path)
    for col in [PRIMARY, *SECONDARY_METRICS, *MECHANISM_METRICS, *COST_METRICS, "removed_edges", "observed_remove_ratio"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["dataset_label"] = df["dataset"].replace({"realworld_completed": "realworld24"})
    df["is_finished"] = df["status"].eq("finished")
    return df


def mean_ci(values: pd.Series) -> dict[str, float]:
    values = pd.to_numeric(values, errors="coerce").dropna()
    n = int(len(values))
    mean = float(values.mean()) if n else np.nan
    sd = float(values.std(ddof=1)) if n > 1 else 0.0 if n == 1 else np.nan
    se = sd / math.sqrt(n) if n > 1 else 0.0 if n == 1 else np.nan
    margin = 1.96 * se if n > 1 else 0.0 if n == 1 else np.nan
    return {"n": n, "mean": mean, "std": sd, "ci95_low": mean - margin, "ci95_high": mean + margin}


def build_paired_comparisons(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metrics = [PRIMARY, *SECONDARY_METRICS, *MECHANISM_METRICS, *COST_METRICS]
    for (dataset, graph_id, seed), group in df.groupby(["dataset", "graph_id", "seed"], sort=True):
        by_method = group.set_index("method")
        for left, right in COMPARISONS:
            if left not in by_method.index or right not in by_method.index:
                continue
            row = {
                "dataset": dataset,
                "dataset_label": group["dataset_label"].iloc[0],
                "graph_id": graph_id,
                "seed": seed,
                "comparison": f"{left} minus {right}",
                "left_method": left,
                "right_method": right,
            }
            for metric in metrics:
                if metric in by_method.columns:
                    left_value = by_method.loc[left, metric]
                    right_value = by_method.loc[right, metric]
                    row[f"{metric}_left"] = left_value
                    row[f"{metric}_right"] = right_value
                    row[f"{metric}_diff"] = left_value - right_value
            diff = row.get(f"{PRIMARY}_diff", np.nan)
            eps = 1e-9
            row["left_better"] = int(diff < -eps) if pd.notna(diff) else 0
            row["right_better"] = int(diff > eps) if pd.notna(diff) else 0
            row["tie"] = int(abs(diff) <= eps) if pd.notna(diff) else 0
            rows.append(row)
    return pd.DataFrame(rows)


def build_effect_sizes(paired: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (dataset, comparison), group in paired.groupby(["dataset", "comparison"], sort=True):
        diffs = pd.to_numeric(group[f"{PRIMARY}_diff"], errors="coerce").dropna()
        stats = mean_ci(diffs)
        sd = stats["std"]
        rows.append(
            {
                "dataset": dataset,
                "dataset_label": group["dataset_label"].iloc[0],
                "comparison": comparison,
                "metric": PRIMARY,
                **stats,
                "cohen_dz": stats["mean"] / sd if sd and not np.isnan(sd) else np.nan,
                "left_wins": int((diffs < -1e-9).sum()),
                "right_wins": int((diffs > 1e-9).sum()),
                "ties": int((diffs.abs() <= 1e-9).sum()),
                "direction_note": "negative mean means left method has lower AUC and stronger dismantling",
            }
        )
    return pd.DataFrame(rows)


def build_metric_summary(df: pd.DataFrame, metrics: list[str], summary_kind: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (dataset, method), group in df.groupby(["dataset", "method"], sort=True):
        for metric in metrics:
            if metric not in group.columns:
                continue
            stats = mean_ci(group[metric])
            rows.append(
                {
                    "summary_kind": summary_kind,
                    "dataset": dataset,
                    "dataset_label": group["dataset_label"].iloc[0],
                    "method": method,
                    "metric": metric,
                    **stats,
                }
            )
    return pd.DataFrame(rows)


def add_mechanism_relation_rows(summary: pd.DataFrame, paired: pd.DataFrame) -> pd.DataFrame:
    rows = [summary]
    relation_rows: list[dict[str, Any]] = []
    target = paired[paired["comparison"].eq("SASB-structured minus SASB-matched")].copy()
    for dataset, group in target.groupby("dataset", sort=True):
        auc_diff = pd.to_numeric(group[f"{PRIMARY}_diff"], errors="coerce")
        for metric in MECHANISM_METRICS:
            col = f"{metric}_diff"
            if col not in group.columns:
                continue
            values = pd.to_numeric(group[col], errors="coerce")
            valid = pd.DataFrame({"auc_diff": auc_diff, "metric_diff": values}).dropna()
            corr = float(valid["auc_diff"].corr(valid["metric_diff"], method="spearman")) if len(valid) >= 3 else np.nan
            relation_rows.append(
                {
                    "summary_kind": "structured_minus_matched_relation",
                    "dataset": dataset,
                    "dataset_label": group["dataset_label"].iloc[0],
                    "method": "SASB-structured minus SASB-matched",
                    "metric": f"{metric}_diff_spearman_with_auc_diff",
                    "n": int(len(valid)),
                    "mean": corr,
                    "std": np.nan,
                    "ci95_low": np.nan,
                    "ci95_high": np.nan,
                }
            )
    if relation_rows:
        rows.append(pd.DataFrame(relation_rows))
    return pd.concat(rows, ignore_index=True, sort=False)


def build_report(df: pd.DataFrame, paired: pd.DataFrame, effects: pd.DataFrame, mechanism: pd.DataFrame, cost: pd.DataFrame) -> str:
    target = effects[effects["comparison"].eq("SASB-structured minus SASB-matched")].copy()
    lines = [
        "# P1 Source-Policy Ablation Formal Experiment Report",
        "",
        "## 1. 主要结果",
        "",
    ]
    for _, row in target.sort_values("dataset").iterrows():
        lines.append(
            "- `{}`: structured - matched normalized GCC-AUC mean = `{:.6f}`; 95% CI = `[{:.6f}, {:.6f}]`; wins/losses/ties = `{}/{}/{}`.".format(
                row["dataset"],
                row["mean"],
                row["ci95_low"],
                row["ci95_high"],
                int(row["left_wins"]),
                int(row["right_wins"]),
                int(row["ties"]),
            )
        )
    lines.extend(
        [
            "",
            "A negative paired difference means `SASB-structured` has lower normalized GCC-AUC and therefore stronger dismantling than `SASB-matched` on that network.",
            "",
            "## 2. 是否支持 H1",
            "",
        ]
    )
    for _, row in target.sort_values("dataset").iterrows():
        supports = row["mean"] < 0 and row["ci95_high"] < 0 and row["left_wins"] > row["right_wins"]
        partial = row["mean"] < 0 and row["left_wins"] >= row["right_wins"]
        if supports:
            judgment = "supports H1 under the preregistered paired criterion"
        elif partial:
            judgment = "directionally weak but inconclusive; it is not sufficient support for H1"
        else:
            judgment = "does not support H1"
        lines.append(f"- `{row['dataset']}`: `{judgment}`.")
    lines.extend(["", "## 3. 是否只能支持 candidate bias", ""])
    for dataset in sorted(df["dataset"].unique()):
        sub = effects[(effects["dataset"].eq(dataset)) & (effects["comparison"].isin([
            "SASB-structured minus SASB-matched",
            "SASB-structured minus SASB-random",
        ]))]
        sm = sub[sub["comparison"].eq("SASB-structured minus SASB-matched")]
        sr = sub[sub["comparison"].eq("SASB-structured minus SASB-random")]
        if sm.empty or sr.empty:
            continue
        sm_mean = float(sm["mean"].iloc[0])
        sr_mean = float(sr["mean"].iloc[0])
        sm_ci_low = float(sm["ci95_low"].iloc[0])
        sm_ci_high = float(sm["ci95_high"].iloc[0])
        if sm_mean >= 0:
            note = "candidate-bias-only interpretation is more consistent than source-policy bias"
        elif sm_ci_low <= 0 <= sm_ci_high:
            note = "candidate-bias-only interpretation remains plausible because structured-matched is statistically inconclusive"
        elif abs(sm_mean) < abs(sr_mean) * 0.25:
            note = "candidate-bias-only interpretation remains plausible because structured-matched is much smaller than structured-random"
        else:
            note = "source-policy contribution would need additional robustness checks before being claimed"
        lines.append(f"- `{dataset}`: structured-random mean diff `{sr_mean:.6f}`, structured-matched mean diff `{sm_mean:.6f}`; `{note}`.")
    lines.extend(["", "## 4. SASB 在哪些网络上有效", ""])
    sm_pair = paired[paired["comparison"].eq("SASB-structured minus SASB-matched")].copy()
    wins = sm_pair[sm_pair[f"{PRIMARY}_diff"] < -1e-9]
    for dataset, group in wins.groupby("dataset", sort=True):
        best = group.sort_values(f"{PRIMARY}_diff").head(10)
        lines.append(f"- `{dataset}` structured beats matched on `{len(group)}` networks. Strongest examples: " + ", ".join(best["graph_id"].astype(str).tolist()) + ".")
    lines.extend(["", "## 5. SASB 在哪些网络上失效", ""])
    losses = sm_pair[sm_pair[f"{PRIMARY}_diff"] > 1e-9]
    for dataset, group in losses.groupby("dataset", sort=True):
        worst = group.sort_values(f"{PRIMARY}_diff", ascending=False).head(10)
        lines.append(f"- `{dataset}` structured loses to matched on `{len(group)}` networks. Strongest failures: " + ", ".join(worst["graph_id"].astype(str).tolist()) + ".")
    if losses.empty:
        lines.append("- No network has structured worse than matched under the exact AUC tie threshold.")
    lines.extend(["", "## 5b. 失败网络和异常网络分析", ""])
    status_counts = df.groupby(["dataset", "status"]).size().reset_index(name="count")
    for _, row in status_counts.iterrows():
        lines.append(f"- `{row['dataset']}` status `{row['status']}`: `{int(row['count'])}` method-network runs.")
    for dataset, group in df.groupby("dataset", sort=True):
        long_runtime = group.sort_values("runtime_seconds", ascending=False).head(5)
        examples = [
            "{}:{}:{:.1f}s".format(r.graph_id, r.method.replace("SASB-", ""), float(r.runtime_seconds))
            for _, r in long_runtime.iterrows()
        ]
        lines.append(f"- `{dataset}` longest runtime examples: " + ", ".join(examples) + ".")
    lines.extend(["", "## 6. 可能机制", ""])
    relation = mechanism[mechanism["summary_kind"].eq("structured_minus_matched_relation")]
    if relation.empty:
        lines.append("- Mechanism relation rows were not available.")
    else:
        for dataset, group in relation.groupby("dataset", sort=True):
            selected = group.sort_values("metric").head(8)
            vals = [f"{r.metric}={r['mean']:.3f}" for _, r in selected.iterrows() if pd.notna(r["mean"])]
            lines.append(f"- `{dataset}` Spearman relation between mechanism differences and AUC differences: " + "; ".join(vals) + ".")
    lines.extend(["", "## 7. 论文中可以写的结论", ""])
    lines.append(
        "P1 can be written as a controlled ablation that separates source-policy bias from candidate-set bias by holding the candidate builder, source budget, seed schedule, and dynamic GCC evaluation fixed."
    )
    lines.append(
        "Any claim about source-policy bias should be tied specifically to the structured-vs-matched paired AUC result, not to smoke validation or structured-vs-random alone."
    )
    lines.extend(["", "## 8. 仍然不能声称的内容", ""])
    lines.append("- Do not claim that code execution proves method effectiveness.")
    lines.append("- Do not claim universal superiority if realworld and synthetic results diverge or if wins are concentrated in a small subset.")
    lines.append("- Do not claim source-policy bias from structured-vs-random unless structured also beats matched.")
    lines.extend(["", "## 9. 是否需要下一轮实验", ""])
    lines.append(
        "A next experiment is needed if the structured-vs-matched effect is small, dataset-dependent, or contradicted by mechanism/cost indicators. Candidate-set ablations or repeated-seed robustness should then be prioritized."
    )
    lines.extend(["", "## Output Files", ""])
    for name in [
        "formal_results.csv",
        "paired_comparisons.csv",
        "effect_sizes.csv",
        "mechanism_summary.csv",
        "cost_summary.csv",
    ]:
        lines.append(f"- `{OUT_DIR / name}`")
    lines.append(f"- `{PLOTS_DIR}`")
    return "\n".join(lines) + "\n"


def plot_results(df: pd.DataFrame, paired: pd.DataFrame) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    for dataset, group in df.groupby("dataset", sort=True):
        data = [group[group["method"].eq(method)][PRIMARY].dropna().to_numpy() for method in METHOD_ORDER]
        plt.figure(figsize=(8, 4.5))
        plt.boxplot(data, tick_labels=[m.replace("SASB-", "") for m in METHOD_ORDER], showmeans=True)
        plt.ylabel("normalized GCC-AUC (lower is better)")
        plt.title(f"{dataset}: normalized GCC-AUC by source policy")
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / f"{dataset}_auc_boxplot.png", dpi=200)
        plt.close()

    sm = paired[paired["comparison"].eq("SASB-structured minus SASB-matched")].copy()
    for dataset, group in sm.groupby("dataset", sort=True):
        plot_df = group.sort_values(f"{PRIMARY}_diff")
        plt.figure(figsize=(10, max(4, 0.18 * len(plot_df))))
        colors = ["#2f6f4e" if value < 0 else "#a64242" if value > 0 else "#777777" for value in plot_df[f"{PRIMARY}_diff"]]
        plt.barh(plot_df["graph_id"], plot_df[f"{PRIMARY}_diff"], color=colors)
        plt.axvline(0, color="black", linewidth=0.8)
        plt.xlabel("structured - matched normalized GCC-AUC")
        plt.title(f"{dataset}: paired source-policy effect")
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / f"{dataset}_structured_minus_matched_auc_diff.png", dpi=200)
        plt.close()

    plt.figure(figsize=(8, 4.5))
    for method in METHOD_ORDER:
        vals = df[df["method"].eq(method)]["runtime_seconds"].dropna()
        plt.scatter([method.replace("SASB-", "")] * len(vals), vals, alpha=0.6)
    plt.yscale("log")
    plt.ylabel("runtime_seconds (log scale)")
    plt.title("Runtime by source policy")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "runtime_by_source_policy.png", dpi=200)
    plt.close()

    if "positive_delta_gcc_rate_diff" in sm.columns:
        plt.figure(figsize=(6, 5))
        for dataset, group in sm.groupby("dataset", sort=True):
            plt.scatter(group["positive_delta_gcc_rate_diff"], group[f"{PRIMARY}_diff"], label=dataset, alpha=0.75)
        plt.axhline(0, color="black", linewidth=0.8)
        plt.axvline(0, color="black", linewidth=0.8)
        plt.xlabel("structured - matched positive delta-GCC rate")
        plt.ylabel("structured - matched normalized GCC-AUC")
        plt.title("Mechanism difference vs AUC difference")
        plt.legend()
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "mechanism_vs_auc_diff.png", dpi=200)
        plt.close()


def main() -> None:
    df = read_formal_results()
    paired = build_paired_comparisons(df)
    effects = build_effect_sizes(paired)
    mechanism = add_mechanism_relation_rows(build_metric_summary(df, MECHANISM_METRICS + SECONDARY_METRICS, "method_metric_summary"), paired)
    cost = build_metric_summary(df, COST_METRICS, "cost_summary")

    write_csv(df, OUT_DIR / "formal_results.csv")
    write_csv(paired, OUT_DIR / "paired_comparisons.csv")
    write_csv(effects, OUT_DIR / "effect_sizes.csv")
    write_csv(mechanism, OUT_DIR / "mechanism_summary.csv")
    write_csv(cost, OUT_DIR / "cost_summary.csv")
    plot_results(df, paired)
    report = build_report(df, paired, effects, mechanism, cost)
    (OUT_DIR / "formal_experiment_report.md").write_text(report, encoding="utf-8")

    manifest = {
        "formal_results_rows": int(len(df)),
        "paired_comparisons_rows": int(len(paired)),
        "effect_sizes_rows": int(len(effects)),
        "mechanism_summary_rows": int(len(mechanism)),
        "cost_summary_rows": int(len(cost)),
        "plots": sorted(path.name for path in PLOTS_DIR.glob("*.png")),
    }
    (OUT_DIR / "formal_analysis_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
