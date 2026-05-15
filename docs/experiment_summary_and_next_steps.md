# 当前实验总结与后续研究路线

本文档总结目前 `network-collapse` 项目的实验进度、主要发现、当前方法的局限，以及后续加入深度学习和强化学习方法时更合理的推进路线。

## 1. 当前研究目标

本项目研究的是复杂网络在边删除攻击下的崩塌过程。核心问题是：

- 给定一个网络，应该按什么顺序删除边，才能最快破坏最大连通分量？
- 社区结构、节点度、边介数等结构指标对攻击效果有什么影响？
- 是否可以训练机器学习或深度学习模型，自动学习比传统启发式方法更强的边攻击策略？

当前主要评价指标是攻击曲线的 AUC。AUC 越低，表示网络越快碎裂，攻击效果越好。

## 2. 已完成实验

### 2.1 基础攻击方法对比

已在多个网络上比较了传统启发式攻击方法，包括：

- M1 Random
- M2 degree product
- M3 community size product
- M4 community internal edges / pair edges
- M5 edge betweenness
- M6 community internal edges product
- M7 community size / pair edges
- M8 community bridge-degree

覆盖网络包括：

- SBM strong / medium / weak
- karate
- football
- ca-netscience
- bio-diseasome
- inf-USAir97

主要结论：

- M5 dynamic edge betweenness 是目前整体最强基线。
- M4 和 M7 在社区结构明显的网络上表现接近 M5。
- M8 没有带来预期提升，乘上 degree product 后反而没有稳定超过 M4/M7。
- SBM 实验显示，社区结构强弱会明显影响社区感知方法的效果。

对应结果：

- `result/attack_summary/analysis/attack_summary_notes.md`
- `result/attack_summary/analysis/method_rank_summary.csv`

### 2.2 ML 攻击数据集构建

已构建边级别机器学习数据集：

- synthetic train: 84 个图
- validation: 18 个图
- synthetic test: 18 个图
- real external test: 5 个真实网络

每条边包含：

- 节点度相关特征
- clustering / pagerank / node betweenness
- 社区大小、社区内部边数、社区对之间边数
- M3/M4/M6/M7/M8 分数
- edge betweenness
- one-step GCC drop
- 排名标签

对应结果：

- `data/ml_attack_dataset/README.md`
- `scripts/build_ml_attack_dataset.py`

### 2.3 MLP attack ranker baseline

已训练一个 MLPRegressor 作为边排序模型。

当前目标：

- `edge_betweenness_rank_pct`

训练方式：

- 只用 synthetic train 拟合。
- validation、synthetic test、real external test 不参与训练。
- 排除了直接泄漏标签的列。

主要结果：

| Split | Spearman | Kendall | MLP AUC | 最强基线 |
| --- | ---: | ---: | ---: | --- |
| synthetic_test | 0.803 | 0.613 | 0.679 | M5, AUC 0.397 |
| real_external_test | 0.703 | 0.535 | 0.400 | M5, AUC 0.177 |

结论：

- MLP 对 teacher ranking 的相关性还可以。
- 但拿 MLP 排序直接做攻击时，AUC 明显弱于 M5。
- 这说明“模仿 edge betweenness 排名”不等于“学到最优网络崩塌策略”。

对应结果：

- `scripts/train_mlp_attack_ranker.py`
- `result/ml_mlp_attack_ranker/mlp_attack_ranker_notes.md`

### 2.4 Strategy selector oracle

已做一个策略选择器 oracle：

- 每一步让 M2/M4/M5/M7/M8 各自提出下一条边。
- oracle 尝试这些候选边。
- 选择 immediate GCC drop 最大的边。

主要结果：

| Split | Oracle AUC | M5 AUC | 结论 |
| --- | ---: | ---: | --- |
| synthetic_test | 0.397 | 0.397 | 基本等同 M5 |
| real_external_test | 0.177 | 0.177 | 基本等同 M5 |

候选使用情况：

- synthetic_test 中几乎 100% 选择 M5。
- real_external_test 中 99.9% 选择 M5。

结论：

- 如果候选池只包含各方法的 top-1 动态边，策略选择器上界几乎退化成 M5。
- 继续学习“从 M2/M4/M5/M7/M8 中选一个方法”价值不大。

