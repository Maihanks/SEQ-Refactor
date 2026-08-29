# Quality-score sensitivity: H3 per quality-weight vector, summed vs. step-count-normalised AUC

| weight_vector | score_mode | n | statistic | p_value | effect_size_r | ci_low | ci_high | mean_difference | supported | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| current_accepted_count | summed | 28 | 90.0 | 0.0009 | 0.978 | 5.4987 | 16.5366 | 10.75 | True | supported at p<0.05 (H_alt: greater) |
| current_accepted_count | normalised | 28 | 90.0 | 0.0009 | 0.978 | 0.6036 | 1.8394 | 1.1929 | True | supported at p<0.05 (H_alt: greater) |
| equal | summed | 28 | 156.0 | 0.0011 | 0.8246 | 1.7362 | 5.1478 | 3.3341 | True | supported at p<0.05 (H_alt: greater) |
| equal | normalised | 28 | 155.0 | 0.0012 | 0.8129 | 0.1913 | 0.5701 | 0.3701 | True | supported at p<0.05 (H_alt: greater) |
| coupling_complexity_heavy | summed | 28 | 155.0 | 0.0012 | 0.8129 | 1.9517 | 5.8656 | 3.8093 | True | supported at p<0.05 (H_alt: greater) |
| coupling_complexity_heavy | normalised | 28 | 155.0 | 0.0012 | 0.8129 | 0.2159 | 0.6513 | 0.4227 | True | supported at p<0.05 (H_alt: greater) |
| readability_architecture_heavy | summed | 28 | 156.0 | 0.0011 | 0.8246 | 2.2112 | 6.5642 | 4.2397 | True | supported at p<0.05 (H_alt: greater) |
| readability_architecture_heavy | normalised | 28 | 156.0 | 0.0011 | 0.8246 | 0.2428 | 0.726 | 0.4707 | True | supported at p<0.05 (H_alt: greater) |
