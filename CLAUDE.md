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

\- ALWAYS REBUILD `paper/main.pdf` AFTER ANY EDIT, including one-word ones.

&#x20; Four passes from cold: `powershell -File scripts\build_paper.ps1 -Clean`.

&#x20; Confirm zero undefined references, zero undefined citations and zero

&#x20; overfull boxes before reporting the edit as done. An edit that has not

&#x20; been built is not finished: a broken cross-reference, a dropped brace

&#x20; or an overfull box is invisible in the .tex and obvious in the build.



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

## Reports

Every report goes in `C:\research\electrocom61\reports\` and nowhere else. This
is the single location; do not write reports to the scratchpad, to a sibling of
the repository, or to a subfolder of `notes/`. If a report is found anywhere
else, it is in the wrong place — move it here and leave only one copy.

Keep the structure that a report pass defines, including `reports/tables/` for
any rendered page images and any CSV a pass is asked to produce.

**`reports/tables/` is gitignored and its images are never committed.** Decided
2026-08-17. Page images rendered from prior-work PDFs are reproductions of
copyrighted papers and this repository is public, which is the same reason the
PDFs themselves stay out. Render them, read the tables off them, and leave them
uncommitted. What IS committed is `reports/*.txt` and any `reports/*.csv`: those
cite page and table numbers rather than reproducing the page, so the evidence
trail survives without the images. A consequence to accept rather than fix: a
fresh checkout has the reports but not the images they were read from, so
re-checking a transcribed value means re-rendering the page.

Reports are not byte-reproducible: they record a run date and a commit hash, so
re-running a pass legitimately changes them. That is unlike everything under
`runs/`, `tables/` and `figures/`, which must regenerate identically — see
`notes/clean-clone-verification.md`.

**Source material for a report stays out of the repository.** Prior-work PDFs
are copyrighted and Section 8 of the manuscript states they are not part of it.
Read them from outside the repo and cite page and table numbers; never copy them
in. As of 2026-08-17 the home directory is unreadable (`.claude/settings.json`
denies `Read(~/**)`), so PDFs to be read must sit outside `C:\Users\athar` —
`C:\research\pdfs\` works and is a sibling of the repository rather than part
of it.

## Current task

Draft the paper, in the order given by `notes/writing-plan.md`. Section 5 is
complete; Section 3 is next.

(The previous task — detecting whether near-duplicate photo bursts are split
across train/valid/test — is finished. It produced the burst-aware split
released in `runs/20260804_burst_aware_split_04/`.)

