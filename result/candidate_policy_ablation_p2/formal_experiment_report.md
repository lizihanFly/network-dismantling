# P2 Candidate-Set Ablation Exploratory Report

## Research Question

With source policy, source budget upper bound, seed, and dynamic GCC workflow fixed, does the SASB candidate-edge set provide an independent beneficial structural bias?

The core comparison is `SASB-candidate` versus `Structure-matched-candidate`; comparing only against size-matched random candidates is insufficient.

## Run Integrity

- summary rows: `207`.
- all finished: `True`.
- datasets: `{"realworld_completed": 72, "synthetic45": 135}`.
- methods: `Random-size-matched-candidate, SASB-candidate, Structure-matched-candidate`.
- failed or non-finished runs: `0`.

## Main Result: normalized GCC-AUC

### realworld_completed
- `SASB-candidate` mean AUC: `0.420669` (n=24).
- `Random-size-matched-candidate` mean AUC: `0.424498` (n=24).
- `Structure-matched-candidate` mean AUC: `0.438821` (n=24).
- Core SASB-minus-structure-matched diff: `-0.018152`, 95% descriptive CI `[-0.037552, 0.001248]`, wins/losses/ties `16/8/0`; supports candidate-rule H1: `False`.

### synthetic45
- `SASB-candidate` mean AUC: `0.630081` (n=45).
- `Random-size-matched-candidate` mean AUC: `0.605076` (n=45).
- `Structure-matched-candidate` mean AUC: `0.626577` (n=45).
- Core SASB-minus-structure-matched diff: `0.003504`, 95% descriptive CI `[-0.006192, 0.013201]`, wins/losses/ties `29/16/0`; supports candidate-rule H1: `False`.

## Paired Difference Summary

- `realworld_completed` `SASB-candidate minus Random-size-matched-candidate`: mean `-0.003829`, 95% descriptive CI `[-0.034580, 0.026921]`, wins/losses/ties `14/10/0`.
- `realworld_completed` `SASB-candidate minus Structure-matched-candidate`: mean `-0.018152`, 95% descriptive CI `[-0.037552, 0.001248]`, wins/losses/ties `16/8/0`.
- `realworld_completed` `Structure-matched-candidate minus Random-size-matched-candidate`: mean `0.014323`, 95% descriptive CI `[-0.007166, 0.035811]`, wins/losses/ties `13/11/0`.
- `synthetic45` `SASB-candidate minus Random-size-matched-candidate`: mean `0.025005`, 95% descriptive CI `[0.007330, 0.042681]`, wins/losses/ties `23/22/0`.
- `synthetic45` `SASB-candidate minus Structure-matched-candidate`: mean `0.003504`, 95% descriptive CI `[-0.006192, 0.013201]`, wins/losses/ties `29/16/0`.
- `synthetic45` `Structure-matched-candidate minus Random-size-matched-candidate`: mean `0.021501`, 95% descriptive CI `[0.006637, 0.036365]`, wins/losses/ties `19/26/0`.
## Candidate Match Quality

- `realworld_completed` structure-matched mean feature L1 difference `0.000000`, strict matches `6585311`, degree-only `0`, community-only `0`, fallback `0`.
- `synthetic45` structure-matched mean feature L1 difference `0.000000`, strict matches `1989791`, degree-only `0`, community-only `0`, fallback `0`.
- Match quality is measured on the coarse structural features used by P2 matching; exact edge-set equality is not claimed.

## Source Count

### realworld_completed
- `SASB-candidate` actual source_count min/max/mean = `2.0` / `32.0` / `21.127`; true source traversal mean `48089.4`.
- `Random-size-matched-candidate` actual source_count min/max/mean = `2.0` / `32.0` / `23.259`; true source traversal mean `52881.0`.
- `Structure-matched-candidate` actual source_count min/max/mean = `2.0` / `32.0` / `21.716`; true source traversal mean `49227.3`.

### synthetic45
- `SASB-candidate` actual source_count min/max/mean = `2.0` / `32.0` / `23.949`; true source traversal mean `14185.6`.
- `Random-size-matched-candidate` actual source_count min/max/mean = `2.0` / `32.0` / `25.093`; true source traversal mean `14966.1`.
- `Structure-matched-candidate` actual source_count min/max/mean = `2.0` / `32.0` / `24.280`; true source traversal mean `14435.8`.

## Mechanism Metrics

### realworld_completed
- `first_positive_drop_step` mean: SASB-candidate=430.541667, Random-size-matched-candidate=31.250000, Structure-matched-candidate=519.208333.
- `positive_delta_gcc_rate` mean: SASB-candidate=0.078713, Random-size-matched-candidate=0.123038, Structure-matched-candidate=0.084149.
- `conditional_mean_delta_gcc` mean: SASB-candidate=0.013556, Random-size-matched-candidate=0.009733, Structure-matched-candidate=0.012554.
- `inter_community_ratio` mean: SASB-candidate=0.365334, Random-size-matched-candidate=0.304364, Structure-matched-candidate=0.367396.
- `mean_edge_embeddedness` mean: SASB-candidate=0.250889, Random-size-matched-candidate=0.246348, Structure-matched-candidate=0.247484.
- `mean_common_neighbors` mean: SASB-candidate=2.721108, Random-size-matched-candidate=2.721108, Structure-matched-candidate=2.721108.

### synthetic45
- `first_positive_drop_step` mean: SASB-candidate=302.666667, Random-size-matched-candidate=87.644444, Structure-matched-candidate=298.177778.
- `positive_delta_gcc_rate` mean: SASB-candidate=0.119464, Random-size-matched-candidate=0.156800, Structure-matched-candidate=0.129582.
- `conditional_mean_delta_gcc` mean: SASB-candidate=0.020126, Random-size-matched-candidate=0.016856, Structure-matched-candidate=0.019022.
- `inter_community_ratio` mean: SASB-candidate=0.387462, Random-size-matched-candidate=0.310492, Structure-matched-candidate=0.378834.
- `mean_edge_embeddedness` mean: SASB-candidate=0.098584, Random-size-matched-candidate=0.089501, Structure-matched-candidate=0.099730.
- `mean_common_neighbors` mean: SASB-candidate=0.299408, Random-size-matched-candidate=0.299408, Structure-matched-candidate=0.299408.


## Cost

### realworld_completed
- `SASB-candidate` runtime mean `134.075s`, source traversal mean `48089.4`.
- `Random-size-matched-candidate` runtime mean `141.846s`, source traversal mean `52881.0`.
- `Structure-matched-candidate` runtime mean `428.535s`, source traversal mean `49227.3`.

### synthetic45
- `SASB-candidate` runtime mean `13.572s`, source traversal mean `14185.6`.
- `Random-size-matched-candidate` runtime mean `13.813s`, source traversal mean `14966.1`.
- `Structure-matched-candidate` runtime mean `24.538s`, source traversal mean `14435.8`.

## Scientific Interpretation Rules

- If SASB-candidate beats both random-size-matched and structure-matched candidates, this supports an independent candidate selection contribution.
- If SASB-candidate beats random-size-matched but is close to structure-matched, candidate structural composition may matter more than the exact SASB scoring rule.
- If all three are close, no stable independent candidate-set advantage is observed under this protocol.
- If random-size-matched is better, the current SASB candidate rule may introduce an unfavorable structural bias.

## What This Experiment Cannot Claim

- It cannot claim universal effectiveness from code completion.
- It cannot prove candidate bias as the only mechanism.
- It cannot claim source-policy bias, because source policy is fixed here.
- It does not require candidate hashes to remain identical after dynamic trajectories diverge.
