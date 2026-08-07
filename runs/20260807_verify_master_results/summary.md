# Master table verification

Run directory: `20260807_verify_master_results`

**4 passed, 2 failed** of 6 known values.

| result | check | expected | found |
|---|---|---|---|
| PASS | YOLO26s corrected test mAP@50 | `0.9427` | `0.9427` |
| PASS | YOLO26s corrected test mAP@50-95 | `0.6317` | `0.6317` |
| PASS | RT-DETR-l published test mAP@50 | `0.9171` | `0.9171` |
| PASS | YOLOv12s published test mAP@50-95 | `0.5842` | `0.5842` |
| **FAIL** | YOLO11s params_fused | `9,436,407` | `9,451,399` |
| **FAIL** | RT-DETR-l gflops | `105.6` | `110.16` |

