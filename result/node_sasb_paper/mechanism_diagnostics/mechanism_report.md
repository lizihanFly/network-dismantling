# SASB-N Mechanism Diagnostic Report

## 1. 实验目的

本实验只诊断两个问题：structured source policy 为什么可能不如 random-source，以及四种 source policy 的节点排序谁更接近精确 M5 node betweenness。它不重新分析其他 pilot budget，也不运行 73 网络正式实验。

## 2. 实验定义

源点多样性指标在每种策略自己的动态攻击轨迹中逐步计算。不同策略的逐步轨迹不同，因此不做逐步 source-set Jaccard 横向比较；跨策略 source-set overlap 只在相同初始图状态下计算。

排序指标在每种策略自己的当前 GCC 上计算：先用该策略当前源点集合得到 sampled dependency，再在同一个当前 GCC 上计算精确 M5 node betweenness。checkpoint 为 remove ratio 最接近 0、0.1、0.2、0.3、0.5 的 step。

## 3. 数据和实验设置

- 网络：pilot 中 24 个网络，synthetic45 12 个、realworld_completed 12 个。
- 方法：SASB-N-structured、SASB-N-random-source、SASB-N-degree-source、SASB-N-frozen-source。
- source budget：固定为 B=64。
- seeds：20260513--20260517。
- 源点距离：源点对不超过 64 对时使用全部源点对，否则使用由 `stable_seed(seed, graph_id, method, step, source-distance-pairs)` 固定抽取的 64 对。
- source betweenness proxy：当前 sampled dependency score 在源点上的均值，不是精确 M5 betweenness。

## 4. Smoke 验证

```json
{
  "run_count": true,
  "network_count": true,
  "method_count": true,
  "seed_count": true,
  "all_finished": true,
  "source_rows_nonempty": true,
  "ranking_rows_nonempty": true,
  "source_budget_correct": true,
  "active_source_valid": true,
  "candidate_scope_valid": true,
  "no_nan_core_source_metrics": true,
  "no_nan_core_ranking_metrics": true,
  "passed": true
}
```

## 5. 源点多样性结果

下表是按 dataset 和 strategy 汇总的逐步结果。不同策略的均值用于描述策略行为，不表示它们在同一图状态上逐步配对。

| dataset_group | method | step_count | mean_community_coverage | mean_community_entropy | mean_source_pairwise_distance_mean | mean_boundary_source_fraction | mean_positive_dependency_node_fraction | mean_source_set_jaccard_previous_step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| realworld_completed | SASB-N-degree-source | 52535 | 0.543 | 2.8838 | 1.0961 | 0.1369 | 0.1553 | 0.6917 |
| realworld_completed | SASB-N-frozen-source | 52535 | 0.0994 | 0.76 | 0.3724 | 0.1217 | 0.0821 | 0.9014 |
| realworld_completed | SASB-N-random-source | 52535 | 0.5507 | 2.9044 | 1.2235 | 0.099 | 0.1545 | 0.1496 |
| realworld_completed | SASB-N-structured | 52535 | 0.5485 | 2.9037 | 1.0895 | 0.1503 | 0.1539 | 0.6597 |
| synthetic45 | SASB-N-degree-source | 9140 | 0.9973 | 1.8186 | 1.9578 | 0.3603 | 0.4616 | 0.6209 |
| synthetic45 | SASB-N-frozen-source | 9140 | 0.648 | 1.3504 | 1.6911 | 0.3788 | 0.4378 | 0.6833 |
| synthetic45 | SASB-N-random-source | 9140 | 0.9996 | 1.8262 | 1.9885 | 0.3336 | 0.4567 | 0.4579 |
| synthetic45 | SASB-N-structured | 9140 | 0.9999 | 1.8317 | 1.9177 | 0.3883 | 0.4563 | 0.5544 |

## 6. 节点排序相关性结果

排序结果按 checkpoint 汇总；正相关表示 sampled dependency 排序更接近精确 M5 排序。

