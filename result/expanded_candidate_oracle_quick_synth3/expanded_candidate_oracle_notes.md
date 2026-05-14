# Expanded Candidate Oracle

Each step builds a candidate pool from the top-5 edges suggested by M2/M4/M5/M7/M8, deduplicates those edges, and lets an oracle choose from the expanded pool.

For horizon `h1`, the oracle chooses the edge with the largest immediate GCC reduction. For larger horizons, it scores the first edge by simulating greedy expanded-oracle choices for the remaining horizon and minimizing the short-horizon average GCC.

## AUC Summary

- synthetic_test: best=Expanded oracle top-5 h1 (mean AUC=0.383)

## Candidate Pool

- synthetic_test / Expanded oracle top-5 h1: mean candidates=12.0, median=14.0, range=1-23

## Selected Source Usage

- synthetic_test / Expanded oracle top-5 h1: M5 dynamic edge betweenness: 790 (47.9%); M2 dynamic degree product: 489 (29.7%); M4 dynamic community internal / pair: 356 (21.6%); M7 dynamic community size / pair: 14 (0.8%)

## Config

- top_k=5
- rollout_depths=[1]
