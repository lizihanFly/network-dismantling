# SASB-N Node Dismantling Pilot Report

## 研究状态

本文件当前状态：`pilot_complete`。smoke 验证只用于检查实验管线，不是科学证据。
本 pilot 是节点 SASB-N 实验，不使用原始 edge SASB 的候选边集合，也不与 edge AUC 混合。

## 研究问题与定义

研究问题是：在相同当前 GCC、相同源点预算和相同种子下，结构化源点是否产生有条件有益的结构偏差。
SASB-N-structured 动态选择源点；random-source 均匀采样；degree-source 按当前节点度选择；frozen-source 只在初始 GCC 选择 structured 源点，后续只保留仍存在的源点。
节点候选集合始终是当前最大连通分量的全部节点。

## 数据和抽样

本报告覆盖 synthetic45, realworld_completed，包含 24 个 pilot 网络。选网只使用初始 GCC 节点数和固定 seed 的 Louvain 模块度，未使用 SASB AUC 或任何攻击结果。
完整 pilot 预算为 B=16,32,64,128，种子为 20260513--20260517。M5、dynamic-degree、dynamic-closeness、dynamic-k-core 每网络运行一次；random 每网络每种子运行一次，预算不参与 random 排序。

## 指标和差值

`delta_m5 = AUC_SASB - AUC_M5`；`delta_policy = AUC_structured - AUC_random_source`。AUC 越低越好，因此负值表示前者更好。统计汇总见 `pilot_statistical_summary.csv`。

## 八个决策问题

- 1. structured 是否比 random-source 稳定？见 `delta_policy_random_source` 的逐预算 paired 结果；只有跨网络方向稳定且置信区间支持时，才可称为 pilot 支持。
- 2. dynamic-source 是否比 frozen-source 稳定？这里用 structured 与 frozen-source 的配对差值回答；不能把动态重算的优势写成结构化源点本身的普遍优势。
- 3. 64 个源点是否已经足够？比较 B=64 与 B=128 的 AUC 差异及其置信区间；若收益接近零，才可把 B=64 视为候选折中点。
- 4. 128 个源点的额外收益是否值得额外成本？必须同时查看 AUC 改善和 runtime 增长，不能只看 AUC。
- 5. SASB-N 的优势是否只出现在某些网络？按网络输出 paired delta，并与 `node_mechanism_metrics.csv` 的模块度、桥接节点比例等结构量关联。
- 6. 是否值得继续运行 73 个网络的全量正式实验？本报告只给出 pilot 级建议；不能因为 pilot 平均值有利就自动批准全量。
- 7. 正式实验保留哪些 source_budget？由 B=64/128 的收益-成本比较决定；在没有稳定差异前保留四档。
- 8. 当前结果能否支持论文结论？即使 pilot 完整，也只能支持有条件的 pilot 证据；普遍优于 M5 仍不能写入论文。

## 数值结果摘要

下表按已完成运行汇总；random 和确定性基线只显示配置中实际执行的预算。

| method | source_budget | runs | mean normalized AUC | mean runtime (s) |
| --- | --- | --- | --- | --- |
| SASB-N-structured | 16 | 120 | 0.1986 | 11.859 |
| SASB-N-structured | 32 | 120 | 0.1904 | 12.149 |
| SASB-N-structured | 64 | 120 | 0.1848 | 14.565 |
| SASB-N-structured | 128 | 120 | 0.1826 | 18.810 |
| SASB-N-random-source | 16 | 120 | 0.1856 | 9.455 |
| SASB-N-random-source | 32 | 120 | 0.1835 | 10.110 |
| SASB-N-random-source | 64 | 120 | 0.1816 | 12.893 |
| SASB-N-random-source | 128 | 120 | 0.1809 | 16.172 |
| SASB-N-degree-source | 16 | 120 | 0.1980 | 10.413 |
| SASB-N-degree-source | 32 | 120 | 0.1911 | 12.686 |
| SASB-N-degree-source | 64 | 120 | 0.1867 | 12.371 |
| SASB-N-degree-source | 128 | 120 | 0.1821 | 16.700 |
| SASB-N-frozen-source | 16 | 120 | 0.2099 | 11.040 |
| SASB-N-frozen-source | 32 | 120 | 0.2003 | 8.597 |
| SASB-N-frozen-source | 64 | 120 | 0.1890 | 9.699 |
| SASB-N-frozen-source | 128 | 120 | 0.1839 | 12.397 |
| M5 | 16 | 24 | 0.1813 | 238.825 |
| dynamic-degree | 16 | 24 | 0.2134 | 1.555 |
| dynamic-closeness | 16 | 24 | 0.1968 | 29.828 |
| dynamic-k-core | 16 | 24 | 0.2144 | 1.965 |
| random | 16 | 120 | 0.3781 | 4.083 |

