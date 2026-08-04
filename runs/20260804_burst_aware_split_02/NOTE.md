# SUPERSEDED — do not cite this run

Canonical burst-aware run: `runs/20260804_burst_aware_split_04/`.

Note added 2026-08-04, after the run. Every file beside it is exactly as the
run produced them.

## Why

This run used **tau = 30 s**, chosen before the sweep existed on the reasoning
that it was the smallest value at which every rescued class had two qualifying
groups. That reasoning was sound but the premise was too narrow: feasibility is
satisfied at every tau from 15 s upward, so it was never the binding
constraint.

`runs/20260804_burst_aware_tau_sweep/` showed the binding constraint is how
many images the test split can give back, which collapses as tau grows (59
available at tau=15, 10 at tau=30, 1 at tau=60). At tau=30 test owed 20 and
could return only 10, so this run ended at **1458/438/225** and violated the
frozen sizes.

At tau=15 the same allocator holds **1478/438/205** exactly, with the same zero
test<->train contamination, for 68 images moved instead of 64.

Nothing here is wrong — the numbers are what tau=30 produces. It is simply not
the tau to use.
