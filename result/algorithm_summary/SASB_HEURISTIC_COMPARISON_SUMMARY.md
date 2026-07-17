# SASB 与启发式算法瓦解效果对比总结

## 1. 研究问题

本报告只聚焦 SASB 与仓库中已经实际运行过的启发式 edge-removal 算法在网络瓦解效果上的比较。P1/P2 source/candidate 消融不作为主体。

核心指标是 normalized GCC-AUC，越低表示 GCC 瓦解越快；辅助指标是 runtime。所有数字来自 `result/paper_experiments/baselines/` 的已有 CSV，没有运行新实验。

## 2. 对照组和实验组

实验组：SASB，即 per-graph 表中的 `M19-theory-fast-no-delta` 或 `M19-sampled-BE-fast`，以及 summary 表中的 `M19-sampled-BE-fast`。

对照组：M5、M7、M12、dynamic-community-bridge、static-community-bridge、static-edge-betweenness、degree-product、random-edge，以及 M19-original / M19-no-bridge 两个近邻变体。`k-core/k-shell` 与 Collective Influence 在当前 baseline 阶段是 node-removal reference，标记为未运行，不混入 edge-removal 公平排名。

## 3. 证据集合

1. `synthetic45_all_methods_45`：45 张 synthetic graph，适合做全方法比较。
2. `realworld_main_28`：28 张真实网络，适合比较 SASB、M5、M7、M12 和 M19 变体。
3. `realworld_common_classic_13`：13 张真实网络 common subset，要求 classic edge-removal baseline 全部完成，适合做 classic baseline 公平比较。

## 4. Synthetic45：45 图全方法比较

| method_display | graph_count | mean_normalized_auc | std_normalized_auc | mean_runtime_seconds | rank_by_auc |
| --- | --- | --- | --- | --- | --- |
| SASB | 45 | 0.342167 | 0.119224 | 11.489873 | 1.000000 |
| M19-original | 45 | 0.346563 | 0.128012 | 8.959637 | 2.000000 |
| M19-no-bridge | 45 | 0.346591 | 0.128002 | 7.152616 | 3.000000 |
| M5 dynamic edge betweenness | 45 | 0.355794 | 0.134196 | 22.296199 | 4.000000 |
| M7 dynamic community bridge | 45 | 0.367549 | 0.132581 | 6.454483 | 5.000000 |
| dynamic community bridge | 45 | 0.375719 | 0.133602 | 2.546621 | 6.000000 |
| M12 stale community | 45 | 0.386083 | 0.143173 | 2.402602 | 7.000000 |
| static community bridge | 45 | 0.467465 | 0.136688 | 1.530858 | 8.000000 |
| static edge betweenness | 45 | 0.651171 | 0.162646 | 1.793021 | 9.000000 |
| degree product | 45 | 0.696054 | 0.102762 | 2.498223 | 10.000000 |
| random edge | 45 | 0.722356 | 0.099265 | 2.031892 | 11.000000 |

结论：SASB mean normalized GCC-AUC = 0.342167，低于 M5 的 0.355794、M7 的 0.367549、M12 的 0.386083。SASB mean runtime = 11.490s，低于 M5 的 22.296s。

## 5. Realworld：28 图主方法比较

| method_display | graph_count | mean_normalized_auc | std_normalized_auc | mean_runtime_seconds | rank_by_auc |
| --- | --- | --- | --- | --- | --- |
| M5 dynamic edge betweenness | 28 | 0.203664 | 0.165807 | 4297.176027 | 1.000000 |
| SASB | 28 | 0.224016 | 0.189407 | 288.683310 | 2.000000 |
| M19-original | 28 | 0.229407 | 0.190251 | 234.052345 | 3.000000 |
| M19-no-bridge | 28 | 0.229544 | 0.190148 | 212.800936 | 4.000000 |
| M7 dynamic community bridge | 28 | 0.231593 | 0.183696 | 137.236297 | 5.000000 |
| M12 stale community | 28 | 0.371794 | 0.274034 | 99.458545 | 6.000000 |

