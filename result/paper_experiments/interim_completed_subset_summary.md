# M5 真实网络实验阶段性总结：completed subset（非最终）

生成时间：2026-07-06 17:41 后

本报告只使用当前已经落盘的 CSV、markdown report 和图表；正在运行的 `bio_grid_worm` 相关结果没有计入 completed subset，也不作为最终结论。AUC 均为 normalized GCC AUC，数值越低表示 GCC 瓦解越快。

## 1. 当前 completed subset 覆盖情况

- 当前机制诊断 completed subset：**24 / 28** 张真实网络。
- 权威覆盖文件：`result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/graph_method_summary.csv` 与 `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/COVERAGE_NOTE.md`。
- 当前目录中的 completed 判定：同一图同时存在 M5 与 SASB 的完整诊断汇总。

已完成真实网络：

- `bio_celegans`
- `bio_celegans_dir`
- `bio_celegansneural`
- `bio_diseasome`
- `bio_grid_mouse`
- `bio_grid_plant`
- `bio_sc_ts`
- `ca_csphd`
- `ca_netscience`
- `football`
- `ia_email_univ`
- `ia_enron_only`
- `ia_infect_dublin`
- `ia_infect_hyper`
- `ia_radoslaw_email`
- `inf_euroroad`
- `inf_power`
- `inf_usair97`
- `rt_retweet`
- `rt_twitter_copen`
- `soc_dolphins`
- `soc_wiki_vote`
- `web_edu`
- `web_polblogs`

未完成真实网络：

- `ia_fb_messages`
- `bio_grid_worm`
- `econ_mahindas`
- `ca_grqc`

## 2. synthetic45：SASB 与 M5/M7/M12 的 AUC 和 runtime

数据源：`result/paper_experiments/baselines/baseline_synthetic45_summary.csv`。该表是正式 baseline 汇总，包含 M5、M7、M12 与 `M19-sampled-BE-fast`。

| 方法 | 图数 | mean normalized AUC | mean runtime | 相对 M5 speedup | 结论 |
|---|---:|---:|---:|---:|---|
| M19-sampled-BE-fast / SASB | 45 | 0.342167 | 11.49s | 1.94x | AUC 低于 M5/M7/M12，runtime 比 M5 更低 |
| M5 | 45 | 0.355794 | 22.30s | 1.00x | 完整动态 edge betweenness 对照 |
| M7 | 45 | 0.367549 | 6.45s | 3.45x | runtime 快于 SASB，但 AUC 较差 |
| M12 | 45 | 0.386083 | 2.40s | 9.28x | runtime 最快，但 AUC 较差 |

synthetic45 上，`M19-sampled-BE-fast / SASB` 的 mean normalized AUC 为 0.342167，低于 M5 的 0.355794、M7 的 0.367549 和 M12 的 0.386083；按 baseline runtime 计算，SASB 相比 M5 约 **1.94x** 加速。

补充机制诊断源：`result/sasb_m5_edge_diagnostics/full_synthetic45/graph_method_summary.csv` 中 M5/SASB 的 AUC 与 baseline 基本一致，但 runtime 受诊断记录开销影响，不能直接与 M7/M12 混为同一 runtime 表。

## 3. realworld completed subset（当前 24 图）：SASB 与 M5/M7/M12 的 AUC 和 runtime

全方法比较数据源：`result/paper_experiments/baselines/baseline_realworld_m5_completed_per_graph.csv`，并按当前 24 个 completed graph 过滤。

| 方法 | 图数 | mean normalized AUC | mean runtime | 相对 M5 speedup | 结论 |
|---|---:|---:|---:|---:|---|
| M19-sampled-BE-fast / SASB | 24 | 0.219339 | 100.80s | 5.26x | 平均 AUC 未超过 M5，但优于 M7/M12，runtime 明显低于 M5 |
| M5 | 24 | 0.204369 | 530.05s | 1.00x | 当前 24 图中平均 AUC 最低，但成本最高 |
| M7 | 24 | 0.225788 | 46.56s | 11.38x | runtime 快于 SASB，AUC 略差于 SASB |
| M12 | 24 | 0.356317 | 37.35s | 14.19x | runtime 快，但 AUC 明显较差 |

