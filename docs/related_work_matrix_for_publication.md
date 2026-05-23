# 投稿相关工作矩阵

本文档整理当前项目在投稿前必须讨论或补做对比的相关工作。当前项目研究的是 dynamic edge-removal attack，也就是在攻击过程中逐步删除边，并用 GCC 曲线衡量网络崩塌速度。

## 最接近的 Edge-Dismantling 工作

### FIGHTER：基于 line graph transformation 和 DRL 的关键边寻找

- 年份：2025。
- 任务设置：edge dismantling。
- 方法类型：line graph + GraphSAGE-like encoder + deep reinforcement learning。
- 为什么重要：这是最接近“学习式关键边攻击”的直接竞争工作。它把边选择建模成 MDP，并在 line graph 上学习边特征。
- 后续动作：必须在 related work 中详细讨论。如果能找到代码，应尝试复现；如果复现成本太高，也要做概念对比，并避免宣称“learning-based edge attack 本身是新的”。

### Network dismantling with community-based edge percolation (CEP)

- 年份：2025。
- 任务设置：edge dismantling。
- 方法类型：community detection + explosive percolation。
- 为什么重要：它和当前项目的 community-aware edge attack 思路直接重合，而且比较了多个 edge dismantling baseline。
- 后续动作：最好实现一个 CEP-like baseline；如果暂时实现不了，也必须在论文中说明它是关键相关工作和待补强基线。

### Edge Collective Influence / IECI / IECIR

- 年份：2023-2026。
- 任务设置：edge dismantling。
- 方法类型：line-graph optimal percolation and reinsertion。
- 为什么重要：这是很强的非学习 edge baseline，近期 CEP 类工作也会拿它作对比。
- 后续动作：作为目标 baseline 加入，或实现一个可解释的近似版本。

### Hierarchy-based Link Centrality (HLC)

- 年份：2025。
- 任务设置：edge dismantling。
- 方法类型：link hierarchy centrality。
- 为什么重要：近期 CEP 文献中把它列为 SOTA edge dismantling 竞争方法。
- 后续动作：加入 related work；如果公式和实现成本可控，后续补实现。

### Edge Betweenness (EB)

- 年份：经典基线。
- 任务设置：edge dismantling。
- 方法类型：dynamic centrality。
- 为什么重要：当前实验显示 dynamic EB 是最强内部基线。
- 后续动作：继续作为核心 baseline，并明确说明 edge betweenness 是否在每一步动态重算。

来源：

- FIGHTER: https://www.sciencedirect.com/science/article/pii/S0957417425017427
- CEP: https://www.sciencedirect.com/science/article/pii/S0306457325002365
- ECI preprint: https://arxiv.org/abs/2310.06407

## 最接近的 Learning-Based Node-Dismantling 工作

### Machine learning dismantling and early-warning signals of disintegration

- 年份：2021。
- 任务设置：node dismantling。
- 方法类型：graph neural network。
- 为什么重要：这是较早的重要 ML dismantling 工作，说明模型可以从 synthetic networks 迁移到 real networks。
- 后续动作：作为 learning-based dismantling 背景引用，但要明确它做的是节点攻击，不是边攻击。

### Dismantling with graph contrastive learning and multi-hop aggregation

- 年份：2024。
- 任务设置：node dismantling。
- 方法类型：contrastive learning + multi-hop aggregation。
- 为什么重要：说明 learned node dismantling 已经不止是简单监督排序。
- 后续动作：放在 GNN 和 representation learning 相关工作中讨论。

### Higher-order GNN network dismantling / SPR

- 年份：2026。
- 任务设置：node dismantling。
- 方法类型：higher-order GNN。
- 为什么重要：这是较新的高水平 GNN dismantling 工作，会提高审稿人对 GNN 部分的期待。
- 后续动作：不要把“用了 GNN”当作主要创新点。真正的差异应放在 edge-level dynamic attack 和 community-aware candidate learning 上。

### MIND：learning network dismantling without handcrafted inputs

- 年份：2026。
- 任务设置：node dismantling。
- 方法类型：不依赖人工特征的深度学习方法。
- 为什么重要：如果后续加入 GNN edge scorer，它是必须讨论的最新学习式 dismantling 背景。
- 后续动作：作为近期 learning-based dismantling 相关工作引用。

来源：

- GDM / ML dismantling: https://www.nature.com/articles/s41467-021-25485-8
- HoGNN / SPR: https://www.nature.com/articles/s42005-026-02601-y
- MIND: https://ojs.aaai.org/index.php/AAAI/article/view/39790

## 当前项目更稳妥的定位

最安全的贡献不是泛泛地说“提出一种新的 network dismantling 学习方法”。这个方向已经比较拥挤。

更可辩护的差异点是：

1. 做 dynamic edge-removal attack，而不是 node dismantling。
2. 做 community-aware candidate generation，而不是全边排序。
3. 直接学习 damage，而不是模仿 edge betweenness。
4. 系统分析学习方法什么时候能接近或局部改善 dynamic EB。
5. 讨论攻击效果和运行时间的 tradeoff，因为 dynamic EB 很强但代价高。

## Baseline 优先级

Priority 1：

- Dynamic edge betweenness。
- CEP 或 CEP-like community edge percolation。
- ECI / IECI / IECIR 或明确的近似实现。
- 当前已有的 M2/M4/M7/M8 project baselines。

Priority 2：

- HLC。
- Static EB versus dynamic EB。
- Random 和 degree-product baselines。

Priority 3：

- 如果代码和依赖实际可行，尝试复现 FIGHTER。
- 只有在 ranking target 信号稳定后，再加入 GNN edge scorer。

