# SEQ-REFACTOR results summary

Read this before updating any paper claim with a number from `results/`.

| Hypothesis | Supported | n | p-value | effect size (r) | note |
| --- | --- | --- | --- | --- | --- |
| H1_fewer_cascading_violations_vs_unordered | insufficient data | 18 | n/a | n/a | every paired difference is exactly zero; the test is degenerate. |
| H2_higher_nsr_vs_unordered | insufficient data | 18 | n/a | n/a | every paired difference is exactly zero; the test is degenerate. |
| H2_higher_nsr_vs_topo_only | insufficient data | 18 | n/a | n/a | every paired difference is exactly zero; the test is degenerate. |
| H3_higher_auc_vs_topo_only | no | 18 | 0.2641 | 0.2857 | not supported at p<0.05 (H_alt: greater) |
| H4_dependency_mass | no | 18 | 0.8273 | -0.2967 | not supported at p<0.05 (H_alt: greater) |

H5 (incremental maintenance is bit-for-bit identical to a from-scratch rebuild) is not a statistical hypothesis: it is guaranteed by construction (see `seqrefactor/graph/incremental.py`'s design note) and enforced by `tests/property/test_incremental_equivalence.py`, which must pass for any number in `table4_efficiency` to be trustworthy.

HONESTY NOTE: H4's dependency-mass inputs are seeded catalogue defaults (`seqrefactor/graph/rules.py`), not mined from version history -- see that module's docstring. RQ4's weight-sensitivity sweep (`seqrefactor/eval/weight_sweep.py`) and the open-source subject tier with mined reference orders (paper Section VII-C) remain out of scope for this increment; see REPO_MAP.md.
