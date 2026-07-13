# 网络拆解算法研究进展总结

本文档汇总当前项目中对“用少量源节点估计全局边介数，并用于网络拆解”的主要研究进展。重点是算法原则、步骤、参数、实验数字、失败机制和下一步方向。所有结论都来自当前已有报告和结果文件；未找到的文件或指标会明确标注为“not found in current files”。

## 1. Research Objective

本文固定目标是：

- 用少量源节点近似估计全局边介数，而不是每一步都运行完整 Brandes 式全源边介数计算。
- 在计算成本低于完整 M5 / full edge betweenness 的前提下，尽量接近 full M5 的边选择质量。
- 把该估计用于边删除式网络拆解，即每一步选择一条边删除，使最大连通分量尽快变小。
- 用 GCC 曲线和 GCC-AUC 评价拆解效果。

这里的核心不是单纯“模仿 M5 top-1 边”，而是用少源估计服务于动态拆解。已有实验显示：静态边介数估计变好，并不自动保证 GCC-AUC 变好。

## 2. Background Concepts

**GCC**：Giant Connected Component，最大连通分量。对无向图来说，GCC 是当前图中节点数最多的连通块。拆解算法希望删除少量边后，让 GCC 快速缩小。

**网络拆解**：network dismantling。这里采用边攻击形式：每一步根据某种评分选择一条边删除，然后重新计算当前图状态。若 GCC 比例下降更快，说明拆解更有效。

**边介数**：edge betweenness centrality。一条边的边介数表示它出现在多少节点对最短路径上。高边介数边通常连接重要通道，但在动态 GCC 目标下，高边介数不一定总是最能立刻削减 GCC。

**Brandes / full-M5**：Brandes 是经典的高效介数计算框架。项目里的 M5 / full-M5 可理解为每个攻击状态下，对候选边计算接近完整全源边介数或依赖分数，然后选最高分边删除。它是强参考基线，但计算成本高。

**源节点采样**：source sampling。完整边介数需要从大量源节点出发累计最短路径依赖。采样方法只选一小部分源节点，估计每条候选边的依赖均值。

**sampled dependency**：采样依赖分数。对候选边 `e`，从若干源节点得到单源贡献，再取均值 `mu(e)`，作为 sampled edge betweenness 的近似。

**候选边集合**：candidate edge set。为了避免对所有边评分，v3 会先构造一个候选边集合，通常包含跨社区、边界、桥状或结构上更可能重要的边。后续 v3、ACES 等方法都主要在该候选集合内选边。

**GCC-AUC**：GCC 曲线下的面积。横轴是删除步数，纵轴是 GCC 比例。AUC 越小，表示 GCC 下降越快，拆解越好。

**active-window AUC**：只在 GCC 有明显变化的活动窗口中计算 AUC，用于避免大量平坦前缀掩盖真实差异。

**top1 agreement**：某方法选出的最高分边是否等于 full-M5 top-1 边。

**NDCG@10**：Normalized Discounted Cumulative Gain at 10，衡量方法给出的前 10 名排序是否接近 full-M5 排序，越高越好。

**Spearman**：Spearman rank correlation，排序相关系数，用于衡量方法整体排序与 full-M5 排序的一致性。

**survival**：在 ACES 中，Stage 1 后保留的 top-K survivor 集合是否包含 full-M5 top-1。

**effective source cost**：有效源节点成本。固定 k 方法的成本约等于 k。ACES Stage 2 只精修 top-K survivor，因此成本按 `k1 + k2 * K / candidate_count` 折算，而不是简单算 `k1+k2`。

## 3. Baselines and Early Methods

### M5 full edge betweenness

目标：作为强参考基线，每一步尽量使用完整边介数 / full-M5 candidate dependency 选边。

步骤：

1. 重建当前 GCC。
2. 构造当前候选边集合。
3. 对候选边计算完整 M5 依赖分数。
4. 删除 full-M5 top-1 边。

结果：在 ACES prefix smoke v2 中，M5 平均 prefix AUC 为 0.618579，active-window AUC 为 0.564212，平均成本约 190.258。M5 是高成本参考，不是低成本目标。

结论：M5 是当前 paper goal 的参考对象，但不能声称 M5 对 GCC-AUC 全局最优。ia_enron_only 中 M5 也会出现 stall。

### fixed k32

目标：固定采样 32 个源节点，用 sampled dependency 均值 `mu(e)` 近似 M5。

步骤：

1. 使用 v3 候选集。
2. 选择 32 个源节点。
3. 对候选边累计单源贡献并取均值。
4. 删除 sampled top-1 边。

关键结果：

- ACES Phase 0.5 静态诊断：top1 agreement 0.456897，NDCG@10 0.867128，Spearman 0.727976，成本 31.137931。
- Prefix smoke v2：mean active-window AUC 0.540659，mean delta GCC after T 0.579727，top1 agreement 0.591667，成本 32。
- ia_enron_only 上 fixed k32 active-window AUC 0.838749，优于 pure ACES 和 M5。

