# Balanced candidate learning progress

This note records the current balanced synthetic experiments for candidate damage learning.

## Data

- Dataset: `data/ml_attack_dataset_balanced_pilot`
- Mode: balanced synthetic generation
- Groups: `sbm_strong`, `sbm_medium`, `sbm_weak`, `sbm_mixed`, `ba`, `er`, `ws`
- Split counts: 35 train, 14 validation, 35 synthetic test
- Real external graphs are still included in the dataset but were not used in these pilot attacks.

All graphs are treated as undirected, unweighted simple graphs. Experiments attack the current GCC. During dynamic attack, GCC, Louvain communities, edge betweenness, and candidate features are recomputed after deletions when required by the method.

## Main group2 20% comparison

These runs use 2 test graphs per structural group and attack up to 20% removed edges.

| Setting | Candidate sources at attack | Mean AUC | Normalized AUC | Final GCC | Mean time (s) |
| --- | --- | ---: | ---: | ---: | ---: |
| Candidate, with M5 candidates | `m2,m4,m5,m7,m8,bridge,random` | 0.150834 | 0.947835 | 0.890007 | 19.585 |
| Candidate, no M5 candidates | `m2,m4,m7,m8,bridge,random` | 0.155270 | 0.973023 | 0.947975 | 13.456 |
| Candidate, no M5 wide candidates | `m2,m4,m7,m8,bridge,random`, wider bridge/random | 0.154893 | 0.971021 | 0.946587 | 13.192 |
| Candidate, train with M5 and attack without M5 wide | train: all, attack: no M5 wide | 0.153035 | 0.960592 | 0.919423 | 17.456 |
| Candidate, sampled EB k=16 | `m2,m4,sampled_eb,m7,m8,bridge,random` | 0.151017 | 0.948829 | 0.893656 | 13.401 |
| M5 dynamic edge betweenness | M5 baseline | 0.144961 | 0.914363 | 0.780926 | 10.241 |

Lower AUC and lower normalized AUC mean faster network collapse.

Current interpretation:

- M5 dynamic edge betweenness remains the strongest attack in this pilot.
- Removing M5 from candidate generation saves substantial time versus candidate-with-M5, but loses destructive effect.
- Widening non-M5 candidates slightly improves the no-M5 setting, but not enough to close the gap to M5.
- Training with M5 candidates and attacking without M5 wide candidates improves over no-M5 wide candidates, but is slower and still behind the candidate-with-M5 and M5 baselines.
- Sampled edge betweenness candidates are the strongest non-full-M5 candidate source so far. They nearly match candidate-with-M5 while avoiding full edge-betweenness candidate generation.
- The largest gap remains on WS and SBM-weak graphs.

## Mini 15% ablations

These runs use 1 test graph per structural group and attack up to 15% removed edges. They are not final evidence, but they are useful for fast direction checks.

| Setting | Mean AUC | Normalized AUC | Final GCC | Mean time (s) |
| --- | ---: | ---: | ---: | ---: |
| No M5 candidates, h=1 | 0.110443 | 0.980152 | 0.959831 | 10.047 |
| No M5 wide candidates, h=1 | 0.109435 | 0.971624 | 0.943599 | 10.239 |
| Train with M5, attack without M5 wide | 0.109689 | 0.973191 | 0.945650 | 16.409 |
| No M5 candidates, h=3 | 0.110753 | 0.982311 | 0.970287 | 10.655 |
| Sampled EB k=16 | 0.108311 | 0.961556 | 0.921000 | 10.399 |
| M5 dynamic edge betweenness | 0.108379 | 0.959306 | 0.929045 | 9.098 |

Current interpretation:

- `damage_horizon=3` did not improve the no-M5 setting in the mini run.
- Training with M5 candidates but attacking without M5 candidates did not outperform training and attacking without M5 wide candidates, and was slower.
- The most promising non-full-M5 setting so far is sampled EB k=16 with one-step damage.

## Next experiments

The next priority should be a different candidate source for WS/SBM-weak rather than more h-step labels.

Recommended directions:

- Add shortest-path bridge candidates that approximate high edge betweenness without computing full edge betweenness.
- Add static or stale edge-betweenness candidates recomputed every several steps, then compare runtime against fully dynamic M5.
- Add WS-specific long-range shortcut candidates using low clustering or high endpoint distance proxies.
- Tune sampled EB with smaller and larger `sampled_eb_k` values to find the speed/effect tradeoff.
