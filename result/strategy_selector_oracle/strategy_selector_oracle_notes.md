# Strategy Selector Oracle

At each step, the oracle asks M2/M4/M5/M7/M8 for their next dynamic edge, tries those candidate deletions, and chooses the one with the largest immediate GCC drop. Ties prefer M5, then M4, M7, M8, and M2.

This is an upper-bound check for a future learned strategy selector. It is not a trainable model yet.

## AUC Summary

- real_external_test: best=Oracle strategy selector (mean AUC=0.177); oracle mean AUC=0.177
- synthetic_test: best=Oracle strategy selector (mean AUC=0.397); oracle mean AUC=0.397

## Oracle Method Usage

- real_external_test: M5 dynamic edge betweenness: 4913 (99.9%); M4 dynamic community internal / pair: 4 (0.1%); M7 dynamic community size / pair: 2 (0.0%)
- synthetic_test: M5 dynamic edge betweenness: 11286 (100.0%)
