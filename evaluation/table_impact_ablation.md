# Impact-score ablation: H3 (SEQ-REFACTOR vs. topology-only AUC) per impact weighting

| configuration | alpha | beta | gamma | n | statistic | p_value | effect_size_r | ci_low | ci_high | mean_difference | supported | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1_coupling_only | 1.0 | 0.0 | 0.0 | 28 | None | None | None | 0.0 | 0.0 | 0.0 | None | every paired difference is exactly zero; the test is degenerate. |
| A2_complexity_only | 0.0 | 1.0 | 0.0 | 28 | 62.5 | 0.0324 | 0.6026 | 0.125 | 5.0187 | 2.4107 | True | supported at p<0.05 (H_alt: greater) |
| A3_cooccurrence_only | 0.0 | 0.0 | 1.0 | 28 | 13.5 | 0.2641 | 0.2857 | -0.6964 | 1.4469 | 0.3036 | False | not supported at p<0.05 (H_alt: greater) |
| A4_coupling_complexity_equal | 0.5 | 0.5 | 0.0 | 28 | 62.5 | 0.0324 | 0.6026 | 0.125 | 5.0187 | 2.4107 | True | supported at p<0.05 (H_alt: greater) |
| A5_all_three_default | 0.4 | 0.4 | 0.2 | 28 | 90.0 | 0.0009 | 0.978 | 5.4987 | 16.5366 | 10.75 | True | supported at p<0.05 (H_alt: greater) |
