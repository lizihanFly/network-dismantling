# 投稿路线图

本文档把当前 `network-collapse` 项目整理成面向较好英文期刊/会议的研究路线。当前目标不是马上宣称提出了最强攻击方法，而是构建一个能够经得起审稿人质疑的 dynamic edge dismantling 实验框架。

## 暂定标题

Community-Aware Candidate Learning for Dynamic Edge Dismantling of Complex Networks

中文理解：

> 面向复杂网络动态边删除崩塌的社区感知候选边学习方法。

## 核心判断

Dynamic edge betweenness 是一个非常强的基线，而且计算代价高。当前项目不应该继续简单模仿 edge betweenness ranking，而应该研究：

- 能否直接学习候选边的 GCC damage；
- 学习方法在哪些网络结构上能接近或超过 dynamic edge betweenness；
- 社区强度如何影响社区感知方法和学习方法的有效性；
- 是否能在保持破坏效果接近的情况下减少计算成本。

## 可能贡献点

1. 系统比较动态边删除攻击中的 degree-based、community-aware、betweenness-based、oracle 和 learned damage-prediction 方法。
2. 提出一个候选边 damage learning 框架，从启发式方法、社区结构、bridge edges 和 random candidates 中构造候选集，然后直接预测候选边的 GCC damage。
3. 分析社区强度如何影响 community-aware 和 learned edge attack 的成功或失败。
4. 比较攻击效果和运行时间，讨论学习候选策略在什么条件下可以近似 dynamic edge betweenness。

## 投稿前必须补齐的内容

### 指标

论文中应报告：

- GCC 曲线的 AUC。
- Robustness index / normalized AUC。
- `fc`：GCC 降到 0.5、0.2、0.1 等阈值时需要删除的边比例。
- Runtime。
- 动态重算次数或攻击步数。

当前进展：

- `scripts/train_candidate_damage_predictor.py` 已经会在新实验中输出 `normalized_auc`、`robustness_index`、`observed_remove_ratio`、`final_gcc_ratio`、`num_steps` 和 `elapsed_seconds`。

### 基线方法

最低限度需要比较：

- Random edge attack。
- Degree product。
- Dynamic edge betweenness。
- 当前已有的 M4/M7/M8 community-aware 方法。
- CEP 或 CEP-like baseline。
- ECI / IECI / IECIR 或近似实现。

可选但有价值：

- HLC。
- Static EB vs dynamic EB。
- 如果代码和依赖可行，尝试复现 FIGHTER。

### 合成网络

需要做受控 synthetic benchmark：

- SBM：系统改变社区强度。
- LFR：系统改变 mixing parameter `mu`。
- ER、BA、WS：作为无社区或弱社区对照。

关键图不应只是“哪个方法赢”，而是：

> 方法差距如何随着社区结构变弱或变强而变化。

### 真实网络

保留当前真实网络：

- karate。
- football。
- ca-netscience。
- bio-diseasome。
- inf-USAir97。

在基线和评价协议稳定之前，不要盲目扩大真实网络集合。

## 方法路线

### 阶段 1：稳定 benchmark

目标：

- 把已有实验变成可比较、可复现、可写论文的 benchmark。

任务：

- 用扩展指标重新跑核心方法。
- 加入 runtime 表格。
- 明确记录 Louvain、GCC、edge betweenness 是否每一步动态重算。
- 如果实现成本可控，加入 CEP-like 和 ECI-like baseline。

### 阶段 2：Ranking damage predictor

目标：

- 把普通 MSE 回归 `gcc_delta` 改成更贴近攻击决策的排序目标。

任务：

- 每个动态状态构造候选边列表。
- 用 one-step 或 h-step damage 形成 pairwise/listwise 标签。
- 比较 GBDT 回归、pairwise ranking、listwise ranking。
- 使用同一个动态攻击循环评估最终攻击效果。

当前实现：

- `scripts/train_candidate_damage_predictor.py` 已经支持 `--model-type pairwise_logistic`。
- 该模型在同一个动态状态内构造候选边差分样本，学习哪条候选边 damage 更大。
- 该模型输出的是排序分数，不是校准后的 `gcc_delta`，所以 MAE/RMSE 对它不太有解释意义。
- 评估时应主要看 Spearman、Kendall、top-1 hit、chosen/best delta ratio、AUC、robustness index 和 runtime。