对应结果：

- `scripts/evaluate_strategy_selector_oracle.py`
- `result/strategy_selector_oracle/strategy_selector_oracle_notes.md`

### 2.5 Expanded candidate oracle quick probe

为判断是否值得扩大候选池，已做 quick probe：

- 每一步从 M2/M4/M5/M7/M8 的 top-5 边构造候选池。
- oracle 选择 immediate GCC drop 最大的边。
- 只跑小规模探测，避免完整实验耗时过高。

结果：

| Probe | Expanded oracle AUC | 对照 |
| --- | ---: | --- |
| synthetic_test 前 3 个图 | 0.383415 | 同三图 M5 约 0.383547，几乎打平 |
| karate | 0.373115 | 差于 M5 0.337293 |
| football | 0.225023 | 差于 M5 0.217732 |

结论：

- top-5 immediate oracle 没有显示出明显超过 M5 的潜力。
- 完整 expanded oracle 非常耗时，目前不建议优先继续跑。
- 更值得转向“重新设计学习目标”。

对应结果：

- `scripts/evaluate_expanded_candidate_oracle.py`
- `result/expanded_candidate_oracle_quick_notes.md`

## 3. 当前阶段总判断

目前最重要的发现是：

1. M5 dynamic edge betweenness 是非常强的基线。
2. 社区方法 M4/M7 在部分网络上接近 M5，尤其适合解释社区结构对网络崩塌的作用。
3. 直接模仿 M5 排名的 MLP 并不能得到强攻击策略。
4. 简单策略选择器和 expanded top-k one-step oracle 目前都没有明显超过 M5。

因此，后续研究不要再只围绕“模仿 M5”或“在已有启发式方法之间选择”展开。更合理的方向是：让模型直接面向最终崩塌目标进行学习。

## 4. 后续加入深度学习的方法

### 4.1 不建议继续的方向

不建议继续把 `edge_betweenness_rank_pct` 作为主要监督目标。

原因：

- 当前 MLP 已经证明，teacher ranking 相关性高不代表攻击 AUC 好。
- edge betweenness 是单步中心性指标，不一定等价于多步边删除后的全局崩塌效果。
- 模型最终要优化的是 GCC 曲线，而不是某个中心性指标的排序。

### 4.2 推荐方向一：直接预测 GCC damage

把监督学习目标从 teacher rank 改成 damage prediction。

可选标签：

- `gcc_delta`: 删除当前边后的 one-step GCC drop。
- `future_auc_delta`: 删除当前边后，再用某个 rollout 策略继续攻击若干步产生的 AUC 改善。
- `h_step_gcc_drop`: 删除当前边并 rollout `h` 步后的 GCC drop。

推荐先做：

1. 构造 candidate set，而不是对所有边排序。
2. 对每个候选边计算 one-step 或 h-step damage。
3. 训练模型预测 damage。
4. 每一步选择预测 damage 最大的边。

候选集可以来自：

- M5 top-k
- M4 top-k
- M7 top-k
- M8 top-k
- degree product top-k
- random exploration candidates

这样做的原因：

- 候选集能降低计算量。
- 学习目标直接贴近 GCC 崩塌。
- 比模仿 M5 更可能发现局部超过 M5 的边。

### 4.3 推荐方向二：GNN 边打分模型

如果要加入深度学习，优先考虑 GNN，而不是普通 MLP。

原因：

- MLP 只看人工特征，不能充分利用图结构。
- GNN 可以学习节点表示，再组合成边表示。
- 边删除攻击天然是图结构任务，GNN 更贴合问题。

推荐模型形式：

- 输入：当前图 `G_t`
- 节点特征：degree、clustering、pagerank、community id/size、是否在 GCC 中等
- GNN backbone：GCN / GraphSAGE / GAT
- 边表示：`concat(h_u, h_v, h_u * h_v, edge_features)`
- 输出：每条候选边的 damage score

训练目标：

- 回归：预测 `gcc_delta` 或 `h_step_gcc_drop`
- 排序：pairwise ranking loss，让更高 damage 的边排在前面
- 分类：预测 top damage candidate

推荐先从 GraphSAGE 开始。

原因：

