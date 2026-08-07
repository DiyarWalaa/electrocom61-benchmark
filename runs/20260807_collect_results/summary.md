# Master results table

Run directory: `20260807_collect_results`

Output: `data/master_results.csv` — 10 rows from 10 input files.

| model | split | val@50 | val@50-95 | test@50 | test@50-95 | cls_val | cls_test | params_fused | gflops | epochs | train_min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rtdetr-l | corrected | 0.954 | 0.6355 | 0.9444 | 0.6164 | 61 | 61 | 32,931,431 | 110.16 | 59 | 132.1 |
| rtdetr-l | published | 0.938 | 0.6016 | 0.9171 | 0.6045 | 45 | 46 | 32,931,431 | 110.16 | 73 | 163.2 |
| yolo11s | corrected | 0.9335 | 0.6321 | 0.9313 | 0.6187 | 61 | 61 | 9,451,399 | 21.8 | 100 | 58.4 |
| yolo11s | published | 0.9238 | 0.5975 | 0.8921 | 0.6084 | 45 | 46 | 9,451,399 | 21.8 | 100 | 58.9 |
| yolo12s | corrected | 0.9022 | 0.6021 | 0.9197 | 0.6017 | 61 | 61 | 9,276,743 | 23.61 | 100 | 80.2 |
| yolo12s | published | 0.894 | 0.5871 | 0.877 | 0.5842 | 45 | 46 | 9,276,743 | 23.61 | 100 | 80.0 |
| yolo26s | corrected | 0.9359 | 0.6271 | 0.9427 | 0.6317 | 61 | 61 | 9,995,078 | 23.0 | 100 | 70.4 |
| yolo26s | published | 0.9196 | 0.5944 | 0.9021 | 0.6129 | 45 | 46 | 9,995,078 | 23.0 | 100 | 70.5 |
| yolov9s | corrected | 0.9426 | 0.6405 | 0.9319 | 0.6186 | 61 | 61 | 7,311,015 | 27.51 | 100 | 77.0 |
| yolov9s | published | 0.9233 | 0.6021 | 0.9045 | 0.6063 | 45 | 46 | 7,311,015 | 27.51 | 100 | 79.8 |

## Latency

All six latency columns are **empty** and `latency_source` is `pending_unified_pass`.

The inputs do carry `latency_ms`, `fps` and per-section `speed_ms`, and none of it was copied. Those were measured in ten separate Kaggle sessions on whatever P100 each was allotted, under unknown contention. They cannot support a cross-model claim: a 2x gap between two rows could be scheduling noise. A unified pass over all ten checkpoints on one machine — warmup, `torch.cuda.synchronize()`, p50 and p95, batch size stated — is required before these columns are filled.

## What could make this misleading

- `params_fused` is copied from the JSON's `params`. The inputs do not state whether that count is fused or unfused.
- `classes_evaluated` is split into val and test columns because they differ on the published split (45 vs 46). One column would have hidden that.
- Rows are not comparable across splits by accuracy alone: the published split evaluates ~46 of 61 classes, the corrected split all 61, so a lower corrected mAP may reflect harder coverage rather than a worse model.

