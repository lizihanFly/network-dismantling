# SASB 算法总结与实验收束

## 1. 研究问题

本报告收束当前仓库中 SASB 的算法定义、证据链和论文表述边界。核心问题是：SASB 是否能作为结构感知的 sampled betweenness 网络瓦解算法写入论文，以及已有 P1/P2/P2b 证据分别能支持什么、不能支持什么。

本次任务只整理已有内容，不运行新实验，不启动 P2b 300-run pilot，不修改 P1/P2 正式结果，不提交或推送 GitHub。

## 2. SASB 算法定义

仓库当前论文级名称应统一为 **SASB**。baseline 表和历史代码中仍出现 `M19-sampled-BE-fast` 或 `M19 structure-aware sampled community betweenness attack`，可在论文中解释为 SASB 的实现族，但正文应避免混用 SABA。

SASB 的输入是当前图、候选边生成规则、源点预算、源点策略、随机种子和停止预算；输出是边删除序列、GCC trajectory、normalized GCC-AUC、GCC@5/10/20/40、机制指标和成本指标。

## 3. 数学原理

完整边介数：

$$
B(e)=\sum_{\substack{s,t\in V\\s\ne t}}\frac{\sigma_{st}(e)}{\sigma_{st}}.
$$

源点采样近似：

$$
\widehat{B}_{\mathcal{S}}(e)=\frac{|V|}{|\mathcal{S}|}\sum_{s\in\mathcal{S}}\delta_s(e).
$$

单源点依赖量：

$$
\delta_s(e)=\sum_{t\in V\setminus\{s\}}\frac{\sigma_{st}(e)}{\sigma_{st}}.
$$

候选集约束：

$$
e_t=\underset{e\in C_t(G_t)}{\arg\max}\;\widehat{B}_{\mathcal{S}_t}(e).
$$

图状态更新：

$$
G_{t+1}=G_t\setminus\{e_t\}.
$$

源点采样引入估计方差与系统性欠采样误差；结构化源点可能引入社区边界、高度节点或低嵌入边偏差；候选集是硬约束，直接排除 `C_t(G_t)` 外的边。SASB 不是传统 SGD、mini-batch 或正则化，因为它没有可微目标函数、梯度更新或参数学习过程。

## 4. 核心代码结构

| file | function | role |
| --- | --- | --- |
| scripts/evaluate_m19_theory_calibrated.py | adaptive_k | adaptive candidate breadth |
| scripts/evaluate_m19_theory_calibrated.py | candidate_features | SASB candidate generation |
| scripts/evaluate_m18_candidate.py | select_m19_sources | structured source selection |
| scripts/evaluate_m18_candidate.py | sampled_candidate_edge_dependencies | sampled shortest-path dependency |
| scripts/evaluate_m19_theory_calibrated.py | choose_theory_or_calibrated_edge | candidate scoring and edge selection |
| scripts/evaluate_m19_theory_calibrated.py | simulate_attack | dynamic edge removal and GCC metrics |
| scripts/evaluate_source_policy_ablation.py | choose_policy_edge | P1 fixed-candidate source-policy selection |
| scripts/evaluate_candidate_policy_ablation.py | sasb/random_size_matched/structure_matched candidates | P2 candidate-policy generators |
| scripts/evaluate_candidate_policy_ablation_p2b.py | dry_run / one_step_intervention / frozen_source_trajectory | P2b design and planned causal isolation |

调用关系：Input graph -> current GCC/preprocessing -> adaptive k -> candidate generation -> source selection -> sampled dependency scoring -> edge selection -> remove edge -> recompute GCC -> repeat -> metrics/output。

决定科学机制的是 candidate generation、structured source selection、sampled dependency scoring 和动态 edge selection；写 CSV、路径管理、报告和绘图函数主要是工程封装。

## 5. 数据集

| dataset | network_count | source_or_generation | n_min | n_max | m_min | m_max | avg_degree_min | avg_degree_max | community_info |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic45 | 45 | baseline_synthetic45_per_graph.csv | 65 | 240 | 121 | 1175 | 3.723 | 10.495 | recorded |
| realworld_completed | 24 current completed / 28 metadata inventory | baseline_realworld_m5_completed_per_graph.csv + completed-subset diagnostics | 62 | 1025 | 117 | 2211 | 2.035 | 66.0 | 仓库中未记录 |

