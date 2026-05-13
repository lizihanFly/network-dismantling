from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_CSV = ROOT / "result" / "attack_summary" / "all_networks_attack_summary.csv"
OUT_DIR = ROOT / "result" / "attack_summary" / "analysis"

NETWORK_ORDER = [
    "sbm_strong",
    "sbm_medium",
    "sbm_weak",
    "karate",
    "football",
    "ca_netscience",
    "bio_diseasome",
    "inf_USAir97",
]
SBM_ORDER = ["sbm_strong", "sbm_medium", "sbm_weak"]
COMMUNITY_METHODS = [
    "M3 max C_i*C_j with Louvain",
    "M4 max E_i*E_j/E_ij with Louvain",
    "M6 max E_i*E_j with Louvain",
    "M7 max C_i*C_j/E_ij with Louvain",
    "M8 max (C_i*C_j/E_ij)*(k_i*k_j) with Louvain",
]
CORE_METHODS = [
    "M2 max k_i*k_j",
    "M4 max E_i*E_j/E_ij with Louvain",
    "M7 max C_i*C_j/E_ij with Louvain",
    "M8 max (C_i*C_j/E_ij)*(k_i*k_j) with Louvain",
]
METRICS = [
    "auc",
    "remove_ratio_gcc_le_0_5",
    "remove_ratio_gcc_le_0_2",
    "remove_ratio_gcc_le_0_1",
]


def method_short_name(method):
    return method.split(" ", 1)[0]


def lower_is_better_rank(series):
    return series.rank(method="min", ascending=True).astype(int)