### 阶段 3：社区强度分析

目标：

- 找到论文中最有说服力的机制性结果。

任务：

- 生成 SBM/LFR sweep。
- 对每种社区强度，比较 M5、M4/M7/M8、CEP-like、ECI-like 和 candidate damage learning。
- 画出方法差距随社区强度变化的趋势。

可能的论文级发现：

> Dynamic EB 仍然是整体最强基线，但 community-aware candidate learning 在某些网络结构或社区强度下可以接近甚至局部超过 M5。

### 阶段 4：GNN edge scorer

目标：

- 只有当 ranking target 的信号足够稳定之后，再加入 GNN。

任务：

- 使用 GraphSAGE/GAT 编码当前图状态。
- 用端点表示和边/社区特征构造 edge embedding。
- 只给候选边打分，而不是给全图所有边打分。
- 与非 GNN ranking model 做对比。

### 阶段 5：论文写作

论文结构建议：

1. Introduction：边攻击、网络鲁棒性、动态重算成本、为什么 dynamic EB 难以超越。
2. Related Work：edge dismantling、community percolation、learning-based node dismantling、DRL edge attack。
3. Problem Definition：dynamic edge removal、GCC curve、AUC/R/fc/runtime。
4. Methods：baselines、candidate generation、damage learning、ranking target。
5. Experiments：datasets、synthetic controls、real networks、dynamic recomputation policy。
6. Results：攻击效果、运行时间、社区强度机制、消融实验。
7. Discussion：为什么 EB 很强、什么时候学习方法有用、局限性。

## 已完成实验与结论

### Publication metrics smoke test

已跑通：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --top-k 2 --max-train-graphs 1 --max-eval-graphs 1 --max-train-steps 3 --train-max-remove-ratio 0.03 --max-attack-steps 4 --attack-max-remove-ratio 0.03 --eval-splits synthetic_test --attack-splits synthetic_test --skip-baselines --out-dir result\candidate_damage_predictor_publication_metrics_smoke
```

意义：

- 验证扩展指标可以正常输出。
- 这只是 smoke test，不用于性能结论。

### Pairwise ranking smoke test

已跑通：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --model-type pairwise_logistic --top-k 5 --random-candidates 6 --bridge-top-k 6 --pairwise-max-pairs-per-state 24 --max-train-graphs 2 --max-eval-graphs 1 --max-train-steps 15 --train-max-remove-ratio 0.08 --max-attack-steps 12 --attack-max-remove-ratio 0.08 --eval-splits synthetic_test --attack-splits synthetic_test --skip-baselines --out-dir result\candidate_damage_pairwise_logistic_smoke
```

意义：

- 验证 `pairwise_logistic` 训练和动态攻击流程能跑通。
- 这只是 smoke test，不用于性能结论。

### Synth6 pairwise probe

运行命令：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --model-type pairwise_logistic --top-k 5 --random-candidates 8 --bridge-top-k 8 --pairwise-max-pairs-per-state 48 --damage-horizon 1 --max-train-graphs 12 --max-eval-graphs 6 --max-train-steps 30 --train-max-remove-ratio 0.15 --max-attack-steps 60 --attack-max-remove-ratio 0.15 --eval-splits synthetic_test --attack-splits synthetic_test --out-dir result\candidate_damage_pairwise_logistic_synth6
```

结果：

- 输出目录：`result/candidate_damage_pairwise_logistic_synth6`。
- Pairwise ranking 在前 6 个 synthetic test 图上的 mean AUC：0.097723。
- M5 dynamic edge betweenness 在同一批图上的 mean AUC：0.097855。
- 之前 one-step GBDT diverse probe 的 mean AUC：0.098861。

解释：

- Pairwise ranking 在这个小 probe 里略优于 M5。
- 但只赢 3/6 个图，输 3/6 个图，优势极小。
- 因此它只能说明“有信号”，不能作为论文结论。

### Synth18 pairwise validation

运行命令：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --model-type pairwise_logistic --top-k 5 --random-candidates 8 --bridge-top-k 8 --pairwise-max-pairs-per-state 48 --damage-horizon 1 --max-train-graphs 24 --max-eval-graphs 18 --max-train-steps 30 --train-max-remove-ratio 0.15 --max-attack-steps 60 --attack-max-remove-ratio 0.15 --eval-splits synthetic_test --attack-splits synthetic_test --out-dir result\candidate_damage_pairwise_logistic_synth18
```

