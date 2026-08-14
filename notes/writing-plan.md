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
| 1 | 3 — Dataset Audit | stub |
| 2 | 4 — A Corrected Split | stub |
| 3 | **5 — Benchmark Setup** | **complete** (5.1–5.6 drafted, fact-checked) |
| 4 | 6 — Results | stub |
| 5 | 7 — Discussion | stub |
| 6 | 8 — Limitations | stub |
| 7 | 2 — Related Work | stub |
| 8 | 9 — Conclusion | stub |
| 9 | 1 — Introduction | stub |
| 10 | Abstract | not started |

Section 5 is finished and is the model for the rest: every number in it traces
to a committed file, and the two places where it does not are marked in the
file's own header comment rather than left silent.

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

## Section skeletons

Claim-plus-evidence bullets are supplied per section before drafting. Recorded
here as they arrive; the *Evidence available* column is what the repository
already holds, so drafting does not have to go looking for it.

### Section 3 — Dataset Audit

Claims: _to be supplied._

Evidence available:
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

### Section 4 — A Corrected Split

Claims: _to be supplied._

Evidence available:
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

### Section 6 — Results

Claims: _to be supplied._

Evidence available:
- `data/master_results.csv` — 11 rows, 10 `inclusion=benchmark`, read only
  through `ec61.load_benchmark_rows`
- `data/latency_by_arch.csv` — per-architecture means and pair gaps
- Tables T4, T5, T6; Figures F5, F6

Rule 5 bites hardest here. The accuracy spread between the top models is small;
every ordering claim needs its margin stated, and the latency resolution
(0.24 ms / 1.75%) governs which latency orderings are reportable at all.

### Section 7 — Discussion

Claims: _to be supplied._

Evidence available:
- The framework-version argument, already set up in 5.2
- The uniform-but-not-neutral argument from 5.3, referenced forward as
  `sec:discussion`
- The two prior-work findings in `notes/writing-corrections.md`
- `reference/electrocom61-yolov9.ipynb` and the README's reading of it — what
  the 95.9% figure does and does not evidence

### Section 8 — Limitations

Claims: _to be supplied._

Evidence available: single seed, one GPU, no variance estimate; the augmentation
confound; the scope limit on the contamination figures; RT-DETR-l evaluated at
`l` scale against YOLO `s` scale.

### Section 2 — Related Work

Claims: _to be supplied._

Blocker: `references.bib` holds **two** entries (`yolov12paper`,
`yolov13paper`). Section 5 twice refers to "the three published studies" on this
dataset. A third entry is required before either sentence can carry a citation.

### Section 9 — Conclusion, Section 1 — Introduction, Abstract

Written last, from the settled claims of 3–8. No skeleton until those are drafted.

## Open items carried from Section 5

These are in `05-benchmark-setup.tex`'s header comment and must be closed before
submission. They are listed here so they are not lost when that file is next
edited.

1. **5.3 says "five convolutional detectors"; it should be four.** Four are
   convolutional; the fifth is the transformer the sentence contrasts them
   against. Author's fix.
2. **5.3's diverged-run numbers** (epochs 6/7/19/4, 0.0039, 0.0057) are not yet
   verifiable from a committed file.
3. **The fused/unfused claim about three published studies** needs the three
   PDFs; it cannot be checked from this repository.
4. **5.4 references `sec:dataset-audit`**, which resolves to an empty Section 3.
   A resolved reference to an empty section looks correct in the PDF and cannot
   be found by grepping for undefined references. Re-check when 3 is written.
