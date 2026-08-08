# Split ratio by capture group

Run directory: `20260809_split_ratio_by_group`

Source: `runs/20260802_class_date_provenance/date_split_summary.csv`

The aggregate split is **69.7 / 20.7 / 9.7** over 2121 images — to the eye a textbook 70/20/10. Per capture group it is nothing of the sort.

| group | images | train % | valid % | test % | dev train pp | dev valid pp | dev test pp | shape |
|---|---|---|---|---|---|---|---|---|
| 19 Feb 2024 | 100 | 100.0 | 0.0 | 0.0 | +30.0 | -20.0 | -10.0 | train-only |
| 20 Feb 2024 | 486 | 100.0 | 0.0 | 0.0 | +30.0 | -20.0 | -10.0 | train-only |
| 28 Feb 2024 | 482 | 35.9 | 55.2 | 8.9 | -34.1 | +35.2 | -1.1 | skewed |
| 3 Mar 2024 | 188 | 29.3 | 20.2 | 50.5 | -40.7 | +0.2 | +40.5 | skewed |
| 6 Mar 2024 | 244 | 70.5 | 19.7 | 9.8 | +0.5 | -0.3 | -0.2 | near-nominal |
| 9 Mar 2024 | 328 | 70.1 | 20.1 | 9.8 | +0.1 | +0.1 | -0.2 | near-nominal |
| 17 Apr 2024 | 54 | 70.4 | 18.5 | 11.1 | +0.4 | -1.5 | +1.1 | skewed |
| 18 Nov 2024 | 50 | 70.0 | 20.0 | 10.0 | +0.0 | +0.0 | +0.0 | near-nominal |
| iPhone (no timestamp) | 189 | 100.0 | 0.0 | 0.0 | +30.0 | -20.0 | -10.0 | train-only |

## Deviation in images

Actual minus what a uniform 70/20/10 draw over that group would have produced. Not rounded to whole images: the residue of rounding would be up to one image per cell and the deviations here are tens wide.

| group | images | train | valid | test |
|---|---|---|---|---|
| 19 Feb 2024 | 100 | +30.0 | -20.0 | -10.0 |
| 20 Feb 2024 | 486 | +145.8 | -97.2 | -48.6 |
| 28 Feb 2024 | 482 | -164.4 | +169.6 | -5.2 |
| 3 Mar 2024 | 188 | -76.6 | +0.4 | +76.2 |
| 6 Mar 2024 | 244 | +1.2 | -0.8 | -0.4 |
| 9 Mar 2024 | 328 | +0.4 | +0.4 | -0.8 |
| 17 Apr 2024 | 54 | +0.2 | -0.8 | +0.6 |
| 18 Nov 2024 | 50 | +0.0 | +0.0 | +0.0 |
| iPhone (no timestamp) | 189 | +56.7 | -37.8 | -18.9 |

## Shapes

- **near-nominal** (3): `6 Mar 2024`, `9 Mar 2024`, `18 Nov 2024`
- **train-only** (3): `19 Feb 2024`, `20 Feb 2024`, `iPhone (no timestamp)`
- **skewed** (3): `28 Feb 2024`, `3 Mar 2024`, `17 Apr 2024`

`near-nominal` means every share is within 1.0 percentage point of 70/20/10.

## What could make this misleading

- The nominal 70/20/10 is inferred from the aggregate, not documented by the dataset authors. If they intended some other ratio, every deviation here shifts.
- Percentages over small groups are coarse: 17 Apr has 54 images, so one image moves its test share by 1.9 points. The images column is there to keep that visible.
- Ratios are over IMAGES. A split that looks balanced by image can still be unbalanced by annotation instance, which is what actually feeds a detector's loss.
- Shape is a label applied at one tolerance, not a test. `near-nominal` at 1.0 pp would admit more groups at 2.0.

