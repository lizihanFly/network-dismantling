# SASB-N Mechanism Diagnostics

本目录保存 SASB-N 节点版本的两个正式机制实验，基于 24 个 pilot 网络、4 种 source policy、5 个固定 seed 和 `source_budget=64`。

## 实验一：source diversity

实验一逐步记录每种 source policy 在自身动态瓦解轨迹中的源点结构，包括 active source count、当前 GCC 大小、source fraction、社区覆盖率、社区熵、源点距离、边界源点比例、跨社区 source pair 比例、正依赖节点比例、source-set hash 和相邻步骤 Jaccard。

不同 source policy 的逐步轨迹不同，因此不把不同策略的逐步 Jaccard 当作横向配对证据；跨策略 source overlap 只在初始图状态计算。

## 实验二：sampled dependency 与 M5 排序

在每种策略自己的当前 GCC 上，于移除比例最接近 `0, 0.1, 0.2, 0.3, 0.5` 的 checkpoint，比较 sampled dependency 与同一图状态下 exact M5 node betweenness 的 Spearman、Kendall、Pearson、Top-1%/5%/10% overlap、precision/recall，以及被删除节点的 M5 rank。

## 核心结果

- 480 条运行全部完成，source-step 记录 246,700 行，ranking checkpoint 记录 2,400 行。
- Spearman 总体均值为 `0.7634`，Kendall 总体均值为 `0.7067`。
- synthetic45 中 structured 相对 random-source 的平均 AUC 差值为 `+0.0039`，胜平负为 `4/0/8`。
- realworld_completed 中 structured 相对 random-source 的平均 AUC 差值为 `+0.0025`，胜平负为 `3/1/8`。
- structured 的边界源点比例高于 random-source，但没有稳定转化为更低 AUC；因此当前证据不能支持“结构化源点偏差普遍有益”或“SASB-N 普遍优于 random-source”。

这些结论只适用于当前 24 个 pilot 网络和 `B=64`，不替代 73 网络正式实验，也不证明原始 edge SASB 已被完整验证。

## 文件说明

- `../../../scripts/run_node_mechanism_diagnostics.py`：可复现实验与聚合源码。
- `mechanism_config.json`：实验配置。
- `source_diversity_step_metrics.csv.gz`：实验一逐步结果；因未压缩文件超过 GitHub 100 MB 限制，按 gzip 保存。
- `source_diversity_summary.csv`：实验一汇总。
- `source_policy_initial_overlap.csv`：初始 source-set overlap。
- `ranking_correlation_step_metrics.csv`：实验二逐 checkpoint 结果。
- `ranking_correlation_summary.csv`：实验二汇总。
- `mechanism_statistical_tests.csv`：配对检验、bootstrap CI 和结构关联分析。
- `pilot_b64_auc_reference.csv`：用于 `delta_policy` 的 B=64 pilot 参考结果。
- `plots/`：source diversity、排序相关性和案例图。
- `mechanism_report.md`：正式机制诊断报告。
