# Scene signatures from YOLO labels

Label-only duplicate detection. No pixels, no model, no downloads.

- images on disk: **2121**
- with usable (non-empty) label files: **2121**
- missing label file: 0; empty label file: 0
- distinct class-multiset buckets: **595**
- buckets compared: 293; pairs examined: 32822
- buckets skipped: 0 (full coverage of all candidate pairs)

## Same-scene pairs by epsilon

| scoring | eps | excl_low_info | n_pairs | test_w_train_twin | n_test | pct | valid_w_train_twin |
|---|---|---|---|---|---|---|---|
| raw | 0.01 | False | 2 | 0 | 205 | 0.0 | 1 |
| raw | 0.01 | True | 1 | 0 | 205 | 0.0 | 0 |
| raw | 0.02 | False | 12 | 0 | 205 | 0.0 | 2 |
| raw | 0.02 | True | 4 | 0 | 205 | 0.0 | 0 |
| raw | 0.05 | False | 61 | 4 | 205 | 2.0 | 9 |
| raw | 0.05 | True | 26 | 0 | 205 | 0.0 | 1 |
| aligned | 0.01 | False | 129 | 9 | 205 | 4.4 | 18 |
| aligned | 0.01 | True | 3 | 0 | 205 | 0.0 | 0 |
| aligned | 0.02 | False | 139 | 9 | 205 | 4.4 | 18 |
| aligned | 0.02 | True | 13 | 0 | 205 | 0.0 | 0 |
| aligned | 0.05 | False | 213 | 10 | 205 | 4.9 | 21 |
| aligned | 0.05 | True | 85 | 0 | 205 | 0.0 | 3 |

`raw` = centres compared directly (re-shot static scene).
`aligned` = centroid subtracted first (panned/drifted burst).
`excl_low_info` drops pairs with <=2 boxes, where a centre match
is cheap to achieve by chance. Quote the excl_low_info=True row.

## Coverage of the untimestamped `counter` family

- `counter` images with usable labels: **189**
- of those, appearing in at least one candidate pair: **71**

These images carry no timestamp and are invisible to
`burst_clusters.py`. They sit entirely in train, so they cannot
leak into test -- but duplicates AMONG them still inflate the
effective size of the training set relative to its nominal count.

