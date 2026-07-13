# PROJECT LATEST PROGRESS AND NEXT PLAN

Generated: 2026-06-20. Read-only survey of v3, v4, v5, CLAUDE.md, and reports. No files modified.

---

## 1. 项目总体目标

边删除网络瓦解（edge-removal network dismantling）：每一步选择一条边删除，让 GCC（最大连通分量）尽快缩小。核心评价指标是 **归一化 GCC-AUC**（越低越好），运行时间单独报告。

当前项目有两条方向：

1. **SASB / M19-sampled-BE-fast（投稿主线）**：结构候选集 + 采样边介数排序，不依赖手工权重和 Δ_GCC。在 synthetic45 上已超过 M5；在真实网络 28 图上以约 1/15 的时间逼近 M5。这是当前唯一达投稿状态的方法。

2. **AP-M5-HIR 源点预算路由系列（探索前沿）**：用自适应/神经/专家路由替代固定源点预算，在不改变最终删边规则的前提下降低每步计算成本。包含 v1→v2→v3→v4→v5 的演进链。**尚未有任何版本达到扩展验收标准。**

---

## 2. 方法演进全景与当前状态

### 2.1 已投稿/可投稿（SASB 家族）

| 方法 | 状态 | 结论 |
|---|---|---|
| M5 (dynamic edge betweenness) | 28/31 真实网络完成 | 效果上限基线，极慢（真实网络总时间 120321s） |
| M7 (community size/pair) | 31/31 真实网络完成 | 最稳定的社区启发式基线 |
| M12 (stale community CEP-lite) | 31/31 完成 | 速度基线，效果弱 |
| M19-original (α/β/γ/δ 手工权重) | 31/31 完成 | 工程强基线 |
| M19-no-bridge | 31/31 完成 | 速度版候选 |
| **SASB (M19-sampled-BE-fast)** | **28 图 M5 subset + 31 图 completion** | **投稿主方法。synthetic45 超 M5；真实网络 14.89x 加速，AUC 差仅 +0.020** |

### 2.2 AP-M5-HIR 系列（所有版本均未通过验收）

| 版本 | 全称 | 核心创新 | 状态 |
|---|---|---|---|
| v1 (`ap_m5_hir.py`) | basic pivot sampling | 结构化四类源节点采样 | smoke 完成，被 v2 取代 |
| v2 (`ap_m5_hir_v2_confidence.py`) | + confidence intervals | CI-based source budget | smoke 完成，被 v3 取代 |
| **v3** (`ap_m5_hir_v3_candidate_ci.py`) | + candidate CI + pairwise gap stop | 候选集 CI + top-1 vs top-2 gap stopping | **6 图 smoke。AUC ✅ Speed ✅，但 CI-stop ❌ (0.6%)，source reduction ❌ (k/n=0.986)，推荐不扩展到 synthetic45** |
| v3-coverage-only | v3 消融 | 仅社区覆盖路由 | 消融对照，不进入主线 |
| **v4** (`ap_m5_hir_v4_neural_sampling.py`) | neural budget + router | 神经网络预测 k_ratio + 源类型配比 | **6 图 full_eval。所有模式均未通过三项验收。Router acc=36.4%。结论：尚未 work** |
| **v5** (`experiments/v5_expert_router/`) | expert routing only | 学习从 5 个固定专家中选最优 | **3 图 smoke。V5 IS NOT SUCCESSFUL。路由器 100% 预测 balanced，AUC 与 static-balanced 完全相同** |

---

## 3. 各版本详细状态

### 3.1 v3 (AP-M5-HIR-v3-candidate-ci)

**验收标准与结果**（6 图 smoke，正式配置 `epsilon=0.15_default`）：

| 标准 | 阈值 | 实际 | 通过？ |
|---|---|---|---|
| AUC gap vs M5 | < 0.005 | 0.004534 | ✅ |
| Speedup vs M5 | > 1.5x | 3.37x | ✅ |
| CI early-stop 率 | > 20% | **0.6%** | ❌ |
| mean(k_final/n_t) | < 0.7 | **0.986** | ❌ |
| Louvain 重算比例 | < 20% | **44.8%** | ❌ |
| 候选覆盖率 | > 85% | **83.6%** | ❌ |
| 建议扩展到 synthetic45 | — | — | **不推荐** |

**核心问题**：Pairwise CI 几乎从不提前停止（0.6%）。速度提升来自 `epsilon=0.15` 产生的较小统计 kmax，而不是 CI 证书。source reduction 本质上不存在（k/n=0.986）。在小 GCC 阶段（晚期攻击）source 数接近全枚举，掩盖了大 GCC 阶段的节省。