结论：fixed k32 是非常重要的动态基线。它不一定更准确估计 M5，但它的采样噪声有时会选到更能切碎 GCC 的低 M5 rank 外围边。

### fixed k48

目标：用更多源节点提高 sampled dependency 对 M5 的估计质量。

关键结果：

- ACES Phase 0.5：top1 agreement 0.518966，NDCG@10 0.911291，Spearman 0.770327，成本 45.137931。
- Prefix smoke v2：active-window AUC 0.542857，top1 agreement 0.700，成本 48。

结论：fixed k48 静态估计更接近 M5，但动态 GCC-AUC 不稳定优于 fixed k32。这支持“更像 M5 不一定更会拆解”的机制判断。

### v3 candidate-CI / v3 candidate set

目标：用候选边集合和 pairwise CI 停止规则减少源节点使用。

关键参数：

- epsilon 默认 0.15。
- candidate range 约 10%-50%。
- pairwise gap CI lower confidence bound 大于 0 时提前停止。

v3 候选边集合的具体构造来自 `scripts/ap_m5_hir_v3_candidate_ci.py` 中的 `build_candidate_edges_v3(graph, partition, structural, profile, state=None)`。它每个攻击状态在当前 GCC 上工作，输入包括当前图、Louvain 社区划分 `partition`、结构统计 `structural` 和候选 profile。

候选 profile 有三组参数：

| Profile | min_fraction | max_fraction | degree_top_fraction | 用途 |
|---|---:|---:|---:|---|
| default | 0.10 | 0.50 | 0.10 | formal 默认配置 |
| tight | 0.05 | 0.30 | 0.10 | 更激进地缩小候选集 |
| safe | 0.15 | 0.60 | 0.15 | 更保守地扩大候选集 |

formal v3 使用 `FORMAL_EPSILON = 0.15` 和 `FORMAL_PROFILE = "default"`，所以候选集大小被限制在当前 GCC 边数 `m_t` 的 10%-50% 之间，并额外取 degree-product 排名前 10% 的边参与候选生成。

具体步骤：

1. 在当前 GCC 上取所有无向规范边 `edges = canonical_edges(graph)`，边数记为 `m_t`。
2. 用 Louvain 分区识别跨社区边 `cross`：若边 `(u,v)` 的两个端点社区不同，则加入。
3. 计算每个节点的 boundary degree，即连接到其他社区的邻居数量；只要边的任一端点 boundary degree > 0，就加入 `boundary`。
4. 用 `nx.bridges(graph)` 找真实桥边 `bridges`，即删除后会增加连通分量数量的边。
5. 计算共同邻居数；若一条边两端共同邻居数量 `<= 1`，加入 `low_cn`。这是低嵌入 / 近似局部桥信号。
6. 按 `degree(u) * degree(v)` 从高到低排序，取前 `ceil(degree_top_fraction * m_t)` 条边作为 `degree_top`。default 下是前 10%。
7. 取五类边的并集：

```text
raw = cross union boundary union bridges union low_cn union degree_top
```

8. 计算候选数量下限和上限：

```text
min_count = min(m_t, max(1, ceil(min_fraction * m_t)))
max_count = min(m_t, max(min_count, ceil(max_fraction * m_t)))
```

default 下就是至少 `ceil(0.10*m_t)` 条，最多 `ceil(0.50*m_t)` 条。

9. 若 `raw` 超过上限，按结构优先级截断。排序 key 等价于：

```text
priority(edge) =
  more memberships first,
  bridge first,
  cross-community first,
  boundary first,
  low-common-neighbor first,
  larger degree product first,
  deterministic edge id tie-break
```

也就是说，同时属于更多结构类别的边优先；其中真实桥边优先级最高，其次是跨社区、边界、低共同邻居和高度数乘积。

10. 若截断后仍少于 `min_count`，则从全图 degree-product 排序中继续补边，直到达到下限。

11. 最终返回排序后的去重候选边集合 `selected`，并记录 trace 字段，包括 `raw_candidate_count`、`candidate_size`、`candidate_fraction`、`cross_candidate_count`、`boundary_candidate_count`、`bridge_candidate_count`、`low_cn_candidate_count`、`degree_top_candidate_count` 以及各类入选数量。

Louvain 分区不是每步无条件重算。v3 使用漂移触发机制：`modularity_drift_threshold = 0.05`，`cross_ratio_drift_threshold = 0.05`，`boundary_jaccard_threshold = 0.70`，`routing_l1_drift_threshold = 0.25`，综合 `drift_score_threshold = 1.50`。此外有最小重算间隔 `max(5, ceil(0.01*m0))`；但如果当前 GCC 节点不被旧 partition 覆盖，会触发 coverage recompute 例外。

