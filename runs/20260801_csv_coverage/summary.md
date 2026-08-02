# Metadata CSV coverage

- images on disk: **2121**
- CSV data rows: **2071**
- joined: **2071**
- images with no CSV row: **50**
- CSV rows with no image on disk: **0**
- duplicate CSV IMAGE_NAME keys: **0**

Arithmetic check: 2121 on disk - 50 missing = 2071 joined; 2071 CSV rows - 0 orphans = 2071 joined.

## Images missing a CSV row, by family and split

| filename_family | train | valid | test | total |
|---|---|---|---|---|
| ts_compact | 34 | 10 | 5 | 49 |
| ts_compact_sub | 1 | 0 | 0 | 1 |
| TOTAL | 35 | 10 | 5 | 50 |

## Same, by capture date

| capture_date | train | valid | test | total |
|---|---|---|---|---|
| 20241118 | 35 | 10 | 5 | 50 |

## Contiguity

`n_contiguous_runs` = 1 means every missing image in that
family+date block is a single unbroken stretch in capture order,
which points at one un-exported session rather than scattered loss.

| family | date | n_on_disk | n_missing | first | last | runs |
|---|---|---|---|---|---|---|
| ts_compact | 20241118 | 49 | 49 | 101346 | 161943 | 1 |
| ts_compact_sub | 20241118 | 1 | 1 | 160515 | 160515 | 1 |

## Does CSV DATA_TYPE match the directory the file is in?

| csv_DATA_TYPE | actual_train | actual_valid | actual_test | total |
|---|---|---|---|---|
| test | 123 | 0 | 82 | 205 |
| train | 1150 | 189 | 115 | 1454 |
| valid | 170 | 239 | 3 | 412 |
| TOTAL | 1443 | 428 | 200 | 2071 |

**600 joined rows disagree with their actual directory.** The CSV must NOT be used to assign splits; use the directory.

