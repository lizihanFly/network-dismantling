# P1 Source-Policy Ablation Formal Experiment Preregistration

## Research Question

P1 asks whether the observed advantage of SASB comes from the structured source sampling policy itself, or whether the main useful bias is already contained in the structured candidate edge set.

The formal question is:

When candidate set construction, source budget, random seed, and dynamic GCC attack procedure are fixed, does `SASB-structured` outperform `SASB-matched` on network dismantling effectiveness?

## Hypotheses

H0: Structured source sampling has no independent beneficial effect.

Under H0, `SASB-structured` and `SASB-matched` should have similar normalized GCC-AUC and similar mechanism indicators. Any advantage over `SASB-random` should mainly be attributed to matching degree, community, and source-strata distributions, or to the shared candidate-set bias.

H1: Structured source sampling has an independent beneficial bias.

Under H1, `SASB-structured` should achieve lower normalized GCC-AUC than `SASB-matched` under the same candidate set, same source budget, same random seed schedule, and same dynamic GCC procedure.

## Compared Methods

`SASB-structured`

- Uses the current structured SASB/M19 source policy.
- Source selection prioritizes boundary sources, degree/core sources, community representatives, and random fill.

`SASB-random`

- Samples 32 source nodes uniformly from the current GCC.
- Uses the same seed schedule as the other policies.
- Serves as a weak random-source baseline.

`SASB-matched`

- Randomly selects sources while matching the structured source profile as closely as possible.
- Matching targets include degree-bin distribution, Louvain community distribution, and source-strata distribution.
- This is the key causal control for source-policy bias.

The central comparison is `SASB-structured` versus `SASB-matched`, not merely `SASB-structured` versus `SASB-random`.

## Fixed Variables

Candidate set must be fixed because P1 isolates source policy. If candidate edges change across methods, performance differences cannot be attributed to source selection.

Source budget is fixed at 32 because the number of source traversals controls sampled dependency accuracy and runtime cost.

Random seed is fixed so that stochastic source policies are compared under the same reproducibility conditions.

Dynamic GCC procedure is fixed because network dismantling is path-dependent. GCC is recomputed after every edge removal, and source-policy comparisons must use the same attack trajectory measurement protocol.

## Primary Endpoint

The primary endpoint is normalized GCC-AUC.

Lower normalized GCC-AUC means the largest connected component is reduced faster over the dismantling trajectory. This endpoint is preferred because it summarizes the whole trajectory rather than a single removal budget.

## Secondary, Mechanism, and Cost Metrics

Secondary trajectory metrics:

- GCC@5%
- GCC@10%
- GCC@20%
- GCC@40%

Mechanism metrics:

- first positive drop step
- positive delta-GCC rate
- conditional mean delta-GCC
- inter-community ratio
- embeddedness

Cost metrics:

- true source traversal count
- runtime_seconds

Candidate-set sanity metric:

- candidate set equality under the same graph state, builder, parameters, and tie-breaking rule.

## Interpretation Rules

Results support source-policy bias if:

- `SASB-structured` has lower normalized GCC-AUC than `SASB-matched` on the paired comparison;
- the advantage is stable across networks, not only driven by one or two outliers;
- mechanism metrics indicate earlier or more frequent positive GCC drops;
- the result is not explained by higher traversal count or disproportionate runtime;
- candidate-set equivalence checks remain valid.

Results support only candidate bias if:

- `SASB-structured` improves over `SASB-random`, but is close to `SASB-matched`;
- `SASB-matched` reproduces the main trajectory and mechanism behavior of `SASB-structured`;
- differences are small relative to network-to-network variance.

Results would weaken or reject the current source-policy hypothesis if:

- `SASB-structured` does not outperform `SASB-matched`;
- `SASB-random` outperforms `SASB-structured`;
- advantages appear only in a small number of networks and disappear in the paired summary;
- candidate-set equivalence fails;
- runtime or traversal cost explains the apparent gain;
- many networks show no GCC response or abnormal trajectories.

## Data Scope

Synthetic data:

- synthetic45 full set.
- remove_ratio = 1.0.
- Complete dismantling trajectory is used.

Real-world data:

- Current completed 24/28 realworld subset.
- Only the networks already completed in the current diagnostic subset are included.
- The remaining incomplete realworld networks are not added during this formal P1 run.

## Implementation Constraint

The formal experiment must not modify original v3, v4, or v5 scripts. The P1 ablation uses an independent script and reuses the current SASB candidate-set builder without editing those original files.

## Planned Outputs

The formal analysis will generate:

- `formal_results.csv`
- `paired_comparisons.csv`
- `effect_sizes.csv`
- `mechanism_summary.csv`
- `cost_summary.csv`
- `formal_experiment_report.md`
- `plots/`

The final report will separate synthetic45 and realworld results, include paired differences, win/loss/tie counts, effect sizes, mechanism analysis, runtime and traversal cost, and failure or abnormal network analysis.
