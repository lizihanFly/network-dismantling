# Candidate Damage Predictor

This experiment changes the supervised target from teacher-rank imitation to direct 3-step damage prediction.

At each dynamic state, candidates are built from M2/M4/M5/M7/M8 plus random and bridge candidates. The model predicts candidate damage and removes the edge with the largest predicted damage.

## Config

- model_type=gbdt
- top_k=5
- random_candidate_count=6
- bridge_top_k=6
- damage_horizon=3
- damage_rollout_policy=m5
- rollout_policy=m5
- max_train_steps=15
- train_max_remove_ratio=0.1

## Candidate Ranking Quality

- synthetic_test: states=30, top1_hit=0.533, Spearman=0.099, chosen/best delta=0.589

## Attack AUC

- synthetic_test: best=M5 dynamic edge betweenness (mean AUC=0.066); damage predictor mean AUC=0.068
