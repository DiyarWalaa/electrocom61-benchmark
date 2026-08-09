# SUPERSEDED - do not cite this run

Canonical run: `runs/20260809_split_v1_vs_v2_by_group_03/`.

Note added 2026-08-09, after the run. Every file beside it is exactly as the
run produced it.

## Why

No number differs. `split_v1_vs_v2_by_group.csv` and
`split_transitions_by_group.csv` are identical in `_03`; the analysis is
deterministic and was unchanged.

What `_03` adds is prose the paper depends on:

- the caveat about the v1 column is restated as a **dependency on Finding 2's
  T4 test** rather than as an open doubt. T4 compared `DATA_TYPE` against an
  actual v1 download and found zero disagreements across all 2071 rows, so the
  v1 side is measured, not assumed.
- the excluded session's v2 composition is now captured and reported: 18 Nov
  2024 was split 35/10/5 of 50, exactly 70/20/10, zero deviation in every
  cell. `_02` reported only that the session was excluded, not how v2 handled
  it.

`figures/f2_capture_group_composition` is built from `_03`.