主要结果：

- v3 六图报告中 formal config：AUC gap to M5 约 0.004534，speedup vs M5 约 3.37x。
- CI early-stop rate 只有约 0.6%。
- mean k/n 约 0.986。
- Louvain ratio 44.8%，candidate coverage 83.6%。
- CI diagnostic 中 v3 rows 10346，CI pass rate 0.551，但 early CI-stop 仍只有 0.006；middle/late stage 基本不早停。

结论：v3 候选集有价值，AUC 接近 M5；但 CI 机制几乎不能降低源节点使用。后续 ACES 保留 v3 候选构造，但不把 CI 作为主加速机制。

### v4 neural budget

目标：用神经或学习式预算决定源节点数量。

主要结果：

- budget-only：mean abs AUC gap to M5 0.021535，k/n 0.8463，under-sampling error 0.6667。
- risk-ci：gap 0.018704，CI pass 0.0561。
- router-ci：gap 0.005626，但 k/n 0.9969，几乎没有节省。
- 没有模式同时满足 source reduction、AUC gap 和 runtime gate。

结论：v4 未通过成功标准。它证明“直接学预算”不够安全。

### v5 ExpertRouter

目标：训练专家路由器，在不同状态选择不同专家策略。

主要结果：

- 严格过滤后只有 8 个有效训练行。
- balanced oracle label 约 38%，bridge_fragility 约 38%。
- 路由器在 15/15 attack steps 中都预测 balanced。
- accuracy 0.25，macro F1 0.133，AUC improvement over static-balanced = 0。

结论：v5 ExpertRouter 当前不成功。问题不是一定没有状态差异，而是数据和标签不足，模型退化为 balanced。

### source priority

目标：判断某些 Brandes 源节点是否更有信息量，并从结构特征预测它们。

主要结果：

- dataset 2404 rows，图包括 synthetic_test_001、synthetic_test_002、football。
- pairwise_margin R2 = -0.124。
- source_vector_spearman R2 = -0.556。
- top1_contribution R2 = -0.107。
- Smoke 中 v3/oracle/learned 都出现 top1 agreement 1.0、Spearman 1.0、k/n 1.0，说明该烟测没有提供可用增益。

结论：高信息源节点存在差异，但用当前结构特征预测很弱，不适合继续作为主线。

### candidate pruning / cross_first

目标：减少候选边数量，降低采样排序难度。

主要结果：

- 简单 pruning：threshold 0.25 时 M5 top1 recall 0.6667；threshold 0.50 时 recall 0.4667，不安全。
- recall-first probe：`cross_first` retention 0.60 时 M5 top1 recall 0.9074，mean candidate fraction 0.3019，但 gap improvement 只有 0.0006，entropy reduction 0.0009。
- cross_first attack wrapper：candidate fraction 0.3024，但 M5 top1 candidate recall 0.700，低于 0.85 成功标准，AUC 相对 v3 变差。

结论：静态 recall-first pruning 有一点信号，但进入动态攻击后 top1 recall 不足，不能作为主方向。

### mixed edge scoring

目标：测试 sampled contribution 分布中的信息，例如 `mu`、CV、consensus、structural score，是否能超过 `mu_only`。

主要结果：

- 12 states，football 和 synthetic_test_002，k=16/32/64。
- k32 下 `mu_only` top1 0.250，Spearman 0.7233。
- `grid_mu0.7_struct` top1 0.333，Spearman 0.739，top1 提升 0.083，但不稳定。
- `mu_minus_cv` Spearman 0.826，12/12 states 排序相关提升，但 top1 只有 0.083。

结论：分布统计对排序相关有弱信号，但没有形成可直接拆解的成功方法。

### SALSA allocation

目标：学习 boundary/core/community/random 的源节点配比。

主要结果：

- 状态行 18，oracle ratio 近似均衡：boundary 0.2451，core 0.2513，community 0.2550，random 0.2486。
- Random forest 预测塌缩到 balanced，balanced rate 1.0。
- balanced MAE 0.0055 优于 RF MAE 0.0078。

结论：v3 源节点 strata 分配本身几乎就是 balanced，SALSA allocation 不值得继续。

### IMPACT one-step GCC drop

目标：直接预测候选边删除后的单步 GCC drop。

主要结果：

- 30 states，5 graphs。
- 正的一步 GCC drop states 只有 2 个。
- full-M5 与 exact GCC-drop 的 Spearman 约 0.202。
- sampled mu 与 exact GCC-drop 的 Spearman 约 0.194-0.205。
- k32,K20 recall true best GCC-impact edge 0.367。

结论：一步 GCC drop 信号太稀疏，暂不足以支撑前缀攻击，但它揭示了 M5 分数与 GCC 目标的低相关风险。

## 4. ACES Phase 0.5: Static Betweenness Estimation