| dataset_group | method | checkpoint_target_ratio | mean_spearman_rank_correlation | mean_kendall_rank_correlation | mean_top_5pct_overlap | mean_removed_node_m5_rank_percentile |
| --- | --- | --- | --- | --- | --- | --- |
| realworld_completed | SASB-N-degree-source | 0.0 | 0.9791 | 0.9182 | 0.8261 | 0.0 |
| realworld_completed | SASB-N-degree-source | 0.1 | 0.9893 | 0.9497 | 0.9246 | 0.0026 |
| realworld_completed | SASB-N-degree-source | 0.2 | 0.7415 | 0.7158 | 0.9077 | 0.0072 |
| realworld_completed | SASB-N-degree-source | 0.3 | 0.4147 | 0.4069 | 0.9792 | 0.0011 |
| realworld_completed | SASB-N-degree-source | 0.5 | 0.1667 | 0.1667 | 1.0 | 0.0 |
| realworld_completed | SASB-N-frozen-source | 0.0 | 0.9782 | 0.9184 | 0.8591 | 0.0 |
| realworld_completed | SASB-N-frozen-source | 0.1 | 0.721 | 0.6632 | 0.7208 | 0.0495 |
| realworld_completed | SASB-N-frozen-source | 0.2 | 0.3614 | 0.3268 | 0.6637 | 0.053 |
| realworld_completed | SASB-N-frozen-source | 0.3 | 0.1853 | 0.1682 | 0.8402 | 0.0224 |
| realworld_completed | SASB-N-frozen-source | 0.5 | 0.1397 | 0.1246 | 0.9333 | 0.0085 |
| realworld_completed | SASB-N-random-source | 0.0 | 0.9785 | 0.9147 | 0.8375 | 0.0001 |
| realworld_completed | SASB-N-random-source | 0.1 | 0.9853 | 0.9466 | 0.8881 | 0.008 |
| realworld_completed | SASB-N-random-source | 0.2 | 0.8242 | 0.7989 | 0.9109 | 0.002 |
| realworld_completed | SASB-N-random-source | 0.3 | 0.5326 | 0.5277 | 0.9792 | 0.0015 |
| realworld_completed | SASB-N-random-source | 0.5 | 0.25 | 0.25 | 1.0 | 0.0 |
| realworld_completed | SASB-N-structured | 0.0 | 0.9782 | 0.9184 | 0.8591 | 0.0 |
| realworld_completed | SASB-N-structured | 0.1 | 0.9895 | 0.9526 | 0.9126 | 0.0042 |
| realworld_completed | SASB-N-structured | 0.2 | 0.8267 | 0.8026 | 0.9227 | 0.0014 |
| realworld_completed | SASB-N-structured | 0.3 | 0.5316 | 0.5241 | 0.9708 | 0.003 |
| realworld_completed | SASB-N-structured | 0.5 | 0.25 | 0.25 | 1.0 | 0.0 |
| synthetic45 | SASB-N-degree-source | 0.0 | 0.9431 | 0.8103 | 0.7156 | 0.0083 |
| synthetic45 | SASB-N-degree-source | 0.1 | 0.9498 | 0.8385 | 0.7355 | 0.018 |
| synthetic45 | SASB-N-degree-source | 0.2 | 0.9633 | 0.8774 | 0.831 | 0.0069 |
| synthetic45 | SASB-N-degree-source | 0.3 | 0.9766 | 0.9153 | 0.865 | 0.012 |
| synthetic45 | SASB-N-degree-source | 0.5 | 0.5833 | 0.5833 | 1.0 | 0.0 |
| synthetic45 | SASB-N-frozen-source | 0.0 | 0.9442 | 0.8126 | 0.7434 | 0.0074 |
| synthetic45 | SASB-N-frozen-source | 0.1 | 0.9339 | 0.8007 | 0.597 | 0.0384 |
| synthetic45 | SASB-N-frozen-source | 0.2 | 0.9153 | 0.7879 | 0.6781 | 0.0299 |
| synthetic45 | SASB-N-frozen-source | 0.3 | 0.9104 | 0.7973 | 0.5973 | 0.0426 |
| synthetic45 | SASB-N-frozen-source | 0.5 | 0.5786 | 0.5333 | 0.7833 | 0.059 |
| synthetic45 | SASB-N-random-source | 0.0 | 0.9462 | 0.8142 | 0.7282 | 0.004 |
| synthetic45 | SASB-N-random-source | 0.1 | 0.9583 | 0.8559 | 0.7455 | 0.0079 |
| synthetic45 | SASB-N-random-source | 0.2 | 0.9705 | 0.8904 | 0.7804 | 0.0095 |
| synthetic45 | SASB-N-random-source | 0.3 | 0.9846 | 0.9342 | 0.8629 | 0.0027 |
| synthetic45 | SASB-N-random-source | 0.5 | 0.6667 | 0.6667 | 1.0 | 0.0 |
| synthetic45 | SASB-N-structured | 0.0 | 0.9442 | 0.8126 | 0.7434 | 0.0074 |
| synthetic45 | SASB-N-structured | 0.1 | 0.9521 | 0.8455 | 0.7036 | 0.0241 |
| synthetic45 | SASB-N-structured | 0.2 | 0.9641 | 0.8794 | 0.7671 | 0.0147 |
| synthetic45 | SASB-N-structured | 0.3 | 0.9784 | 0.9179 | 0.7979 | 0.0092 |
| synthetic45 | SASB-N-structured | 0.5 | 0.65 | 0.65 | 1.0 | 0.0 |

## Numeric comparison for the mechanism question