### Source budget 与效果/成本

源点策略的 budget 关系如下。AUC 越低越好，runtime 为单次运行的平均值；这张表不把预算增加本身解释成效果改进。

| source policy | budget | runs | mean normalized AUC | mean runtime (s) |
| --- | --- | --- | --- | --- |
| SASB-N-structured | 16 | 120 | 0.1986 | 11.859 |
| SASB-N-structured | 32 | 120 | 0.1904 | 12.149 |
| SASB-N-structured | 64 | 120 | 0.1848 | 14.565 |
| SASB-N-structured | 128 | 120 | 0.1826 | 18.810 |
| SASB-N-random-source | 16 | 120 | 0.1856 | 9.455 |
| SASB-N-random-source | 32 | 120 | 0.1835 | 10.110 |
| SASB-N-random-source | 64 | 120 | 0.1816 | 12.893 |
| SASB-N-random-source | 128 | 120 | 0.1809 | 16.172 |
| SASB-N-degree-source | 16 | 120 | 0.1980 | 10.413 |
| SASB-N-degree-source | 32 | 120 | 0.1911 | 12.686 |
| SASB-N-degree-source | 64 | 120 | 0.1867 | 12.371 |
| SASB-N-degree-source | 128 | 120 | 0.1821 | 16.700 |
| SASB-N-frozen-source | 16 | 120 | 0.2099 | 11.040 |
| SASB-N-frozen-source | 32 | 120 | 0.2003 | 8.597 |
| SASB-N-frozen-source | 64 | 120 | 0.1890 | 9.699 |
| SASB-N-frozen-source | 128 | 120 | 0.1839 | 12.397 |

### 配对差值、胜平负与 bootstrap CI

统计单位是网络：同一网络内先对 5 个 seed 的 normalized AUC 求均值，再进行配对比较。因此 `n_pairs` 是网络数，胜/平/负也是网络级统计；M5 等确定性基线只运行一次。

