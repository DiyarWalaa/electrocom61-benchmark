# SUPERSEDED — this run does NOT describe the released split

Released split: **`runs/20260804_burst_aware_split_04/`** (burst-aware, τ=15 s,
seed 20260804). For its contamination figures use
`runs/20260804_burst_aware_split_04/contamination_comparison.csv`.

Note added 2026-08-09, after the run. Every file beside it is exactly as the
run produced it, and its numbers are correct — for the split it actually
measured.

## Which split this run describes

Its manifest is `runs/20260803_corrected_split_02/split_manifest.csv`: the
**image-level** corrected split, which moved individual images and was
superseded by the burst-aware allocator. Its `corrected` rows therefore report
that split, not the released one, and the two differ on the number that matters
most:

| test↔train near-duplicate pairs, ε=0.05 | raw | aligned |
|---|---|---|
| this run's `corrected` (image-level split) | **2** | **4** |
| released split (`burst_aware_split_04`) | **0** | **0** |

Reading this run's `corrected` rows as the released split's contamination would
report two-to-four near-duplicate pairs that the released split does not have.

## What this run is still the right source for

Its **`published`** rows, and its three-way breakdown method. It is the run
that established the published split carries zero test↔train pairs but 1 raw /
3 aligned **valid↔train** pairs at ε=0.05 — the correction that "the published
split had zero near-duplicate pairs" was true only for test↔train. That result
is unaffected by which corrected split it was compared against.

It also remains the reconciliation against `runs/20260802_scene_signature`, all
six published-split rows matching exactly.