- 实现相对直接。
- 对不同大小网络泛化更自然。
- 比 GCN 更适合归纳学习。

### 4.4 推荐方向三：Learning to Rank

另一个比 MLP 回归更合适的方向是 learning-to-rank。

每个图、每个 step 形成一个候选边列表：

- 输入：候选边特征
- 标签：这些边实际造成的 damage 排名
- 损失：pairwise ranking loss 或 listwise loss

这样做的原因：

- 攻击决策本质是排序问题。
- 绝对 damage 值在不同网络之间尺度不同。
- 排序损失比 MSE 更贴合“选哪条边”的目标。

## 5. 后续加入强化学习的方法

强化学习是合理方向，但不建议一开始就直接做完整 RL。原因是边删除环境动作空间很大，而且每一步图都会变化，训练成本高。

更稳妥的路线是分三阶段。

### 5.1 阶段一：把攻击过程封装成环境

先实现一个标准环境，而不是马上训练 agent。

环境定义：

- State: 当前残余图 `G_t`
- Action: 删除一条候选边 `e_t`
- Reward: GCC 下降量，例如 `gcc_before - gcc_after`
- Episode: 删除到指定比例，或 GCC 小于阈值
- Return: 负 AUC 或累计 GCC drop

关键设计：

- 动作空间不要用全图所有边，先用 candidate set。
- candidate set 可由 M5/M4/M7/top degree/random 混合生成。
- 每一步保留候选边特征和实际 reward，方便后续监督学习和 RL 共用。

### 5.2 阶段二：先做 imitation / offline RL

不要直接在线探索。

先用已有强策略产生轨迹：

- M5
- M4
- M7
- expanded oracle quick probe 中的候选选择
- random perturbation 策略

然后训练模型模仿或改进这些轨迹。

推荐方法：

- Behavior cloning：学习强策略在候选集中的选择。
- DAgger-like 数据增强：模型选边后继续收集状态。
- Conservative Q-learning 思路：先用离线数据估计候选边价值。

原因：

- 网络攻击环境计算贵。
- 在线 RL 从零探索效率很低。
- 离线数据已经很多，可以先利用起来。

### 5.3 阶段三：候选集上的 Policy Gradient / Actor-Critic

在环境稳定后，再做真正 RL。

推荐形式：

- Policy 网络对候选边输出概率。
- 每一步从候选集中采样或选择边。
- Reward 用 immediate GCC drop，并加入最终 AUC 奖励。
- 使用 actor-critic 降低方差。

可以尝试：

- REINFORCE baseline
- PPO on candidate actions
- DQN / Double DQN on candidate actions

首选 PPO 或 actor-critic。

原因：

- 动作空间每一步变化，candidate action policy 比固定动作编号更自然。
- PPO 比纯 REINFORCE 稳定。
- DQN 也可以做，但需要处理变长候选动作的 Q 值 mask。

## 6. 推荐的实际推进顺序

### Step 1：整理总实验报告

目标：

- 把传统攻击、MLP、oracle、expanded oracle 的结论整理成一条完整故事线。

原因：

- 当前已有结果已经足够形成阶段性结论。
- 先写清楚现有发现，后续加入深度学习/RL 时不会偏题。

### Step 2：实现 candidate damage dataset

目标：

- 每个图、每个攻击 step，生成候选边及其 one-step damage。

建议字段：

- `split`
- `graph_id`
- `step`
- `candidate_source`
- `u`
- `v`
- `candidate_rank`
- `edge_features`
- `gcc_before`
- `gcc_after`
- `gcc_delta`
- `damage_rank`

原因：

- 这是监督学习、learning-to-rank、offline RL 的共同数据基础。

### Step 3：训练 damage predictor

先用非 GNN 模型做 baseline：

- RandomForestRegressor
- GradientBoostingRegressor
- MLPRegressor
- pairwise ranking MLP

原因：

- 比 GNN/RL 快，容易验证目标是否有效。
- 如果 damage predictor 都不能超过 M5，直接上 RL 成本会更高。

### Step 4：实现 GNN edge scorer

目标：

- 用 GraphSAGE/GAT 给候选边打 damage score。

原因：

- 这是深度学习版本的自然升级。
- 可以验证图结构表示是否比人工特征更强。

