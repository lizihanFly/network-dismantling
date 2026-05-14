# Expanded Candidate Oracle Quick Probe

This quick probe checks whether an expanded top-k candidate pool is worth a full expensive run.

Settings:

- `top_k=5`
- `rollout_depths=1`
- `--skip-baselines`
- Synthetic probe: first 3 `synthetic_test` graphs only.
- Real probes: `karate` and `football`.

## Results

| Probe | Expanded oracle AUC | Reference comparison |
| --- | ---: | --- |
| synthetic_test first 3 graphs | 0.383415 | Same three M5 graphs average about 0.383547, essentially tied. |
| karate | 0.373115 | Worse than M5 0.337293 and M4/M7 0.325603. |
| football | 0.225023 | Worse than M5 0.217732, better than M4/M7/M8 around 0.241. |

## Interpretation

The expanded top-5 one-step oracle does not show a meaningful advantage over dynamic edge betweenness in this probe. The synthetic sample is effectively tied with M5, while the two real-network probes are worse than M5.

Given runtime cost, a full top-k/deeper-rollout run is probably not the best next step unless the implementation is optimized or the research question specifically needs an oracle upper bound. A more useful next direction is to either:

- treat M5 as the strong baseline and focus the write-up on when community methods approach it, or
- redesign the learned attack target away from teacher-rank imitation and toward direct multi-step GCC damage prediction.