### 3.2 v4 (AP-M5-HIR-v4-neural)

**验收标准与结果**（6 图 full_eval，最佳模式 `budget-risk-ci`）：

| 标准 | 阈值 | 实际 | 通过？ |
|---|---|---|---|
| mean \|AUC gap\| vs M5 | < 0.005 | **0.0187** | ❌ |
| Runtime faster than v3 | — | **0.86x** (slower) | ❌ |
| Source reduction vs v3 | > 15% | **13.6%** | ❌ |

**训练数据**：900 样本，30 图，72 特征。训练/测试按图划分。

**模型表现**：
- Budget predictor (LightGBM): R²=0.9845, calibrated MAE=0.024。这是 v4 中唯一有实用价值的部分。
- Router classifier (8-class): accuracy=**36.4%**, top-2 accuracy=51.8%。远低于可用阈值。
- Router 几乎总是预测 majority class。

**所有 8 个模式的验收结果**：

```
mean_abs_auc_gap_lt_0.005   method                               runtime_faster_than_v3   source_reduction_gt_15pct
                    False   AP-M5-HIR-v4-neural-budget-only                    False                       True
                    False   AP-M5-HIR-v4-neural-budget-risk-ci                 False                      False
                    False   AP-M5-HIR-v4-neural-budget-safe                    False                       True
                    False   AP-M5-HIR-v4-neural-budget-soft-ci                 False                      False
```

**结论**：v4 未 work。Budget 模型有潜力但受限于 router 和 CI 机制。source reduction 最高仅 15.7%（budget-only），不足以弥补 AUC 退化。

### 3.3 v5 (ExpertRouter)

**目标**：暂停 v4 的 source budget 学习，只学习"当前网络状态应该用哪个源专家画像"。

**五大专家画像**：

| 专家 | boundary | core | community | random | 适用场景 |
|---|---|---|---|---|---|
| community_boundary | 0.50 | 0.10 | 0.30 | 0.10 | 社区边界密集 |
| hub_core | 0.20 | 0.55 | 0.10 | 0.15 | 核心枢纽节点 |
| bridge_fragility | 0.45 | 0.20 | 0.10 | 0.25 | 脆弱桥接边 |
| dense_random | 0.20 | 0.20 | 0.10 | 0.50 | 高随机探索 |
| balanced | 0.25 | 0.25 | 0.25 | 0.25 | 均衡（fallback） |

**Oracle 机制**：对每个 (graph, step)，用 k_probe=min(n_t, ceil(0.3×n_t)) 个源评估所有 5 个专家，计算 loss = 1.0×I(sampled_top1≠full_m5_top1) + 0.5×|gcc_after_diff|。最低 loss 专家为 oracle_expert。

**严格过滤 (strict-oracle)**：丢弃所有 5 个专家 loss 相同的行（零信号行）。

**实验结果（3 图 smoke）**：

| 指标 | 过滤前 | 严格过滤后 |
|---|---|---|
| 样本数 | 15 | **8** |
| balanced 占比 | 7/9 (78%) | 3/8 (38%) |
| bridge_fragility 占比 | 1/9 (11%) | 3/8 (38%) |
| balanced 不在最优集中的行 | — | **5/8 (62%)** |
| Oracle tie rate (≥2 experts at min loss) | — | **87.5% (7/8)** |
| Unique winner rate | — | **12.5% (1/8)** |

**路由器训练结果（5-class）**：

| 指标 | 值 |
|---|---|
| Accuracy | 0.250 |
| Macro F1 | 0.133 |
| Mean Regret | 0.750 |
| Non-balanced predictions during attack | **0/15 (0%)** |
| AUC improvement over static-balanced | **0** |

**关键发现**：
- ✅ **Oracle 信号存在**：严格过滤后，62% 的行中 balanced 不在最优专家集合中。非 balanced 专家可以在这些行实现 loss=0（匹配 M5 top-1）。
- ❌ **路由器无法学习**：100% 预测 balanced。8 个样本跨 3 张图对 5-class 分类器来说数量严重不足。
- ❌ **Oracle tie rate 87.5%**：绝大多数行有 2-4 个专家并列最低 loss。这意味着 5 个专家的区分度本身不够。
- ❌ **V5 IS NOT SUCCESSFUL**（v5 报告中明确写明）。

---