### Step 5：封装 RL environment

目标：

- 让任意策略都能在同一个环境中评估。

原因：

- 统一 M5、MLP、GNN、RL 的评估接口。
- 后面写实验更清楚。

### Step 6：做 offline RL / PPO

目标：

- 在候选边动作空间上学习长期回报。

原因：

- 只有当监督 damage predictor 显示有潜力后，RL 才值得投入。

## 7. 当前最推荐的下一步

下一步最推荐做：

> 构建 candidate damage dataset，并训练一个直接预测 `gcc_delta` 或 `h_step_gcc_drop` 的 baseline。

这是后续所有深度学习和强化学习路线的基础。

理由：

- 直接优化网络崩塌目标。
- 避免继续模仿 M5。
- 计算成本比完整 RL 小。
- 可以复用现有 synthetic/real split。
- 如果这个方向有效，再上 GNN 和 RL 才有依据。

## 8. 已开始的新方向：candidate damage predictor

已经新增脚本：

- `scripts/train_candidate_damage_predictor.py`

这个脚本实现了第一版 damage prediction pipeline：

1. 每个动态攻击状态下，从 M2/M4/M5/M7/M8 的 top-k 边构造 candidate set。
2. 对每条候选边计算 one-step `gcc_delta`。
3. 用 synthetic train 上采集到的候选边样本训练模型。
4. 评估时每一步重新构造 candidate set，并删除预测 `gcc_delta` 最大的边。

当前默认模型是 `gbdt`，也支持：

- `mlp`
- `random_forest`
- `gbdt`

### 8.1 当前具体模型

当前优先使用的是 `gbdt`，即 Gradient Boosting Decision Tree 回归模型。

选择它作为第一版 baseline 的原因：

- 数据量还不算大，GBDT 在中小规模表格特征上通常比 MLP 更稳。
- 当前特征主要是人工结构特征，不是原始图张量，树模型适合处理这类非线性表格数据。
- GBDT 不需要特征标准化，也不太依赖复杂调参。
- 它训练快，方便我们快速判断 damage prediction 目标是否有潜力。

当前脚本里的 GBDT 设置：

- `n_estimators = max_iter`
- `learning_rate = 0.05`
- `max_depth = 3`
- `random_state = 20260513`

它学习的是回归目标：

```text
target = gcc_delta
```

也就是候选边删除前后的最大连通分量占比下降量：

```text
gcc_delta = gcc_before - gcc_after
```

### 8.2 训练数据如何生成

训练不是直接使用原始图的所有边，而是在动态攻击过程中采样状态。

每个训练图上重复以下过程：

1. 当前图为 `G_t`。
2. 从 M2/M4/M5/M7/M8 各取 top-k 边。
3. 合并去重，得到 candidate set。
4. 对 candidate set 中每条边临时删除一次，计算真实 `gcc_delta`。
5. 保存候选边的动态结构特征和 `gcc_delta` 标签。
6. 用 rollout policy 删除一条边，让图进入下一状态 `G_{t+1}`。

当前默认 rollout policy 是 `m5`。

这意味着训练状态主要来自 M5 攻击轨迹。这样做的好处是训练数据质量较高，坏处是状态分布会偏向 M5。后续如果要增强探索，可以混入：

- `damage_oracle` rollout；
- random rollout；
- M4/M7 rollout；
- 模型自身 rollout。

### 8.3 输入特征

每条候选边的输入特征包括四类。

图状态特征：

- 当前节点数；
- 当前边数；
- 当前 GCC ratio；
- 当前 density；
- 当前平均度；
- 当前社区数量；
- 当前删除比例。

边两端节点特征：

- degree；
- degree product；
- degree sum；
- degree difference；
- clustering；
- pagerank；
- node betweenness。

社区结构特征：

- 是否跨社区；
- 两端社区大小；
- 两端社区内部边数；
- 两社区之间的边数；
- M4/M7/M8 分数。

候选来源特征：

- 是否来自 M2 top-k；
- 是否来自 M4 top-k；
- 是否来自 M5 top-k；
- 是否来自 M7 top-k；
- 是否来自 M8 top-k；
- 被几个启发式方法同时提名；
- 在候选方法中的最小 rank。

