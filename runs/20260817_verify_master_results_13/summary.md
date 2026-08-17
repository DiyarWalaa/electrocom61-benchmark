# Table verification

Run directory: `20260817_verify_master_results_13`

**17 passed, 0 failed** of 17 known values.

| result | check | expected | found | note |
|---|---|---|---|---|
| PASS | benchmark rows | `10` | `10` | structural |
| PASS | run rtdetr_l_pub labelled diverged | `yes` | `yes` | structural |
| PASS | unique (model, split_set) among benchmark rows | `yes` | `yes` | structural |
| PASS | ec61.load_benchmark_rows() accepts the table | `yes` | `yes` | structural |
| PASS | YOLO26s corrected test mAP@50 | `0.9427` | `0.9427` |  |
| PASS | YOLO26s corrected test mAP@50-95 | `0.6317` | `0.6317` |  |
| PASS | RT-DETR-l published test mAP@50 | `0.9171` | `0.9171` |  |
| PASS | YOLOv12s published test mAP@50-95 | `0.5842` | `0.5842` |  |
| PASS | YOLO11s params_fused | `9,436,407` | `9,436,407` |  |
| PASS | RT-DETR-l gflops_fused | `105.6` | `105.6` |  |
| PASS | YOLOv9s gflops_fused | `26.855` | `26.855` |  |
| PASS | YOLO26s post_ms (both runs) | `0.38` | `0.38` |  |
| PASS | yolo11s mean p50 | `13.68` | `13.68` | within +/-0.01 |
| PASS | yolo26s mean p50 | `14.65` | `14.645` | within +/-0.01 |
| PASS | yolo12s mean p50 | `18.95` | `18.945` | within +/-0.01 |
| PASS | yolov9s mean p50 | `21.05` | `21.045` | within +/-0.01 |
| PASS | rtdetr-l mean p50 | `47.21` | `47.21` | within +/-0.01 |

