# SUPERSEDED — do not cite this run

Canonical burst-aware run: `runs/20260804_burst_aware_split_04/`.

(This note originally pointed at `_02`. `_02` has since been superseded too:
it used tau=30 and could not hold the frozen sizes. `_04` uses tau=15, chosen
by `runs/20260804_burst_aware_tau_sweep/`, and holds 1478/438/205 exactly.)

Note added 2026-08-04, after the run. The files beside it are exactly as the
run produced them.

## Why

No result differs. The split, the manifest, the contamination counts and the
size outcome are identical — the allocator is deterministic under seed
20260804 and was unchanged.

What this run lacked was the diagnosis. It reported that the size constraint
failed for test without saying why, which is not usable in a paper. `_02` adds
the return-pool statistics that identify the cause: test holds only 6 removable
groups totalling 10 images against the 20 it needed to give back, so the
failure is an absence of slack in the test split rather than a granularity
problem with group sizes.

Cite `_02` for the same numbers plus the reason.