The following tables make the structured versus random-source comparison explicit. Negative AUC delta means structured is better; positive means structured is worse.

| dataset_group | mean_delta_structured_minus_random | median_delta_structured_minus_random | structured_better | ties | structured_worse |
| --- | --- | --- | --- | --- | --- |
| realworld_completed | 0.0025 | 0.0015 | 3 | 1 | 8 |
| synthetic45 | 0.0039 | 0.0049 | 4 | 0 | 8 |

Mean B=64 normalized AUC by source policy:

| dataset_group | method | normalized_auc |
| --- | --- | --- |
| realworld_completed | SASB-N-degree-source | 0.1109 |
| realworld_completed | SASB-N-frozen-source | 0.1176 |
| realworld_completed | SASB-N-random-source | 0.1082 |
| realworld_completed | SASB-N-structured | 0.1107 |
| synthetic45 | SASB-N-degree-source | 0.2624 |
| synthetic45 | SASB-N-frozen-source | 0.2603 |
| synthetic45 | SASB-N-random-source | 0.2549 |
| synthetic45 | SASB-N-structured | 0.2589 |

## Structured versus M5 ranking correlation

Each value compares sampled dependency with exact M5 node betweenness on the same policy-specific current GCC; ranking correlation is not equivalent to dismantling AUC.

| dataset_group | method | spearman_rank_correlation | kendall_rank_correlation | top_5pct_overlap |
| --- | --- | --- | --- | --- |
| realworld_completed | SASB-N-degree-source | 0.6583 | 0.6315 | 0.9275 |
| realworld_completed | SASB-N-frozen-source | 0.4771 | 0.4403 | 0.8034 |
| realworld_completed | SASB-N-random-source | 0.7141 | 0.6876 | 0.9231 |
| realworld_completed | SASB-N-structured | 0.7152 | 0.6895 | 0.933 |
| synthetic45 | SASB-N-degree-source | 0.8832 | 0.805 | 0.8294 |
| synthetic45 | SASB-N-frozen-source | 0.8565 | 0.7464 | 0.6798 |
| synthetic45 | SASB-N-random-source | 0.9052 | 0.8323 | 0.8234 |
| synthetic45 | SASB-N-structured | 0.8978 | 0.8211 | 0.8024 |

Structured minus random-source mean Spearman correlation:

| dataset_group | mean_spearman_delta | median_spearman_delta |
| --- | --- | --- |
| realworld_completed | 0.0011 | 0.0 |
| synthetic45 | -0.0075 | 0.0 |

## Structured versus random-source source diversity

These are trajectory-level mean differences, not stepwise paired comparisons across policies.

| dataset_group | delta_community_coverage | delta_community_entropy | delta_source_pairwise_distance | delta_boundary_fraction |
| --- | --- | --- | --- | --- |
| realworld_completed | -0.0022 | -0.0006 | -0.134 | 0.0513 |
| synthetic45 | 0.0003 | 0.0055 | -0.0707 | 0.0548 |

## 7. Structured 与 random-source

初始 source-set overlap 见 `source_policy_initial_overlap.csv`。source diversity 和 ranking 的 paired tests 见 `mechanism_statistical_tests.csv`。delta_policy 使用已有 pilot 的 B=64 结果定义为 `AUC_structured - AUC_random_source`，本诊断不重新运行其他 budget。

## 8. 机制解释和证据边界

本报告不直接声称结构化偏差有益。若 structured 的 boundary fraction 较高、community entropy 或 source distance 较低，同时排序相关性和 AUC 较差，则更符合当前 boundary-first 规则引入不利偏差的解释；若排序相关性较低但 AUC 较好，则说明瓦解目标不要求完全恢复 M5 排序；若 random-source 的排序相关性和 AUC 都更好，则当前结构化规则没有显示优势；若 structured 社区覆盖更好但 AUC 更差，则社区覆盖本身不能保证覆盖真正的高介数路径。

## 9. 案例

案例图按已有 B=64 pilot 的 delta_policy 选择极端网络，仅用于机制展示，不作为主要证据，也不删除任何负结果。

- structured failure case：`synthetic45/synthetic_test_038; delta_policy=0.0147`。
- random-source success case：`synthetic45/synthetic_test_043; delta_policy=-0.0050`。

## 10. 运行和输出

- 诊断运行数：480。
- 完成数：480；失败数：0。
- source step rows：246700；ranking checkpoint rows：2400。
- 累计运行时间：11783.27 秒。

## 11. 下一步建议

下一版应根据本诊断中 source diversity、排序相关性和 AUC 的共同证据决定：继续改进 structured 的 boundary-first 规则，还是将 random-source 作为更稳健的采样基线。仅凭单一 AUC 或单一排序相关性不能做出主方法决策。