结论：28 图真实网络上，SASB mean normalized GCC-AUC = 0.224016，高于 M5 的 0.203664，因此不能声称 SASB 超过 M5；但 SASB runtime = 288.683s，显著低于 M5 的 4297.176s。SASB 的 AUC 优于 M7 和 M12。

## 6. Realworld：13 图 classic-baseline common subset

| method_display | graph_count | mean_normalized_auc | std_normalized_auc | mean_runtime_seconds | rank_by_auc |
| --- | --- | --- | --- | --- | --- |
| M5 dynamic edge betweenness | 13 | 0.160090 | 0.118876 | 96.255363 | 1.000000 |
| M19-original | 13 | 0.167289 | 0.124895 | 27.418115 | 2.000000 |
| M19-no-bridge | 13 | 0.167507 | 0.124808 | 20.762284 | 3.000000 |
| SASB | 13 | 0.168316 | 0.124493 | 32.295214 | 4.000000 |
| M7 dynamic community bridge | 13 | 0.176583 | 0.122396 | 12.476458 | 5.000000 |
| dynamic community bridge | 13 | 0.202888 | 0.138748 | 8.316361 | 6.000000 |
| static community bridge | 13 | 0.262179 | 0.158941 | 6.308447 | 7.000000 |
| M12 stale community | 13 | 0.272961 | 0.207388 | 9.393339 | 8.000000 |
| static edge betweenness | 13 | 0.379884 | 0.193841 | 7.637258 | 9.000000 |
| degree product | 13 | 0.476070 | 0.291358 | 9.345293 | 10.000000 |
| random edge | 13 | 0.532831 | 0.230222 | 9.449868 | 11.000000 |

结论：13 图 common subset 上，SASB 不优于 M5，但优于 M7、M12、dynamic-community-bridge、static-community-bridge、static-edge-betweenness、degree-product 和 random-edge 的均值 AUC。

## 7. Paired Difference

| evidence_set | comparison | n_graphs | mean_auc_diff | median_auc_diff | sasb_wins | sasb_losses | ties |
| --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic45_all_methods_45 | SASB minus M5 | 45 | -0.013627 | -0.005976 | 31 | 14 | 0 |
| synthetic45_all_methods_45 | SASB minus M7 | 45 | -0.025382 | -0.020454 | 39 | 6 | 0 |
| synthetic45_all_methods_45 | SASB minus M12 | 45 | -0.043916 | -0.039180 | 44 | 1 | 0 |
| synthetic45_all_methods_45 | SASB minus dynamic-community-bridge | 45 | -0.033552 | -0.032618 | 41 | 4 | 0 |
| synthetic45_all_methods_45 | SASB minus static-community-bridge | 45 | -0.125299 | -0.120419 | 45 | 0 | 0 |
| synthetic45_all_methods_45 | SASB minus static-edge-betweenness | 45 | -0.309004 | -0.315736 | 45 | 0 | 0 |
| synthetic45_all_methods_45 | SASB minus degree-product | 45 | -0.353887 | -0.322163 | 45 | 0 | 0 |
| synthetic45_all_methods_45 | SASB minus random-edge | 45 | -0.380189 | -0.348281 | 45 | 0 | 0 |
| synthetic45_all_methods_45 | SASB minus M19-original | 45 | -0.004396 | -0.001226 | 24 | 21 | 0 |
| synthetic45_all_methods_45 | SASB minus M19-no-bridge | 45 | -0.004424 | -0.001226 | 25 | 20 | 0 |
| realworld_main_28 | SASB minus M5 | 28 | 0.020353 | 0.001088 | 7 | 19 | 2 |
| realworld_main_28 | SASB minus M7 | 28 | -0.007577 | -0.006608 | 23 | 5 | 0 |
| realworld_main_28 | SASB minus M12 | 28 | -0.147778 | -0.170441 | 28 | 0 | 0 |
| realworld_main_28 | SASB minus M19-original | 28 | -0.005391 | -0.000390 | 15 | 13 | 0 |
| realworld_main_28 | SASB minus M19-no-bridge | 28 | -0.005528 | -0.000755 | 16 | 12 | 0 |
| realworld_common_classic_13 | SASB minus M5 | 13 | 0.008226 | 0.000365 | 3 | 9 | 1 |
| realworld_common_classic_13 | SASB minus M7 | 13 | -0.008267 | -0.006751 | 11 | 2 | 0 |
| realworld_common_classic_13 | SASB minus M12 | 13 | -0.104644 | -0.087474 | 13 | 0 | 0 |
| realworld_common_classic_13 | SASB minus dynamic-community-bridge | 13 | -0.034572 | -0.030172 | 13 | 0 | 0 |
| realworld_common_classic_13 | SASB minus static-community-bridge | 13 | -0.093863 | -0.083811 | 13 | 0 | 0 |
| realworld_common_classic_13 | SASB minus static-edge-betweenness | 13 | -0.211568 | -0.209625 | 13 | 0 | 0 |
| realworld_common_classic_13 | SASB minus degree-product | 13 | -0.307754 | -0.317933 | 13 | 0 | 0 |
| realworld_common_classic_13 | SASB minus random-edge | 13 | -0.364515 | -0.399675 | 13 | 0 | 0 |
| realworld_common_classic_13 | SASB minus M19-original | 13 | 0.001027 | 0.000826 | 4 | 9 | 0 |
| realworld_common_classic_13 | SASB minus M19-no-bridge | 13 | 0.000810 | 0.000304 | 4 | 9 | 0 |