ACES 是 Adaptive Cascade Sampling，即自适应级联采样。它的目标不是删掉候选边，而是用两阶段采样更有效地估计候选边的全局边介数。

### ACES 算法思想

对一个图状态：

1. 构造当前 GCC。
2. 构造原始 v3 候选边集合，记候选边数量为 `C`。
3. Stage 1：用 `k1` 个源节点，对所有候选边计算 sampled dependency 均值。
4. 根据 Stage 1 分数，保留 top-K survivor 边。
5. Stage 2：再增加 `k2` 个源节点，但只精修 survivor 边。
6. 对 survivor 边使用 Stage 1+Stage 2 的 refined score；非 survivor 边保留 Stage 1 score。
7. 输出最终 top-1 或排序。

这不是 candidate pruning。Stage 2 只是在计算上延迟精修低优先级边，不是从研究逻辑上永久删除它们。

### 参数网格

从 `aces_phase05_run_metadata.json` 和 Phase 0.5 报告可见：

- fixed k baselines：k = 8, 16, 24, 32, 48, 64。
- 报告重点：k = 16, 32, 48。
- ACES k1：16, 24, 32。
- ACES k2：16, 32。
- survivor K：50, 75, 100, 0.2C, 0.4C。
- gap tau：1.0, 1.5, 2.0, 2.5。
- bootstrap gate probability：0.7, 0.8, 0.9。
- `C` 表示当前候选边数量。

### 源节点顺序与可比性

代码位置：`experiments/aces_phase05_expanded_diagnostic/run_aces_phase05.py`。

关键函数：

- `seeded_pools(strata, graph_id, state_id, seed_index)`：对每个 v3 source type 的节点池做稳定随机打乱。
- `allocate_sources(context, pools, target, existing=None)`：使用 v3 的 `target_quotas` 按 strata 配额选源节点。
- `build_state_context(...)`：调用 v3 的 `routing_proportions` 构造 source profile。
- `get_scores(target)` 和 `get_sources(target, existing)`：缓存同一 seed 下的源节点选择和分数。

结论：

- 源节点顺序不是全图 uniform random。
- 它是 v3 balanced / stratified allocation：先按 boundary、core、community、random 等 strata 分配目标配额，再在每个 strata 内用稳定随机顺序取节点。
- fixed k32、fixed k48 和 ACES 在同一 `graph_id/state_id/seed_index` 下共享可比的 seeded pools。
- ACES Stage 1 使用 quota allocation 取 `k1` 个源节点。
- Stage 2 使用 `existing=stage1_selected`，从同一批 seeded pools 中继续追加到 `k1+k2`，不是独立重采样。
- Stage 2 的 effective cost 按 `len(stage1_flat) + extra_count * survivor_count / candidate_count` 折算。

### Phase 0.5 实验规模

从报告和 metadata：

- evaluated graphs：21。
- effective states：58。
- seeds per state：10。
- small graphs n<80 appendix：7。
- max states per graph：3，state ratios = 0.0, 0.08, 0.35。
- max candidates：1000。
- max k：96。
- runtime 约 250.7 秒。
- `ACES_PHASE05_AUDIT_AND_NEXT_PLAN.md`：not found in current files。

### 关键结果

固定采样基线：

| Method | top1 agreement | NDCG@10 | Spearman | effective cost |
|---|---:|---:|---:|---:|
| fixed_k16 | 0.300000 | 0.787735 | 0.667717 | 15.931034 |
| fixed_k32 | 0.456897 | 0.867128 | 0.727976 | 31.137931 |
| fixed_k48 | 0.518966 | 0.911291 | 0.770327 | 45.137931 |
| fixed_k64 | 0.605172 | 0.939859 | 0.806938 | 58.862069 |

最强 top1 ACES：

- `aces_stability_batch_agree_k132_k232_K0.4C`
- top1 agreement 0.605172。
- NDCG@10 0.935302。
- Spearman 0.769329。
- effective cost 40.941244。
- survival 0.982759。
- gate precision 0.923810。
- gate coverage 0.181034。

最佳 practical near-k32 ACES：

- `aces_stability_batch_agree_k124_k232_K0.4C`
- top1 agreement 0.572414。
- NDCG@10 0.924013。
- Spearman 0.750123。
- effective cost 33.853192。
- survival 0.977586。
- gate precision 0.939759。
- gate coverage 0.143103。

最佳 no-gate cascade 之一：

- `aces_nogate_always_stage2_k132_k232_K0.4C`
- top1 agreement 0.601724。
- NDCG@10 0.939163。
- Spearman 0.771802。
- effective cost 42.284914。
- survival 0.982759。

### Gate 与 survival

Phase 0.5 显示：