`synthetic45` 是正式 synthetic test 集；`realworld_completed` 的元数据清单覆盖 28 张真实网络；当前用于正式机制/P1/P2结论的是 24/28 completed subset，未完成图不能被自动纳入最终真实网络结论。缺失的图级来源细节在报告中记为“仓库中未记录”，不外推。

## 6. 实验设计演进

阶段 A：SASB 与 M5/M7/M12、degree product、static edge betweenness、static community bridge 等仓库真实有结果的 baseline 比较，主要看 normalized GCC-AUC、GCC trajectory 和 runtime。

阶段 B：P1 source-policy ablation 固定 candidate builder、source budget、seed schedule 和动态 GCC 测量，只改变 source policy：`SASB-structured`、`SASB-random`、`SASB-matched`。

阶段 C：P2 candidate-policy ablation 固定 source policy 规则和动态 workflow，改变 candidate policy：`SASB-candidate`、`Random-size-matched-candidate`、`Structure-matched-candidate`。P2 仍存在 source-set trajectory confounding。

阶段 D：P2b 当前只有 dry-run 和 pilot design；one-step intervention 与 frozen-source trajectory 还没有正式运行。

## 7. 与标准启发式算法比较

| method | principle | uses_full_graph_info | source_sampling | candidate_set | dynamic_update | main_cost |
| --- | --- | --- | --- | --- | --- | --- |
| SASB | sampled dependency over SASB candidate set | partial current graph | yes | yes | yes | candidate generation + sampled paths |
| M5 dynamic edge betweenness | exact edge betweenness on current GCC | yes | no | no | yes | full betweenness recomputation |
| M7 dynamic community bridge | dynamic community bridge score | community partition | no | implicit | yes | Louvain/community scoring |
| M12 stale community attack | stale community attack | initial/stale partition | no | implicit | partly | low runtime |
| Degree product | endpoint degree product | local degree | no | no | yes | low |
| Static edge betweenness | initial edge betweenness order | yes initial graph | no | no | no | one full betweenness pass |
| Static community bridge | static community bridge order | initial community | no | implicit | no | low/moderate |

| dataset_group | method_canon | networks | mean_normalized_auc | std_normalized_auc | mean_final_gcc | mean_runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| realworld_completed | M12 stale community attack | 28 | 0.371794 | 0.274034 | 0.003619 | 99.459 |
| realworld_completed | M5 dynamic edge betweenness | 28 | 0.203664 | 0.165807 | 0.003619 | 4297.176 |
| realworld_completed | SASB | 28 | 0.229407 | 0.190251 | 0.003619 | 234.052 |
| realworld_completed | Static community bridge | 28 | 0.262179 | 0.158941 | 0.00452 | 6.308 |
| realworld_completed | Static edge betweenness | 28 | 0.407809 | 0.213544 | 0.004437 | 8.705 |
| synthetic45 | M12 stale community attack | 45 | 0.386083 | 0.143173 | 0.00692 | 2.403 |
| synthetic45 | M5 dynamic edge betweenness | 45 | 0.355794 | 0.134196 | 0.00692 | 22.296 |
| synthetic45 | Static community bridge | 45 | 0.467465 | 0.136688 | 0.00692 | 1.531 |
| synthetic45 | Static edge betweenness | 45 | 0.651171 | 0.162646 | 0.00692 | 1.793 |

AUC 越低表示瓦解越快。synthetic45 上 SASB 平均 AUC 低于 M5/M7/M12；realworld completed subset 上 SASB 平均 AUC 未超过 M5，但优于 M7/M12，并有明显 runtime 优势。

## 8. P1 源点策略实验

P1 正式结果：`result/source_policy_ablation_p1/formal_results.csv`，共 207 行。

