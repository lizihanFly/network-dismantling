# 为什么 SASB 在部分真实网络上赢 M5、在部分网络上输给 M5

本报告基于 `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/` 中当前 24/28 completed subset 的 M5 与 SASB 诊断结果生成。剩余 4 个真实网络尚未纳入本报告，因此以下结论是阶段性解释，不是最终 full realworld 结论。AUC 使用 normalized GCC AUC，数值越低表示瓦解越快；`SASB-M5 AUC difference < 0` 表示 SASB 优于 M5。

## 1. 数据与分组

读取文件：

- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/graph_method_summary.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/network_diagnosis.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/phase_auc_by_graph.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/edge_step_diagnostics.csv`

图级结构特征从 `data/realnetworks_40plus/cleaned/*.edges` 重新读取，并统一转为无向、无权、去自环后的 GCC 计算。当前环境的 NetworkX 不提供 Louvain 接口，因此本报告中的 modularity、community count 与 graph-level inter-community edge ratio 使用 `greedy_modularity_communities` 近似；M5/SASB 逐边诊断中的 community/inter-community 字段仍来自原实验记录。

分组结果：

- SASB better than M5：7 个网络，`bio_celegansneural`, `bio_diseasome`, `football`, `ia_email_univ`, `ia_enron_only`, `ia_infect_dublin`, `soc_wiki_vote`
- SASB worse than M5：16 个网络，`bio_celegans`, `bio_celegans_dir`, `bio_grid_mouse`, `bio_grid_plant`, `bio_sc_ts`, `ca_csphd`, `ca_netscience`, `ia_infect_hyper`, `ia_radoslaw_email`, `inf_euroroad`, `inf_power`, `inf_usair97`, `rt_twitter_copen`, `soc_dolphins`, `web_edu`, `web_polblogs`
- tie / close：1 个网络，`rt_retweet`

## 2. 每类网络的结构特征

| outcome_class | graphs | auc_diff_mean | n_mean | m_mean | average_degree_mean | degree_cv_mean | clustering_coefficient_mean | modularity_mean | num_communities_mean | bridge_ratio_mean | core2_size_ratio_mean | average_edge_embeddedness_mean | inter_community_edge_ratio_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SASB better than M5 | 7 | -0.0061 | 500.4286 | 2243.1429 | 9.7299 | 0.7956 | 0.3706 | 0.5693 | 10.1429 | 0.0307 | 0.9029 | 0.4479 | 0.2011 |
| SASB worse than M5 | 16 | 0.0249 | 970.5625 | 2340.9375 | 13.2985 | 1.1782 | 0.3896 | 0.5782 | 20.1250 | 0.1775 | 0.7332 | 0.4744 | 0.1696 |
| tie / close | 1 | 0.0000 | 96.0000 | 117.0000 | 2.4375 | 1.0540 | 0.0607 | 0.6793 | 8.0000 | 0.5299 | 0.3542 | 0.1243 | 0.1795 |

从当前 24 图看，SASB 赢/输组的 modularity 均值接近，不能把胜负简单归因于“模块度更高”。更稳的结构差异是：SASB 赢的网络平均 2-core ratio 更高、初始 bridge ratio 更低；SASB 输的网络平均 bridge ratio 明显更高、2-core ratio 更低，说明这些图中存在更多树状分支或瓶颈式割边，完整 M5 的全局 edge betweenness 更容易稳定捕捉这类关键桥边。

Spearman 相关用于辅助观察，不作为因果证明：

| feature | spearman_corr_with_sasb_minus_m5_auc |
|---|---|
| modularity | -0.2035 |
| bridge_ratio | 0.0287 |
| core2_size_ratio | -0.0905 |
| degree_cv | 0.1840 |
| clustering_coefficient | 0.0922 |
| average_edge_embeddedness | 0.1400 |
| inter_community_edge_ratio | 0.1383 |

## 3. M5 与 SASB 选边结构差异

| outcome_class | method | selected_edges | bridge_selection_ratio | inter_community_edge_ratio | mean_common_neighbors | mean_edge_embeddedness | mean_degree_product | mean_immediate_delta_gcc |
|---|---|---|---|---|---|---|---|---|
| SASB better than M5 | M5 | 15702 | 0.2226 | 0.4142 | 1.3295 | 0.3294 | 121.8026 | 0.0004 |
| SASB better than M5 | SASB | 15702 | 0.2226 | 0.5522 | 1.3295 | 0.3032 | 131.2181 | 0.0004 |
| SASB worse than M5 | M5 | 37455 | 0.4142 | 0.3344 | 3.6905 | 0.3653 | 272.2837 | 0.0004 |
| SASB worse than M5 | SASB | 37455 | 0.4142 | 0.4635 | 3.6905 | 0.3059 | 350.7838 | 0.0004 |
| tie / close | M5 | 117 | 0.8120 | 0.3932 | 0.1026 | 0.0293 | 13.1026 | 0.0085 |
| tie / close | SASB | 117 | 0.8120 | 0.3932 | 0.1026 | 0.0293 | 13.1026 | 0.0085 |

SASB 相比 M5 更倾向于选择 inter-community edge；在当前 24 图总体报告中，SASB 的 inter-community ratio 为 0.455046，高于 M5 的 0.346077。这说明少量结构化源点采样确实引入了偏向社区边界的结构偏差。这个偏差在模块化结构较清晰、核心部分较大的网络中可能有益；但在 bridge 较多、网络更树状或关键割边更分散的网络中，过强的社区边界偏好不一定等价于最大 GCC 降幅。

## 4. early / middle / late phase AUC

| outcome_class | attack_phase | M5 | SASB |
|---|---|---|---|
| SASB better than M5 | early | 0.5058 | 0.5117 |
| SASB better than M5 | late | 0.0287 | 0.0198 |
| SASB better than M5 | middle | 0.0973 | 0.0818 |
| SASB worse than M5 | early | 0.3910 | 0.4544 |
| SASB worse than M5 | late | 0.0655 | 0.0531 |
| SASB worse than M5 | middle | 0.1611 | 0.1848 |
| tie / close | early | 0.3403 | 0.3403 |
| tie / close | late | 0.0224 | 0.0224 |
| tie / close | middle | 0.0477 | 0.0477 |

SASB 赢的图通常不是每一步 immediate delta 都更大；在当前分组均值中，SASB better 组的 early phase 反而略高于 M5，但 middle 与 late phase 更低，说明优势主要在中后段兑现。SASB 输的图中，M5 在 early 与 middle 阶段更稳定地压低 GCC，后续差距会被整体 AUC 放大。late 阶段的 phase AUC 绝对值较小，解释时应弱于 early/middle。

## 5. 图表路径

- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_vs_modularity.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_vs_bridge_ratio.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_vs_2core_ratio.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/selected_edge_embeddedness_distribution_by_method.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/selected_edge_delta_gcc_distribution_by_method.png`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/phase_auc_comparison_by_outcome.png`

## 6. 回答核心问题

**SASB 在哪些网络结构上更容易赢 M5？**

当前 completed subset 中，SASB 更容易在 2-core 占比较高、初始 bridge ratio 较低的网络上获胜；modularity 本身不是充分解释变量，因为赢/输组的均值很接近。这类网络的关键边更可能体现为核心中的跨模块通路或低嵌入连接，SASB 的 `S_comm/S_boundary/S_local` 候选集与 sampled dependency 更容易把采样预算集中到这些结构位置。

**SASB 输给 M5 的网络有什么共同特征？**

SASB 输的网络平均 bridge ratio 更高、2-core ratio 更低，说明图中树状分支、局部瓶颈和割边更多。对于这类网络，完整 M5 的动态 edge betweenness 对全局最短路流量和桥边变化更敏感；SASB 的结构化采样如果偏向社区边界，可能会错过某些在当前 GCC 中真正承担最大割裂作用的桥边或准桥边。

**SASB 选边和 M5 选边的结构差异是什么？**

最稳定的差异是 SASB 更偏向 inter-community edge，并且在不少图上选到更低 embeddedness 的边。这种差异说明 SASB 不是简单复刻完整 edge betweenness，而是形成了社区边界优先的近似介数偏差。该偏差在某些网络中降低 AUC，在另一些网络中会牺牲 M5 的全局精度。

**少量结构化源点采样是否带来了有益的结构偏差？**

初步结果表明，少量结构化源点采样确实带来了结构偏差，而且这种偏差不是纯噪声：在 7 个 SASB better 网络中，它能以更低成本识别出足够有效的跨社区或低嵌入边；但在 16 个 SASB worse 网络中，这种偏差不足以替代完整 M5 对全局桥边和动态最短路流量的刻画。因此更准确的表述是：结构化源点采样带来了有条件有益的偏差，而不是普遍优于完整 betweenness。

**后续是否应该发展 adaptive source budget 或 adaptive source composition？**

应该。当前结果支持两个自适应方向：第一，adaptive source budget，应在 bridge ratio 高、2-core ratio 低或 early-phase AUC 开始落后时增加源点预算；第二，adaptive source composition，应根据网络是否呈现强模块化、树状桥多、核心密集等结构，动态调节社区源点、边界源点与局部源点的比例。这样可以保留 SASB 的速度优势，同时降低在桥多网络上输给 M5 的风险。

## 7. 产出文件

- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/graph_structure_by_outcome.csv`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/structure_summary_by_outcome.csv`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/selected_edge_summary_by_outcome_method.csv`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/phase_auc_summary_by_outcome_method.csv`
- `result/sasb_m5_edge_diagnostics/why_sasb_wins_or_loses/auc_diff_feature_correlations.csv`