# Candidate Damage Predictor

This experiment changes the supervised target from teacher-rank imitation to direct 1-step damage prediction.

At each dynamic state, candidates are built from M2/M4/M5/M7/M8 plus optional random and bridge candidates. The model predicts candidate damage and removes the edge with the largest predicted damage.

## Config

- model_type=gbdt
- top_k=5
- random_candidate_count=8
- bridge_top_k=8
- damage_horizon=1
- damage_rollout_policy=m5
- rollout_policy=m5
- max_train_steps=30
- train_max_remove_ratio=0.15

## Candidate Ranking Quality

- synthetic_test: states=180, top1_hit=1.000, Spearman=0.298, chosen/best delta=1.000

## Attack AUC

- synthetic_test: best=M5 dynamic edge betweenness (mean AUC=0.098); damage predictor mean AUC=0.099
