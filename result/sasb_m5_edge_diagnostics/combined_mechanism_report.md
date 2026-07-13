# SASB 与 M5 选边机制诊断报告

## 1. 诊断目标

本诊断围绕“少量结构化源点近似边介数为什么可能更适合网络瓦解”展开。主方法固定为 `M19-sampled-BE-fast / SASB`，不设计新算法。诊断脚本逐步重跑 M5 dynamic edge betweenness 与 SASB，并记录每一步被选中边的结构属性、即时 GCC 下降、组件数变化、bridge 标记、社区关系、端点度、共同邻居、embeddedness、完整边介数分数和采样边介数分数。

新增脚本：

- `scripts/diagnose_sasb_vs_m5_edge_choices.py`

当前实现来源：

- M5：`scripts/evaluate_heuristic_attacks.py::choose_betweenness_edge`
- SASB：`scripts/evaluate_m19_theory_calibrated.py` 中 `M19-sampled-BE-fast` / no-Delta fast 口径，即 `S_comm/S_boundary/S_local` 结构候选集 + sampled dependency 排序。

## 2. 已完成的诊断数据

| 结果集 | 网络范围 | 攻击预算 | 状态 | 主要路径 |
|---|---:|---:|---|---|
| full synthetic45 | 45/45 合成测试图 | 100% 删边 | M5 与 SASB 均 finished | `result/sasb_m5_edge_diagnostics/full_synthetic45/` |
| full real partial24 | realworld completed subset 中 24/28 图，当前最大到 `num_edges=6594` | 100% 删边 | M5 与 SASB 均 finished | `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/` |
| prefix50 real extended | realworld completed subset 中已完成/部分完成的 22 图 | 前 50 步或 timeout 前缀 | 20 个 M5 前缀完成，2 个 M5 timeout；21 个 SASB 前缀完成 | `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/` |

注意：完整 realworld completed subset 当前有 28 个 M5 completed 图。由于大图上的逐步 M5 full edge betweenness 代价很高，本轮已完成其中 24 个图的 100% 机制诊断，剩余 4 个为更大图。因此真实网络结论需要分为“24 图 full 证据”和“22 图 prefix50 扩展诊断证据”。

## 3. 逐步记录字段

`edge_step_diagnostics.csv` 已记录以下关键字段：

- `step`
- `method`
- `selected_edge`
- `gcc_before`
- `gcc_after`
- `delta_gcc`
- `num_components_before`
- `num_components_after`
- `is_bridge_before_removal`
- `is_inter_community_edge`
- `degree_u`
- `degree_v`
- `degree_product`
- `common_neighbors`
- `edge_embeddedness`
- `full_edge_betweenness_score`
- `sampled_betweenness_score`
- `attack_phase`

full synthetic45 的逐步记录为 50,610 行；full real partial24 的逐步记录覆盖 24 个真实网络的完整逐步选边过程。除特别说明外，诊断 Louvain 每步重算；`inf_power` 和 `ia_email_univ` 使用 `diagnostic_louvain_interval=25` 的 stale 诊断分区，以控制大图机制记录成本。

## 4. synthetic45 完整诊断结论

证据路径：

