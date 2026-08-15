# Writing plan

The order we draft in, what each remaining section has to establish, and the
rules every paragraph is held to. This is the document to read before drafting
anything; it exists so that a whole section can be written in one pass instead
of a paragraph at a time.

## Order

We do not write in reading order. Evidence-bearing sections come first, because
the sections that summarise and frame them cannot be written honestly until
their claims are settled.

| Order | Section | Status |
|---|---|---|
| 1 | **3 — Dataset Audit** | **complete** (3.1–3.7 drafted, fact-checked) |
| 2 | **4 — A Corrected Split** | **complete** (4.1–4.8 drafted, fact-checked) |
| 3 | **5 — Benchmark Setup** | **complete** (5.1–5.6 drafted, fact-checked) |
| 4 | **6 — Results** | **complete** (6.1–6.5 drafted, fact-checked) |
| 5 | **7 — Discussion** | **complete** (7.1–7.4 drafted, fact-checked) |
| 6 | **8 — Limitations** | **complete** (drafted, fact-checked) |
| 7 | **2 — Related Work** | **complete** (2.1–2.4 drafted, fact-checked) |
| 8 | **9 — Conclusion** | **complete** (drafted, constraint-checked) |
| 9 | 1 — Introduction | stub |
| 10 | Abstract | not started |

**Sections 2 through 9 are complete and fact-checked.** They are the model for
the rest: every number in them traces to a committed file, and anything that does
not is marked in the section file's own header comment rather than left silent.

**Remaining: Section 1 and the abstract.** Neither is blocked.

## Writing rules

These are not style preferences. Each one exists because breaking it produced a
defect we then had to find and fix.

1. **One claim per paragraph, and the paragraph carries its evidence and its
   implication.** A paragraph that states a fact without saying what follows
   from it is a note, not prose. A paragraph carrying two claims makes both
   harder to check.

2. **Discrepancies are stated as facts requiring resolution, never as
   accusations.** "Neither prior study states an Ultralytics version, which
   determines the layer composition of every model it provides" — not "prior
   work failed to report". The reader draws the conclusion; we supply what makes
   it available. This is also what keeps the claim defensible if an author
   responds.

3. **Every number traces to a committed file.** Name the file or the run
   directory in the source comment if not in the prose. A number that cannot be
   traced does not go in, however confident we are of it. Numbers awaiting
   evidence get a `PENDING` comment in the section file, not a hedge in the
   prose.

4. **Never a bare mAP@50.** Always paired with mAP@50–95. This is a project rule
   (`CLAUDE.md`) and the single most likely thing to slip, because prior work on
   this dataset reports mAP@50 alone and quoting it invites matching its form.

5. **Any ranking that rests on one number states the gap alongside it.** "A
   beats B" is not reportable without the margin, because the margin is what
   tells the reader whether the ordering survives the measurement's resolution.
   For latency that resolution is stated in 5.5: the largest duplicate-pair gap
   is 0.24 ms, or 1.75% of the pair mean, and differences of that order are not
   treated as meaningful.

6. **Percentages within a subsection share one basis, and the subsection says
   which.** 5.5 uses gap/mean throughout and states so. Mixing bases inside a
   subsection makes two numbers look comparable when they are not.

## Length

**As of 2026-08-14 the paper is 24 pages with Sections 1, 2, 7, 8 and 9 still
unwritten.** Sections 3 and 4 are more detailed than most venues will
accommodate, and some of that material is expected to move to supplementary
material at submission.

The instruction for now is **stop adding, do not cut**. Nothing is removed until
a venue and its page limit are known — cutting early would discard material that
may simply relocate, and the run directories the prose cites are not going
anywhere. From here, new sections are drafted tighter rather than to the density
of 3 and 4.

## Section skeletons

Claim-plus-evidence bullets are supplied per section before drafting. Recorded
here as they arrive; the *Evidence available* column is what the repository
already holds, so drafting does not have to go looking for it.

### Section 3 — Dataset Audit — DRAFTED

Seven subsections: class coverage, the mechanism, allocation uniformity,
metadata provenance, what the v2 re-split changed, camera coverage, duplicate
contamination. 38 assertions re-derived from source. Three drafted bullets
diverged from their committed source and the source was followed in each case;
the divergences are recorded in the section file's header.

Evidence used:
- `runs/20260801_csv_coverage/` — 2121 images on disk against 2071 CSV rows;
  `DATA_TYPE` against the directory each image sits in
- `runs/20260801_device_split/` — images per capture device per split, device
  derived two independent ways and cross-checked
- `runs/20260802_class_date_provenance/` — the 15 never-evaluated classes,
  per-class verdict of session-confined against merely rare
- `runs/20260802_burst_clusters*/`, `runs/20260802_scene_signature/`,
  `runs/20260802_counter_duplicates/` — near-duplicate detection, two regimes
- `runs/20260805_consecutive_counter_pairs/` — the untimestamped `counter`
  images; pairs never compared against pairs compared and cleared
- `v1_provenance.py` — whether v2's metadata CSV was ever regenerated for v2
- Table T1, Figures F1 and F2