| budget | comparison | n_pairs | mean delta | wins/ties/losses | CI low | CI high | Wilcoxon p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16 | SASB-N-structured vs M5 | 12 | 0.0089 | 2/1/9 | 0.0031 | 0.0163 | 0.009 |
| 16 | SASB-N-structured vs M5 | 12 | 0.0255 | 0/0/12 | 0.0161 | 0.0348 | 0.000 |
| 16 | SASB-N-structured vs SASB-N-degree-source | 12 | -0.0006 | 5/1/6 | -0.0044 | 0.0026 | 0.966 |
| 16 | SASB-N-structured vs SASB-N-degree-source | 12 | 0.0018 | 7/0/5 | -0.0018 | 0.0062 | 0.791 |
| 16 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0083 | 11/0/1 | -0.0141 | -0.0033 | 0.007 |
| 16 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0143 | 11/0/1 | -0.0229 | -0.0064 | 0.005 |
| 16 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0066 | 3/0/9 | 0.0016 | 0.0130 | 0.042 |
| 16 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0192 | 1/0/11 | 0.0124 | 0.0260 | 0.001 |
| 32 | SASB-N-structured vs M5 | 12 | 0.0048 | 2/1/9 | 0.0019 | 0.0085 | 0.007 |
| 32 | SASB-N-structured vs M5 | 12 | 0.0132 | 1/0/11 | 0.0062 | 0.0197 | 0.005 |
| 32 | SASB-N-structured vs SASB-N-degree-source | 12 | -0.0024 | 6/1/5 | -0.0069 | 0.0005 | 0.465 |
| 32 | SASB-N-structured vs SASB-N-degree-source | 12 | 0.0009 | 5/0/7 | -0.0032 | 0.0049 | 0.677 |
| 32 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0109 | 12/0/0 | -0.0173 | -0.0052 | 0.000 |
| 32 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0090 | 12/0/0 | -0.0145 | -0.0049 | 0.000 |
| 32 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0045 | 1/1/10 | 0.0017 | 0.0078 | 0.005 |
| 32 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0091 | 2/0/10 | 0.0040 | 0.0142 | 0.012 |
| 64 | SASB-N-structured vs M5 | 12 | 0.0022 | 3/1/8 | 0.0006 | 0.0043 | 0.027 |
| 64 | SASB-N-structured vs M5 | 12 | 0.0047 | 3/0/9 | -0.0002 | 0.0094 | 0.077 |
| 64 | SASB-N-structured vs SASB-N-degree-source | 12 | -0.0003 | 7/2/3 | -0.0014 | 0.0009 | 0.695 |
| 64 | SASB-N-structured vs SASB-N-degree-source | 12 | -0.0036 | 9/1/2 | -0.0058 | -0.0013 | 0.010 |
| 64 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0069 | 11/1/0 | -0.0126 | -0.0023 | 0.001 |
| 64 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0015 | 8/0/4 | -0.0033 | 0.0003 | 0.151 |
| 64 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0025 | 3/1/8 | 0.0007 | 0.0047 | 0.014 |
| 64 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0039 | 4/0/8 | 0.0006 | 0.0072 | 0.064 |
| 128 | SASB-N-structured vs M5 | 12 | 0.0014 | 4/3/5 | 0.0001 | 0.0030 | 0.320 |
| 128 | SASB-N-structured vs M5 | 12 | 0.0013 | 1/5/6 | 0.0003 | 0.0024 | 0.031 |
| 128 | SASB-N-structured vs SASB-N-degree-source | 12 | 0.0010 | 1/6/5 | -0.0000 | 0.0026 | 0.156 |
| 128 | SASB-N-structured vs SASB-N-degree-source | 12 | 0.0002 | 4/6/2 | -0.0010 | 0.0014 | 1.000 |
| 128 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0016 | 9/2/1 | -0.0038 | -0.0003 | 0.005 |
| 128 | SASB-N-structured vs SASB-N-frozen-source | 12 | -0.0010 | 4/4/4 | -0.0031 | 0.0008 | 0.641 |
| 128 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0015 | 3/2/7 | 0.0001 | 0.0033 | 0.067 |
| 128 | SASB-N-structured vs SASB-N-random-source | 12 | 0.0019 | 1/4/7 | 0.0004 | 0.0034 | 0.039 |

## Pilot-level interpretation

以下判断只适用于本 pilot 的 24 个网络，不替代完整网络集合上的正式实验。delta<0 表示 structured 的 AUC 更低。

### synthetic45

