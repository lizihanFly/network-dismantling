# 结构化少源点采样偏差审计报告

## 1. 研究问题
本审计只分析已有结果，检验 SASB / M19-sampled-BE-fast 是否相对 M5 产生系统性结构选边偏差，以及这种偏差是否在部分网络结构和攻击阶段与更快 GCC 瓦解相对应。

## 2. 方法定义
- SASB / M19-sampled-BE-fast: 结构候选边集合 + k=32 结构化源点采样 + sampled dependency 排序。
- fixed_k32: 每一步固定 32 个源点的少源点动态基线；本报告只引用已有 baseline，不新增实验。
- M5: 完整动态 edge betweenness，是强效果和高成本参考基线。
- ACES: 仅作为静态排序相似度参考，不作为本次动态瓦解主方法。

## 3. 数据和文件范围
- synthetic45: full diagnostic 覆盖 45/45 张图，M5 与 SASB 均完成。
- realworld_completed: 当前 full diagnostic 覆盖 24/28 张真实图，M5 与 SASB 均完成。
- 剩余未进入当前 full diagnostic 的真实网络: ia_fb_messages, bio_grid_worm, econ_mahindas, ca_grqc。
- 本次未运行任何大规模新实验；所有统计来自现有 CSV 和曲线文件。
- 任务指定输入文件均存在。

## 4. synthetic45 结果
- normalized GCC-AUC: SASB-M5 均值差 -0.0136; SASB better 31/45, worse 14/45。
- inter-community ratio: M5 0.4590, SASB 0.5511, 差值 0.0921。
- mean embeddedness: M5 0.1311, SASB 0.1309, 差值 -0.0002。
- P(delta_gcc > 0): M5 0.0877, SASB 0.0618, 差值 -0.0259。

## 5. realworld 24 图结果
- normalized GCC-AUC: SASB-M5 均值差 0.0148; SASB better 7/24, worse 16/24。
- inter-community ratio: M5 0.3461, SASB 0.4550, 差值 0.1090。
- mean embeddedness: M5 0.3452, SASB 0.3038, 差值 -0.0413。
- P(delta_gcc > 0): M5 0.0637, SASB 0.0460, 差值 -0.0177。

## 6. SASB 与 M5 的结构选边差异
全程 bridge ratio 只作为一致性检查，因为完整删边过程中 bridge 选择总量可能受边集合和删除顺序的共同约束，不能单独证明 M5 与 SASB 的机制差异；正式比较应看 early/middle/late 分阶段指标。
- synthetic45: bridge ratio 差值 0.0000; common neighbors 差值 0.0000; min endpoint degree 差值 0.1811。
- realworld_completed_24of28: bridge ratio 差值 0.0000; common neighbors 差值 0.0000; min endpoint degree 差值 1.0811。

## 7. early/middle/late 阶段差异
- synthetic45:
  - early: phase AUC SASB-M5 0.0370; inter-community 差值 0.1949; P(delta_gcc>0) 差值 -0.0463。
  - middle: phase AUC SASB-M5 -0.0572; inter-community 差值 0.1024; P(delta_gcc>0) 差值 -0.0146。
  - late: phase AUC SASB-M5 -0.0207; inter-community 差值 -0.0214; P(delta_gcc>0) 差值 -0.0167。
- realworld_completed_24of28:
  - early: phase AUC SASB-M5 0.0440; inter-community 差值 0.1702; P(delta_gcc>0) 差值 -0.0300。
  - middle: phase AUC SASB-M5 0.0113; inter-community 差值 0.1452; P(delta_gcc>0) 差值 -0.0162。
  - late: phase AUC SASB-M5 -0.0109; inter-community 差值 0.0115; P(delta_gcc>0) 差值 -0.0068。

## 8. SASB better/worse 网络结构差异
- Spearman modularity_vs_sasb_minus_m5_normalized_auc: -0.2035
- Spearman degree_cv_vs_sasb_minus_m5_normalized_auc: 0.1840
- Spearman average_edge_embeddedness_vs_sasb_minus_m5_normalized_auc: 0.1400
- Spearman inter_community_edge_ratio_vs_sasb_minus_m5_normalized_auc: 0.1383
- Spearman clustering_coefficient_vs_sasb_minus_m5_normalized_auc: 0.0922
这些相关性是探索性分析，不是因果证明；真实网络样本量只有 24 张，不能外推为完整 realworld 结论。

## 9. source bias 与 candidate bias 的可识别性
当前 SASB 同时包含结构化候选边集合和结构化源点采样。已有机制日志不能单独固定 candidate set 后只替换 source policy，因此不能证明全部收益主要来自源点选择，也不能把 SASB 整体效果完全归因于 source bias。

## 10. 关键数据缺失
- edge-level 规范字段均能在当前 M5/SASB 机制诊断 CSV 中映射。
- 当前没有完整候选边排序，因此不计算 top-1 recall、NDCG、Spearman 或完整 candidate rank。
- selected edge 分数仅代表被选边的记录，不能当作完整候选边排序。
- mechanism diagnostic runtime 含诊断记录开销，不能与普通 baseline runtime 直接混用。

## 11. 当前证据边界
已有证据可以支持 SASB 存在结构偏差，并且这种偏差在部分网络和阶段与 GCC-AUC 或 immediate GCC drop 改善相伴。但真实网络只覆盖 24/28，且 candidate/source bias 尚未解耦，所以不能写成 SASB 在所有真实网络上优于 M5。

## 12. 下一阶段 P1 实验设计
- 比较方法: M5, fixed_k32, SASB structured-source, SASB uniform-random-source, SASB degree-community-matched-source。
- 固定 candidate set 相同、source budget=32、random seeds 相同、动态更新 GCC。
- synthetic45 使用 remove_ratio=1.0；realworld 使用当前 24/28 completed subset。
- 只有 structured-source 同时优于 uniform-random-source 和 degree-community-matched-source，并改善 GCC-AUC、保持结构偏差方向稳定且 runtime 可接受，才支持核心源点采样假设。
- 如果只提高 top1 agreement、NDCG 或 Spearman 而不改善 GCC-AUC，只能说明更像 M5，不能说明更适合网络瓦解。

## 明确结论
结论 B：已有证据支持存在结构偏差，但目前不能证明收益主要来自源点选择。

## 生成文件
- result/structure_bias_audit/file_inventory.csv
- result/structure_bias_audit/field_availability.csv
- result/structure_bias_audit/structure_bias_summary.csv
- result/structure_bias_audit/phase_bias_summary.csv
- result/structure_bias_audit/phase_bias_by_graph.csv
- result/structure_bias_audit/outcome_structure_summary.csv
- result/structure_bias_audit/budget_gcc_summary.csv
- result/structure_bias_audit/plots/common_neighbors_by_method_phase.png
- result/structure_bias_audit/plots/embeddedness_by_method_phase.png
- result/structure_bias_audit/plots/inter_community_ratio_by_method_phase.png
- result/structure_bias_audit/plots/min_endpoint_degree_by_method_phase.png
- result/structure_bias_audit/plots/phase_auc_comparison.png
- result/structure_bias_audit/plots/positive_gcc_drop_probability.png
- result/structure_bias_audit/plots/sasb_m5_auc_difference_vs_bridge_ratio.png
- result/structure_bias_audit/plots/sasb_m5_auc_difference_vs_core2_ratio.png
- result/structure_bias_audit/plots/sasb_m5_auc_difference_vs_degree_cv.png