- `result/sasb_m5_edge_diagnostics/full_synthetic45/edge_step_diagnostics.csv`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/graph_method_summary.csv`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/network_diagnosis.csv`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/phase_auc_by_graph.csv`

总体结果：

| 方法 | mean normalized AUC | mean delta_gcc | bridge ratio | inter-community ratio | mean CN | mean embeddedness | mean runtime |
|---|---:|---:|---:|---:|---:|---:|---:|
| M5 | 0.355783 | 0.002308 | 0.318910 | 0.459018 | 0.299408 | 0.131099 | 25.30s |
| SASB | 0.342169 | 0.002308 | 0.318910 | 0.551142 | 0.299408 | 0.130869 | 17.06s |

逐网络胜负：

- SASB better：31/45
- SASB worse：14/45

按网络类型：

| 类型 | SASB better | SASB worse | mean(SASB-M5 AUC) |
|---|---:|---:|---:|
| BA | 8 | 1 | -0.017837 |
| ER | 4 | 3 | -0.011971 |
| SBM | 12 | 10 | -0.013635 |
| WS | 7 | 0 | -0.009763 |

阶段 AUC：

| 方法 | early | middle | late |
|---|---:|---:|---:|
| M5 | 0.734790 | 0.284400 | 0.048160 |
| SASB | 0.771828 | 0.227188 | 0.027491 |

解释：

- SASB 在 early 阶段平均 AUC 高于 M5，说明它在攻击早期并不总是比完整 M5 更激进。
- SASB 在 middle 和 late 阶段明显低于 M5，说明它的优势主要出现在网络已被部分扰动后：结构候选集和少量源点采样更容易转向跨社区、低冗余或局部割裂边。
- SASB 与 M5 的整体 bridge ratio 几乎相同，但 SASB 的 inter-community ratio 更高，说明差异不是简单“是否选桥”，而是更偏向社区边界上的路径瓶颈。

## 5. realworld completed 24 图完整诊断

证据路径：

- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/edge_step_diagnostics.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/graph_method_summary.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/network_diagnosis.csv`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/phase_auc_by_graph.csv`

覆盖 24 个真实网络：`bio_celegans`、`bio_celegans_dir`、`bio_celegansneural`、`bio_diseasome`、`bio_grid_mouse`、`bio_grid_plant`、`bio_sc_ts`、`ca_csphd`、`ca_netscience`、`football`、`ia_email_univ`、`ia_enron_only`、`ia_infect_dublin`、`ia_infect_hyper`、`ia_radoslaw_email`、`inf_euroroad`、`inf_power`、`inf_usair97`、`rt_retweet`、`rt_twitter_copen`、`soc_dolphins`、`soc_wiki_vote`、`web_edu`、`web_polblogs`。

总体结果：

| 方法 | mean normalized AUC | mean delta_gcc | bridge ratio | inter-community ratio | mean CN | mean embeddedness | mean runtime |
|---|---:|---:|---:|---:|---:|---:|---:|
| M5 | 0.204375 | 0.001188 | 0.382876 | 0.346077 | 2.721108 | 0.345160 | 612.52s |
| SASB | 0.219158 | 0.001188 | 0.382876 | 0.455046 | 2.721108 | 0.303843 | 148.17s |

逐网络胜负：

- SASB better：7/24
- SASB worse：16/24
- tie：1/24

阶段 AUC：

| 方法 | early | middle | late |
|---|---:|---:|---:|
| M5 | 0.422346 | 0.137781 | 0.052998 |
| SASB | 0.466360 | 0.149039 | 0.042077 |

解释：

- 在这 24 个真实图上，SASB 平均 AUC 仍弱于 M5，但平均运行时间约为 M5 的 24.2%。
- 与 synthetic45 不同，真实图中 SASB 的 early 和 middle 阶段平均 AUC 高于 M5；late 阶段低于 M5。
- SASB 的优势个例仍主要是小幅优势，机制诊断显示常与较低 embeddedness、社区边界偏好或更大的局部 GCC drop 相关。

## 6. realworld completed 扩展前缀诊断

证据路径：

- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/edge_step_diagnostics.csv`
- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/graph_method_summary.csv`
- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/network_diagnosis.csv`

该结果用于扩展真实网络结构观察，但由于多数网络只跑前 50 步，不能作为完整 AUC 结论。

prefix50 真实网络总体：

| 方法 | mean normalized AUC | mean delta_gcc | bridge ratio | inter-community ratio | mean CN | mean embeddedness |
|---|---:|---:|---:|---:|---:|---:|
| M5 | 0.775698 | 0.006472 | 0.154242 | 0.724848 | 5.291212 | 0.178273 |
| SASB | 0.780828 | 0.006339 | 0.121905 | 0.850476 | 4.987619 | 0.196626 |

解释：

- 前 50 步中，SASB 比 M5 更偏向 inter-community edge。
- SASB 的 bridge ratio 和 mean delta_gcc 略低于 M5，因此早期前缀上通常不能直接超过 M5。
- 这与 full synthetic45 的阶段结果一致：SASB 的优势更可能出现在 middle/late 阶段，而不是最早期。

## 7. 统计图路径

full synthetic45：

- `result/sasb_m5_edge_diagnostics/full_synthetic45/plots/selected_edge_delta_gcc_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/plots/bridge_selection_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/plots/inter_community_edge_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/plots/selected_edge_common_neighbors_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/plots/selected_edge_embeddedness_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_synthetic45/plots/phase_auc_comparison.png`

full real partial24：

- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/selected_edge_delta_gcc_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/bridge_selection_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/inter_community_edge_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/selected_edge_common_neighbors_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/selected_edge_embeddedness_distribution.png`
- `result/sasb_m5_edge_diagnostics/full_real_completed_edges_le1305/plots/phase_auc_comparison.png`

real prefix50：

- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/plots/selected_edge_delta_gcc_distribution.png`
- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/plots/bridge_selection_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/plots/inter_community_edge_ratio_by_phase.png`
- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/plots/selected_edge_common_neighbors_distribution.png`
- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/plots/selected_edge_embeddedness_distribution.png`
- `result/sasb_m5_edge_diagnostics/prefix50_synthetic45_real_completed/plots/phase_auc_comparison.png`

## 8. 回答机制问题

### SASB 为什么有时比 M5 更好？

当前 full synthetic45 结果表明，SASB 的优势主要不来自 early 阶段，而来自 middle/late 阶段。M5 在早期会严格追逐完整边介数最高的边；SASB 则通过结构候选集和少量源点采样，更频繁地把排序注意力放在社区边界、低冗余和局部瓶颈边上。当网络已经被部分扰动后，这种偏差可能更快触发 GCC 继续碎裂。

### SASB 选的边和 M5 有什么结构差异？

最稳定的差异是 inter-community edge ratio。full synthetic45 中，SASB 的 inter-community ratio 为 0.551142，高于 M5 的 0.459018；full real partial24 中，SASB 为 0.455046，高于 M5 的 0.346077；prefix50 real 中，SASB 为 0.850476，高于 M5 的 0.724848。bridge ratio 在 full synthetic45 和 full real partial24 中总体接近，说明 SASB 并不是简单“更多选桥”，而是更偏向社区边界上的 sampled shortest-path dependency 高分边。

### SASB 在哪些网络类型上更容易有效？

full synthetic45 中，SASB 在 BA、WS、ER、SBM 的平均 AUC 差值均为负，即总体优于 M5。其中 BA 为 -0.017837，WS 为 -0.009763，且 WS 为 7 胜 0 负。当前结果显示，SASB 对合成网络的中后期瓦解尤其有效。

full real partial24 中，SASB 在 7 个真实网络上优于 M5，但优势幅度总体较小。这说明真实网络上的有效性更依赖具体结构，尚不能泛化为真实网络全面优于 M5。

### SASB 在哪些网络类型上仍然不如 M5？

full real partial24 中，SASB 在 collaboration、infrastructure、contact、web 以及部分 social/communication 图上仍弱于 M5。prefix50 real 也显示，在真实网络早期阶段，SASB 的 mean delta_gcc 和 bridge ratio 往往低于 M5。因此，如果网络早期存在完整 M5 能稳定识别的高介数割裂边，SASB 的采样偏差可能反而损失 early collapse speed。

### 少量源点采样是简单误差，还是有益结构偏差？

当前证据支持一个克制结论：少量结构化源点采样不只是随机误差，它在部分网络和阶段上形成了有益结构偏差。这个偏差表现为更高的 inter-community edge ratio，以及在 synthetic45 的 middle/late 阶段更低的 AUC。但它不是无条件有益：真实网络小图和真实网络前缀结果显示，SASB 在 early 阶段经常弱于 M5，说明这种偏差只有在候选集召回、采样源点和网络瓦解阶段匹配时才转化为优势。

因此，论文中更稳妥的表述是：

> 初步机制诊断表明，SASB 的少量结构化源点采样并非简单近似误差。在合成网络的完整攻击过程中，它更倾向于选择社区边界上的路径瓶颈边，并在 middle/late 阶段获得比完整动态 edge betweenness 更低的 GCC-AUC。然而，在真实网络尤其是攻击早期，完整 M5 仍然更稳定。因此，SASB 应被定位为一种具有结构偏差的高效 sampled betweenness 瓦解方法，而不是对 M5 的无条件替代。

## 9. 尚未完成的部分

- 尚未完成全部 28 个 realworld completed 图的 100% 逐步机制诊断；当前已完成 24/28。
- 剩余 4 个大图为 `ia_fb_messages`、`bio_grid_worm`、`econ_mahindas`、`ca_grqc`。这些图的既有 M5 full run 已经从约 8584 秒到 42545 秒不等；逐步机制诊断还会额外计算 bridge、Louvain 社区和局部结构特征。
- 后续如需完整覆盖，应按网络分批后台运行，并优先复用当前脚本的断点缓存机制。