结果：

- 输出目录：`result/candidate_damage_pairwise_logistic_synth18`。
- Pairwise ranking 在全部 18 个 synthetic test 图上的 mean AUC：0.102422。
- M5 dynamic edge betweenness 在同一批图上的 mean AUC：0.101366。

解释：

- Synth6 里的小优势没有泛化。
- Pairwise ranking 仍然优于弱启发式方法，但没有稳定超过 dynamic edge betweenness。
- 这批 synthetic_test 的 SBM 子集仍然不平衡：mixed=5，weak=3，strong=1，因此不能支撑社区强度结论。

结论：

- 不能宣称 pairwise ranking 超过 dynamic edge betweenness。
- 应该把它作为 multi-step damage、listwise ranking 或结构条件分析的基础。

## 大数据集检查

原始数据集太小，不足以支撑论文级结论。因此已经在不覆盖旧数据的前提下生成了更大的 synthetic dataset：

```powershell
D:\ana\python.exe scripts\build_ml_attack_dataset.py --num-synthetic 300 --out-dir data\ml_attack_dataset_large300
```

数据集规模：

- Train：210 个 synthetic graphs。
- Validation：45 个 synthetic graphs。
- Synthetic test：45 个 synthetic graphs。
- Real external test：5 个真实网络。
- Edge feature rows：173,902。

### Large300 synth45 short experiment

运行命令：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --data-dir data\ml_attack_dataset_large300 --model-type pairwise_logistic --top-k 5 --random-candidates 8 --bridge-top-k 8 --pairwise-max-pairs-per-state 48 --damage-horizon 1 --max-train-graphs 120 --max-eval-graphs 45 --max-train-steps 20 --train-max-remove-ratio 0.10 --max-attack-steps 40 --attack-max-remove-ratio 0.10 --eval-splits synthetic_test --attack-splits synthetic_test --out-dir result\candidate_damage_pairwise_logistic_large300_synth45_short
```

结果：

- Pairwise candidate damage predictor mean AUC：0.073561。
- M5 dynamic edge betweenness mean AUC：0.072615。
- 总体结论：M5 仍然更强。

分结构结果：

- BA：candidate 略优于 M5。
- ER：candidate 略优于 M5。
- SBM-medium：candidate 略优于 M5。
- SBM-weak：candidate 略优于 M5。
- SBM-mixed：candidate 略弱于 M5。
- SBM-strong：candidate 明显弱于 M5。
- WS：candidate 明显弱于 M5。

这个结果说明：

> 当前学习方法不是全局强于 M5，而是具有结构条件性。它可能在部分网络类型或社区强度下有效，但在 strong community 和 WS 图上明显不足。

## 下一步建议

### 优先级 1：Balanced SBM/LFR sweep

目标：

- 系统控制社区强度，验证 candidate learning 的结构条件结论是否稳定。

建议设置：

- SBM strong：至少 30 个图。
- SBM medium：至少 30 个图。
- SBM weak：至少 30 个图。
- SBM mixed：至少 30 个图。
- LFR 不同 `mu`：每个参数至少 30 个图。
- BA/ER/WS：作为对照组。

### 优先级 2：减少 M5 依赖

当前 candidate 方法推理时仍然使用 M5 top-k 候选，因此速度不占优。后续应测试：

- 不使用 M5 candidates。
- 只在训练阶段使用 M5 candidates，推理阶段不用。
- 降低 M5 candidate 的 top-k。

### 优先级 3：改进目标函数

可以尝试：

- h-step damage。
- pairwise h-step ranking。
- listwise ranking。
- LambdaMART / LightGBMRanker。

### 优先级 4：补强基线

投稿前必须尽量补：

- CEP-like baseline。
- ECI / IECI / IECIR baseline 或近似实现。
- HLC，如果公式和实现成本可控。

