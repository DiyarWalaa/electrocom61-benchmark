# Published complexity figures against measured ones

Run directory: `20260818_compare_published_complexity_14`

Input `data/published_complexity.csv` is **hand-transcribed from the prior-work PDFs**. It is not measured and nothing here can check it; each row names its table so every value can be re-checked in one step.

Measured values are from `data/master_results.csv`, corrected split.

| model | source | published layers | ours | published params (M) | ours fused (M) | ratio | explained by fusion? |
|---|---|---|---|---|---|---|---|
| YOLOv9s | yolov12paper | 930 | 486 | 60.8 | 7.19 | 8.46x | no |
| YOLOv11s | yolov12paper | 272 | 239 | 2.5 | 9.44 | 0.26x | no |
| YOLOv12S | yolov12paper | 292 | 352 | 19.7 | 9.25 | 2.13x | no |
| YOLOv9s | yolov13paper | 930 | 486 | 60.8 | 7.19 | 8.46x | no |
| YOLOv11s | yolov13paper | 272 | 239 | 2.5 | 9.44 | 0.26x | no |
| YOLOv12S | yolov13paper | 292 | 352 | 19.7 | 9.25 | 2.13x | no |

## What could make this misleading

- The input is a hand transcription of a PDF table. A mis-keyed digit would propagate into a claim about someone else's work, and no check here would catch it.
- A published figure may describe a variant, an input resolution or a class count that differs from this study's. The papers state the architecture name and the number; they do not state what else was held fixed when the number was produced.
- `explained_by_fusion` asks only whether the published value falls between the fused and unfused measurements. A `no` rules fusion out as the whole explanation; it does not identify what the explanation is.
- Layer counts are framework-dependent in a way parameter counts are not: what counts as a layer differs between implementations and between Ultralytics releases, so a layer-count difference is weaker evidence than a parameter-count difference.
