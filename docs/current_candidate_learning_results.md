# Current Candidate Learning Results

This note records the currently useful candidate-learning results that should be
kept in GitHub. Raw run outputs, model files, large candidate rows, and generated
datasets are intentionally left out of version control.

## Experiment Setting

- Data: `data/ml_attack_dataset_balanced_pilot`
- Split: `synthetic_test`
- Balanced groups: SBM strong, SBM medium, SBM weak, SBM mixed, BA, ER, WS
- Evaluation size: 2 test graphs per structural group
- Attack budget: about 20% edge removal
- Model: `pairwise_logistic`
- Target: one-step candidate damage ranking from `gcc_delta`
- Dynamic policy: GCC is updated after each deletion. Louvain, candidate
  features, full M5 edge betweenness, sampled edge betweenness, and stale edge
  betweenness candidates are recomputed according to each method definition.
- Graph convention: undirected, unweighted simple graphs.

Lower AUC and lower normalized AUC indicate faster network collapse.

## Candidate Source Comparison

| Setting | Candidate AUC | M5 AUC | Delta vs M5 | Candidate normalized AUC | Final GCC | Candidate time | M5 time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sampled EB k=8 | 0.158602 | 0.150646 | +0.007956 | 0.952448 | 0.896082 | 15.35s | 7.28s |
| sampled EB k=16 | 0.158056 | 0.150646 | +0.007410 | 0.948687 | 0.897680 | 16.37s | 7.51s |
| sampled EB k=32 | 0.157336 | 0.150646 | +0.006690 | 0.943257 | 0.887565 | 16.16s | 7.21s |
| stale EB interval=5 + path bridge | 0.160008 | 0.150646 | +0.009362 | 0.960477 | 0.906603 | 18.26s | 7.65s |
| stale EB interval=10 + path bridge | 0.161572 | 0.150646 | +0.010926 | 0.968406 | 0.935677 | 17.36s | 7.47s |

## Interpretation

- M5 dynamic edge betweenness remains the strongest baseline in this comparison.
- Sampled EB candidates are more promising than stale EB candidates in the
  current candidate-learning setup.
- Increasing sampled EB from k=8 to k=32 improves AUC slightly, but does not
  close the gap to M5.
- Stale EB with interval 5 is better than interval 10, but both are weaker than
  sampled EB and M5.
- Candidate learning still clearly beats the weaker M2/M4/M7/M8 baselines in
  these balanced group2 experiments, but it should not be claimed to beat M5.

## Structural Findings

For sampled EB k=16, the strongest structural signal is conditional performance:

| Structure | Candidate vs M5 AUC delta | Current reading |
| --- | ---: | --- |
| BA | -0.002702 | Candidate slightly better |
| ER | -0.000570 | Candidate slightly better |
| SBM mixed | -0.002713 | Candidate slightly better |
| SBM medium | +0.001821 | Candidate slightly worse |
| SBM strong | +0.001789 | Candidate slightly worse |
| SBM weak | +0.005992 | Candidate worse |
| WS | +0.048253 | Candidate much worse |

This supports the current research framing: candidate learning is not globally
stronger than dynamic edge betweenness. Its value is structure-dependent, and WS
plus weak-community graphs are the main failure cases.

## Useful Result Directories

These directories contain the local raw outputs used for this note:

- `result/candidate_damage_pairwise_logistic_balanced_group2_20pct_sampled_eb_k8`
- `result/candidate_damage_pairwise_logistic_balanced_group2_20pct_sampled_eb_k16_matched`
- `result/candidate_damage_pairwise_logistic_balanced_group2_20pct_sampled_eb_k32`
- `result/candidate_damage_pairwise_logistic_balanced_group2_20pct_stale_eb_i5_path_bridge`
- `result/candidate_damage_pairwise_logistic_balanced_group2_20pct_stale_eb_i10_path_bridge`

## Next Step

The next valuable experiment is a larger balanced `group10` run using sampled EB
candidate sources, plus the existing full-M5 and no-M5 comparisons. Stale EB is
not the priority unless a cheaper implementation is added.
