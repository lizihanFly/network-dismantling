# MLP Attack Ranker Baseline

Target: `edge_betweenness_rank_pct`. Lower predicted values are removed earlier.

Training uses synthetic `train` only. Validation, synthetic test, and real external test are never mixed into fitting.

## Ranking Quality

- real_external_test: Spearman=0.703, Kendall=0.535, MAE=0.273, top-5% overlap=0.331
- synthetic_test: Spearman=0.803, Kendall=0.613, MAE=0.137, top-5% overlap=0.535
- val: Spearman=0.777, Kendall=0.587, MAE=0.146, top-5% overlap=0.466

## Attack AUC

- real_external_test: best=M5 dynamic edge betweenness (mean AUC=0.177); MLP mean AUC=0.400
- synthetic_test: best=M5 dynamic edge betweenness (mean AUC=0.397); MLP mean AUC=0.679

## Generated Files

- `ranking_metrics_by_graph.csv`
- `ranking_metrics_aggregate.csv`
- `attack_summary_by_graph.csv`
- `attack_summary_aggregate.csv`
- `attack_curves.csv`
- `mlp_attack_ranker.pkl`
- `*_auc_by_method.png`
- `*_example_curves.png`
