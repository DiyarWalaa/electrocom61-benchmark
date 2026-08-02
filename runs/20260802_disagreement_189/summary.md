# The 189 rows where CSV says `train` but the file is in `valid/`

- rows in the (csv=train, actual=valid) cell: **189**
- images in the `counter` family (no timestamp, iPhone-style): **189**
- **images in BOTH sets: 0**

**DISJOINT -- the matching counts are a coincidence.** No image appears in both sets. The `counter` family lives in a different directory than this cell, so they cannot overlap by construction.

## Where the `counter` family actually lives

| axis | value | n |
|---|---|---|
| actual directory | train | 189 |
| actual directory | valid | 0 |
| actual directory | test | 0 |
| csv DATA_TYPE | test | 20 |
| csv DATA_TYPE | train | 133 |
| csv DATA_TYPE | valid | 36 |

If the `counter` images are all in `train/` then they cannot be in a cell defined by `actual=valid`, whatever their count.

## What the 189 cell is made of

| axis | value | n |
|---|---|---|
| filename_family | ts_compact | 57 |
| filename_family | ts_underscore | 132 |
| DEVICE_NAME | ONEPLUS_NORD | 57 |
| DEVICE_NAME | REDMI | 132 |
| capture_date | 20240228 | 189 |
| BACKGROUND | Black | 51 |
| BACKGROUND | Tile | 35 |
| BACKGROUND | Wooden | 103 |

## Contiguity in capture order

One run per device = a whole session relabelled in bulk. Many runs = per-image assignment.

| device_key | n_cell_images | n_contiguous_runs | n_device_timeline |
|---|---|---|---|
| ONEPLUS_NORD | 57 | 25 | 391 |
| REDMI | 132 | 44 | 1180 |

