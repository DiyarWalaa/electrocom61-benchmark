# Is the v2 CSV actually v1's metadata?

Hypothesis: `Metadata_ElectroCom61.csv` shipped in v2 was never regenerated and still describes v1.

- v1 image files found: **2071**
- v1 unique stems: **2071** (duplicate stems: 0)
- v2 image files: **2121**
- CSV data rows: **2071**
- v1 split folders detected: `test`, `train`, `valid`
- v1 filename parse routes: roboflow=2071
- v2 filename parse routes: roboflow=2121

## Verdict

| test | prediction | observed | result |
|---|---|---|---|
| T1 | count: |v1| == |CSV rows| | 2071 vs 2071 | **PASS** |
| T2 | identity: {v1 stems} == {CSV keys} | csv-only 0, v1-only 0 | **PASS** |
| T3 | no v1 image dated 20241118 | 0 found | **PASS** |
| T3b | v2 minus v1 == the un-metadata'd images | 50 vs 50 | **PASS** |
| T4 | csv DATA_TYPE == v1 folder | 0 disagreements of 2071 | **PASS** |

**T2 is the test that decides this.** T1 can pass by arithmetic coincidence -- two collections of 2071 files need not be the same files. If T2 passes, the CSV describes v1's contents exactly and the hypothesis is established. If T2 fails, a passing T1 means nothing on its own.

## Capture dates, v1 vs v2

| capture_date | n_v1 | n_v2 | v2_minus_v1 |
|---|---|---|---|
| 20240219 | 100 | 100 | 0 |
| 20240220 | 486 | 486 | 0 |
| 20240228 | 482 | 482 | 0 |
| 20240303 | 188 | 188 | 0 |
| 20240306 | 244 | 244 | 0 |
| 20240309 | 328 | 328 | 0 |
| 20240417 | 54 | 54 | 0 |
| 20241118 | 0 | 50 | 50 |
| <no timestamp> | 189 | 189 | 0 |

## csv DATA_TYPE vs the folder the image sits in under v1

| csv_DATA_TYPE | v1_test | v1_train | v1_valid | total |
|---|---|---|---|---|
| test | 205 | 0 | 0 | 205 |
| train | 0 | 1454 | 0 | 1454 |
| valid | 0 | 0 | 412 | 412 |

Compare against the same table built on v2 (`runs/20260801_csv_coverage/split_agreement.csv`), which has 600 off-diagonal rows. A clean diagonal here means the CSV's splits are v1's splits and v2 re-partitioned without updating the metadata.