负值表示 SASB 的 normalized GCC-AUC 更低。paired 结果显示：synthetic45 上 SASB 相对 M5/M7/M12 和 classic baseline 多数逐图占优；realworld 上 SASB 相对 M5 劣势，但相对 M7/M12 与 classic baseline 有优势。

## 8. 启发式方法定义

| method | principle | graph_information | source_sampling | candidate_set | dynamic_update | main_cost |
| --- | --- | --- | --- | --- | --- | --- |
| SASB / M19-sampled-BE-fast | structure-aware sampled betweenness on candidate edges | yes | yes | yes | yes | candidate generation + sampled shortest paths |
| M5 | dynamic exact edge betweenness | yes | no | no | yes | full edge betweenness each step |
| M7 | dynamic community bridge heuristic | community partition | no | implicit | yes | community bridge scoring |
| M12 | stale community attack | stale partition | no | implicit | partly/stale | low-cost community scoring |
| dynamic-community-bridge | classic dynamic community bridge baseline | community partition | no | implicit | yes | community scoring |
| static-community-bridge | static community bridge baseline | initial community | no | implicit | no | one static ordering |
| static-edge-betweenness | static edge betweenness baseline | initial full graph | no | no | no | one betweenness pass |
| degree-product | endpoint degree product | local degree | no | no | yes | low |
| random-edge | uniform random edge deletion | no | no | no | yes/random | low; 3 seeds in baseline stage |

## 9. 可写入论文的结论

1. synthetic45 上，SASB 是当前 edge-removal baseline 中 mean normalized GCC-AUC 最低的方法，并且 runtime 低于 M5。
2. realworld 28 图上，SASB 没有超过 M5，但以显著更低 runtime 优于 M7/M12。
3. realworld 13 图 common subset 上，SASB 优于多数 classic low-cost heuristic，但仍不优于 M5。
4. 合理定位：SASB 不是全面替代 M5，而是在 synthetic networks 上超过 M5，在 realworld networks 上以较低成本取得接近 M5、优于多数启发式的瓦解效果。

## 10. 不能写入论文的结论

不能写 SASB 在所有真实网络上优于 M5；不能把 13 图 common subset 外推到全部真实网络；不能把 node-removal k-core/CI 与 edge-removal 方法混排；不能只凭 runtime 声称瓦解效果更好。

## 11. 生成文件

- `result/algorithm_summary/SASB_HEURISTIC_COMPARISON_SUMMARY.md`
- `result/algorithm_summary/sasb_heuristic_comparison_summary.csv`
- `result/algorithm_summary/sasb_heuristic_paired_comparisons.csv`
- `result/algorithm_summary/sasb_heuristic_method_definitions.csv`
- `result/algorithm_summary/plots/heuristic_*.png`
