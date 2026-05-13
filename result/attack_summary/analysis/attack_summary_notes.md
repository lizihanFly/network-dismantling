# 攻击结果汇总分析

所有核心指标都是越低越好：AUC 越小，或者达到指定 GCC 阈值所需删除边比例越小，说明网络碎裂越快。

## 主要结论

- 全部网络上平均 AUC 排名最好的是：M5 max edge betweenness，平均排名 1.88。
- M8 在 8 个网络中有 0 个网络取得 AUC 第一；`m8_auc_minus_best` 为正的网络表示乘上度积后仍弱于当前最佳基线。
- SBM 结果显示：社区结构从 strong 到 weak 变弱时，社区感知方法整体 AUC 上升，且不同社区打分之间的相对优势会发生变化。

## SBM 上 AUC 最优的社区方法

- sbm_strong: M7 max C_i*C_j/E_ij with Louvain, AUC=0.1890
- sbm_medium: M4 max E_i*E_j/E_ij with Louvain, AUC=0.3391
- sbm_weak: M4 max E_i*E_j/E_ij with Louvain, AUC=0.4774

## 生成文件

- `sbm_community_methods_summary.csv`
- `all_networks_method_ranks.csv`
- `method_rank_summary.csv`
- `m8_vs_best_auc.csv`
- `sbm_community_methods_auc_trend.png`
- `sbm_community_methods_thresholds.png`
- `all_networks_auc_heatmap.png`
- `core_methods_auc_by_network.png`
