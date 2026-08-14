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



\## Writing

Read `notes/writing-plan.md` before drafting any part of the paper. It holds the
section order, the status of each section, the claim-plus-evidence skeleton for
the ones not yet written, and the rules every paragraph is held to.

The rules in brief — the plan gives the reason for each:
- One claim per paragraph, carrying its evidence and its implication.
- Discrepancies are stated as facts requiring resolution, never as accusations.
- Every number traces to a committed file; untraceable numbers get a `PENDING`
  comment in the section file, not a hedge in the prose.
- Never a bare mAP@50.
- Any ranking resting on one number states the gap alongside it.
- Percentages within a subsection share one basis, and the subsection says which.

Draft a whole section per pass, not a paragraph.

## Current task

Draft the paper, in the order given by `notes/writing-plan.md`. Section 5 is
complete; Section 3 is next.

(The previous task — detecting whether near-duplicate photo bursts are split
across train/valid/test — is finished. It produced the burst-aware split
released in `runs/20260804_burst_aware_split_04/`.)

