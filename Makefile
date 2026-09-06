CONFIG ?= configs/ablation.yaml
OUT ?= results

.PHONY: results test scaling h1-safety

# Regenerate Tables II-IV and results/SUMMARY.md from a fixed seed (Working
# Brief §8). Table III/IV run fully offline; Table II needs the built
# jvm-sidecar (see jvm-sidecar/README.md) and is skipped with a clear message
# if it isn't present.
results:
	uv run seqrefactor results --config $(CONFIG) --out $(OUT)

test:
	uv run pytest -q

# Regenerate Fig. 5 and its labelled step-0/session-mean summary from the
# committed evaluation/table4_efficiency.csv alone (Phase 3c G1/G3/G6). Does
# NOT re-run the scaling study itself -- see REPRODUCE.md step 5 for that.
scaling:
	uv run python -m seqrefactor.eval.plot_scaling

# Regenerate evaluation/H1_SAFETY.md and evaluation/table_h1_safety.csv from
# the committed raw per-subject data (Working Brief Phase 5, Task A). Fully
# offline; reads only committed CSV/JSON, runs no new experiments.
h1-safety:
	uv run python -m seqrefactor.eval.h1_safety_check
