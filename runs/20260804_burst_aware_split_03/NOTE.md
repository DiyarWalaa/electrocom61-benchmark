# SUPERSEDED — do not cite this run

Canonical burst-aware run: `runs/20260804_burst_aware_split_04/`.

Note added 2026-08-04, after the run.

## Why

This run exists only as a refactoring check. `build_units` and `allocate` were
extracted from `main()` into module-level functions so that
`burst_aware_tau_sweep.py` could drive the same allocator instead of carrying a
second copy of it. This run confirmed the extraction changed nothing: at
tau = 30 s it reproduced `_02` exactly — 64 images moved, 1458/438/225, zero
test<->train pairs, 120 straddling groups.

It therefore carries the same tau=30 size violation as `_02`, for the same
reason, and is superseded for the same reason. See `_02`'s note.

The refactor it verified is what makes `runs/20260804_burst_aware_tau_sweep/`
trustworthy: the sweep and the single-tau run provably execute the same code.
