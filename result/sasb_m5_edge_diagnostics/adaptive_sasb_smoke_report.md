# Adaptive-SASB smoke test 报告

输出目录：`result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049`

本实验只在当前 24/28 completed subset 中选出的 8 个真实网络上做 smoke test；不修改当前 running queue，不覆盖既有结果。三种方法均沿用 sampled-BE ranking，区别在于候选/源点预算和源点组成。

评价口径：本次运行为 prefix smoke，`max_steps=120`，`max_remove_ratio=1.0`。因此下文 AUC 是 observed prefix 上的 normalized AUC，不能与 100% edge-removal full AUC 直接混用。

## 1. bridge_selection_ratio 字段核验与统计修复

`edge_step_diagnostics.csv` 中 `is_bridge` / `is_bridge_before_removal` 的语义是：被选中的边在删除前是否为当前 GCC 中的 bridge。字段本身是有效的。

但当前诊断是 100% edge removal。对任意从连通图删到无边图的完整删除序列，bridge 删除次数等于最终连通分量增加量，即约为 `n-1`，因此全程平均 bridge selection ratio 是 order-invariant 的，M5 与 SASB 会完全一样。这不是选边行为相同，而是全程统计口径失去区分度。

修复后的统计口径：保留全程 bridge ratio 作为一致性检查，但主要使用 early/middle/late phase bridge ratio 观察选边偏差。

全程 bridge ratio 差异检查：

| graph_id | m5_full_bridge_ratio | sasb_full_bridge_ratio | full_ratio_diff |
|---|---|---|---|
| bio_celegans | 0.223210 | 0.223210 | 0.000000 |
| bio_celegans_dir | 0.223210 | 0.223210 | 0.000000 |
| bio_celegansneural | 0.137803 | 0.137803 | 0.000000 |
| bio_diseasome | 0.433502 | 0.433502 | 0.000000 |
| bio_grid_mouse | 0.719490 | 0.719490 | 0.000000 |
| bio_grid_plant | 0.466251 | 0.466251 | 0.000000 |
| bio_sc_ts | 0.029851 | 0.029851 | 0.000000 |
| ca_csphd | 0.981783 | 0.981783 | 0.000000 |

分阶段 bridge ratio 文件：`result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/bridge_selection_corrected_by_phase.csv`。

## 2. smoke-test 网络选择

| graph_id | outcome_class | bridge_ratio | core2_size_ratio | m | selection_reason |
|---|---|---|---|---|---|
| bio_celegansneural | SASB better than M5 | 0.0070 | 0.9495 | 2148 | SASB better; very low bridge, high 2-core |
| bio_diseasome | SASB better than M5 | 0.0934 | 0.8140 | 1188 | SASB better; moderate bridge, modular biological graph |
| football | SASB better than M5 | 0.0000 | 1.0000 | 613 | SASB better; low bridge, core2=1, small social graph |
| soc_wiki_vote | SASB better than M5 | 0.0710 | 0.7672 | 2914 | SASB better; medium scale, moderate core2 |
| bio_grid_mouse | SASB worse than M5 | 0.4772 | 0.3477 | 1098 | SASB worse; high bridge, low 2-core |
| ca_csphd | SASB worse than M5 | 0.8984 | 0.0898 | 1043 | SASB worse; extremely high bridge, very low 2-core |
| inf_power | SASB worse than M5 | 0.2443 | 0.6786 | 6594 | SASB worse; large infrastructure graph, high bridge pressure |
| rt_twitter_copen | SASB worse than M5 | 0.4879 | 0.3509 | 1029 | SASB worse; high bridge, low 2-core, medium scale |

## 3. 每个网络的 AUC、runtime、speedup

