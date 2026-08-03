# Corrected split for ElectroCom61 v2

Run directory: `20260803_corrected_split_02`  |  seed: `20260803`

Target: every class holds >= 5 instances in BOTH valid and test, with image counts frozen at 1478 / 438 / 205.

## Reconciliation with Stage 2

All 61 classes reconcile with `class_split_counts.csv` across all three splits.

## Did it work?

| check | result |
|---|---|
| image counts train/valid/test | 1478 / 438 / 205 (unchanged) |
| classes with >= 5 in valid AND test | 61 of 61 |
| classes never evaluable before | 15 |
| allocator passes used | 2 |
| images moved (total) | 64 |

Every class reaches the bar in both splits.

## Images moved, by date group

| capture_date | from | to | n_images |
|---|---|---|---|
| 20240219 | train | test | 2 |
| 20240219 | train | valid | 2 |
| 20240220 | train | test | 10 |
| 20240220 | train | valid | 10 |
| 20240228 | valid | train | 16 |
| 20240303 | test | train | 14 |
| 20240306 | test | train | 1 |
| 20240306 | valid | train | 1 |
| <untimestamped:counter> | train | test | 3 |
| <untimestamped:counter> | train | valid | 5 |

## Which sessions were opened, and by how much

Valid <-> test moves are disallowed, so train is the only path into either split: these columns account for the entire inflow.

| capture group | in train before | -> valid | -> test | released | share of group | left in train |
|---|---|---|---|---|---|---|
| 20240220 | 486 | 10 | 10 | 20 | 4.1% | 466 |
| <untimestamped:counter> | 189 | 5 | 3 | 8 | 4.2% | 181 |
| 20240219 | 100 | 2 | 2 | 4 | 4.0% | 96 |

Totals: valid received **17** images from train, test received **15** -- 32 in all, matched by 32 returned to train.

## Cost: broken bursts

Images excluded from every timeline metric because they carry no timestamp: **189**.

| state | tau | clusters | crossing | test imgs w/ train twin | valid imgs w/ train twin | largest |
|---|---|---|---|---|---|---|
| before | 3 | 1817 | 22 | 7 | 18 | 6 |
| before | 5 | 1438 | 109 | 45 | 81 | 6 |
| before | 10 | 866 | 186 | 83 | 206 | 19 |
| before | 30 | 314 | 120 | 107 | 319 | 58 |
| before | 60 | 134 | 72 | 117 | 396 | 64 |
| after | 3 | 1817 | 27 | 11 | 19 | 6 |
| after | 5 | 1438 | 114 | 52 | 84 | 6 |
| after | 10 | 866 | 209 | 104 | 215 | 19 |
| after | 30 | 314 | 137 | 161 | 338 | 58 |
| after | 60 | 134 | 85 | 180 | 407 | 64 |

## Cost: smallest cross-split time gap

| state | smallest gap (s) | cross-split adjacent pairs |
|---|---|---|
| before | 2 | 537 |
| after | 1 | 600 |

Ten tightest pairs after:

| gap_s | device | stem_a | split_a | stem_b | split_b |
|---|---|---|---|---|---|
| 1 | FAMILY:ts_underscore | IMG_20240220_115315 | test | IMG_20240220_115316 | train |
| 2 | FAMILY:ts_compact | IMG20240306143950 | test | IMG20240306143952 | train |
| 2 | FAMILY:ts_compact | IMG20240306144350 | train | IMG20240306144352 | valid |
| 2 | FAMILY:ts_underscore | IMG_20240228_131857 | valid | IMG_20240228_131859 | train |
| 2 | FAMILY:ts_underscore | IMG_20240306_143943 | test | IMG_20240306_143945 | train |
| 2 | FAMILY:ts_underscore | IMG_20240309_114140 | test | IMG_20240309_114142 | train |
| 3 | FAMILY:ts_compact | IMG20240220120325 | test | IMG20240220120328 | train |
| 3 | FAMILY:ts_compact | IMG20240303111847 | test | IMG20240303111850 | train |
| 3 | FAMILY:ts_compact | IMG20240306121019 | train | IMG20240306121022 | valid |
| 3 | FAMILY:ts_compact | IMG20240306144352 | valid | IMG20240306144355 | train |

## Cost: the untimestamped blind spot

Time gaps cannot be computed for the `counter` family at all. Label-geometry duplicate pairs that end up on opposite sides and involve at least one untimestamped image:

| epsilon | cross-split near-duplicate pairs (low-information excluded) |
|---|---|
| 0.01 | 0 |
| 0.02 | 0 |
| 0.05 | 2 |

Candidate pairs emitted: 2. Buckets skipped as too large: 0.

## What could make this misleading

- **This split manufactures leakage on purpose.** The 15 rescued classes are evaluated on images from the same sessions as their training images. Their per-class scores will be optimistic. `class_counts_before_after.csv` flags them in `was_never_evaluated` so the paper can mark exactly which.
- Reaching the bar makes a class **measurable, not fairly measured**. 5 instances is a floor for existence, not a sample size anyone should quote a confident AP from.
- Greedy allocation is not optimal. A different seed gives a different valid split of equal legality; the seed is recorded so this one is reproducible, not because it is best.
- The time-gap metric is blind to the 189 untimestamped images. The scene-signature pass covers them, but it UNDER-detects by construction (an occluded object changes the class multiset and the pair is never even considered).
- Holding 1478/438/205 removes the training-set-size confound but not the composition confound: train's content changed, so this split is not a clean A/B against the shipped one either.