这些特征的设计目的不是让模型复制某个启发式方法，而是让模型知道：

- 这条边本身的局部结构；
- 它在社区结构中的位置；
- 哪些传统方法认为它重要；
- 当前网络已经被攻击到什么阶段。

### 8.4 训练和推理方式

训练阶段：

```text
候选边动态特征 -> GBDT -> 预测 gcc_delta
```

损失函数是回归误差，由 sklearn 的 `GradientBoostingRegressor` 内部优化平方误差。

推理阶段，也就是真正攻击时：

1. 在当前图上重新生成 candidate set。
2. 给每条候选边提取同样的动态特征。
3. 用模型预测 `pred_gcc_delta`。
4. 删除 `pred_gcc_delta` 最大的边。
5. 更新图结构，进入下一步。

因此，这个方法是一个动态策略，不是静态一次性排序。

### 8.5 当前 probe 结果

已跑一个小规模 synthetic probe：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --top-k 5 --max-train-graphs 8 --max-eval-graphs 2 --max-train-steps 30 --train-max-remove-ratio 0.15 --max-attack-steps 60 --attack-max-remove-ratio 0.15 --eval-splits synthetic_test --attack-splits synthetic_test --out-dir result\candidate_damage_predictor_synth_probe_with_baselines
```

这个 probe 的含义：

- 训练图：8 个 synthetic train 图；
- 评估图：2 个 synthetic test 图；
- candidate set：M2/M4/M5/M7/M8 各 top-5；
- 每个训练图最多采样 30 个攻击状态；
- 训练采样最多到 15% 删除比例；
- 攻击评估也只看前 15% 删除比例。

选择这种受限评估的原因是完整动态评估非常慢，尤其是每一步都要重算 edge betweenness 和 Louvain。先比较早期攻击阶段，可以快速判断方向是否有信号。

当前结果：

| Method | synthetic_test mean AUC, first 15% removal |
| --- | ---: |
| M5 dynamic edge betweenness | 0.096824 |
| Candidate damage predictor | 0.099799 |
| M2 dynamic degree product | 0.104301 |
| M4 dynamic community internal / pair | 0.104301 |
| M7 dynamic community size / pair | 0.104301 |
| M8 dynamic community bridge-degree | 0.104301 |

候选排序质量：

| Metric | Value |
| --- | ---: |
| states | 60 |
| mean candidate count | 19.28 |
| mean top1 hit | 0.950 |
| mean chosen/best delta ratio | 0.625 |
| mean Spearman | 0.037 |
| mean Kendall | 0.033 |

解释：

- damage predictor 已经明显优于 M2/M4/M7/M8 的早期曲线。
- 它接近 M5，但还没有超过 M5。
- `top1_hit` 很高，但 `chosen/best delta ratio` 只有 0.625，说明很多状态里真实 damage 非常稀疏，命中 top damage 的次数不完全等价于拿到最大收益。
- Spearman/Kendall 较低，说明模型更像是在识别少数高 damage 候选，而不是完整排序所有候选边。

当前结论：

- damage prediction 方向能跑通，并且比普通弱启发式方法更好。
- 但第一版 one-step GBDT 还没有稳定超过 M5。
- 下一步应优先改进训练目标和候选集，而不是立刻上完整 RL。

### 8.6 接下来怎么改进

优先级从高到低：

1. 增加候选多样性  
   在启发式 top-k 之外加入 random candidates、桥边候选、跨社区边候选，降低候选池被 M5/M4/M7 限制的风险。

2. 从 one-step damage 改到 h-step damage  
   当前 `gcc_delta` 只看删一条边后的立刻下降。后续应加入 `h_step_gcc_drop`，比如删除当前候选边后，用 M5 或模型 rollout 3-5 步，看多步 GCC 下降。

3. 改用 ranking loss  
   现在是回归 `gcc_delta`。但攻击本质上是“在候选边里选最好的一条”，所以 pairwise/listwise ranking loss 可能比 MSE 更合适。

4. 增加训练状态分布  
   目前默认 rollout 是 M5。后续可以混合 M5、M4、M7、random、damage_oracle，让模型看到更多非 M5 状态。

5. 再上 GNN edge scorer  
   等 damage target 显示出稳定信号后，用 GraphSAGE/GAT 学节点表示，再给候选边打分。

### 8.7 已加入候选集多样性

已经在 `scripts/train_candidate_damage_predictor.py` 中加入两个新参数：

```powershell
--random-candidates
--bridge-top-k
```

含义：

- `--random-candidates N`：每个动态状态额外随机采样 N 条当前 GCC 中的边。
- `--bridge-top-k N`：每个动态状态额外加入 top-N bridge edges，按 degree product 排序。

这样做的原因：

- 只用 M2/M4/M5/M7/M8 top-k 时，模型永远选不到启发式方法没有提名的边。
- random candidates 提供探索能力，让模型看到启发式以外的边。
- bridge candidates 提供结构性补充，因为桥边删除可能直接造成连通分量断裂。
- 这一步是在不直接扩大到全边动作空间的前提下，提高候选池上限。

新增候选来源也会进入模型特征：

- `source_random`
- `source_bridge`

也就是说，模型不仅能看到这些边，还知道它们是随机探索来的，还是桥边规则提名的。

已跑一个 diversity smoke test，确认：

- random/bridge 候选能进入 candidate set；
- 新特征列能进入训练；
- 模型训练和攻击评估链路正常。

随后跑了一个带 baseline 的小规模 synthetic probe：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --top-k 5 --random-candidates 8 --bridge-top-k 8 --max-train-graphs 8 --max-eval-graphs 2 --max-train-steps 30 --train-max-remove-ratio 0.15 --max-attack-steps 60 --attack-max-remove-ratio 0.15 --eval-splits synthetic_test --attack-splits synthetic_test --out-dir result\candidate_damage_predictor_diverse_synth_probe
```

