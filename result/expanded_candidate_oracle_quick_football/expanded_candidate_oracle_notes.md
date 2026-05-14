# Expanded Candidate Oracle

Each step builds a candidate pool from the top-5 edges suggested by M2/M4/M5/M7/M8, deduplicates those edges, and lets an oracle choose from the expanded pool.

For horizon `h1`, the oracle chooses the edge with the largest immediate GCC reduction. For larger horizons, it scores the first edge by simulating greedy expanded-oracle choices for the remaining horizon and minimizing the short-horizon average GCC.

## AUC Summary

- real_external_test: best=Expanded oracle top-5 h1 (mean AUC=0.225)

## Candidate Pool

- real_external_test / Expanded oracle top-5 h1: mean candidates=9.6, median=10.0, range=1-20

## Selected Source Usage

- real_external_test / Expanded oracle top-5 h1: M5 dynamic edge betweenness: 298 (48.6%); M2 dynamic degree product: 172 (28.1%); M4 dynamic community internal / pair: 142 (23.2%); M7 dynamic community size / pair: 1 (0.2%)

## Config

- top_k=5
- rollout_depths=[1]
