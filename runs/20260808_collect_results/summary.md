# Master results table

Run directory: `20260808_collect_results`

`data/master_results.csv` — 10 rows, 23 columns, from 10 per-run files joined to the unified latency pass on the run slug.

## Accuracy

| model | split | val@50 | val@50-95 | test@50 | test@50-95 | cls_val | cls_test | epochs | train_min |
|---|---|---|---|---|---|---|---|---|---|
| rtdetr-l | corrected | 0.954 | 0.6355 | 0.9444 | 0.6164 | 61 | 61 | 59 | 132.1 |
| rtdetr-l | published | 0.938 | 0.6016 | 0.9171 | 0.6045 | 45 | 46 | 73 | 163.2 |
| yolo11s | corrected | 0.9335 | 0.6321 | 0.9313 | 0.6187 | 61 | 61 | 100 | 58.4 |
| yolo11s | published | 0.9238 | 0.5975 | 0.8921 | 0.6084 | 45 | 46 | 100 | 58.9 |
| yolo12s | corrected | 0.9022 | 0.6021 | 0.9197 | 0.6017 | 61 | 61 | 100 | 80.2 |
| yolo12s | published | 0.894 | 0.5871 | 0.877 | 0.5842 | 45 | 46 | 100 | 80.0 |
| yolo26s | corrected | 0.9359 | 0.6271 | 0.9427 | 0.6317 | 61 | 61 | 100 | 70.4 |
| yolo26s | published | 0.9196 | 0.5944 | 0.9021 | 0.6129 | 45 | 46 | 100 | 70.5 |
| yolov9s | corrected | 0.9426 | 0.6405 | 0.9319 | 0.6186 | 61 | 61 | 100 | 77.0 |
| yolov9s | published | 0.9233 | 0.6021 | 0.9045 | 0.6063 | 45 | 46 | 100 | 79.8 |

## Complexity

| model | split_set | params_unfused | gflops_unf | params_fused | gflops_fused | layers_mod |
|---|---|---|---|---|---|---|
| rtdetr-l | corrected | 32,931,431 | 110.159 | 32,109,095 | 105.6 | 515 |
| rtdetr-l | published | 32,931,431 | 110.159 | 32,109,095 | 105.6 | 515 |
| yolo11s | corrected | 9,451,399 | 21.795 | 9,436,407 | 21.549 | 239 |
| yolo11s | published | 9,451,399 | 21.795 | 9,436,407 | 21.549 | 239 |
| yolo12s | corrected | 9,276,743 | 23.612 | 9,254,487 | 23.301 | 352 |
| yolo12s | published | 9,276,743 | 23.612 | 9,254,487 | 23.301 | 352 |
| yolo26s | corrected | 9,995,078 | 22.998 | 9,488,787 | 20.892 | 284 |
| yolo26s | published | 9,995,078 | 22.998 | 9,488,787 | 20.892 | 284 |
| yolov9s | corrected | 7,311,015 | 27.511 | 7,190,695 | 26.855 | 486 |
| yolov9s | published | 7,311,015 | 27.511 | 7,190,695 | 26.855 | 486 |

## Latency (unified pass)

| model | split_set | p50_ms | p95_ms | fps | pre_ms | inf_ms | post_ms |
|---|---|---|---|---|---|---|---|
| rtdetr-l | corrected | 47.15 | 49.49 | 21.2 | 1.31 | 41.88 | 0.59 |
| rtdetr-l | published | 47.27 | 49.63 | 21.2 | 1.32 | 41.89 | 0.56 |
| yolo11s | corrected | 13.8 | 14.74 | 72.5 | 1.26 | 8.4 | 1.07 |
| yolo11s | published | 13.56 | 14.44 | 73.7 | 1.25 | 8.39 | 1.05 |
| yolo12s | corrected | 18.83 | 20.42 | 53.1 | 1.27 | 13.48 | 1.08 |
| yolo12s | published | 19.06 | 21.17 | 52.5 | 1.3 | 13.82 | 1.08 |
| yolo26s | corrected | 14.67 | 16.01 | 68.2 | 1.27 | 10.07 | 0.38 |
| yolo26s | published | 14.62 | 15.85 | 68.4 | 1.28 | 10.05 | 0.38 |
| yolov9s | corrected | 21.11 | 22.72 | 47.4 | 1.28 | 15.8 | 1.07 |
| yolov9s | published | 20.98 | 22.67 | 47.7 | 1.28 | 15.81 | 1.06 |

## Latency provenance

`latency_source` = `unified_pass_v3_single_P100_session_committed`

- **batch**: 1
- **burn_in**: 30 images on one model before the loop, discarded
- **complexity**: params, GFLOPs and layers before and after model.fuse(), imgsz=640
- **file_cache**: all 205 images read once before any timing
- **imgsz**: 640
- **timer**: perf_counter + cuda.synchronize, p50/p95 per-image end-to-end predict()
- **warmup**: 20

The per-run JSONs' own `latency_ms`, `fps` and `speed_ms` fields are still not read. They were measured in ten separate sessions under unknown contention and cannot support a cross-model claim.

## Complexity cross-check

The training JSONs' `params` and `gflops` agree with the unified pass's `params_unfused` and `gflops_unfused` on all 10 runs (GFLOPs to within 0.01, the reporting precision). The two files describe the same weights.

## What could make this misleading

- `layers_modules` counts nn.Module objects and is NOT the "layers" figure Ultralytics prints. Do not compare it against a published layer count.
- Rows are not comparable across splits by accuracy alone: the published split evaluates ~46 of 61 classes, the corrected split all 61, so a lower corrected mAP may reflect harder coverage rather than a worse model.
- Latency was measured on one Tesla P100. Ranking may not hold on other hardware, and transformer and CNN detectors do not scale alike across GPUs.