结果：

| Method | synthetic_test mean AUC, first 15% removal |
| --- | ---: |
| M5 dynamic edge betweenness | 0.096824 |
| Candidate damage predictor, diverse candidates | 0.098510 |
| M2 dynamic degree product | 0.104301 |
| M4 dynamic community internal / pair | 0.104301 |
| M7 dynamic community size / pair | 0.104301 |
| M8 dynamic community bridge-degree | 0.104301 |

候选排序质量：

| Metric | Previous top-k only | Diverse candidates |
| --- | ---: | ---: |
| mean candidate count | 19.28 | 28.87 |
| mean top1 hit | 0.950 | 1.000 |
| mean chosen/best delta ratio | 0.625 | 1.000 |
| mean Spearman | 0.037 | 0.458 |
| mean Kendall | 0.033 | 0.445 |

解释：

- 加入 random/bridge candidates 后，候选排序质量明显变好。
- 攻击 AUC 从 0.099799 改善到 0.098510，更接近 M5。
- 但它仍然没有超过 M5，说明 one-step `gcc_delta` + GBDT 还不足以稳定打败 edge betweenness。
- 下一步不应只继续加随机候选，而应转向多步目标 `h_step_gcc_drop` 或 ranking loss。

一个最小 smoke test 已跑通：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --top-k 3 --max-train-graphs 2 --max-eval-graphs 1 --max-train-steps 8 --train-max-remove-ratio 0.08 --eval-splits synthetic_test --attack-splits synthetic_test --skip-baselines --out-dir result\candidate_damage_predictor_smoke
```

该 smoke test 的意义不是给出最终性能结论，而是验证：

- candidate set 能动态生成；
- one-step damage 标签能动态计算；
- 模型能训练；
- 模型能作为攻击策略逐步删除边；
- 结果能落盘用于后续分析。

下一步应扩大这个实验，但要控制计算量：

```powershell
D:\ana\python.exe scripts\train_candidate_damage_predictor.py --top-k 5 --max-train-graphs 12 --max-eval-graphs 4 --max-train-steps 40 --train-max-remove-ratio 0.20 --eval-splits synthetic_test --attack-splits synthetic_test --out-dir result\candidate_damage_predictor_synth_probe
```

如果 synthetic probe 显示 damage predictor 能稳定接近或超过 M5，再扩展到：

- 更多 synthetic test 图；
- real_external_test 小图，比如 `karate,football`；
- 更大的 top-k；
- `h_step_gcc_drop` 标签；
- GNN edge scorer。