## 4. 当前阻塞问题汇总

### 4.1 核心机制阻塞（横跨 v3/v4/v5）

| # | 问题 | 影响范围 | 严重程度 |
|---|---|---|---|
| 1 | **Pairwise CI 几乎从不提前停止**（v3 CI-stop=0.6%） | v3/v5 的加速逻辑基础不成立 | 🔴 致命 |
| 2 | **Source budget 无法有效降低**（v3 k/n=0.986, v4 最多节省 15.7%） | 所有 source-reduction 方向 | 🔴 致命 |
| 3 | **小 GCC 阶段 source 接近全枚举掩盖大 GCC 节省** | v3/v4 的 mean k/n 指标 | 🟡 严重 |
| 4 | **Oracle 标签区分度不够**（v5 tie rate=87.5%） | v5 expert routing 方向 | 🟡 严重 |
| 5 | **训练数据集过小**（v4: 900 样本, v5: 8 样本） | v4/v5 学习可行性 | 🟡 严重 |

### 4.2 工程/代码阻塞

| # | 问题 | 影响 |
|---|---|---|
| 6 | v3/v4/v5 代码分离但 v4/v5 紧耦合 v3 实现 | 修改 v3 可能破坏 v4/v5 |
| 7 | 缺少统一的实验追踪 | 难以跨版本比较 |
| 8 | 无单元测试 | 重构风险高 |
| 9 | `result/` vs `results/` 两个输出根目录并存 | 混淆 |

---

## 5. 可投稿资产清单

以下结果已达到论文投稿质量：

| 资产 | 位置 | 用途 |
|---|---|---|
| SASB synthetic45 完整结果 | `result/m19_sampled_be_fast_report_20260610/` | Table 1: synthetic 主比较 |
| SASB realworld M5-completed 28 图 | `result/paper_experiments/m5_completed_subset/` | Table 2: realworld 主比较 |
| Realworld31 completion | `result/next_stage_fair_comparison/realworld_completion_30plus_*` | Table 3: 可扩展方法比较 |
| 13 图 classic baseline | `result/paper_experiments/baselines/` | Table 4: 经典基线 |
| Δ_GCC + candidate-source ablation | `result/paper_experiments/ablation/` | Figure: 消融 |
| Holm-Bonferroni 统计检验 | `result/paper_experiments/statistical_tests/` | Table: 显著性 |
| Candidate miss vs ranking error | `result/next_stage_fair_comparison/realworld_candidate_recall_*` | Figure: 机制解释 |
| Paper outline | `result/paper_experiments/paper_outline.md` | 论文结构 |

---

## 6. 下一步实现计划

### 6.1 总体判断

**v3/v4/v5 三条线均未达到扩展验收标准。** 根本原因是 CI early-stop 几乎不触发（0.6%）和 source reduction 不显著（k/n 始终接近 1.0）。

在投入更多计算资源扩展 v4/v5 之前，需要首先解决**底层机制问题**（CI 和 source reduction），否则扩展只会产生更多"不 work"的结果。

### 6.2 优先级 P0（立即执行）：机制诊断与修复

#### P0-1: 诊断 CI early-stop 为何不触发

当前 v3 pairwise CI early-stop 仅 0.6%。需要理解原因：

- **假设 A**：候选集 top-1 和 top-2 的 sampled dependency 差距本身就小（信号弱），CI radius 即使在较大 k 下也无法覆盖这个 gap。
- **假设 B**：per-source dependency 方差大，CI radius 收敛慢。
- **假设 C**：ε=0.15 的 kmax 本身就太小，CI 还没来得及触发就到达上限。

**具体操作**：
```
1. 在现有的 v3 trace 数据（result/node_approx_betweenness/ap_m5_hir_v3_candidate_ci/ap_m5_hir_v3_k_trace.csv，10346 步）中，提取以下分布：
   - top-1 vs top-2 raw gap 分布（分 n_t 桶）
   - pairwise CI radius 随 k 增长的曲线
   - gap/radius ratio 分布
   - 不同停止原因的分布和 k 值
2. 生成诊断图：gap vs k, radius vs k, gap/radius histogram
3. 写诊断报告（1 页），明确 CI 不触发的根因。
```

相关代码：`scripts/visualize_v3_k_vs_gcc.py`（已有框架，可能需要扩展）。

#### P0-2: 实验"大 ε"或"adaptive ε"能否触发 source reduction