按这 24 个 completed graph 的 baseline per-graph 过滤结果，SASB 的 mean normalized AUC 为 0.219339，高于 M5 的 0.204369，因此 **SASB 没有超过 M5**；但 SASB 低于 M7 的 0.225788 和 M12 的 0.356317。按 baseline runtime 计算，SASB 相比 M5 约 **5.26x** 加速。

## 4. 当前机制诊断目录中的 M5/SASB 结果

数据源：`result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/graph_method_summary.csv` 与 `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/mechanism_diagnostic_report.md`。

| 方法 | 图数 | mean normalized AUC | mean runtime | 相对 M5 speedup |
|---|---:|---:|---:|---:|
| M5 | 24 | 0.204375 | 612.52s | 1.00x |
| SASB | 24 | 0.219158 | 148.17s | 4.13x |

当前机制诊断目录中，SASB better / worse / tie = **7 / 16 / 1**。这里的 M5/SASB 结果同样显示：SASB 在当前真实网络 completed subset 上没有超过 M5，SASB 平均 AUC 更高，但平均 runtime 约为 M5 的 1/4.13。

## 5. 关键 CSV、报告与图表路径

正式 baseline / 全方法比较：

- `result/paper_experiments/baselines/baseline_synthetic45_summary.csv`
- `result/paper_experiments/baselines/baseline_synthetic45_per_graph.csv`
- `result/paper_experiments/baselines/baseline_realworld_m5_completed_per_graph.csv`
- `result/paper_experiments/baselines/baseline_auc_runtime.png`
- `result/paper_experiments/baselines/baseline_average_gcc_curve.png`

当前机制诊断 completed subset：

- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/graph_method_summary.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/network_diagnosis.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/phase_auc_by_graph.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/edge_step_diagnostics.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/mechanism_diagnostic_report.md`
- `result/sasb_m5_edge_diagnostics/combined_mechanism_report.md`

当前机制诊断图表：

- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/selected_edge_delta_gcc_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/bridge_selection_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/inter_community_edge_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/selected_edge_common_neighbors_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/selected_edge_embeddedness_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/phase_auc_comparison.png`

## 6. 仍不完整、不能作为最终结论的部分

- 当前真实网络机制诊断只完成 24/28；`ia_fb_messages`、`bio_grid_worm`、`econ_mahindas`、`ca_grqc` 尚未全部进入 completed subset。
- 当前正在运行的 remaining4 队列仍在 `bio_grid_worm` 的 M5 阶段；本报告没有等待它完成，也没有把其中间状态计入最终统计。
- M7/M12 的真实网络比较来自 baseline per-graph CSV，并按当前 24 图过滤；当前机制诊断目录本身只包含 M5 与 SASB，不包含 M7/M12 的逐边机制诊断。
- synthetic45 的 all-method runtime 来自 baseline summary；机制诊断目录中的 runtime 含逐边诊断记录开销，适合解释机制，不适合直接与 baseline 的 M7/M12 runtime 混合比较。
- 因此，当前结论只能称为 completed subset 阶段性结论，不能写成 full realworld completed subset 的最终结论。

## 7. 五条最重要结论

1. 当前 M5/SASB 机制诊断 completed subset 为 **24/28** 张真实网络；未完成图为 `ia_fb_messages`、`bio_grid_worm`、`econ_mahindas`、`ca_grqc`。
2. synthetic45 上，`M19-sampled-BE-fast / SASB` 的平均 AUC 最低：0.342167，优于 M5 的 0.355794、M7 的 0.367549 和 M12 的 0.386083；同时相对 M5 约 1.94x 加速。
3. 当前 24 图 realworld completed subset 上，SASB 的平均 AUC 为 0.219339，未超过 M5 的 0.204369；因此真实网络阶段性结果不能声称 SASB 优于 M5。
4. 当前 24 图 realworld subset 上，SASB 的平均 AUC 优于 M7 和 M12，并且相对 M5 有明显速度优势：baseline 过滤表约 5.26x，当前机制诊断表约 4.13x。
5. 现有证据更适合表述为：SASB 在 synthetic45 上表现出比完整 M5 更低 AUC 与更快 runtime；在真实网络 completed subset 上，它主要体现为显著加速与接近但未超过 M5 的瓦解效果，最终结论必须等待剩余 4 图完成后再更新。
