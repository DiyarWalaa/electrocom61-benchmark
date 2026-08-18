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
| 9 | **1 — Introduction** | **complete** (drafted, constraint-checked) |
| 10 | **Abstract** | **complete** (drafted, constraint-checked) |
| 11 | **10 — Data and Code Availability** | **complete** (drafted 2026-08-15; DOI placeholder) |

**Sections 1 through 9 are complete and fact-checked.** They are the model for
the rest: every number in them traces to a committed file, and anything that does
not is marked in the section file's own header comment rather than left silent.

**The draft is complete.** Nothing remains to be written. What remains before
submission is listed under *Before this can be submitted* below, and none of it
is drafting.

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

## Handoff — read this first if you are a fresh session

State as of 2026-08-15, after the abstract and the availability statement. The
paper builds clean at **36 pages**: 0 undefined references, 0 undefined
citations, 0 BibTeX warnings, **0 overfull and 0 underfull boxes**. 80 citation
instances across 35 entries. **Every section, the abstract, the availability
statement and the appendix are drafted and fact-checked. The draft is done.**

### Single homes for repeated figures, established 2026-08-15

A full-paper read found four figures stated more than once in near-identical
words. Each now has one home and everything else points at it. Restating any of
them is a regression, not an improvement.

| Figure | Home | Points back |
|---|---|---|
| 0.24 ms latency noise floor | **5.5** (value + derivation) | 6.4 names the value and cites 5.5; 8 cites 5.5 without the value. Figure and table captions keep it in full — captions must stand alone. |
| 0.0515 margin, 95 excluded low-information pairs (23 test–train) | **3.7** | 4.7 points, asserting nothing about carry-over. The appendix restates both; it is a standalone verification sheet and was left. |
| 95.9% / 84.9% published disagreement | **1** (states it), **2.1** (states it with the architecture) | Both now attribute metric and architecture; `data/published_accuracy.csv` is the source. |
| "more than a quarter" of annotation effort | 27.0% in **3.1** | 1 and 3's opening both say "more than a quarter". Never "a quarter" — 27.0% is more. |

### Two things a fresh session must not undo

1. **"under one configuration, with a single documented deviation."** This
   phrasing appears in the abstract, in Section 1's third contribution and in
   Section 9's first paragraph, and it replaced a bare "under a single
   configuration" on 2026-08-15. The bare form flattened 5.3 — RT-DETR-l needs a
   learning rate a hundredfold lower and does not train at all without it — in a
   paper whose whole argument is that experimental conditions go under-reported.
   Section 9 additionally said "holds every setting but the architecture fixed",
   which 5.3 flatly contradicts; it now reads "otherwise holds". The wording is
   5.2's and 5.3's own. Do not compress it back. Note the scope: the deviation is
   the *learning rate*. RT-DETR-l's early stop at epochs 59 and 73 is an outcome
   of a patience setting shared by all ten runs, not a second deviation, and
   Section 8 is where it belongs.
2. **Section 10 is load-bearing for two promises.** The abstract's closing
   sentence and Section 9's last paragraph both say this material "is released".
   Before Section 10 existed the paper named no location at all. **Both promises
   are now discharged by a minted DOI, and no `\fbox` placeholder remains
   anywhere in the document** — filled 2026-08-18, so the softening contingency
   recorded here is closed. The paper cites the **concept** DOI
   `10.5281/zenodo.21994825`, not the v1.0 version DOI `10.5281/zenodo.21994826`,
   because the v1.0 archive contains this paper's source with the placeholders
   still unfilled; the release carrying the filled text is tagged `v1.0.1`. Do
   not switch the citation to the version DOI. The sentence was reworded as well
   as filled: it had promised that "the version this paper describes stays
   retrievable" from an identifier that floats to the latest version by design,
   and it now states what the concept DOI does and names the tag as what fixes
   the version.

### The abstract — DRAFTED

248 words, in `paper/main.tex` rather than a section file, because
`\begin{abstract}` is class-specific and belongs with the rest of the
class-dependent preamble. Six moves in one paragraph: task and dataset; the
defect; what was done; the headline result; the deployment result; availability.
Its header comment records the constraints and the two pieces of wording that
must not drift. The constraints it was held to, all checked mechanically:

1. **Every number already appears in the body.** Used: 15 of 61 classes; 2,121
   images; 12,937 annotations; five detectors; 1478/438/205; the 0.5, 0.95 and
   ten thresholds of the metric definitions. All verified present elsewhere.
2. **Never a bare mAP@50** — both uses are paired with mAP@50-95 (`CLAUDE.md`).
3. **The "none of the three" form is bounded to TIMING.** Do NOT extend it to
   mAP@50-95 or to variance: both benchmark studies *plot* mAP@50-95 in training
   curves, and one *does* report confidence intervals and paired t-tests. A
   version of that false claim reached a built PDF on 2026-08-15 and had spread
   to four sections before it was caught. For mAP@50-95, "none of the three
   prior studies tabulates" is the exact wording.
4. **RT-DETR-l leads on mAP@50 only**, not mAP@50-95, where YOLO26s leads. Any
   phrasing like "most accurate" is wrong. The deployment recommendation is
   YOLO26s. The abstract names no model, which removes the hazard entirely.
5. **No citation, no undefined abbreviation.** mAP@50 and mAP@50-95 are expanded
   on first use; no model name appears, so YOLO and RT-DETR never need expanding.

### Verification habits this project runs on

There is no runner script. The suite is this list, run by hand, so adding a
check means adding it here.

