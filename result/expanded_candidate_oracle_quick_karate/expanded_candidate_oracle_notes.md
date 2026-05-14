# Expanded Candidate Oracle

Each step builds a candidate pool from the top-5 edges suggested by M2/M4/M5/M7/M8, deduplicates those edges, and lets an oracle choose from the expanded pool.

For horizon `h1`, the oracle chooses the edge with the largest immediate GCC reduction. For larger horizons, it scores the first edge by simulating greedy expanded-oracle choices for the remaining horizon and minimizing the short-horizon average GCC.

## AUC Summary

- real_external_test: best=Expanded oracle top-5 h1 (mean AUC=0.373)

## Candidate Pool

- real_external_test / Expanded oracle top-5 h1: mean candidates=7.1, median=8.0, range=1-14

## Selected Source Usage

- real_external_test / Expanded oracle top-5 h1: M2 dynamic degree product: 45 (57.7%); M5 dynamic edge betweenness: 20 (25.6%); M4 dynamic community internal / pair: 12 (15.4%); M7 dynamic community size / pair: 1 (1.3%)

## Config

- top_k=5
- rollout_depths=[1]
