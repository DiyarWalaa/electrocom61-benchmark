\# ElectroCom61 Benchmark Study



\## What this project is

A benchmark paper on the ElectroCom61 object detection dataset

(61 electronic component classes, 2121 images, 12937 annotations).

Prior work reports contradictory results; we produce a controlled benchmark.



\## Non-negotiable rules

\- Every result must state: which split (train/valid/test), which seed,

&#x20; which hardware, which exact model weights.

\- Never report a number without saving the config that produced it.

\- Never overwrite a previous run. New run = new folder in runs/.

\- Report mAP@50 AND mAP@50-95. Never mAP@50 alone.

\- For latency: warmup runs first, torch.cuda.synchronize(), report

&#x20; p50 and p95, state batch size.



\## How to work with me

\- Explain the approach BEFORE writing code. I need to understand it.

\- Comment every non-obvious line.

\- After writing any script, tell me what could make its output misleading.

\- Do not install packages or download data without asking first.



\## Current task

Detect whether near-duplicate images (photo bursts) are split across

train/valid/test, using timestamps encoded in the filenames.

