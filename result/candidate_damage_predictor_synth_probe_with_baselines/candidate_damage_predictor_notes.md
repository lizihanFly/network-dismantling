# Candidate Damage Predictor

This experiment changes the supervised target from teacher-rank imitation to direct one-step damage prediction.

At each dynamic state, candidates are built from the top-k edges suggested by M2/M4/M5/M7/M8. The model predicts `gcc_delta` for each candidate and removes the edge with the largest predicted damage.

## Config

- model_type=gbdt
- top_k=5
- rollout_policy=m5
- max_train_steps=30
- train_max_remove_ratio=0.15

## Candidate Ranking Quality

- synthetic_test: states=60, top1_hit=0.950, Spearman=0.037, chosen/best delta=0.625

## Attack AUC

- synthetic_test: best=M5 dynamic edge betweenness (mean AUC=0.097); damage predictor mean AUC=0.100
