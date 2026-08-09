# v1 vs v2 split, per capture group

Run directory: `20260809_split_v1_vs_v2_by_group_03`

v1 = `DATA_TYPE` in `Metadata_ElectroCom61.csv`; v2 = the folder on disk. Restricted to the **2071 images the CSV covers**, so both sides describe the same set.

- **Excluded: 18 Nov 2024** — 50 images, none of which carry a CSV row, so it has no v1 label to compare against. v2 split them 35/10/5.

| group | imgs | v1 tr/va/te % | v1 shape | v2 tr/va/te % | v2 shape | changed |
|---|---|---|---|---|---|---|
| 19 Feb 2024 | 100 | 70.0 / 20.0 / 10.0 | near-nominal | 100.0 / 0.0 / 0.0 | train-only | 30 (30%) |
| 20 Feb 2024 | 486 | 70.2 / 20.0 / 9.9 | near-nominal | 100.0 / 0.0 / 0.0 | train-only | 145 (30%) |
| 28 Feb 2024 | 482 | 70.1 / 20.1 / 9.8 | near-nominal | 35.9 / 55.2 / 8.9 | skewed | 292 (61%) |
| 3 Mar 2024 | 188 | 70.2 / 20.2 / 9.6 | near-nominal | 29.3 / 20.2 / 50.5 | skewed | 77 (41%) |
| 6 Mar 2024 | 244 | 70.5 / 19.7 / 9.8 | near-nominal | 70.5 / 19.7 / 9.8 | near-nominal | 0 (0%) |
| 9 Mar 2024 | 328 | 70.1 / 20.1 / 9.8 | near-nominal | 70.1 / 20.1 / 9.8 | near-nominal | 0 (0%) |
| 17 Apr 2024 | 54 | 70.4 / 18.5 / 11.1 | near-nominal | 70.4 / 18.5 / 11.1 | near-nominal | 0 (0%) |
| iPhone (no timestamp) | 189 | 70.4 / 19.0 / 10.6 | skewed | 100.0 / 0.0 / 0.0 | train-only | 56 (30%) |
| **ALL** | 2071 | 70.2 / 19.9 / 9.9 | (n/a) | 69.7 / 20.7 / 9.7 | (n/a) | 600 (29%) |

Groups near-nominal: **v1 7 of 8 → v2 3 of 8**.

## Where the images went

| group | moves (v1 → v2) |
|---|---|
| 19 Feb 2024 | valid→train 20, test→train 10 |
| 20 Feb 2024 | valid→train 97, test→train 48 |
| 28 Feb 2024 | train→valid 189, train→test 38, valid→train 17, valid→test 3, test→train 45 |
| 3 Mar 2024 | train→test 77 |
| 6 Mar 2024 | none |
| 9 Mar 2024 | none |
| 17 Apr 2024 | none |
| iPhone (no timestamp) | valid→train 36, test→train 20 |

## Borderline classifications

- **iPhone (no timestamp) (v1)** is scored `skewed` but misses the 1.5-image tolerance by only 1.8 images on a 189-image group — 0.95 percentage points. Read it as near-nominal in substance.

The aggregate row carries no shape label at all. The tolerance is an image count, so across 2071 images it is 0.07 percentage points and no aggregate could ever pass it.

## Two clarifications

### The v1 column is verified, not assumed

That `DATA_TYPE` describes v1 is established, not inferred. Finding 2's fourth provenance test (`runs/20260802_v1_provenance`, T4) compared the column against an actual v1 download and found the contingency table perfectly diagonal — 1454 train, 412 valid, 205 test — with **zero disagreements across all 2071 rows**; `t4_disagreements.csv` is empty.

This analysis therefore carries a **dependency on T4**, not an open doubt. Every change reported above is a change relative to a v1 assignment that was checked against v1 itself. Phrase it that way in the paper: if T4 were overturned the dependency would matter, but while it stands the v1 column is a measurement.

### v2 split the newly added session correctly

`18 Nov 2024` is the one session absent from v1 — its 50 images were added in v2 and have no CSV row. v2 split it **35 / 10 / 5 of 50**, which is 70.0 / 20.0 / 10.0 percent — worst deviation from 70/20/10 across the three cells: **0.0 images**.

Recorded as an observation. Whatever produced the v2 split handled a brand-new session at the nominal ratio, so the changes documented above are confined to assignments that already existed. No mechanism is claimed here for why the pre-existing ones changed.

## What could make this misleading

- The v1 column rests on T4 (see above). That is a dependency on a passing test, not an assumption, but it is still a dependency.
- 70/20/10 is inferred from the aggregate, not documented by the dataset authors.
- Ratios are over images, not annotation instances.
- A group can hold its ratios while churning every image inside them; that is why transitions are reported and not only the before-and-after shares.
- `shape` is a label at one tolerance, not a test, and the tolerance is in images. It is well behaved for groups of 50-500 and meaningless outside that range; see the borderline section above.

