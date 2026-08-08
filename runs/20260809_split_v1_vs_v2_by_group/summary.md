# v1 vs v2 split, per capture group

Run directory: `20260809_split_v1_vs_v2_by_group`

v1 = `DATA_TYPE` in `Metadata_ElectroCom61.csv`; v2 = the folder on disk. Restricted to the **2071 images the CSV covers**, so both sides describe the same set.

- **Excluded: 18 Nov 2024** — 50 images, none of which carry a CSV row, so it has no v1 label to compare against.

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
| **ALL** | 2071 | 70.2 / 19.9 / 9.9 | skewed | 69.7 / 20.7 / 9.7 | skewed | 600 (29%) |

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

## What could make this misleading

- The v1 labels are trusted to be v1's, which rests on audit Finding 2 rather than on anything measured here. If the CSV were a partially-updated v2 artefact, every change below would be an artefact of that.
- 70/20/10 is inferred from the aggregate, not documented by the dataset authors.
- Ratios are over images, not annotation instances.
- A group can hold its ratios while churning every image inside them; that is why transitions are reported and not only the before-and-after shares.

