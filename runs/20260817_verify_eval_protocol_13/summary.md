# Evaluation-protocol verification (section 5.4)

Run directory: `20260817_verify_eval_protocol_13`

## 1. Ten runs, twenty evaluations

`master_results.csv` has **10 rows**. Every row carries mAP@50 and mAP@50-95 for both validation and test, giving **20 complete evaluations**. The count is taken from the presence of all four figures per run, not from multiplying by two.

## 2. Classes evaluated

| split | classes on val | classes on test | runs | unanimous |
|---|---|---|---|---|
| corrected | 61 | 61 | 5 | True |
| published | 45 | 46 | 5 | True |

## 3. ESP32

For each of the 5 published-split runs, the set of classes appearing in the test per-class table minus those appearing in the validation table:

| run | val | test | test - val | val - test |
|---|---|---|---|---|
| `rtdetr_l_pub_lr1e4` | 45 | 46 | ESP32 | (none) |
| `yolo11s_pub` | 45 | 46 | ESP32 | (none) |
| `yolo12s_pub` | 45 | 46 | ESP32 | (none) |
| `yolo26s_pub` | 45 | 46 | ESP32 | (none) |
| `yolov9s_pub` | 45 | 46 | ESP32 | (none) |

ESP32 instance counts from `class_split_counts.csv`: **190 train, 0 valid, 2 test** across 190 / 0 / 2 images.

## 4. Validation thresholds

| run | mode | split | conf | iou | max_det |
|---|---|---|---|---|---|
| `rtdetr_l_corr` | train | val | null | 0.7 | 300 |
| `rtdetr_l_pub_lr1e4` | train | val | null | 0.7 | 300 |
| `yolo11s_corr` | train | val | null | 0.7 | 300 |
| `yolo11s_pub` | train | val | null | 0.7 | 300 |
| `yolo12s_corr` | train | val | null | 0.7 | 300 |
| `yolo12s_pub` | train | val | null | 0.7 | 300 |
| `yolo26s_corr` | train | val | null | 0.7 | 300 |
| `yolo26s_pub` | train | val | null | 0.7 | 300 |
| `yolov9s_corr` | train | val | null | 0.7 | 300 |
| `yolov9s_pub` | train | val | null | 0.7 | 300 |

- **conf**: identical across all 10 runs; value(s) `null`
- **iou**: identical across all 10 runs; value(s) `0.7`
- **max_det**: identical across all 10 runs; value(s) `300`

## What could make this misleading

- **These args.yaml describe `mode: train`.** They are the argument snapshot of the training run. Ultralytics writes no args.yaml for the end-of-run validation and test passes, so these files are evidence of what was configured, not a record of what those passes were called with.
- **`conf: null` means unset, not zero.** Ultralytics resolves it at runtime by mode, and the value it resolves to in validation is not written to any file in this repository. Quoting `null` as though it were a threshold would state the opposite of what the file says.
- The class difference is computed from per-class tables, which list a class only when it has ground-truth instances in that split. A class present but never predicted still appears; a class with no instances does not.
- ESP32 and ESP32-CAM are different classes whose names differ by a suffix.