| dataset | method | n | mean_auc | runtime | source_traversal |
| --- | --- | --- | --- | --- | --- |
| realworld_completed | SASB-matched | 24 | 0.420829 | 140.797989 | 48150.125 |
| realworld_completed | SASB-random | 24 | 0.419362 | 123.214157 | 48182.375 |
| realworld_completed | SASB-structured | 24 | 0.420669 | 126.409427 | 48089.375 |
| synthetic45 | SASB-matched | 45 | 0.629307 | 12.205925 | 14178.577778 |
| synthetic45 | SASB-random | 45 | 0.627637 | 10.918098 | 14175.066667 |
| synthetic45 | SASB-structured | 45 | 0.630081 | 11.204774 | 14185.555556 |

核心 paired result：

- realworld_completed structured - matched: mean=-0.000160, CI=[-0.004517, 0.004198], wins/losses/ties=14/10/0, n=24
- synthetic45 structured - matched: mean=0.000774, CI=[-0.003706, 0.005254], wins/losses/ties=25/20/0, n=45

P1 不足以支持稳定 source-policy bias；structured-vs-random 不能单独作为因果证据，必须优先看 structured-vs-matched。

## 9. P2 候选策略实验

P2 输出：`result/candidate_policy_ablation_p2/formal_results.csv`，共 207 行；报告标题标注为 exploratory。

| dataset | method | n | mean_auc | runtime | source_traversal |
| --- | --- | --- | --- | --- | --- |
| realworld_completed | Random-size-matched-candidate | 24 | 0.424498 | 141.84593 | 52881.0 |
| realworld_completed | SASB-candidate | 24 | 0.420669 | 134.075379 | 48089.375 |
| realworld_completed | Structure-matched-candidate | 24 | 0.438821 | 428.534695 | 49227.291667 |
| synthetic45 | Random-size-matched-candidate | 45 | 0.605076 | 13.813414 | 14966.066667 |
| synthetic45 | SASB-candidate | 45 | 0.630081 | 13.572493 | 14185.555556 |
| synthetic45 | Structure-matched-candidate | 45 | 0.626577 | 24.537745 | 14435.822222 |

核心 paired result：

- realworld_completed SASB - structure-matched: mean=-0.018152, CI=[-0.037552, 0.001248], wins/losses/ties=16/8/0, n=24
- synthetic45 SASB - structure-matched: mean=0.003504, CI=[-0.006192, 0.013201], wins/losses/ties=29/16/0, n=45

P2 不支持 universal candidate bias。structure-matched 只匹配粗粒度结构特征，不代表候选边完全相同。

## 10. P2b 当前状态

P2b 当前是 dry-run/pilot design。`p2b_dry_run_report.md` 记录选择 20 图、5 seeds、计划 300 one-step rows 和 300 frozen-source trajectory runs，但 formal pilot execution 为 `not started`。

## 11. 主要实验结果

| result_set | path | evidence_status |
| --- | --- | --- |
| P1 source-policy ablation | result/source_policy_ablation_p1/formal_results.csv | formal experiment; fixed candidate builder/source budget/seed schedule |
| P2 candidate-policy ablation | result/candidate_policy_ablation_p2/formal_results.csv | completed 207 runs but report title is exploratory; one formal seed and trajectory confounding remain |
| synthetic45 baseline | result/paper_experiments/baselines/baseline_synthetic45_summary.csv | formal baseline summary for 45 synthetic graphs |
| realworld completed subset baseline | result/paper_experiments/baselines/baseline_realworld_m5_completed_per_graph.csv | stage-completed 24/28 real networks; not final full realworld |
| SASB/M5 synthetic45 diagnostics | result/sasb_m5_edge_diagnostics/full_synthetic45/graph_method_summary.csv | formal mechanism diagnostic for M5 vs SASB |
| SASB/M5 realworld24 diagnostics | result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/graph_method_summary.csv | completed-subset mechanism diagnostic |

当前最可靠结论：SASB 在 synthetic45 上显示出比 M5 更低 AUC 与更快 runtime；在真实网络 completed subset 上未超过 M5，但优于 M7/M12 且显著节省 runtime。P1/P2 对机制只提供弱或方向性证据。

## 12. 机制解释

现有证据更适合写成“条件性结构偏差”和“网络拓扑依赖”。SASB 效果可能来自 source-policy 结构偏差和 candidate-set 结构偏差叠加；P1 对 source-policy 的支持很弱，P2 对 candidate-policy 尚未完成因果隔离。

