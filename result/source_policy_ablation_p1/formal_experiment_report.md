# P1 Source-Policy Ablation Formal Experiment Report

## 1. 主要结果

- `realworld_completed`: structured - matched normalized GCC-AUC mean = `-0.000160`; 95% CI = `[-0.004517, 0.004198]`; wins/losses/ties = `14/10/0`.
- `synthetic45`: structured - matched normalized GCC-AUC mean = `0.000774`; 95% CI = `[-0.003706, 0.005254]`; wins/losses/ties = `25/20/0`.

A negative paired difference means `SASB-structured` has lower normalized GCC-AUC and therefore stronger dismantling than `SASB-matched` on that network.

## 2. 是否支持 H1

- `realworld_completed`: `directionally weak but inconclusive; it is not sufficient support for H1`.
- `synthetic45`: `does not support H1`.

## 3. 是否只能支持 candidate bias

- `realworld_completed`: structured-random mean diff `0.001307`, structured-matched mean diff `-0.000160`; `candidate-bias-only interpretation remains plausible because structured-matched is statistically inconclusive`.
- `synthetic45`: structured-random mean diff `0.002444`, structured-matched mean diff `0.000774`; `candidate-bias-only interpretation is more consistent than source-policy bias`.

## 4. SASB 在哪些网络上有效

- `realworld_completed` structured beats matched on `14` networks. Strongest examples: soc_wiki_vote, bio_celegansneural, inf_usair97, ia_email_univ, ia_enron_only, web_edu, inf_euroroad, bio_celegans, ca_netscience, bio_diseasome.
- `synthetic45` structured beats matched on `25` networks. Strongest examples: synthetic_test_002, synthetic_test_009, synthetic_test_041, synthetic_test_043, synthetic_test_024, synthetic_test_004, synthetic_test_003, synthetic_test_028, synthetic_test_035, synthetic_test_025.

## 5. SASB 在哪些网络上失效

- `realworld_completed` structured loses to matched on `10` networks. Strongest failures: bio_sc_ts, web_polblogs, ia_infect_dublin, bio_celegans_dir, bio_grid_plant, rt_retweet, rt_twitter_copen, football, ia_infect_hyper, inf_power.
- `synthetic45` structured loses to matched on `20` networks. Strongest failures: synthetic_test_010, synthetic_test_007, synthetic_test_031, synthetic_test_033, synthetic_test_030, synthetic_test_040, synthetic_test_001, synthetic_test_038, synthetic_test_032, synthetic_test_021.

## 5b. 失败网络和异常网络分析

- `realworld_completed` status `finished`: `72` method-network runs.
- `synthetic45` status `finished`: `135` method-network runs.
- `realworld_completed` longest runtime examples: ia_email_univ:matched:978.0s, ia_email_univ:structured:848.1s, ia_email_univ:random:834.7s, web_edu:matched:393.1s, web_edu:structured:380.6s.
- `synthetic45` longest runtime examples: synthetic_test_019:matched:43.6s, synthetic_test_003:matched:40.2s, synthetic_test_019:structured:39.9s, synthetic_test_019:random:38.6s, synthetic_test_003:random:36.8s.

## 6. 可能机制

- `realworld_completed` Spearman relation between mechanism differences and AUC differences: conditional_mean_delta_gcc_diff_spearman_with_auc_diff=-0.083; first_positive_drop_step_diff_spearman_with_auc_diff=-0.068; inter_community_ratio_diff_spearman_with_auc_diff=-0.238; mean_edge_embeddedness_diff_spearman_with_auc_diff=-0.047; positive_delta_gcc_rate_diff_spearman_with_auc_diff=0.122.
- `synthetic45` Spearman relation between mechanism differences and AUC differences: conditional_mean_delta_gcc_diff_spearman_with_auc_diff=-0.292; first_positive_drop_step_diff_spearman_with_auc_diff=0.450; inter_community_ratio_diff_spearman_with_auc_diff=-0.311; mean_edge_embeddedness_diff_spearman_with_auc_diff=-0.178; positive_delta_gcc_rate_diff_spearman_with_auc_diff=0.371.

## 7. 论文中可以写的结论

P1 can be written as a controlled ablation that separates source-policy bias from candidate-set bias by holding the candidate builder, source budget, seed schedule, and dynamic GCC evaluation fixed.
Any claim about source-policy bias should be tied specifically to the structured-vs-matched paired AUC result, not to smoke validation or structured-vs-random alone.

## 8. 仍然不能声称的内容

- Do not claim that code execution proves method effectiveness.
- Do not claim universal superiority if realworld and synthetic results diverge or if wins are concentrated in a small subset.
- Do not claim source-policy bias from structured-vs-random unless structured also beats matched.

## 9. 是否需要下一轮实验

A next experiment is needed if the structured-vs-matched effect is small, dataset-dependent, or contradicted by mechanism/cost indicators. Candidate-set ablations or repeated-seed robustness should then be prioritized.

## Output Files

- `D:\network collapse\result\source_policy_ablation_p1\formal_results.csv`
- `D:\network collapse\result\source_policy_ablation_p1\paired_comparisons.csv`
- `D:\network collapse\result\source_policy_ablation_p1\effect_sizes.csv`
- `D:\network collapse\result\source_policy_ablation_p1\mechanism_summary.csv`
- `D:\network collapse\result\source_policy_ablation_p1\cost_summary.csv`
- `D:\network collapse\result\source_policy_ablation_p1\plots`
