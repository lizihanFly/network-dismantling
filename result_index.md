# Curated Research Results Index

更新时间：2026-07-13

本索引只保留当前复杂网络边瓦解研究中仍有论文或阶段汇报价值的结果。大量逐步曲线、逐边日志、临时 smoke/probe/oracle 结果和原始真实网络数据不作为 GitHub curated update 的重点内容。

## 1. 当前主线

- 项目阶段性总览：`RESEARCH_PROGRESS_ALGORITHM_SUMMARY.md`
- 最新计划与研究进展：`PROJECT_LATEST_PROGRESS_AND_NEXT_PLAN.md`
- M19 / SASB 方法说明与对比：`M19_sampled_BE_fast_method_and_comparison.md`
- fixed-k32 方法总结：`FIXED_K32_METHOD_DETAILED_SUMMARY_CN.md`

## 2. M5 与 SASB 真实网络机制诊断

- 24/28 completed subset 阶段性总结：`result/paper_experiments/interim_completed_subset_summary.md`
- SASB 为什么赢/输 M5 的机制报告：`result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses.md`
- M5/SASB 综合机制报告：`result/sasb_m5_edge_diagnostics/combined_mechanism_report.md`

关键小型汇总和图表：

- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/structure_summary_by_outcome.csv`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/selected_edge_summary_by_outcome_method.csv`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/phase_auc_summary_by_outcome_method.csv`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_vs_modularity.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_vs_bridge_ratio.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_vs_2core_ratio.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/phase_auc_comparison_by_outcome.png`

## 3. Adaptive-SASB smoke 结果

- 中文报告：`result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_report.md`
- 运行脚本：`scripts/run_adaptive_sasb_smoke.py`
- 机制分析脚本：`scripts/analyze_why_sasb_wins_or_loses.py`

本次 Adaptive-SASB 结果是 8 图、120-step prefix smoke，用于判断方向是否值得扩展，不等同于完整 100% edge removal 结论。

关键小型汇总：

- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/per_graph_method_summary.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/method_average_summary.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/adaptive_vs_fixed_auc_delta.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/source_composition_summary.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/bridge_selection_corrected_by_phase.csv`

## 4. 不纳入本次 curated update 的内容

- `edge_steps.csv`、`curves.csv`、运行日志、queue note 等过程文件。
- 原始真实网络数据目录 `data/realnetworks_40plus/`。
- 大体量历史实验目录，例如早期 candidate-damage、oracle、quick/probe/smoke 结果。
- 已经被新结论覆盖的早期七方法对比图、旧 SBM/real-network 临时结果。