def save_table(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def save_figure(path, tight=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    if tight:
        plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def add_rank_columns(df):
    ranked = df.copy()
    for metric in METRICS:
        ranked[f"{metric}_rank"] = (
            ranked.groupby("network")[metric].transform(lower_is_better_rank).astype(int)
        )
    return ranked


def build_tables(df):
    ranked = add_rank_columns(df)

    sbm_community = ranked[
        ranked["network"].isin(SBM_ORDER) & ranked["method"].isin(COMMUNITY_METHODS)
    ].copy()
    sbm_community["network"] = pd.Categorical(sbm_community["network"], SBM_ORDER, ordered=True)
    sbm_community["method_id"] = sbm_community["method"].map(method_short_name)
    sbm_community = sbm_community.sort_values(["network", "method_id"])
    save_table(sbm_community, OUT_DIR / "sbm_community_methods_summary.csv")

    all_ranks = ranked.copy()
    all_ranks["method_id"] = all_ranks["method"].map(method_short_name)
    all_ranks["network"] = pd.Categorical(all_ranks["network"], NETWORK_ORDER, ordered=True)
    all_ranks = all_ranks.sort_values(["network", "auc_rank", "method_id"])
    save_table(all_ranks, OUT_DIR / "all_networks_method_ranks.csv")

    grouped = all_ranks.groupby("method")
    rank_summary = pd.DataFrame(
        {
            "mean_auc": grouped["auc"].mean(),
            "median_auc_rank": grouped["auc_rank"].median(),
            "mean_auc_rank": grouped["auc_rank"].mean(),
            "best_auc_count": grouped["auc_rank"].apply(lambda s: int((s == 1).sum())),
            "mean_gcc_0_5_rank": grouped["remove_ratio_gcc_le_0_5_rank"].mean(),
            "mean_elapsed_seconds": grouped["elapsed_seconds"].mean(),
        }
    ).reset_index()
    rank_summary["method_id"] = rank_summary["method"].map(method_short_name)
    rank_summary = rank_summary.sort_values(["mean_auc_rank", "mean_auc", "method_id"])
    save_table(rank_summary, OUT_DIR / "method_rank_summary.csv")

    m8 = df[df["method"].str.startswith("M8")][["network"] + METRICS].set_index("network")
    rows = []
    for network, group in df.groupby("network"):
        best = group.loc[group["auc"].idxmin()]
        m8_row = m8.loc[network]
        rows.append(
            {
                "network": network,
                "best_method_by_auc": best["method"],
                "best_auc": best["auc"],
                "m8_auc": m8_row["auc"],
                "m8_auc_minus_best": m8_row["auc"] - best["auc"],
                "m8_remove_ratio_gcc_le_0_5": m8_row["remove_ratio_gcc_le_0_5"],
                "m8_remove_ratio_gcc_le_0_2": m8_row["remove_ratio_gcc_le_0_2"],
                "m8_remove_ratio_gcc_le_0_1": m8_row["remove_ratio_gcc_le_0_1"],
            }
        )
    m8_delta = pd.DataFrame(rows)
    m8_delta["network"] = pd.Categorical(m8_delta["network"], NETWORK_ORDER, ordered=True)
    m8_delta = m8_delta.sort_values("network")
    m8_delta = m8_delta[
        [
            "network",
            "best_method_by_auc",
            "best_auc",
            "m8_auc",
            "m8_auc_minus_best",
            "m8_remove_ratio_gcc_le_0_5",
            "m8_remove_ratio_gcc_le_0_2",
            "m8_remove_ratio_gcc_le_0_1",
        ]
    ]
    save_table(m8_delta, OUT_DIR / "m8_vs_best_auc.csv")

    return ranked, sbm_community, rank_summary, m8_delta


def plot_sbm_community_auc(sbm_community):
    sns.set(style="whitegrid", font_scale=1.05)
    plot_df = sbm_community.copy()
    plot_df["method_id"] = plot_df["method"].map(method_short_name)
    x_pos = {network: i for i, network in enumerate(SBM_ORDER)}
    plot_df["x_pos"] = plot_df["network"].astype(str).map(x_pos)

    plt.figure(figsize=(8.8, 5.2))
    ax = plt.gca()
    for method_id, group in plot_df.groupby("method_id"):
        group = group.sort_values("x_pos")
        ax.plot(group["x_pos"], group["auc"], marker="o", linewidth=2.2, label=method_id)
    ax.set_title("SBM community-method AUC across community strength")
    ax.set_xlabel("")
    ax.set_ylabel("AUC (lower is better)")
    ax.set_xticks(range(len(SBM_ORDER)))
    ax.set_xticklabels(SBM_ORDER)
    ax.legend(title="Method", ncol=3, frameon=True)
    save_figure(OUT_DIR / "sbm_community_methods_auc_trend.png")


def plot_sbm_thresholds(sbm_community):
    plot_df = sbm_community.copy()
    plot_df["method_id"] = plot_df["method"].map(method_short_name)
    threshold_labels = {
        "remove_ratio_gcc_le_0_5": "GCC <= 0.5",
        "remove_ratio_gcc_le_0_2": "GCC <= 0.2",
        "remove_ratio_gcc_le_0_1": "GCC <= 0.1",
    }
    method_ids = [method_short_name(method) for method in COMMUNITY_METHODS]
    colors = sns.color_palette(n_colors=len(method_ids))
    x = np.arange(len(SBM_ORDER))
    width = 0.14

    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.6), sharey=True)
    for ax, metric in zip(axes, threshold_labels):
        for i, method_id in enumerate(method_ids):
            values = []
            for network in SBM_ORDER:
                match = plot_df[
                    (plot_df["network"].astype(str) == network)
                    & (plot_df["method_id"] == method_id)
                ]
                values.append(float(match.iloc[0][metric]))
            offset = (i - (len(method_ids) - 1) / 2.0) * width
            ax.bar(x + offset, values, width=width, color=colors[i], label=method_id)
        ax.set_title(threshold_labels[metric])
        ax.set_xticks(x)
        ax.set_xticklabels(SBM_ORDER, rotation=0)
        ax.set_xlabel("")
        ax.grid(axis="y", alpha=0.5)
    axes[0].set_ylabel("Removed edge ratio (lower is better)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, title="Method", loc="lower center", ncol=len(method_ids))
    fig.subplots_adjust(bottom=0.22, wspace=0.08)
    save_figure(OUT_DIR / "sbm_community_methods_thresholds.png", tight=False)


def plot_all_network_auc_heatmap(ranked):
    plot_df = ranked.copy()
    plot_df["network"] = pd.Categorical(plot_df["network"], NETWORK_ORDER, ordered=True)
    plot_df["method_id"] = plot_df["method"].map(method_short_name)
    matrix = plot_df.pivot(index="network", columns="method_id", values="auc")

    plt.figure(figsize=(9.8, 5.4))
    ax = sns.heatmap(
        matrix,
        annot=True,
        fmt=".3f",
        cmap="viridis_r",
        linewidths=0.5,
        cbar_kws={"label": "AUC (lower is better)"},
    )
    ax.set_title("AUC by network and attack method")
    ax.set_xlabel("Method")
    ax.set_ylabel("")
    save_figure(OUT_DIR / "all_networks_auc_heatmap.png")


def plot_core_method_auc(ranked):
    plot_df = ranked[ranked["method"].isin(CORE_METHODS)].copy()
    plot_df["network"] = pd.Categorical(plot_df["network"], NETWORK_ORDER, ordered=True)
    plot_df["method_id"] = plot_df["method"].map(method_short_name)
    x_pos = {network: i for i, network in enumerate(NETWORK_ORDER)}
    plot_df["x_pos"] = plot_df["network"].astype(str).map(x_pos)

    plt.figure(figsize=(10.4, 5.2))
    ax = plt.gca()
    for method_id, group in plot_df.groupby("method_id"):
        group = group.sort_values("x_pos")
        ax.plot(group["x_pos"], group["auc"], marker="o", linewidth=2.0, label=method_id)
    ax.set_title("Core baseline AUC comparison")
    ax.set_xlabel("")
    ax.set_ylabel("AUC (lower is better)")
    ax.set_xticks(range(len(NETWORK_ORDER)))
    ax.set_xticklabels(NETWORK_ORDER, rotation=25, ha="right")
    ax.legend(title="Method", ncol=4, frameon=True)
    save_figure(OUT_DIR / "core_methods_auc_by_network.png")


def write_notes(rank_summary, m8_delta, sbm_community):
    best_by_mean_rank = rank_summary.iloc[0]
    m8_wins = int((m8_delta["m8_auc_minus_best"].abs() < 1e-12).sum())
    sbm_best = (
        sbm_community.loc[sbm_community.groupby("network")["auc"].idxmin()][
            ["network", "method", "auc"]
        ]
        .sort_values("network")
        .copy()
    )

    lines = [
        "# 攻击结果汇总分析",
        "",
        "所有核心指标都是越低越好：AUC 越小，或者达到指定 GCC 阈值所需删除边比例越小，说明网络碎裂越快。",
        "",
        "## 主要结论",
        "",
        f"- 全部网络上平均 AUC 排名最好的是：{best_by_mean_rank['method']}，平均排名 {best_by_mean_rank['mean_auc_rank']:.2f}。",
        f"- M8 在 {len(m8_delta)} 个网络中有 {m8_wins} 个网络取得 AUC 第一；`m8_auc_minus_best` 为正的网络表示乘上度积后仍弱于当前最佳基线。",
        "- SBM 结果显示：社区结构从 strong 到 weak 变弱时，社区感知方法整体 AUC 上升，且不同社区打分之间的相对优势会发生变化。",
        "",
        "## SBM 上 AUC 最优的社区方法",
        "",
    ]
    for row in sbm_best.itertuples(index=False):
        lines.append(f"- {row.network}: {row.method}, AUC={row.auc:.4f}")
    lines.extend(
        [
            "",
            "## 生成文件",
            "",
            "- `sbm_community_methods_summary.csv`",
            "- `all_networks_method_ranks.csv`",
            "- `method_rank_summary.csv`",
            "- `m8_vs_best_auc.csv`",
            "- `sbm_community_methods_auc_trend.png`",
            "- `sbm_community_methods_thresholds.png`",
            "- `all_networks_auc_heatmap.png`",
            "- `core_methods_auc_by_network.png`",
        ]
    )
    (OUT_DIR / "attack_summary_notes.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8-sig"
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SUMMARY_CSV)
    for metric in METRICS + ["elapsed_seconds"]:
        df[metric] = pd.to_numeric(df[metric], errors="raise")

    ranked, sbm_community, rank_summary, m8_delta = build_tables(df)
    plot_sbm_community_auc(sbm_community)
    plot_sbm_thresholds(sbm_community)
    plot_all_network_auc_heatmap(ranked)
    plot_core_method_auc(ranked)
    write_notes(rank_summary, m8_delta, sbm_community)

    print(f"Wrote analysis files to {OUT_DIR}")


if __name__ == "__main__":
    main()