- structured vs random-source：B=16: 0.0192 (W/T/L=1/0/11); B=32: 0.0091 (W/T/L=2/0/10); B=64: 0.0039 (W/T/L=4/0/8); B=128: 0.0019 (W/T/L=1/4/7)。这组 delta 的符号决定 structured 是更好还是更差；不能据此写成普遍优势。
- structured vs M5：B=16: 0.0255 (W/T/L=0/0/12); B=32: 0.0132 (W/T/L=1/0/11); B=64: 0.0047 (W/T/L=3/0/9); B=128: 0.0013 (W/T/L=1/5/6)。M5 是完整动态节点介数基线，当前结果只能说明二者的 pilot 差异。
- structured vs frozen-source：B=16: -0.0143 (W/T/L=11/0/1); B=32: -0.0090 (W/T/L=12/0/0); B=64: -0.0015 (W/T/L=8/0/4); B=128: -0.0010 (W/T/L=4/4/4)。该比较直接反映动态重新选择源点相对于冻结初始源点的差异。
- structured vs degree-source：B=16: 0.0018 (W/T/L=7/0/5); B=32: 0.0009 (W/T/L=5/0/7); B=64: -0.0036 (W/T/L=9/1/2); B=128: 0.0002 (W/T/L=4/6/2)。若 CI 跨过 0，应视为未分出稳定差异。
- B=64 与 B=128：structured 平均 AUC 为 0.2589 -> 0.2555，平均 runtime 为 1.489s -> 2.218s（runtime 变化 48.9%）。因此 B=64 可作为成本-效果候选，B=128 更适合作为敏感性档位；这不能证明 B=64 在所有网络上已经足够。
- full experiment 决策：pilot 只能用于决定是否值得继续以及优先保留哪些 budget；不能把本 pilot 的平均差异写成 SASB-N 普遍优于 M5，也不能事后按 AUC 筛选网络。

### realworld_completed

- structured vs random-source：B=16: 0.0066 (W/T/L=3/0/9); B=32: 0.0045 (W/T/L=1/1/10); B=64: 0.0025 (W/T/L=3/1/8); B=128: 0.0015 (W/T/L=3/2/7)。这组 delta 的符号决定 structured 是更好还是更差；不能据此写成普遍优势。
- structured vs M5：B=16: 0.0089 (W/T/L=2/1/9); B=32: 0.0048 (W/T/L=2/1/9); B=64: 0.0022 (W/T/L=3/1/8); B=128: 0.0014 (W/T/L=4/3/5)。M5 是完整动态节点介数基线，当前结果只能说明二者的 pilot 差异。
- structured vs frozen-source：B=16: -0.0083 (W/T/L=11/0/1); B=32: -0.0109 (W/T/L=12/0/0); B=64: -0.0069 (W/T/L=11/1/0); B=128: -0.0016 (W/T/L=9/2/1)。该比较直接反映动态重新选择源点相对于冻结初始源点的差异。
- structured vs degree-source：B=16: -0.0006 (W/T/L=5/1/6); B=32: -0.0024 (W/T/L=6/1/5); B=64: -0.0003 (W/T/L=7/2/3); B=128: 0.0010 (W/T/L=1/6/5)。若 CI 跨过 0，应视为未分出稳定差异。
- B=64 与 B=128：structured 平均 AUC 为 0.1107 -> 0.1098，平均 runtime 为 27.642s -> 35.402s（runtime 变化 28.1%）。因此 B=64 可作为成本-效果候选，B=128 更适合作为敏感性档位；这不能证明 B=64 在所有网络上已经足够。
- full experiment 决策：pilot 只能用于决定是否值得继续以及优先保留哪些 budget；不能把本 pilot 的平均差异写成 SASB-N 普遍优于 M5，也不能事后按 AUC 筛选网络。

### 完整性与运行时间

完成记录：2136 / 2136；unfinished：0；normalized_auc NaN：0；runtime_seconds NaN：0。
已完成运行的 runtime_seconds 累计为 31012.307 秒；该值是各运行 CPU/算法计时之和，不等同于并行作业的墙钟时间。

## 运行量和成本

本报告范围预计运行 2136 条记录：source policies 1920 条，random 120 条，确定性基线 96 条。
断点目录按 `dataset_group/graph_id/method/B{source_budget}/seed{seed}` 组织，已完成且 status=finished 的运行会复用，不会覆盖旧的 edge/node 结果目录。
预计运行时间约为 28.70--114.79 小时（规划区间，不是实测保证）。
估计假设和分方法明细见 `pilot_runtime_estimate.json`。

## 证据边界

本 pilot 不删除失败网络，不按 SASB AUC 事后筛选主要证据，不把 runtime 下降写成瓦解效果提升。任何论文结论都必须基于完整网络集合、逐网络配对差值和统计检验。
