# P1 Source-Policy Ablation Implementation Plan

## Goal

P1 isolates whether SASB's observed advantage comes from the structured source sampling policy itself, rather than from the structured candidate edge set.

Decision rule:

- If `SASB-structured` outperforms `SASB-matched`, the result supports the claim that structured source sampling creates an independent beneficial bias.
- If `SASB-structured` is close to `SASB-matched`, the paper claim should be revised toward: structured candidate edge sets create the useful bias, while the source policy is not independently decisive.

This phase only prepares the implementation. No large-scale experiment should be started until explicitly confirmed.

## Code Reuse Check

The current SASB candidate set can be reused without modifying v3, v4, or v5 files.

The independent P1 script uses the current SASB candidate-set path:

- `scripts/evaluate_m19_theory_calibrated.py::candidate_features`
- `variant = "conservative"`
- `delta_mode = "none"`
- adaptive `k` through the existing SASB/theory configuration

The new script changes only the source-selection policy before sampled dependency scoring. Candidate generation is recorded before source selection, and each step stores candidate-set backend, config, size, and hash.

Important interpretation:

- For the same current graph state and same candidate configuration, all three source policies use the same candidate-set construction.
- After policies remove different edges, graph trajectories can diverge. Candidate hashes are therefore comparable at the same graph state/backend/config, not as a naive same-step equality guarantee after trajectories diverge.

## Fixed P1 Settings

- Candidate set: current SASB conservative candidate set.
- Source budget: `32`.
- GCC: dynamically recomputed after every edge removal.
- Random seeds: shared across all source policies.
- synthetic45: `remove_ratio = 1.0`.
- realworld: current 24/28 completed subset from the existing realworld diagnostic coverage.
- v3/v4/v5 original files: not modified.

## Source Policies

`SASB-structured`

- Reproduces the current structured source policy used by SASB/M19:
  - boundary-heavy sources,
  - high-degree/core sources,
  - community representatives,
  - random fill if needed.
- The script records source-strata labels so matched sampling has an explicit target profile.

`SASB-random`

- Uniformly samples 32 nodes from the current GCC.
- Uses the same deterministic seed schedule as the other policies.
- Does not condition on degree, community, or source stratum.

`SASB-matched`

- Randomly samples 32 nodes from the current GCC while matching the structured source profile as closely as possible.
- Matching targets:
  - degree-bin distribution,
  - Louvain community distribution,
  - structured source-strata distribution.
- The implementation first tries exact degree-bin plus community candidates, then relaxes to degree-bin, then community, then remaining unused nodes if a bucket is too small.
- Original structured source nodes are excluded when feasible, so the matched policy tests a distributional match rather than the identical source set.

## Unified Outputs

Summary-level required fields:

- `normalized_auc`
- `gcc_at_5pct`
- `gcc_at_10pct`
- `gcc_at_20pct`
- `gcc_at_40pct`
- `first_positive_drop_step`
- `positive_delta_gcc_rate`
- `conditional_mean_delta_gcc`
- `inter_community_ratio`
- `mean_edge_embeddedness`
- `mean_common_neighbors`
- `true_source_traversal_count`
- `runtime_seconds`
- `candidate_generation_seconds`
- `sampled_path_scoring_seconds`
- `model_scoring_seconds`
- `louvain_recomputes`
- `candidate_set_backend`
- `candidate_set_config`
- `candidate_set_config_equal_to_structured`
- `candidate_set_hashes_recorded`
- `observed_remove_ratio`
- `removed_edges`

Step-level records include:

- selected edge,
- current/next GCC,
- normalized GCC,
- `delta_gcc`,
- candidate-set hash and size,
- source list and source profile,
- inter-community flag,
- embeddedness/common-neighbor statistics,
- timing fields,
- Louvain recompute flag.

Curve-level records include:

- `removed_fraction`,
- `gcc_fraction`,
- normalized GCC trajectory by method, graph, and seed.

## Config File

Default P1 config has been written to:

`result/source_policy_ablation_p1/p1_experiment_config.json`

The config records:

- methods: `SASB-structured`, `SASB-random`, `SASB-matched`;
- source budget: `32`;
- candidate-set backend/config;
- shared seeds;
- synthetic45 and realworld dataset settings;
- realworld 24/28 completed graph IDs;
- required metric fields;
- safety flags preventing accidental large experiment runs without `--run`.

## Script Entry Point

New standalone script:

`scripts/evaluate_source_policy_ablation.py`

Default behavior:

```powershell
python -B scripts\evaluate_source_policy_ablation.py --write-default-config
```

This only writes/refreshes the config and exits in dry-run design mode.

Formal experiment behavior, only after explicit confirmation:

```powershell
python -B scripts\evaluate_source_policy_ablation.py --run
```

Optional smoke/debug cap after confirmation:

```powershell
python -B scripts\evaluate_source_policy_ablation.py --run --max-graphs 1
```

## Current Stop Point

Prepared:

- standalone P1 ablation script;
- default P1 config;
- implementation plan.

Not performed:

- no large-scale experiment;
- no commit;
- no push;
- no modification to v3/v4/v5 original files.
