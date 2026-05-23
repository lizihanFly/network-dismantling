from pathlib import Path
import argparse

import pandas as pd


DEFAULT_CANDIDATE_METHOD = "Candidate damage predictor"
DEFAULT_REFERENCE_METHOD = "M5 dynamic edge betweenness"
DEFAULT_METADATA_PATH = Path("data") / "ml_attack_dataset" / "graph_metadata.csv"


def read_summary(result_dir):
    path = result_dir / "attack_summary_by_graph.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing attack summary file: {path}")
    return pd.read_csv(path)


def read_metadata(path):
    if not path.exists():
        return None
    metadata = pd.read_csv(path)
    keep_cols = [
        "split",
        "graph_id",
        "community_strength",
        "modularity",
        "n",
        "m",
        "density",
        "avg_degree",
    ]
    keep_cols = [column for column in keep_cols if column in metadata.columns]
    return metadata[keep_cols].drop_duplicates(["split", "graph_id"])


def compare_methods(summary_df, candidate_method, reference_method, metadata_df=None):
    candidate = summary_df[summary_df["method"] == candidate_method].copy()
    reference = summary_df[summary_df["method"] == reference_method].copy()
    key_cols = ["split", "graph_id", "graph_type"]
    merged = candidate.merge(
        reference,
        on=key_cols,
        suffixes=("_candidate", "_reference"),
    )
    if merged.empty:
        raise RuntimeError("No matched graph rows found for candidate and reference methods.")
    merged["auc_delta_vs_reference"] = merged["auc_candidate"] - merged["auc_reference"]
    merged["candidate_wins_auc"] = merged["auc_delta_vs_reference"] < 0
    if "elapsed_seconds_candidate" in merged and "elapsed_seconds_reference" in merged:
        merged["elapsed_delta_vs_reference"] = (
            merged["elapsed_seconds_candidate"] - merged["elapsed_seconds_reference"]
        )
    if "robustness_index_candidate" in merged and "robustness_index_reference" in merged:
        merged["robustness_delta_vs_reference"] = (
            merged["robustness_index_candidate"] - merged["robustness_index_reference"]
        )
    if metadata_df is not None:
        merged = merged.merge(metadata_df, on=["split", "graph_id"], how="left")
    return merged


def aggregate_comparison(comparison_df, candidate_method, reference_method, group_cols=None):
    if group_cols is None:
        group_cols = ["split", "graph_type"]
    rows = []
    for group_key, group in comparison_df.groupby(group_cols):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        row = {
            "candidate_method": candidate_method,
            "reference_method": reference_method,
            "num_graphs": len(group),
            "candidate_auc_wins": int(group["candidate_wins_auc"].sum()),
            "mean_auc_candidate": group["auc_candidate"].mean(),
            "mean_auc_reference": group["auc_reference"].mean(),
            "mean_auc_delta_vs_reference": group["auc_delta_vs_reference"].mean(),
            "median_auc_delta_vs_reference": group["auc_delta_vs_reference"].median(),
        }
        if "elapsed_delta_vs_reference" in group:
            row["mean_elapsed_candidate"] = group["elapsed_seconds_candidate"].mean()
            row["mean_elapsed_reference"] = group["elapsed_seconds_reference"].mean()
            row["mean_elapsed_delta_vs_reference"] = group["elapsed_delta_vs_reference"].mean()
        if "robustness_delta_vs_reference" in group:
            row["mean_robustness_candidate"] = group["robustness_index_candidate"].mean()
            row["mean_robustness_reference"] = group["robustness_index_reference"].mean()
            row["mean_robustness_delta_vs_reference"] = group[
                "robustness_delta_vs_reference"
            ].mean()
        for column, value in zip(group_cols, group_key):
            row[column] = value
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols)


def write_notes(path, aggregate_df, group_cols):
    lines = [
        "# Candidate Attack Comparison",
        "",
        "Lower AUC and lower robustness index mean faster network collapse.",
        "",
        "## Aggregate",
        "",
    ]
    for row in aggregate_df.itertuples(index=False):
        group_label = "/".join(str(getattr(row, column)) for column in group_cols)
        lines.append(
            f"- {group_label}: wins={row.candidate_auc_wins}/{row.num_graphs}, "
            f"mean AUC delta={row.mean_auc_delta_vs_reference:.6f} "
            f"({row.candidate_method} minus {row.reference_method})."
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser(description="Compare candidate attack results against a reference method.")
    parser.add_argument("--result-dir", required=True)
    parser.add_argument("--candidate-method", default=DEFAULT_CANDIDATE_METHOD)
    parser.add_argument("--reference-method", default=DEFAULT_REFERENCE_METHOD)
    parser.add_argument("--metadata-path", default=str(DEFAULT_METADATA_PATH))
    parser.add_argument(
        "--group-cols",
        default="split,graph_type,community_strength",
        help="Comma-separated columns used for aggregate comparison.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    result_dir = Path(args.result_dir)
    summary_df = read_summary(result_dir)
    metadata_df = read_metadata(Path(args.metadata_path))
    comparison_df = compare_methods(
        summary_df,
        args.candidate_method,
        args.reference_method,
        metadata_df=metadata_df,
    )
    group_cols = [part.strip() for part in args.group_cols.split(",") if part.strip()]
    group_cols = [column for column in group_cols if column in comparison_df.columns]
    aggregate_df = aggregate_comparison(
        comparison_df,
        args.candidate_method,
        args.reference_method,
        group_cols=group_cols,
    )
    comparison_path = result_dir / "candidate_vs_reference_by_graph.csv"
    aggregate_path = result_dir / "candidate_vs_reference_aggregate.csv"
    notes_path = result_dir / "candidate_vs_reference_notes.md"
    comparison_df.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    aggregate_df.to_csv(aggregate_path, index=False, encoding="utf-8-sig")
    write_notes(notes_path, aggregate_df, group_cols)
    print(f"Wrote {comparison_path}")
    print(f"Wrote {aggregate_path}")
    print(f"Wrote {notes_path}")
    print(aggregate_df.to_string(index=False))


if __name__ == "__main__":
    main()