当前 ε=0.15 产生 kmax ≈ log(2|C|/δ)/(2ε²)。如果 ε=0.30，kmax 约为原来的 1/4，source reduction 会更显著——代价是 AUC 退化。

**具体操作**：
```
在 3 张 smoke 图上运行 v3 的 epsilon sweep:
  ε ∈ {0.20, 0.30, 0.40, 0.50}
报告:
  - mean k/n
  - AUC gap vs M5
  - CI early-stop rate
  - AUC-runtime Pareto frontier
```

这是纯诊断实验，不需要修改代码逻辑，只需改参数。运行成本低（3 图 × 4 配置 = 12 runs）。

### 6.3 优先级 P1（P0 有结论后执行）：基于诊断结果的方向选择

#### 路径 A：如果大 ε 能显著降低 k/n 且 AUC 退化可控

→ 放弃 CI early-stop 机制（它已被证明不实用）。改为固定较小的 kmax（由大 ε 预算决定），不再依赖 CI 提前停止。

→ 在此前提下，v4 budget predictor 的目标改为"预测最优 ε"而不是"预测 k_ratio"。因为 ε 直接决定 kmax，而 k_ratio 的 label 质量差。

→ v5 的 expert routing 可以在固定 ε 下继续探索，但需要解决 oracle tie rate 87.5% 的问题（见 P1-2）。

#### 路径 B：如果大 ε 导致 AUC 退化不可接受

→ 说明"减少 source 数"这条路在当前候选集结构下走不通。需要回到**扩大候选集覆盖**的方向（NodeApprox-Hybrid），用更聪明的候选集弥补 source 减少的精度损失。

→ 此时 v4/v5 的"source routing"方向应暂停，转回 NodeApprox-Hybrid-Adaptive（已有 `scripts/node_approx_betweenness.py` 和完整设计文档 `next_direction_experiment_plan.md`）。

#### P1-1：如果继续 v4 路线：重构 label 和数据集

当前 v4 label `k_effect_ratio` 来自 v3 trace 的 `k_final`——但 v3 的 k_final 几乎总是 k_conf（因为 CI 几乎不触发）。这导致 label 近乎常数，模型学到的是噪声。

**方案**：使用 oracle k（即\"用尽可能少的 source 达到与 full-M5 top-1 一致\"的最小 k）作为 label。这需要通过 v5 的 oracle 框架重新生成 label，但把 k_probe 替换为 binary search（从 16 到 n_t 二分搜索最小 k）。

#### P1-2：如果继续 v5 路线：解决 oracle 区分度问题

v5 的 87.5% tie rate 说明 5 个专家在 k_probe 个源下的结果经常相同。

**方案**：
- 使用**更小的 k_probe**（如 k_probe=0.15×n_t 替代 0.30/0.45×n_t）：在更少源的情况下，不同专家的差异会被放大。
- 使用**更细粒度的 loss**：将 loss 中的硬 0/1 项替换为 top-1 的 sampled dependency percentile。
- 增加**more diverse experts**：当前 5 个专家的配额差异不够大（最极端的是 dense_random 50% random vs community_boundary 50% boundary）。

### 6.4 优先级 P2（无论 P0 结果如何都应做）：代码整理

| # | 任务 | 预计耗时 |
|---|---|---|
| P2-1 | 将 v3/v4/v5 共享的核心函数（GCC、Louvain drift、候选构造、Brandes、Welford、CI）提取到 `scripts/common_attack.py` | 2-3 小时 |
| P2-2 | 建立统一的方法命名注册表 `scripts/method_registry.py` | 30 分钟 |
| P2-3 | `scripts/` 顶层添加 `run_experiment.py` 统一入口 | 1-2 小时 |
| P2-4 | 清理 `__pycache__/` 和 `.tmp` 文件，更新 `.gitignore` | 20 分钟 |

### 6.5 P3：SASB 投稿补强（独立进行，不阻塞 v3/v4/v5）

| # | 任务 | 状态 |
|---|---|---|
| P3-1 | 补跑 M5 剩余 3 张真实网络（`bio_hs_ht`, `inf_openflights`, `socfb_caltech36`） | 待补 |
| P3-2 | 补全 candidate-source 消融（仅 S_comm / S_boundary / S_local / pairwise） | ablation report 明确说未完成 |
| P3-3 | 参数敏感性正式版（sample_sources 变化对 SASB 的影响） | 仅 smoke |
| P3-4 | 生成论文 Figure 1 (schematic), Figure 2 (per-graph AUC diff bar chart) | 待生成 |

---

## 7. 建议停止的工作

