CONFIG ?= configs/ablation.yaml
OUT ?= results

.PHONY: results test scaling

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