- k1=16 最高 survival 约 0.967。
- k1=24 最高 survival 约 0.979。
- k1=32 最高 survival 约 0.983。
- K=75 最好 survival 约 0.945。
- K=100 最好 survival 约 0.979。
- stability batch_agree gate 在 k1=24 时 precision 0.939759，coverage 0.143103。

### Phase 0.5 结论

ACES 有明确的静态边介数估计信号。相对 fixed k32，某些 ACES 配置能用接近 k32-k41 的 effective cost 达到更高的 top1 agreement 和 NDCG@10。

但这只证明“静态估计 full-M5 candidate dependency 更好”，不证明“动态拆解 GCC-AUC 更好”。因此 Phase 0.5 合理地导向 prefix smoke，而不能声称 ACES 已成功。

## 5. Dynamic Prefix Smoke Experiments

### Prefix smoke v1

目标：验证 ACES 静态估计提升是否能转化为动态拆解性能。

设置：

- 图：synthetic_test_003、synthetic_test_005、synthetic_test_009。
- 10 prefix steps。
- seed 20260513。
- 方法：m5_full、fixed_k32、fixed_k48、ACES no-gate k1=24 k2=32 K=0.2C、ACES stability k1=24 k2=32 K=0.4C。

结果：

- sampled methods mean prefix AUC 全部为 1.000。
- M5 mean prefix AUC 为 0.998988。
- no-gate ACES cost 30.44，top1 agreement 0.200。
- stability ACES cost 36.84，top1 agreement 0.200，gate_stop_rate 0。
- 14/15 graph-method pairs GCC flat。

结论：v1 图太不敏感，不能评价拆解效果。它只验证了动态 loop、成本 accounting 和 top1 diagnostics 管线能跑通。

### Prefix smoke v2

目标：在更敏感的非小图上测试 ACES 动态拆解。

设置：

- 图：ca_netscience、bio_diseasome、ia_enron_only。
- 40 prefix steps。
- 每步重建 GCC、Louvain、v3 candidate set。
- 方法：m5_full、fixed_k32、fixed_k48、ACES no-gate k1=24 k2=32 K=0.2C、ACES stability k1=24 k2=32 K=0.4C。

图敏感性：

- bio_diseasome delta GCC after T = 0.732558，first drop step = 3。
- ca_netscience delta = 0.759894，first drop step = 7。
- ia_enron_only delta = 0.118881，first drop step = 6。
- 0/15 graph-method pairs flat。

平均结果：

| Method | prefix AUC | active AUC | delta GCC after T | top1 agreement | cost |
|---|---:|---:|---:|---:|---:|
| m5_full | 0.618579 | 0.564212 | 0.537111 | 1.000000 | 190.258 |
| fixed_k32 | 0.597816 | 0.540659 | 0.579727 | 0.591667 | 32.000 |
| fixed_k48 | 0.599134 | 0.542857 | 0.558608 | 0.700000 | 48.000 |
| ACES no-gate | 0.609018 | 0.553722 | 0.542365 | 0.700000 | 30.453867 |
| ACES stability | 0.608171 | 0.552696 | 0.557316 | 0.683333 | 32.567327 |

关键失败机制：

- ACES no-gate 的 top1 agreement 达到 0.700，高于 fixed k32 的 0.591667。
- 但 ACES no-gate active AUC 比 fixed k32 差 0.013063。
- ia_enron_only 上差距最大，ACES 比 v3/fixed k32 差约 0.0312 active AUC。

结论：ACES 改善了 M5 / top-betweenness imitation，但没有改善 GCC-AUC。更像 M5 不等于更会拆解。

## 6. Hybrid Safeguard Diagnostic

动机：ia_enron_only 中 ACES/M5 可能卡在高边介数的 core-internal edges。这些边有很多替代路径，删除后 GCC 不降。fixed k32 的采样噪声反而会选到低 M5 rank 的外围 fragmenting edges。

设置：

- 图：ia_enron_only。
- 40 prefix steps。
- 方法：m5_full、fixed_k32、fixed_k48、pure ACES no-gate、hybrid stall5 fixed_k32 fallback、hybrid stall3 fixed_k32 fallback。
- stall 规则：如果 GCC 连续 3 或 5 步没有下降，则切换到 fixed k32 fallback；一旦 GCC 下降，再回到 ACES。

结果：

| Method | active AUC | delta GCC after T | cost |
|---|---:|---:|---:|
| m5_full | 0.882044 | 0.118881 | 128.700 |
| fixed_k32 | 0.838749 | 0.209790 | 32.000 |
| fixed_k48 | 0.869704 | 0.132867 | 48.000 |
| pure ACES | 0.869910 | 0.132867 | 30.441989 |
| hybrid_stall5 | 0.865487 | 0.139860 | 31.185 |
| hybrid_stall3 | 0.859523 | 0.153846 | 31.187 |

fallback 行为：

- stall5 有 19 个 fallback steps，其中 2 步带来 GCC drop。
- stall3 有 19 个 fallback steps，其中 4 步带来 GCC drop。