- `powershell -File scripts\build_paper.ps1` after every prose change. It fails
  the build if `VERIFY`, `PLACEHOLDER`, `TODO` or `UNSOURCED` reaches the printed
  bibliography — that check exists because internal notes were being typeset.
  (This line held a literal backspace byte where the `\b` of the path should
  be, rendering as `scriptsuild_paper.ps1`; repaired 2026-08-18.)
- `python scripts/citation_audit.py` after any change to prose or bibliography.
  Currently 79 citation instances across 35 entries.
- `python scripts/check_prose.py` after any change to prose. **Added 2026-08-18,
  because nothing in the suite read a sentence.** A doubled verb — "What it
  does does not state" — survived several commits and several clean builds in
  7.1 before being caught by eye. It checks three things: doubled words, joining
  consecutive lines so a word split across a line break is still caught; the
  single-homes table below, which it PARSES from this file, so adding a row there
  adds a check with no edit to the script; and the protected phrasings and
  forbidden forms recorded under *Two things a fresh session must not undo* and
  in the abstract's constraints. Those last cannot be parsed from English, so
  each rule in the script carries an exact quotation from this file as its anchor
  and fails if that text is ever rewritten — which is what stops the script and
  this plan drifting apart. Rule 4 (never a bare mAP@50) is reported as a WARNING
  rather than a failure, because quotations of prior work legitimately carry a
  bare one and a hard failure would be wrong more often than right.
- Section files carry header comments recording what was checked, what was
  written weaker than briefed, and why. **Read the header before editing a
  section** — several record wording that must not drift back.

### Open items, all in the author's hands

- **CLOSED 2026-08-15 — the two figures for Section 1, paragraph 2.** The
  concrete instance of the published disagreement is now written: the dataset
  paper reports YOLOv9s at 95.9% mAP@50 while both benchmark studies tabulate
  84.9% for the same architecture. Both figures are recorded in
  `data/published_accuracy.csv`, hand-transcribed from the PDFs with each row
  naming its source table, held to the same discipline as
  `published_complexity.csv`. The objection that held the sentence back is
  resolved rather than overridden: README.md's hedge is an analysis of the
  archived NOTEBOOK, while this sentence quotes what the PAPER attributes in its
  own text and its Table 3. Two different objects. 2.1's metric-free "a headline
  figure of 95.9%" was adopted for the notebook and deliberately still stands.
  The full distinction is in `.gitignore`'s block for the new file and in the
  headers of `01-introduction.tex` and `02-related-work.tex`.
- **CLOSED 2026-08-15 — both typographic defects.** The overfull box was
  `\texttt{optimizer="auto"}` in 5.2, an unbreakable token running the line
  40.8 pt over; "default of X" became the appositive "default, X," and an
  `\allowbreak` was added at the token's `=`. The underfull was Figure 4's
  caption (recorded here earlier as Figure 3, which was wrong), stretched to
  badness 3219 because the second `IMG_...` filename could not be divided;
  `\allowbreak` after each escaped underscore fixed it. The build now reports
  0 and 0.
- **Length.** 36 pages, up 1 for the availability statement. Sections 3 and 4
  exceed what most venues take; the
  standing instruction is *stop adding, do not cut* until a venue is chosen.
- **Unread citations.** Every entry except the three prior studies is
  registry-resolved but unread; Section 8 concedes this. `notes/citation-audit.md`
  lists all 79 uses with their sentences so each can be checked against a source.
- **`dodge2020finetuning`** is in the bibliography, deliberately uncited.
- **Four working files cannot be deleted** (the guard denies deletion) and are
  gitignored: `paper/references.bib.head/.mid/.tail` and `paper/main.bbl.bak`.

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
above. **7.4 was cut from four paragraphs to one on 2026-08-15**, after a
full-paper read found it recapping 6.2, 6.4 and 6.5 rather than interpreting
them, with a closing that shared its construction with 6.5's. What survives is
the only material Section 6 does not carry: the proxy-failure literature
(`vasu2023mobileone`, `chen2023run`, `kong2026edge`), which places 6.4's local
finding in a documented pattern. It was NOT folded into 7.1 — 7.1's claim is
that the three published accuracy figures are not comparable with one another,
which is a claim about reconciling a record; 7.4's is that an accuracy-only
comparison structurally cannot express deployment cost, whatever its reporting
quality. Merging them would give 7.1 two claims. Three claims in 7.1 rest on readings of the prior-work PDFs and are
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

### Section 1 — Introduction — DRAFTED

Five paragraphs, 501 words, written last so it promises only what the body
delivers. Three constraints checked mechanically: every numeral appears
elsewhere (2,121; 12,937; 61; and the 50/95 of mAP@50--95); every citation is
already in the bibliography AND already used elsewhere (electrocom61,
lu2022sorting, sharma2024vision, yolov12paper, yolov13paper); zero sentences of
60 characters or more shared verbatim with any other section.

No separate research-questions list, by decision: the contributions cover the
same ground and two overlapping lists would be redundant at this length.

The contributions list says what each item ESTABLISHES rather than what it
consists of, which is what keeps the section from arguing. The wording "none of
which the three prior studies tabulate" is exact and must not drift back to "no
prior study reports" -- see the correction recorded in 2.4's header.

### Section 9 — Conclusion — DRAFTED

Five short paragraphs, 377 words. Held to three constraints and each checked
mechanically rather than by eye: no citation (none present); no numeral that
does not appear elsewhere (only 15 and 61, both from Section 3); and no sentence
of 60 characters or more shared verbatim with any other section (zero, against
all five checked). The closest near-match to Section 7 scores 0.58 and is
between two different claims that share the words "capture session".

