# ML Attack Dataset

This folder contains edge-level data for learning attack rankings.

## Splits

- `train`: synthetic graphs used for model fitting.
- `val`: synthetic graphs used for model selection.
- `synthetic_test`: held-out synthetic graphs.
- `real_external_test`: real networks only. Do not use this split for fitting or tuning.

Default generation creates 120 synthetic graphs:

- 84 train graphs
- 18 validation graphs
- 18 synthetic test graphs

The current external test set contains the five real networks already used in
`attack_compare.ipynb`: `karate`, `football`, `ca_netscience`, `bio_diseasome`,
and `inf_USAir97`.

## Files

- `edge_features_all.csv`: all edge-level rows.
- `edge_features_synthetic_train.csv`: train rows only.
- `edge_features_synthetic_val.csv`: validation rows only.
- `edge_features_synthetic_test.csv`: held-out synthetic test rows only.
- `edge_features_real_external_test.csv`: real-network external test rows only.
- `graph_metadata.csv`: one row per graph.
- `manifest.json`: generation settings and label descriptions.
- `synthetic_graphs/`: generated synthetic graphs in GML format.

## Labels

For a first MLP ranking baseline, start with one of these targets:

- `edge_betweenness`: M5 teacher score. Higher is more central.
- `edge_betweenness_rank_pct`: graph-normalized M5 rank. Lower is better.
- `gcc_delta`: one-step largest connected component ratio drop after removing the edge.
- `gcc_delta_rank_pct`: graph-normalized one-step damage rank. Lower is better.

Do not train with `edge_betweenness` as both an input feature and the target unless
you intentionally want a teacher-copy sanity check. For a more meaningful MLP,
exclude direct teacher columns and train from local/community/node features.

## Regeneration

Run from the repository root:

```powershell
D:\ana\python.exe scripts\build_ml_attack_dataset.py
```

To generate a different synthetic count:

```powershell
D:\ana\python.exe scripts\build_ml_attack_dataset.py --num-synthetic 300
```