结论：

- hybrid 比 pure ACES 好。
- 但仍远差于 fixed k32。
- stall timing 有帮助，但 fallback 目标不够精准。
- “只在 stall 时随机回到 fixed k32”不能充分恢复 fixed k32 的结构性优势。

## 7. Structural Fallback Diagnostic

动机：FIXED_K32_ADVANTAGE_AUDIT 显示，fixed k32 的有效 GCC-reducing edges 往往是低 M5 rank 的低度外围边。尤其在 step 7 后，fixed k32 的 GCC-reducing edges 的 min endpoint degree 全部为 1 或 2，其中 87.5% 为 1。

结构 fallback 规则：

1. 默认使用 ACES no-gate。
2. 如果 stall_count >= 3，从当前 v3 candidates 中选择 fallback edge。
3. fallback 排序：
   - `min(endpoint_degree)` ascending；
   - 如果实现，则 `common_neighbor_count` ascending；
   - `ACES score` descending。

对比：

- full-candidate fallback：从完整当前 v3 candidates 中选。
- within-ACES-topK fallback：只在 ACES survivor topK 中选。

结果：

| Method | active AUC | delta GCC after T | cost | top1 agreement |
|---|---:|---:|---:|---:|
| fixed_k32 | 0.838749 | 0.209790 | 32.000 | 0.300 |
| pure ACES | 0.869910 | 0.132867 | 30.441989 | 0.450 |
| hybrid_stall3_fixedk32 | 0.859523 | 0.153846 | 31.187339 | 0.275 |
| structural_min_degree | 0.858597 | 0.167832 | 30.441959 | 0.450 |
| structural_min_degree_within_topK | 0.860757 | 0.160839 | 30.441959 | 0.425 |

selected-edge diagnostics：

| Method | mean M5 rank | mean min degree | GCC drop steps | small component rate |
|---|---:|---:|---:|---:|
| fixed_k32 | 7.625 | 6.000 | 10 | 0.250 |
| pure ACES | 2.775 | 10.900 | 4 | 0.100 |
| hybrid_stall3 | 7.421 | 7.105 | 4/19 fallback | 0.2105 |
| structural_min_degree | 33.250 | 1.417 | 7/12 fallback | 0.5833 |
| structural_within_topK | 31.357 | 1.571 | 6/14 fallback | 0.4286 |

结论：

- min-degree structural fallback 明显改善 pure ACES 和 hybrid fixed-k32 fallback。
- 但它仍没有恢复 fixed k32。
- full-candidate fallback 优于 within-ACES-topK，说明有用的外围 fragmenting edges 可能在 ACES topK 之外。
- min degree 是有用信号，但太粗。

## 8. Current Most Important Mechanism Finding

当前最重要机制发现是：边介数估计成功不保证 GCC-AUC 改善。

原因如下：

1. 高边介数边可能是 core-internal edge。它在最短路径上重要，但图中替代路径多，删除后 GCC 不一定下降。
2. fixed k32 的采样噪声有时不是纯坏事。它会把一些低 M5 rank 的外围边提上来，而这些边可能更容易切出小分量。
3. ACES 更准确模仿 M5，因此可能更稳定地选择高介数核心边，反而错过 fragmenting peripheral edges。
4. `min(endpoint_degree)` 能捕捉一部分外围信号，但无法区分“有用的度 2 局部桥”和“无用的度 2 内部边”。
5. 下一层结构信号应关注 common neighbor count、edge embeddedness 和 local bridge-likeness。

术语解释：

- **common neighbor count**：一条边 `(u,v)` 的两个端点共同邻居数量。共同邻居越多，说明这条边嵌在局部三角结构里，替代路径可能越多。
- **edge embeddedness**：边在局部邻域中的嵌入程度，常用共同邻居数量或局部闭三角程度表示。embeddedness 低的边更像桥。
- **local bridge**：局部桥。删除这条边后，两个端点之间没有很短的替代路径。common_neighbor_count = 0 常提示一条边更 bridge-like。

STRUCTURAL_FALLBACK_AUDIT 还指出一个关键 missed productive edge：fixed k32 曾选中 `23|69`，min_degree = 2，common_neighbor_count = 0，GCC 从 119 降到 113。简单 min-degree fallback 没有抓住这类边。

当前已有 `experiments/aces_bridge_fallback_diagnostic/results/bridge_fallback_report.md`，其结果显示：

- bridge fallback 与 min-degree fallback active AUC 相同，均为 0.858597。
- delta GCC after T 均为 0.167832。
- fallback 中 min_degree=1, CN=0 的 7 次选择全部带来 drop。
- min_degree=2, CN=0 的 5 次选择没有带来 drop。
- edge `23|69` 未被 bridge variants 选中。

