# Device x split coverage (ElectroCom-61 v9)

Dataset dir: `C:\research\electrocom61\data\ElectroCom-61_v2`

- images on disk: **2121**
- metadata CSV data rows: **2071**
- images joined to a CSV row: **2071**
- images with NO CSV row: **50**

## Filename family x split

Derived from filenames only -- reproducible with `ls`.

| filename_family | train | valid | test | total |
|---|---|---|---|---|
| counter | 189 | 0 | 0 | 189 |
| ts_compact | 485 | 149 | 109 | 743 |
| ts_compact_sub | 9 | 0 | 0 | 9 |
| ts_underscore | 795 | 289 | 96 | 1180 |
| TOTAL | 1478 | 438 | 205 | 2121 |

## CSV DEVICE_NAME x split

All fields whitespace-stripped on load.

| device_name_csv | train | valid | test | total |
|---|---|---|---|---|
| <no CSV row> | 35 | 10 | 5 | 50 |
| ONEPLUS_NORD | 218 | 91 | 82 | 391 |
| REDMI | 795 | 289 | 96 | 1180 |
| X | 241 | 48 | 22 | 311 |
| iPhone | 189 | 0 | 0 | 189 |
| TOTAL | 1478 | 438 | 205 | 2121 |

## Cross-check: filename family vs CSV device

| filename_family | <no CSV row> | ONEPLUS_NORD | REDMI | X | iPhone |
|---|---|---|---|---|---|
| counter | 0 | 0 | 0 | 0 | 189 |
| ts_compact | 49 | 384 | 0 | 310 | 0 |
| ts_compact_sub | 1 | 7 | 0 | 1 | 0 |
| ts_underscore | 0 | 0 | 1180 | 0 | 0 |

**Families mapping to more than one device:**
- `ts_compact` -> ONEPLUS_NORD (384), X (310)
- `ts_compact_sub` -> ONEPLUS_NORD (7), X (1)

**Devices mapping to more than one family:**
- `ONEPLUS_NORD` -> ts_compact (384), ts_compact_sub (7)
- `X` -> ts_compact (310), ts_compact_sub (1)

## Devices / families confined to a single split

| kind | key | only_split | n_images |
|---|---|---|---|
| device | iPhone | train | 189 |
| family | counter | train | 189 |
| family | ts_compact_sub | train | 9 |

A device present in only one split is a coverage gap: if it is
train-only it is never evaluated; if it is test-only it is never
trained on. This is a distribution problem, distinct from leakage.

