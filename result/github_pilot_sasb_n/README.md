# SASB-N node dismantling pilot

这是 SASB-N 节点瓦解 pilot 的 curated 发布包，包含核心运行代码、实验配置、最终汇总数据和核心图表。

## 内容

- `code/`：运行 pilot 所需的核心 Python 文件。
- `results/`：24 个网络的逐网络/方法最终汇总、统计摘要、预算与 source-policy 消融结果，以及实验报告。
- `figures/`：GCC 瓦解曲线图。

## 实验范围

- 数据集：`synthetic45` 与 `realworld_completed`，各 12 个网络。
- source budget：16、32、64、128。
- 方法：SASB-N structured、random-source、degree-source、frozen-source，以及 M5 和动态基线。
- 主要指标：normalized GCC-AUC、逐网络配对差值和 runtime；AUC 越低越好。

## 运行说明

从仓库根目录运行：

```powershell
python scripts/run_node_dismantling_comparison.py --stage pilot-config
python scripts/run_node_dismantling_comparison.py --stage pilot-run --pilot-config result/node_sasb_paper/pilot_config.json
python scripts/run_node_dismantling_comparison.py --stage pilot-aggregate --pilot-config result/node_sasb_paper/pilot_config.json
```

数据集文件仍使用仓库原有 `data/` 目录；本文件夹不复制原始网络数据。

## 排除项

本包刻意不包含逐步 `curves.csv`、`source_step_metrics.csv`、formal 重复导出、逐运行缓存目录和 smoke 中间文件，以避免把中间结果当作核心证据并控制仓库体积。

## 证据边界

这是 pilot 结果，不是全量正式实验。报告中的差异只能支持有条件的 pilot 观察，不能据此声称 SASB-N 在所有网络上普遍优于 M5 或 random-source。