因此，简单把 common-neighbor 作为 tie-break 还不够。low embeddedness 是正确方向，但需要更精细的状态约束或 fallback 持续策略。

## 9. Current Algorithm Framework

当前可用于论文讨论的算法框架名称：

**Adaptive Source-Sampled Edge Betweenness with Structural Fallback**

中文可称为：**带结构 fallback 的自适应源采样边介数估计拆解算法**。

它仍是研究框架，不是已证明成功的最终算法。

### Pseudocode

```text
Input:
  graph G
  prefix steps T
  ACES parameters: k1 = 24, k2 = 32, K = 0.2C
  stall threshold s = 3

Initialize:
  stall_count = 0
  previous_gcc_size = size of GCC(G)

For step = 1 ... T:
  1. Rebuild current GCC G_t.
  2. Recompute Louvain communities on G_t.
  3. Build original v3 candidate edge set C_t.
  4. Run ACES normal mode:
       a. Stage 1 samples k1 sources using v3 stratified source allocation.
       b. Score all candidate edges by sampled dependency mean.
       c. Keep top K = 0.2 * |C_t| survivor edges.
       d. Stage 2 adds k2 sources from the same seeded source pools.
       e. Refine only survivor edges.
       f. Obtain ACES score for candidate edges.
  5. If stall_count >= 3:
       select fallback edge by:
         min(endpoint_degree) ascending,
         common_neighbor_count ascending,
         ACES score descending.
       mode = structural_fallback
     Else:
       select edge with highest ACES score.
       mode = aces
  6. Delete selected edge.
  7. Recompute GCC size and GCC ratio.
  8. If GCC size decreased:
       stall_count = 0
     Else:
       stall_count += 1
  9. Record:
       selected edge, mode, effective source cost,
       M5 rank if available, GCC ratio,
       endpoint degrees, common-neighbor count,
       runtime.

Output:
  GCC curve, GCC-AUC, active-window AUC, source cost,
  selected-edge diagnostics.
```

注意：这个框架来自当前诊断结果，但 bridge-like fallback 初版未通过成功标准。因此它是“下一步被检验的算法框架”，不能被写成已成功方法。

## 10. Evidence Table

| Method | Goal | Key Parameters | Main Result | Verdict | Paper Use |
|---|---|---|---|---|---|
| M5 full edge betweenness | 强参考基线 | full-M5 candidate dependency | v2 active AUC 0.564212，cost 190.258 | 高成本参考；非全局最优证明 | 定义目标和上界参考 |
| fixed k32 | 低成本 sampled dependency | k=32 | Phase 0.5 top1 0.456897；v2 active AUC 0.540659；ia_enron_only active AUC 0.838749 | 动态强基线 | 必须对比 |
| fixed k48 | 更高采样预算 | k=48 | Phase 0.5 top1 0.518966；v2 top1 0.700，active AUC 0.542857 | 更像 M5，但不一定更好拆解 | 证明估计质量与 GCC 目标可错位 |
| v3 candidate-CI | 候选集 + CI 早停 | epsilon 0.15，CI LCB stop | AUC gap 0.004534；CI early stop 0.6%；mean k/n 0.986 | 候选集有用，CI 加速失败 | 保留 v3 candidate set |
| v4 neural budget | 学习采样预算 | budget/risk/router/soft CI | 最小 gap 与降源不可兼得；router-ci k/n 0.9969 | 不成功 | 负结果，说明预算学习风险 |
| v5 ExpertRouter | 学专家路由 | balanced/bridge 等专家 | router 100% 预测 balanced；AUC improvement 0 | 不成功 | 负结果，说明标签/专家不足 |
| source priority | 学高信息源节点 | RF/LightGBM style diagnostics | R2 为负；smoke 无增益 | 不继续 | 负结果 |
| candidate pruning | 降低候选边数 | simple / cross_first / retention 0.60 | cross_first static recall 0.9074，但 attack recall 0.700 | 不安全 | 说明不能简单剪候选 |
| mixed scoring | 用 contribution 分布改边评分 | mu、CV、consensus、struct | k32 mu_only top1 0.250；mu_minus_cv Spearman +0.103 但 top1 0.083 | 弱信号 | 可作为讨论，不是主线 |
| SALSA allocation | 学 source strata 配比 | boundary/core/community/random | oracle ratios 近 balanced；RF 塌缩 | 不继续 | 负结果 |
| IMPACT one-step GCC drop | 直接学一步 GCC drop | exact one-step impact | positive drop states 仅 2；M5-impact Spearman 0.202 | 信号稀疏 | 支持目标错位解释 |
| ACES Phase 0.5 | 静态边介数估计 | k1 16/24/32，k2 16/32，K 50/75/100/0.2C/0.4C | best practical k1=24,k2=32,K=0.4C：top1 0.572414，NDCG 0.924013，cost 33.853192 | 静态正信号 | 当前最重要正结果 |
| prefix smoke v1 | 动态管线烟测 | 3 synthetic，10 steps | 14/15 GCC flat | 图不敏感 | 验证管线 |
| prefix smoke v2 | 动态敏感图测试 | 3 graphs，40 steps | ACES top1 0.700，但 active AUC 比 fixed k32 差 0.013063 | 翻译失败 | 核心机制发现 |
| hybrid safeguard | stall 后 fixed k32 fallback | stall3/stall5 | stall3 active AUC 0.859523，比 pure ACES 0.869910 好，但不如 fixed k32 0.838749 | 部分改善 | 证明 stall 机制有效但 fallback 不准 |
| structural fallback | stall 后低 min-degree edge | stall3，min degree asc | active AUC 0.858597，fallback drop 7/12 | 部分改善，未恢复 fixed k32 | 支持外围边信号 |
| bridge-like fallback | 加 common neighbor / local bridge | min degree + CN + ACES score | bridge report 中 active AUC 0.858597，与 min-degree 相同；未选中 23\|69 | 初版未成功 | 下一步需更精细低嵌入结构诊断 |