| 停止项 | 原因 |
|---|---|
| 继续扩大 v4 训练数据集或调参 | v4 底层依赖的 CI 机制尚未 work。扩大数据集不能弥补机制缺陷。 |
| 继续扩大 v5 oracle 数据集至更多图/步骤 | Oracle tie rate 87.5% 是根本问题，更多样本不会改变"专家之间区分度不够"的事实。 |
| 在 CI early-stop 率 <5% 的情况下继续用 v3 扩展 | 验收标准明确不推荐扩展。 |

---

## 8. 关键文件速查表

### 当前活跃代码

| 文件 | 版本 | 作用 |
|---|---|---|
| `scripts/ap_m5_hir_v3_candidate_ci.py` | v3 | 候选 CI + pairwise gap stopping（被 v4/v5 导入复用） |
| `scripts/ap_m5_hir_v4_neural_sampling.py` | v4 | 神经预算/路由攻击 |
| `scripts/neural_sampling_dataset.py` | v4 | v4 训练数据集生成 |
| `scripts/train_neural_budget_router.py` | v4 | v4 模型训练 |
| `scripts/evaluate_v4_neural_sampling.py` | v4 | v4 评估报告 |
| `experiments/v5_expert_router/src/` | v5 | v5 专家路由（独立目录，不修改 v3/v4） |
| `scripts/node_approx_betweenness.py` | NodeApprox | NodeApprox-Hybrid（k32/k64/adaptive 框架已有，adaptive 路由未实现） |
| `scripts/evaluate_m19_theory_calibrated.py` | SASB | SASB/M19-theory 全系列 |

### 关键报告

| 文件 | 内容 |
|---|---|
| `paper_core_story.md` | SASB 论文核心故事 |
| `research_cleanup_and_next_plan.md` | 2026-06-13 科研主线与清理计划 |
| `result/paper_experiments/paper_ready_summary.md` | 投稿摘要 |
| `result/node_approx_betweenness/ap_m5_hir_v3_candidate_ci/ap_m5_hir_v3_report.md` | v3 6 图 smoke 验收报告 |
| `results/v4_neural_sampling/reports/v4_neural_sampling_report.md` | v4 6 图 full_eval 报告 |
| `experiments/v5_expert_router/results/reports/v5_expert_router_report.md` | **v5 深度诊断报告（含"V5 is not successful"结论）** |
| `experiments/v5_expert_router/results/reports/v5_expert_router_full_report.md` | v5 综合报告 |
| `next_direction_experiment_plan.md` | NodeApprox-Hybrid-Adaptive 实验计划 |
| `next_direction_node_approx_betweenness.md` | NodeApprox-Hybrid-Adaptive 方法设计 |

### 关键结果数据

| 文件 | 内容 |
|---|---|
| `result/node_approx_betweenness/ap_m5_hir_v3_candidate_ci/ap_m5_hir_v3_k_trace.csv` | v3 10346 步逐步 trace（CI 诊断用） |
| `results/v4_neural_sampling/v4_neural_sampling_trace.csv` | v4 逐步 trace（81MB） |
| `results/v4_neural_sampling/v4_neural_sampling_per_graph.csv` | v4 逐图汇总 |
| `experiments/v5_expert_router/results/datasets/v5_expert_router_dataset.csv` | v5 oracle 数据集（8 样本） |
| `experiments/v5_expert_router/results/models/training_metrics.json` | v5 训练指标 |

---

## 9. 可以发给导师的当前状态总结（≤ 5 行）

1. **SASB（投稿主线）已就绪**：synthetic45 超 M5（p=0.011），真实网络以 1/15 时间逼近 M5。M5 仍缺 3 张大图待补跑。投稿级统计检验和消融已完成。

2. **AP-M5-HIR v3 通过 AUC 和 Speedup 验收，但 CI early-stop 几乎不触发（0.6%），source reduction 不显著（k/n=0.986），不推荐扩展。**

3. **v4 neural budget 未 work**：所有模式均未同时满足三项验收标准。Budget 模型 R²=0.985 但 source 节省不足以弥补 AUC 退化。Router 准确率仅 36%。

4. **v5 expert router 已确认不成功**：路由器 100% 预测 balanced，AUC 与 static baseline 完全相同。Oracle tie rate 87.5%，5 个专家区分度不够。

5. **下一步应优先诊断 CI 机制（P0）而非扩大 v4/v5 规模**。同时 SASB 投稿补强（M5 completion、candidate-source 消融补全）可独立推进。
