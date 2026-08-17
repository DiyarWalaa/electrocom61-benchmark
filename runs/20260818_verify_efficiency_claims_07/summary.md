# Efficiency-claim verification (section 5.5)

Run directory: `20260818_verify_efficiency_claims_07`

## 1. Complexity and fusion

| model | params unfused | params fused | drop | GFLOPs unfused | GFLOPs fused | drop |
|---|---|---|---|---|---|---|
| `yolo11s` | 9451399 | 9436407 | 0.159% | 21.795 | 21.549 | 1.129% |
| `yolo12s` | 9276743 | 9254487 | 0.240% | 23.612 | 23.301 | 1.317% |
| `yolov9s` | 7311015 | 7190695 | 1.646% | 27.511 | 26.855 | 2.385% |
| `rtdetr-l` | 32931431 | 32109095 | 2.497% | 110.159 | 105.600 | 4.139% |
| `yolo26s` | 9995078 | 9488787 | 5.065% | 22.998 | 20.892 | 9.157% |

Parameter reduction spans **0.1586% to 5.0654%**, which to one decimal is 0.2% to 5.1%.

## 2. Protocol

- **batch**: 1
- **burn_in**: 30 images on one model before the loop, discarded
- **complexity**: params, GFLOPs and layers before and after model.fuse(), imgsz=640
- **file_cache**: all 205 images read once before any timing
- **imgsz**: 640
- **timer**: perf_counter + cuda.synchronize, p50/p95 per-image end-to-end predict()
- **warmup**: 20
- **gpu**: Tesla P100-PCIE-16GB

## 3. Duplicate-measurement resolution

| model | e2e p50 gap (ms) | gap (%) |
|---|---|---|
| `yolo11s` | 0.24 | 1.7544 |
| `yolo12s` | 0.23 | 1.2140 |
| `yolov9s` | 0.13 | 0.6177 |
| `rtdetr-l` | 0.12 | 0.2542 |
| `yolo26s` | 0.05 | 0.3414 |

Largest: `yolo11s`, 0.24 ms / 1.7544%.

## 4. Per-session spread

These are the per-run `latency_ms` figures that `collect_results.py` refuses to read, because each was measured in its own Kaggle session. They are cited here as evidence of their own unreliability, which is the only claim they can support.

| model | min p50 | max p50 | gap (ms) | gap (%) |
|---|---|---|---|---|
| `yolov9s` | 18.58 | 24.23 | 5.65 | 30.41 |
| `yolo11s` | 10.83 | 12.08 | 1.25 | 11.54 |
| `yolo26s` | 12.60 | 12.89 | 0.29 | 2.30 |
| `yolo12s` | 15.81 | 16.14 | 0.33 | 2.09 |
| `rtdetr-l` | 44.09 | 44.81 | 0.72 | 1.63 |

## What could make this misleading

- The per-session figures in section 4 are not comparable to the unified pass's numbers and must never be quoted as latencies. They measure session conditions as much as models.
- Fusion percentages are computed from the unified pass's own before/after pair. They are not a claim about what any particular deployment toolchain would produce.
- The pair gap is a resolution floor for THIS hardware and session. It does not bound run-to-run variation on other hardware.