| graph_id | outcome | method | normalized_auc | runtime_seconds | speedup_vs_m5 | mean_k | mean_sample_sources | bridge_core_adaptive_step_ratio |
|---|---|---|---|---|---|---|---|---|
| football | SASB_better | SASB-k32 | 0.9039 | 4.5759 | 1.5996 | 32.0000 | 32.0000 | 0.0000 |
| football | SASB_better | SASB-k64 | 0.7725 | 4.8930 | 1.4960 | 64.0000 | 59.7250 | 0.0000 |
| football | SASB_better | Adaptive-SASB | 0.9039 | 4.5757 | 1.5997 | 32.0000 | 32.0000 | 0.0000 |
| bio_diseasome | SASB_better | SASB-k32 | 0.3079 | 5.3917 | 3.9365 | 32.0000 | 32.0000 | 0.0000 |
| bio_diseasome | SASB_better | SASB-k64 | 0.2655 | 6.0543 | 3.5056 | 64.0000 | 64.0000 | 0.0000 |
| bio_diseasome | SASB_better | Adaptive-SASB | 0.3079 | 5.4374 | 3.9034 | 32.0000 | 32.0000 | 0.0000 |
| bio_celegansneural | SASB_better | SASB-k32 | 1.0000 | 22.1271 | 13.0018 | 32.0000 | 32.0000 | 0.0000 |
| bio_celegansneural | SASB_better | SASB-k64 | 1.0000 | 25.6536 | 11.2145 | 64.0000 | 64.0000 | 0.0000 |
| bio_celegansneural | SASB_better | Adaptive-SASB | 1.0000 | 22.5554 | 12.7549 | 32.0000 | 32.0000 | 0.0000 |
| soc_wiki_vote | SASB_better | SASB-k32 | 1.0000 | 37.7149 | 33.3936 | 32.0000 | 32.0000 | 0.0000 |
| soc_wiki_vote | SASB_better | SASB-k64 | 0.9983 | 47.6984 | 26.4042 | 64.0000 | 64.0000 | 0.0000 |
| soc_wiki_vote | SASB_better | Adaptive-SASB | 1.0000 | 37.9473 | 33.1891 | 32.0000 | 32.0000 | 0.0000 |
| ca_csphd | SASB_worse | SASB-k32 | 0.1197 | 3.1025 | 10.3336 | 32.0000 | 29.4000 | 0.0000 |
| ca_csphd | SASB_worse | SASB-k64 | 0.1223 | 3.8842 | 8.2540 | 64.0000 | 42.7250 | 0.0000 |
| ca_csphd | SASB_worse | Adaptive-SASB | 0.1224 | 4.1752 | 7.6786 | 64.0000 | 42.8417 | 1.0000 |
| bio_grid_mouse | SASB_worse | SASB-k32 | 0.4677 | 8.8931 | 5.2835 | 32.0000 | 32.0000 | 0.0000 |
| bio_grid_mouse | SASB_worse | SASB-k64 | 0.5905 | 14.4107 | 3.2606 | 64.0000 | 64.0000 | 0.0000 |
| bio_grid_mouse | SASB_worse | Adaptive-SASB | 0.5635 | 15.5047 | 3.0305 | 64.0000 | 64.0000 | 1.0000 |
| rt_twitter_copen | SASB_worse | SASB-k32 | 0.9309 | 17.4852 | 7.2195 | 32.0000 | 32.0000 | 0.0000 |
| rt_twitter_copen | SASB_worse | SASB-k64 | 0.8598 | 20.1788 | 6.2558 | 64.0000 | 64.0000 | 0.0000 |
| rt_twitter_copen | SASB_worse | Adaptive-SASB | 0.8593 | 22.6101 | 5.5831 | 64.0000 | 64.0000 | 1.0000 |
| inf_power | SASB_worse | SASB-k32 | 0.6295 | 115.4351 | 27.6434 | 32.0000 | 32.0000 | 0.0000 |
| inf_power | SASB_worse | SASB-k64 | 0.3955 | 86.3831 | 36.9403 | 64.0000 | 64.0000 | 0.0000 |
| inf_power | SASB_worse | Adaptive-SASB | 0.5345 | 131.4447 | 24.2765 | 64.0000 | 64.0000 | 1.0000 |

## 4. 方法平均表现

| method | normalized_auc | runtime_seconds | speedup_vs_m5 | mean_k | mean_sample_sources | bridge_core_adaptive_step_ratio |
|---|---|---|---|---|---|---|
| Adaptive-SASB | 0.6614 | 30.5313 | 11.5020 | 48.0000 | 45.3552 | 0.5000 |
| SASB-k32 | 0.6699 | 26.8407 | 12.8015 | 32.0000 | 31.6750 | 0.0000 |
| SASB-k64 | 0.6255 | 26.1445 | 12.1664 | 64.0000 | 60.8062 | 0.0000 |

## 5. source composition 实际比例

| method | ratio_source_boundary | ratio_source_bridge_neighbor | ratio_source_community | ratio_source_community_boundary | ratio_source_core2_boundary | ratio_source_degree | ratio_source_random_fill |
|---|---|---|---|---|---|---|---|
| Adaptive-SASB | 0.3750 | 0.3510 | 0.0702 | 0.2547 | 0.1753 | 0.2251 | 0.1617 |
| SASB-k32 | 0.3791 | nan | 0.0944 | nan | nan | 0.3158 | 0.2107 |
| SASB-k64 | 0.4171 | nan | 0.0473 | nan | nan | 0.2949 | 0.2466 |

## 6. Adaptive-SASB 是否改善 worse 组、是否损害 better 组

- SASB worse 组：Adaptive-SASB 相比 SASB-k32 的 mean AUC delta = `-0.017006`，小于 0 表示改善。
- SASB better 组：Adaptive-SASB 相比 SASB-k32 的 mean AUC delta = `0.000000`，大于 0 表示损害。
- SASB worse 组逐图改善数：`2/4`。
- SASB better 组逐图未损害数：`4/4`。

解释边界：这是 8 图 smoke test，不是最终结论。Adaptive 规则如果在 worse 组降低 AUC，同时在 better 组不明显升高 AUC，才说明值得扩展到 24 图或完整 28 图。

## 7. 输出文件

- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/per_graph_method_summary.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/summary_with_m5_baseline.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/source_composition_summary.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/adaptive_vs_fixed_auc_delta.csv`
- `result/sasb_m5_edge_diagnostics/adaptive_sasb_smoke_20260707_162049/plots/`

原始逐边过程文件 `edge_steps.csv` 与逐步曲线 `curves.csv` 仅在本地结果目录保留，不作为本次 GitHub curated update 的重点内容。
