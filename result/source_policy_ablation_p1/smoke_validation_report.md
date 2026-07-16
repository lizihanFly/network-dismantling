# P1 Smoke Validation Report

- Status: `success`
- Python executable: `C:\Users\86185\AppData\Local\Programs\Python\Python312\python.exe`
- Louvain dependency: `python-louvain` import path checked before smoke run.
- Formal synthetic45 / realworld 24/28 experiment: not run.
- v3/v4/v5 original files: not modified by this script.

## Candidate-Set Equivalence

- Equivalent edge set: `True`

| builder | candidate_count | candidate_fraction | candidate_edge_hash | cross_count | boundary_count | bridge_count | low_cn_count | degree_top_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_sasb_candidate_features | 98 | 0.25257731958762886 | b0d5428e5962878bb31ccc5d8f8943ae0f39ad3105fb8b84ce09f96f9720346e | 98 | 70 | 0 | 98 | 38 |
| p1_build_candidates | 98 | 0.25257731958762886 | b0d5428e5962878bb31ccc5d8f8943ae0f39ad3105fb8b84ce09f96f9720346e | 98 | 70 | 0 | 98 | 38 |

## Smoke Checks

- Three source policies completed: `True` (SASB-matched, SASB-random, SASB-structured)
- Source budget equals 32 on every step: `True`
- Candidate hash identical at the same initial graph state: `True`
- Candidate set never empty: `True`
- GCC values valid and non-null: `True`
- Summary metrics present and numeric: `True`
- Step rows: `120`
- Summary rows: `3`

## Smoke Results

| dataset | graph_id | method | source_policy | status | removed_edges | normalized_auc | gcc_at_5pct | gcc_at_10pct | gcc_at_20pct | gcc_at_40pct | positive_delta_gcc_rate | true_source_traversal_count | runtime_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic45 | synthetic_test_000 | SASB-structured | structured | finished | 40 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 1280 | 1.8044262000039453 |
| synthetic45 | synthetic_test_000 | SASB-random | random | finished | 40 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 1280 | 1.708238799998071 |
| synthetic45 | synthetic_test_000 | SASB-matched | matched | finished | 40 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 1280 | 1.7921340000029886 |

## Recommendation

- Ready for formal synthetic45/realworld run: `True`