## 13. 计算成本

真实成本应报告 `runtime_seconds` 和 `true_source_traversal_count`。SASB 成本主要来自候选生成、Louvain/社区处理与 sampled shortest-path dependency；candidate 数量或 theoretical effective cost 不能替代真实运行成本。

## 14. 统计可靠性

P1 是正式实验但 effect 小、CI 跨 0。P2 只有一个 formal seed，并且 source set 随动态轨迹重新计算。realworld completed subset 是 24/28 阶段性结果。first_positive_drop_step 跨图比较应使用归一化版本。

## 15. 当前可以写入论文的结论

1. SASB 是带结构化源点采样和候选集硬约束的 sampled betweenness-like 动态贪心边删除算法。
2. synthetic45 上 SASB 当前优于 M5/M7/M12 的平均 normalized GCC-AUC，并相对 M5 更快。
3. realworld completed subset 上 SASB 未超过 M5，但优于 M7/M12，并显著降低 runtime。
4. source-policy 与 candidate-policy 机制证据均具有条件性和数据集依赖性。

## 16. 当前不能写入论文的结论

不能声称 SASB 普遍优于所有算法；不能声称 SASB 已被证明普遍有效；不能声称 SASB 一定降低介数估计误差；不能声称 P2b 已证明 candidate bias；不能把 smoke/dry-run/探索实验当作正式证据。

## 17. 开放问题

需要完成 realworld remaining graphs；需要运行 P2b 因果隔离；需要进一步解释 topology features 如何决定 SASB 有效或失效；需要拆分候选生成成本与真实瓦解成本。

## 18. 下一步实验计划

建议在用户确认后运行 P2b pilot，优先使用 dry-run 已选 20 图和 5 seeds，执行 one-step intervention 与 frozen-source trajectory，预注册 normalized GCC-AUC、归一化 first positive drop、positive delta-GCC rate、conditional mean delta-GCC、runtime 和 true source traversal count。

## 19. 论文中推荐使用的算法表述

SASB is a structure-aware sampled betweenness edge-dismantling strategy. At each dynamic attack step, it restricts edge selection to a structurally generated candidate set and estimates candidate edge dependency from a small set of structured source nodes. The selected edge maximizes sampled dependency within the candidate set, after which the graph state and GCC trajectory are updated.

中文表述：SASB 是一种结构感知的采样边介数网络瓦解方法。它在每个动态删除步骤中生成结构化候选边集合，从结构化源点估计候选边 shortest-path dependency，并在候选集内贪心删除估计分数最高的边。

## 附录：生成文件

- `result/algorithm_summary/SASB_ALGORITHM_SUMMARY.md`
- `result/algorithm_summary/file_inventory.csv`
- `result/algorithm_summary/dataset_summary.csv`
- `result/algorithm_summary/core_function_inventory.csv`
- `result/algorithm_summary/heuristic_method_table.csv`
- `result/algorithm_summary/baseline_method_summary.csv`
- `result/algorithm_summary/sasb_m5_paired_differences.csv`
- `result/algorithm_summary/evidence_level_table.csv`

图表：
- `result/algorithm_summary/plots/01_baseline_normalized_auc_comparison.png`
- `result/algorithm_summary/plots/02_auc_distribution_by_dataset.png`
- `result/algorithm_summary/plots/03_gcc_decay_curves_m5_sasb.png`
- `result/algorithm_summary/plots/04_sasb_m5_paired_auc_difference.png`
- `result/algorithm_summary/plots/05_runtime_comparison.png`
- `result/algorithm_summary/plots/06_source_traversal_comparison.png`
- `result/algorithm_summary/plots/07_p1_source_policy_auc.png`
- `result/algorithm_summary/plots/08_p2_candidate_policy_auc.png`
- `result/algorithm_summary/plots/09_p1_p2_mechanism_metrics.png`
- `result/algorithm_summary/plots/10_p2b_design_not_run.png`
- `result/algorithm_summary/plots/existing_baseline_auc_runtime.png`
- `result/algorithm_summary/plots/existing_baseline_average_gcc_curve.png`
