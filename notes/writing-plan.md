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
| 7 | 2 — Related Work | stub — **blocked**, see below |
| 8 | 9 — Conclusion | stub |
| 9 | 1 — Introduction | stub |
| 10 | Abstract | not started |

**Sections 3 through 8 are complete and fact-checked.** They are the model for
the rest: every number in them traces to a committed file, and anything that does
not is marked in the section file's own header comment rather than left silent.

**Remaining: 2, 9, 1 and the abstract.** Section 2 is blocked on a literature
search that has not started (see its entry below). Sections 9, 1 and the abstract
are not blocked --- they are written last by design, from the settled claims of
3 through 8, and those claims are now settled.

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

### Section 2 — Related Work

Claims: _to be supplied._

**BLOCKED on a literature search that has not started.** `references.bib` holds
three entries — `yolov12paper`, `yolov13paper` and `electrocom61` — and all three
are already cited elsewhere in the paper. A Related Work section needs more than
the three papers this study argues with: the detector families evaluated, prior
work on electronic-component and e-waste detection generally, and whatever else
the search turns up. None of that has been gathered.

No search items outstanding.

**Closed 2026-08-15:** whether YOLOv13 is distributed outside the Ultralytics
package. Three sources, all checked: the iMoonLab/yolov13 repository, whose
README states "The code is based on [Ultralytics]"; Ultralytics issues 21181 and
21243, both requesting integration and both closed as not planned; and the
architecture paper. The claim is grounded in 5.1 and 7.1 and the repository is
cited as `yolov13repo`. It has no CITATION.cff and no Zenodo DOI, so it is cited
as software with a URL and an access date.

**Closed 2026-08-15:** `yolov13paper`'s venue, pages and DOI. It was indexed
after all — IEEE Xplore document 11602786, 2026 IEEE International Conference on
Smart Sustainable Systems for Computer and Engineering Applications (3SCEA),
Cairo, 19–21 April 2026, doi `10.1109/3SCEA68071.2026.11602786`. The entry is no
longer in press and no longer carries its ISBN. Xplore shows no page range, so
the field is omitted rather than guessed.

### Section 9 — Conclusion, Section 1 — Introduction, Abstract

Written last, from the settled claims of 3–8. No skeleton until those are drafted.

## Open items

Mirrored from the section files' header comments so they are not lost when those
files are next edited. Closed items are kept with their resolution for one
revision, then dropped.

**Open**

1. **The fourth device identifier.** The metadata records four device names;
   the dataset paper describes three cameras. `X` carries 311 images, 14.7\% of
   the dataset, and has no counterpart in the paper. Stated as a fact in 3.6
   with no cause attributed. Settling whether it is a separate handset or an
   alias needs something the released files do not contain.

**Closed 2026-08-14** — all four items previously listed here.

- *5.3 "five convolutional detectors"* — the prose already reads four. The
  header comment claiming otherwise was stale, not the prose.
- *5.3's diverged-run numbers* — `data/kaggle/results_rtdetr_l_pub.json` is
  committed and `runs/20260812_verify_diverged_run/` checks every figure against
  it, all PASS. Two cautions from that run are worth carrying forward:
  `best_epoch` is derived, not stored, and mAP@50 is exactly zero at epoch 5 as
  well as after divergence, so zero mAP cannot on its own date the divergence.
  5.3 dates it from the loss terms and is unaffected.
- *The fused/unfused claim* — verified by the author against all three PDFs, and
  the finding was finer than the claim: the dataset paper reports no parameter
  counts at all. 5.5 now separates the two studies that report counts without
  stating fusion from the one that reports none.
- *5.4's forward reference to `sec:dataset-audit`* — Section 3 is written and
  establishes the 45/46 class counts and their cause, which is what 5.4 relies
  on it for.