## 11. What Can and Cannot Be Claimed

### Can claim

- ACES 在 Phase 0.5 静态诊断中，相比 fixed k32，在某些配置下显著提高了 full-M5 top1 agreement 和 NDCG@10。
- `aces_stability_batch_agree_k124_k232_K0.4C` 以约 33.85 的 effective source cost 达到 top1 0.572414 和 NDCG@10 0.924013，高于 fixed k32 的 top1 0.456897 和 NDCG@10 0.867128。
- 动态 prefix smoke v2 揭示了边介数估计目标和 GCC-AUC 拆解目标之间的错位。
- fixed k32 的优势不是因为它更像 M5，而可能因为采样噪声选中了低 M5 rank 但更 fragmenting 的外围 / local-bridge-like edges。
- structural fallback 对 pure ACES 有部分改善，并提供了 low endpoint degree / peripheral edge 的诊断证据。
- simple bridge-like fallback 初版没有进一步改善 min-degree fallback，这说明 common-neighbor 需要更精细地进入算法，而不是简单 tie-break。

### Cannot claim

- 不能声称 ACES 已经是成功的动态网络拆解算法。
- 不能声称 ACES 已经在 GCC-AUC 上优于 fixed k32。
- 不能声称 structural fallback 已经恢复 fixed k32。
- 不能声称 bridge-like fallback 已成功。
- 不能声称已经完成 full_eval。
- 不能声称 M5 是 GCC-AUC 的全局最优策略。
- 不能声称 v4 neural budget、v5 ExpertRouter、source priority、candidate pruning 已经成功。

## 12. Next Step

按 `STRUCTURAL_FALLBACK_AUDIT_AND_NEXT_PLAN.md`，当时唯一推荐的下一步诊断是：

**bridge-like fallback diagnostic**。

具体设置：

- 先只在 ia_enron_only 上运行。
- 方法：M5、fixed k32、pure ACES、min-degree fallback、bridge fallback。
- bridge fallback 排序：
  1. `min(endpoint_degree)` ascending；
  2. `common_neighbor_count` ascending；
  3. `ACES score` descending。
- 成功标准：
  - active-window AUC 接近或优于 fixed k32；
  - 优于 pure ACES 和 min-degree fallback；
  - source cost 低于 fixed k48；
  - selected-edge diagnostics 支持 low-degree + low-common-neighbor 解释。

当前文件中已经存在该诊断的初版结果：`experiments/aces_bridge_fallback_diagnostic/results/bridge_fallback_report.md`。结果未达到成功标准：bridge fallback 没有优于 min-degree fallback，也没有恢复 fixed k32。因此如果继续下一轮，不应扩大到三图中评估，而应先修正 bridge-like 结构定义，例如引入更精细的局部桥检测、小侧分量估计、fallback 持续策略，或避免 single-drop 后立刻回到 ACES 的 ping-pong 行为。

## Current Research Story

当前研究故事可以这样概括：我们最初希望用少量源节点近似全局边介数，从而接近 full-M5 的高质量边选择并降低计算成本。v3 证明候选边集合有价值，但 CI 早停几乎不能省源；v4、v5、source priority、candidate pruning 等方向相继暴露出安全性或可学习性不足。ACES Phase 0.5 是目前最强的正结果：两阶段级联采样能在静态 full-M5 边介数估计上明显优于 fixed k32。然而动态 prefix 实验揭示了更关键的问题：更准确模仿 M5 不一定带来更好的 GCC-AUC，因为高边介数边可能是 core-internal edge，而 fixed k32 的噪声有时会选中更能切碎 GCC 的外围局部桥。下一步研究应围绕“源采样边介数 + 结构性 fragmentation fallback”展开，但必须继续以小规模诊断验证，不能直接声称算法已成功。
