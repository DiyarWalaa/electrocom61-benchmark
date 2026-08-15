# Latency by architecture

Run directory: `20260816_latency_by_arch`

`data/latency_by_arch.csv` — 5 architectures, each the mean of its two timed runs.

| model | n | p50 mean (ms) | p50 gap (ms) | p50 gap % | p95 mean | fps mean | pre | inf | post |
|---|---|---|---|---|---|---|---|---|---|
| yolo11s | 2 | 13.68 | 0.24 | 1.75 | 14.59 | 73.10 | 1.25 | 8.39 | 1.06 |
| yolo26s | 2 | 14.64 | 0.05 | 0.34 | 15.93 | 68.30 | 1.27 | 10.06 | 0.38 |
| yolo12s | 2 | 18.95 | 0.23 | 1.21 | 20.80 | 52.80 | 1.28 | 13.65 | 1.08 |
| yolov9s | 2 | 21.05 | 0.13 | 0.62 | 22.70 | 47.55 | 1.28 | 15.80 | 1.06 |
| rtdetr-l | 2 | 47.21 | 0.12 | 0.25 | 49.56 | 21.20 | 1.31 | 41.88 | 0.57 |

## Repeatability

The two runs of an architecture share a graph and differ only in learned weights, so the gap between them is this rig's measurement wobble. The largest p50 gap is **yolo11s at 0.24 ms (1.75% of its mean)**.

**Any latency difference between architectures smaller than that is not a difference.**

## What could make this misleading

- n = 2. A gap from two observations is an observation, not a confidence interval. No standard deviation is computed from a pair and none should be quoted.
- The pair differs in learned weights as well as in run order, so the gap absorbs any real weight-dependent timing effect. For these detectors that should be nil — identical graph, identical shapes — but it is not zero by construction.
- One Tesla P100, one session. The ranking may not hold on other hardware; transformer and CNN detectors do not scale alike across GPUs.
- `fps_p50` is derived from the p50 latency, so its gap is not independent evidence.