Carried from the stub: open with the top-10 result in
`notes/writing-corrections.md` — the unevaluable classes are the **biggest**
classes, not the smallest, which forecloses the class-imbalance reading.

### Section 4 — A Corrected Split — DRAFTED

Eight subsections. 41 assertions re-derived from source. `scripts/split_adjacency_check.py`
was written for 4.6's adjacency claim rather than quoting an unsourced figure.

Evidence used:
- `runs/20260804_burst_aware_split_04/` — the released split, τ=15 s, seed
  20260804; 68 images moved; sizes 1478/438/205 held
- `runs/20260804_burst_aware_tau_sweep/` — why τ=15 and not 20/25/30/35/45/60
- `runs/20260804_burst_feasibility/` — whether the 15 classes can be rescued by
  moving whole bursts
- `runs/20260804_build_corrected_dataset_02/` — 8/8 verification checks, SHA-256
  of every copy against its source
- `runs/20260804_duplicate_contamination/` — three-way contamination, published
  against corrected
- `runs/20260809_split_ratio_by_group*/`, `runs/20260809_split_v1_vs_v2_by_group_03/`
- Table T2, Figure F4, `near_duplicate_pair.png`, `split_verification_sheet.png`

Scope limit that must travel with every contamination number: the figures cover
pairs sharing an **identical class inventory** only. Partial overlap is
pervasive and no split of this dataset eliminates it.

### Section 6 — Results — DRAFTED

Five subsections. 24 assertions re-derived from source. One drafted bullet (the
rescued classes scoring "near 0.995") was NOT written: per-class AP@50 is
committed nowhere, only AP@50-95, so the argument is made on the strict metric.

Evidence used:
- `data/master_results.csv` — 11 rows, 10 `inclusion=benchmark`, read only
  through `ec61.load_benchmark_rows`
- `data/latency_by_arch.csv` — per-architecture means and pair gaps
- Tables T4, T5, T6; Figures F5, F6

Rule 5 bites hardest here. The accuracy spread between the top models is small;
every ordering claim needs its margin stated, and the latency resolution
(0.24 ms / 1.75%) governs which latency orderings are reportable at all.

### Section 7 — Discussion — DRAFTED

Four subsections, deliberately shorter than 3, 4 and 6 per the Length note
above. Three claims in 7.1 rest on readings of the prior-work PDFs and are
flagged in the section header as pending verification: the fork, the
cross-validation protocol, and the published complexity figures.

Evidence used:
- The framework-version argument, already set up in 5.2
- The uniform-but-not-neutral argument from 5.3, referenced forward as
  `sec:discussion`
- The two prior-work findings in `notes/writing-corrections.md`
- `reference/electrocom61-yolov9.ipynb` and the README's reading of it — what
  the 95.9% figure does and does not evidence

### Section 8 — Limitations — DRAFTED

Eight paragraphs, one page, deliberately blunt. Ten assertions re-derived from
source. RT-DETR-l was found to be the exception to the training-budget
paragraph -- it early-stopped at epochs 59 and 73 while every YOLO ran the full
100 -- so the comparison sets four unconverged models against one converged one,
which the paragraph now says.

Evidence used: single seed, one GPU, no variance estimate; the augmentation
confound; the scope limit on the contamination figures; RT-DETR-l evaluated at
`l` scale against YOLO `s` scale.

### Section 2 — Related Work — DRAFTED

Four subsections: results reported on ElectroCom61; the e-waste application;
splits, leakage and evaluation validity; metrics and efficiency reporting. It
DESCRIBES; Section 7 argues. Checked mechanically: no sentence over 60
characters is shared verbatim between the two.

The literature search is done. 25 of the bibliography's 34 entries are cited
here, including the three that were waiting for it — `apicella2025leakage`,
`bernett2024guiding` and `rosenblatt2024leakage`.

**Gap closed 2026-08-15.** 2.2's survey paragraph was omitted in the first draft
because the six prior systems were described rather than named, and resolving
descriptions to papers is an editorial judgement rather than a lookup. Full
titles, authors and venues were then supplied, every field resolved against
Crossref, and the paragraph written: `lu2022sorting`, `sharma2024vision`,
`rajeev2025ewaste`, `sarswat2024realtime`, `sterkens2021xray`,
`puttero2024disassembly`. Three supplied years disagreed with Crossref and
Crossref was preferred in each case.

**Two claims from the brief were written weaker,** both in 2.1 and both recorded
in the section header: "three backgrounds" (no background count is recorded
anywhere in this repository) and "two detectors, both above 95% mAP@50" (the
detector count is not recorded, and the README's reading of the archived
notebook is that the 95.9% figure comes from a dictionary unlabelled as to which
metric it is, so attaching "mAP@50" to it asserts more than the source supports).

### Section 9 — Conclusion — DRAFTED

Five short paragraphs, 377 words. Held to three constraints and each checked
mechanically rather than by eye: no citation (none present); no numeral that
does not appear elsewhere (only 15 and 61, both from Section 3); and no sentence
of 60 characters or more shared verbatim with any other section (zero, against
all five checked). The closest near-match to Section 7 scores 0.58 and is
between two different claims that share the words "capture session".

