# Candidate Damage Predictor

This experiment changes the supervised target from teacher-rank imitation to direct one-step damage prediction.

At each dynamic state, candidates are built from the top-k edges suggested by M2/M4/M5/M7/M8. The model predicts `gcc_delta` for each candidate and removes the edge with the largest predicted damage.

## Config

- model_type=gbdt
- top_k=5
- random_candidate_count=8
- bridge_top_k=8
- rollout_policy=m5
- max_train_steps=30
- train_max_remove_ratio=0.15

## Candidate Ranking Quality

- synthetic_test: states=60, top1_hit=1.000, Spearman=0.458, chosen/best delta=1.000

## Attack AUC

- synthetic_test: best=M5 dynamic edge betweenness (mean AUC=0.097); damage predictor mean AUC=0.099
