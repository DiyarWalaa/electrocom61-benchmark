# Fact-check: drafted subsections 5.1 and 5.2

Every number, count and claim in `paper/sections/05-benchmark-setup.tex`
checked against the committed sources: `data/config_provenance.csv`, the ten
`data/kaggle/results_*.json`, the ten `args.yaml`, `data/master_results.csv`,
`data/latency_by_arch.csv`, and the generated `tables/t3_training_config.tex`
and `tables/t5_efficiency.tex`.

**The prose has not been edited.** This file records what was found.

Machine-checked: 26 assertions, 25 pass, 1 fails.

---

## Everything numeric checks out

| Claim | Verdict |
|---|---|
| seven settings copied | **7** in `config_provenance.csv` |
| seven settings added | **7** |
| three added concern reproducibility | `seed`, `deterministic`, `ultralytics` — **3** |
| two added concern training behaviour | `patience`, `pretrained` — **2** |
| remaining two added | `lr0 (RT-DETR-l)`, `models (new)` — **2** |
| copied set = the six named + replicated models | exact match |
| 100 epochs | `epochs = 100` |
| batch size 16 | `batch = 16` |
| AdamW optimiser | `optimizer = AdamW` |
| learning rate 0.01 | `lr0 = 0.01` |
| weight decay 0.0005 | `weight_decay = 0.0005` |
| patience 15 | `patience = 15` |
| seed 0 | `seed = 0` |
| 640 pixels | `imgsz = 640` |
| Ultralytics 8.4.115 | `ultralytics = 8.4.115` |
| PyTorch 2.5.1+cu121 | `torch = 2.5.1+cu121` |
| Tesla P100 | `Tesla P100-PCIE-16GB` |
| all ten runs | 10 results JSONs |
| five detectors | 5 distinct models |
| all YOLO variants at "s" scale | `yolo11s`, `yolo12s`, `yolo26s`, `yolov9s` |
| RT-DETR-l higher params and cost | 32,109,095 / 105.6 vs next-highest 9,488,787 / 20.892 |

The environment is identical across all ten runs, so quoting one GPU, one
PyTorch version and one Ultralytics version for the whole benchmark is
justified.

---

## 1. One factual mismatch

> "All ten runs used an identical configuration, with one exception described in
> Section 5.3."

**Two settings vary across the ten `args.yaml` files, not one:** `lr0` and
`model`.

`lr0` is the intended exception. `model` obviously varies — it is what the
benchmark compares — but the sentence as written says the configurations are
identical apart from one thing, and taken literally that is false.

Trivial to fix in wording ("identical apart from the architecture itself and
one exception"), but it is a factual claim and it is currently wrong.

---

## 2. The most serious issue: what `default` means

> "Table 3 lists every setting that was not left at its framework default."

**The data cannot support this claim, and it may be false for three rows.**

`args.yaml` records the *resolved* configuration — every setting appears in it
whether it was specified explicitly or filled in by the framework.
`config_provenance.csv` was scaffolded from those files, so it has no way to
distinguish "specified by us" from "left at the default". The `source` column
records something different: **whether prior work states the setting**, and if
not, who decided it.

Three settings marked non-`default` plausibly *equal* the Ultralytics default:

| Setting | Value | Marked | Concern |
|---|---|---|---|
| `imgsz` | 640 | constrained | 640 is, to the best of my knowledge, the Ultralytics default |
| `deterministic` | true | added | likewise |
| `pretrained` | true | added | likewise |

I cannot verify this from the repository: Ultralytics is not installed here, and
nothing committed records its defaults. But if any of the three does equal the
default, then Table 3 contains a setting that *was* left at its framework
default, and the sentence is false.

The safe restatement is to describe what the column actually encodes — settings
that prior work states, or that this study decided — rather than framework
divergence. That also matches the caption `make_tables.py` generates.

---

## 3. Cross-references that will not survive compilation

- **"Table 3"** is a typed number. The table's label is
  `tab:training-config`, and **no table is `\input` anywhere in the document
  yet**, so at present the paper contains zero tables and the reference points
  at nothing. Even once tables are added, a typed number breaks the moment one
  is inserted before it.
- **"Section 6"**, **"Section 7"** are typed. They currently correspond to
  Results and Discussion given the nine-file ordering, but only by coincidence
  of that ordering.
- **"Section 5.3"** is referenced twice and **does not exist**. The section
  file's TODO records it as still to be written.

None of these was changed, since the brief was to insert the prose with a
specific list of substitutions.

---

## 4. Claims that cannot be traced to any committed source

Not errors — they are simply outside what this repository can confirm. Each
needs a citation or an author check before submission.

| Claim | Status |
|---|---|
| YOLO26s "released in January 2026" | no source in repo |
| YOLO26s "the most recent member of the YOLO family" | no source in repo |
| YOLO26s "removes non-maximum suppression from its detection head" | **corroborated, not stated**: its postprocess time is 0.38 ms against 1.06–1.08 ms for the other three YOLO models (`latency_by_arch.csv`) — consistent with an NMS-free head, but the architectural claim itself is external |
| RT-DETR-l "is a transformer-based detector" | **corroborated, not stated**: the `lr_note` field in both RT-DETR results JSONs reads "transformer diverged at the YOLO learning rate" |
| "RT-DETR is not published at an equivalent scale" | no source in repo |
| YOLOv13 "distributed as a fork of the Ultralytics package rather than within it" | no source in repo; this is the stated reason for an exclusion and should be citable |
| Ultralytics default is `optimizer="auto"`, which "silently overrides the initial learning rate" | no source in repo; Ultralytics is not installed here. This is a strong claim about another package's behaviour and needs a citation to its source or documentation |
| "Both studies report PyTorch 2.0.0" | recorded in `notes/writing-corrections.md` from the author's reading of the PDFs; flagged there as unverified by tooling |
| "The first three appear in the comparison tables of both prior studies" | from the citation column of `config_provenance.csv`, itself the author's reading of the PDFs |
| dataset "distributed at 640×640, having been resized during its own preparation" | traceable to `README.md`, which reports the Roboflow export applied a stretch resize to 640×640. The primary source, `README.roboflow.txt`, ships inside the gitignored dataset archive |
| "a conveyor-belt sorting system runs on modest hardware" | motivation, not a factual claim about the data |

---

## 5. One style note on my own transformation

`[X], [Y]` was rendered literally as `\citep{yolov12paper},
\citep{yolov13paper}` — two adjacent citations. `\citep{yolov12paper,yolov13paper}`
would set as a single bracketed group and is almost certainly what is wanted.
Left as-is because the brief specified the substitution.

No en-dash substitutions were made: the prose contains no numeric ranges. No
characters needed escaping — there are no ampersands, percent signs,
underscores or braces in the text.

---

# Fact-check: subsection 5.3 (2026-08-10)

`A configuration that is uniform but not neutral`, inserted verbatim. Prose not
edited. Two substitutions applied per the brief: `Section 6` ->
`Section~\ref{sec:results}`, `Table 3` -> `Table~\ref{tab:training-config}`.

## Verified against committed sources

| Claim | Source | Verdict |
|---|---|---|
| lr0 reduced 0.01 -> 0.0001 | `data/config_provenance.csv` rows `lr0`, `lr0 (RT-DETR-l)` | PASS |
| "a factor of one hundred" | 0.01 / 0.0001 = 100 exactly | PASS |
| converged run val mAP@50 0.938 | `results_rtdetr_l_pub_lr1e4.json` `val.mAP50` | PASS |
| converged run test mAP@50 0.9171 | same file, `test.mAP50` | PASS |
| best checkpoint at epoch 58 | `rtdetr_l_pub_lr1e4_training_curves.csv`, argmax of Ultralytics fitness (0.1*mAP50 + 0.9*mAP50-95) = epoch 58, fitness 0.635047 | PASS |
| "the ten runs" | `master_results.csv` has 10 rows | PASS |
| lr0 is the only non-architecture difference among runs | `config_provenance.csv`: `lr0 (RT-DETR-l)` is the sole per-model override | PASS |

Note on epoch 58: the run ran to epoch 73, exactly 15 beyond the best epoch,
which independently corroborates `patience = 15`. Epoch 58 is best by FITNESS,
not by mAP@50 alone -- epoch 63 scores higher on mAP@50 (0.94041). The claim is
correct because Ultralytics selects `best.pt` by fitness, but it is only correct
under that definition.

## FAILED

**"the same value that trains five convolutional detectors to convergence"** --
should be FOUR. `master_results.csv` holds five distinct models: `yolo11s`,
`yolo12s`, `yolo26s`, `yolov9s` (convolutional) and `rtdetr-l` (transformer).
The sentence contrasts the convolutional detectors against the transformer, so
counting the transformer among them inflates the evidence and contradicts the
clause it sits in. Not edited; flagged for the author.

## NOT YET VERIFIABLE -- awaiting the recovered run

Every number describing the diverged run itself. Nothing committed contains
them; they need `data/kaggle/results_rtdetr_l_pub.json` and
`data/kaggle/artifacts/rtdetr_l_pub/rtdetr_l_pub_training_curves.csv`:

- losses finite through epoch 6, NaN from epoch 7 (per-term onset unconfirmed)
- validation mAP@50 exactly zero from epoch 7 onward
- early stopping at epoch 19
- best checkpoint from epoch 4
- 0.0039 mAP@50 validation, 0.0057 test

Also unverified: "Both runs are retained in the repository" -- currently only
the lr1e4 run is. Becomes true on ingestion.

## Untraceable claim needing a citation

"Transformer-based detectors are commonly trained at learning rates one to two
orders of magnitude below those used for convolutional detectors." Plausible and
consistent with this study's own evidence, but stated as established practice
with no citation. Same category as the untraceable claims logged for 5.1/5.2.

## Scope note

"This is the single respect in which the ten runs differ" is standalone in 5.3,
where 5.2 says "Apart from the architecture under test". Read alone, 5.3 is
false -- the architecture differs too. Read after 5.2, the qualifier carries.
Not an error; a dependency on reading order worth being aware of.

---

# Fact-check: subsection 5.4 (2026-08-10)

`Evaluation protocol`, inserted verbatim. Prose not edited. Two substitutions:
`Section 3` -> `Section~\ref{sec:dataset-audit}`, `Section 5.2` ->
`Section~\ref{sec:training-configuration}`. Both resolve to the numbers the
draft had typed (3 and 5.2), confirming the manual numbering was correct.

Verification script: `scripts/verify_eval_protocol.py`, run directory
`runs/20260810_verify_eval_protocol_02/`.

## Verified

| Claim | Verdict |
|---|---|
| ten training runs, twenty evaluations | PASS -- 10 rows, all 20 evaluations carry both mAP figures |
| 45 classes on val, 46 on test, published split | PASS -- unanimous across all 5 published runs |
| 61 on both, corrected split | PASS -- unanimous across all 5 corrected runs |
| ESP32 is exactly the 45-vs-46 difference | PASS -- test-minus-val is `{ESP32}` alone in all 5 published runs, with nothing in val-minus-test |
| ESP32: 190 training, 2 test, 0 validation instances | PASS -- `class_split_counts.csv` |
| NMS IoU 0.7, max_det 300, identical across ten runs | PASS -- all 10 args.yaml |
| confidence threshold left unset, resolved by framework at run time | PASS -- `conf: null` in all 10 |

**The threshold paragraph is worded correctly.** It says "The training
configuration recorded ...", which is exactly what the sources support: every
args.yaml is `mode: train`, and no args.yaml exists for the evaluation passes.
A version of this sentence claiming these were the *evaluation* thresholds
would not have been supportable.

## Flagged -- claims about the paper that the paper does not yet meet

**"Precision and recall are reported for completeness."** Not currently true.
Both exist in the per-run results JSONs, but neither appears in
`data/master_results.csv` nor in any generated table -- `t4_main_results` has
Val@50, Val@50--95, Test@50, Test@50--95, Cls val, Cls test and nothing else.
Either the columns get added or the sentence needs softening.

**"per-class average precision is reported for all classes."** Two problems.
No table currently presents per-class AP at all. And "for all classes" is false
under the published split, where per-class AP exists for the 45 and 46
evaluated classes -- not all 61. That contradicts the very next paragraph,
which is this subsection's central point. It is true under the corrected split.

**"Four accuracy quantities are reported."** The paragraph names mAP@50,
mAP@50--95, precision and recall (four), then adds per-class AP as a fifth
item; the following paragraph then calls classes-evaluated "a fifth quantity".
Either per-class AP is not an accuracy quantity, or classes-evaluated is the
sixth. Internal counting inconsistency, not a factual error.

## Not verifiable from committed sources

Three claims about prior work, each needing the two prior-work PDFs rather than
anything in this repository:

- "mAP@50 ... is the only accuracy metric prior work on this dataset reports"
- "no published study on this dataset reports [mAP@50--95]"
- per-class AP, "which no published study on this dataset provides"

Same category as the T3 classifications, which were checked against Section IV
of each PDF.

One procedural claim is supported but not provable from files: "the test
partition was not consulted until training had completed". The artifact layout
is consistent with it -- training used `split: val`, and the test evaluation is
a separate pass -- but only the notebook can establish ordering.

## Cross-reference hazard

`\ref{sec:dataset-audit}` resolves, because the label sits on the Section 3
stub. Section 3 has no content. A resolved reference to an empty section is
worse than a broken one: it prints a plausible number, and no undefined-
reference warning will ever flag it. Re-check when Section 3 is written that it
actually establishes what 5.4 says it does.

---

# Fact-check: subsection 5.5 (2026-08-11)

`Efficiency measurement`, inserted verbatim. Prose not edited. No cross-
references to convert -- 5.5 cites no section or table by number.

Verification script: `scripts/verify_efficiency_claims.py`, run directory
`runs/20260811_verify_efficiency_claims_02/`.

## Verified

| Claim | Verdict |
|---|---|
| YOLO26s 9,995,078 / 22.998 -> 9,488,787 / 20.892 | PASS, exact |
| RT-DETR-l 32,931,431 / 110.159 -> 32,109,095 / 105.6 | PASS, exact |
| parameter reduction spans 0.2% to 5.1% | PASS -- actual 0.1586% (yolo11s) to 5.0654% (yolo26s), which to one decimal is exactly 0.2% and 5.1% |
| batch size one | PASS -- `batch: 1` |
| 640 pixels | PASS -- `imgsz: 640` |
| Tesla P100 | PASS -- `Tesla P100-PCIE-16GB` |
| twenty inferences discarded before timing | PASS -- `warmup: 20` |
| `torch.cuda.synchronize()` before stopping the clock | PASS -- in the timer description |
| median and 95th percentile reported | PASS -- p50 and p95 |
| all ten checkpoints in a single session | PASS -- 10 model entries in one pass |
| all 205 images read once before timing | PASS -- `file_cache` |
| largest pair difference 0.24 ms, 1.75% | PASS, exact -- yolo11s, and the ms and % maxima are the same architecture |
| five architectures | PASS |

Both complexity figures agree between the two runs of every architecture, as
they must if the two rows describe the same weights.

## The 23% figure -- correct, but on a different basis from the 1.75%

The per-session measurements do vary by roughly this much, but the exact
percentage depends on a choice the prose does not state:

| yolov9s | 18.58 vs 24.23 ms, gap 5.65 ms |
|---|---|
| of the smaller | 30.41% |
| of the larger | **23.32%** |
| of the mean | 26.40% |

Only division by the larger reproduces 23%. That is a legitimate convention.
The problem is that the 1.75% pair gap in the same subsection comes from
`latency_by_arch.csv`, which -- verified from its own columns, not assumed --
divides by the **mean**. On that basis the cross-session figure would be 26.4%.

So the subsection states two spreads on two different bases. Neither number is
wrong. Recommend either stating the convention or recomputing 23% as 26.4% for
consistency with the figure it is implicitly being contrasted against.

Worth noting the claim survives on any basis: the smallest of the three, 23.3%,
is still an order of magnitude above the 1.75% within-session resolution, which
is the argument the paragraph is making.

## Omission, not an error

The protocol records a precaution the prose does not mention:

    burn_in: "30 images on one model before the loop, discarded"

This is separate from the 20-iteration warmup, and separate again from the
205-image pre-read that the prose does describe. The paragraph says "Three
precautions were taken" and then names warmup, synchronisation and percentile
choice; the burn-in is a fourth. Given the subsection's argument is that
efficiency protocols are under-reported, leaving one of its own steps out is
worth fixing.

## Not verifiable from committed sources

The debugging narrative in the fourth paragraph:

- "Two further complete passes were required before the protocol was stable"
- "the first model measured returned an end-to-end time approximately 4 ms
  above its identical counterpart while its inference time matched to within
  0.4%"

Only the final pass is committed. The only corroboration is the
`latency_source` string `unified_pass_v3_...`, whose `v3` is consistent with
two earlier passes but does not establish what they showed. The diagnosis --
first read from network-mounted storage -- is likewise not reconstructible from
anything in the repository.

The claim that fusion status "is rarely stated" in other papers is a claim
about the literature and needs a citation or softening.

---

# Corrections applied 2026-08-11

Five author-directed fixes to 5.3 and 5.5. All verified in the rendered PDF by
text extraction: the seven new phrasings present, the three superseded ones
absent.

## 1. Session paragraph replaced (5.5)

The 23% figure is gone. The paragraph now states the raw gap (5.65 ms, 18.58
against 24.23 ms for YOLOv9s) before the percentage, which makes the basis
recoverable by a reader even without the convention sentence.

**Both percentages re-verified on the mean basis:**

- pair gap: `latency_by_arch.csv` gives yolo11s gap 0.24 ms, mean 13.68,
  gap_pct 1.7544. Recomputing 100*0.24/13.68 = 1.7544 -- the column IS
  gap/mean, confirmed from its own values rather than assumed.
- cross-session: 5.65 / ((18.58+24.23)/2) = 5.65/21.405 = 26.3957% -> **26%**.

A sentence was added making the convention explicit: "Every spread quoted in
this subsection is expressed as a percentage of the mean of the two
measurements it describes." This is the only edit not dictated verbatim; it was
authorised by the instruction to say so explicitly if it was not already clear.
It was not clear -- the pair-gap sentence gave a bare "1.75%" -- so that
sentence now reads "1.75% of their mean" as well.

**Consequence to watch:** the convention sentence is a universal claim over the
subsection. Any spread added to 5.5 later on a different basis makes it false.
Recorded in the file header.

## 2. Precautions: three -> four (5.5)

The 30-image burn-in is now stated, distinguished from the 20-iteration warmup
(which is per-model) and given its purpose. Order is now warmup, burn-in,
synchronise, percentiles, matching the protocol block. The warmup sentence was
adjusted from "before timing began" to "before each model was timed", since the
per-model/once-per-loop distinction is the whole point of listing both.

## 3. Five -> four convolutional detectors (5.3)

The failure recorded in the 5.3 fact-check above is now fixed. `yolo11s`,
`yolo12s`, `yolo26s`, `yolov9s` are the four; `rtdetr-l` is the fifth model and
the transformer the sentence contrasts them against.

## 4. Fusion-reporting claim rescoped (5.5)

Was: "Which of the two a study reports is rarely stated" -- an unscoped claim
about the literature.

Now: "None of the three published studies reporting results on this dataset
states whether its parameter counts are fused or unfused."

**PENDING AUTHOR VERIFICATION.** This cannot be checked from anything in this
repository; it needs the three PDFs. Two further notes:

- `paper/references.bib` currently holds **two** entries, `yolov12paper` and
  `yolov13paper`. A third is required before this sentence can carry a
  citation, and the sentence names three studies.
- The claim is now falsifiable by a single counter-example, which is the point,
  but it also means one study stating "fused" breaks it outright. If the check
  finds one, "none" becomes "two of the three" or similar.

## 5. Earlier latency passes -- retrieval instructions issued

The two prior passes are not in the repository; the committed
`results_latency_unified.json` (sha256 23dd0d96..., 4691 bytes) is the third.
Until the earlier two are ingested, the fourth paragraph of 5.5 remains
asserted rather than traceable.

---

# 5.3 re-checked against the recovered run (2026-08-12)

`rtdetr_l_pub` is now ingested. Every number 5.3 asserts about the diverged run
is verifiable, and all of them pass. Verification:
`scripts/verify_diverged_run.py`, run `runs/20260812_verify_diverged_run/`.

## Now verified (was "not yet verifiable")

| Claim | Verdict |
|---|---|
| stopped at epoch 19 | PASS |
| 43.7 training minutes | PASS |
| best checkpoint from epoch 4 | PASS -- derived, see below |
| val mAP@50 0.0039 | PASS |
| test mAP@50 0.0057 | PASS |
| losses NaN from epoch 7, never finite again | PASS for the three TRAINING terms |
| validation mAP@50 exactly zero from epoch 7 to 19 | PASS |
| "Both runs are retained in the repository" | PASS -- now true |

The JSON has no `best_epoch` field. Epoch 4 is derived as the argmax of
Ultralytics fitness (0.1*mAP@50 + 0.9*mAP@50-95 = 0.001841) and corroborated
independently: best 4 + patience 15 = 19, the epoch the run stopped at.

## Flag 1 -- "its three loss terms" is ambiguous, and false on one reading

The curve file has SIX loss columns, not three. Training and validation do not
behave alike:

| column | first NaN | finite after |
|---|---|---|
| `train/giou_loss` | 7 | none |
| `train/cls_loss` | 7 | none |
| `train/l1_loss` | 7 | none |
| `val/giou_loss` | **2** | 4 |
| `val/cls_loss` | **2** | 4 |
| `val/l1_loss` | **2** | 4 |

The three training terms behave exactly as 5.3 describes -- finite through 6,
NaN at 7, never finite again, all three coinciding. The three validation terms
were NaN as early as **epoch 2**, recovered at epoch 4, and went NaN again from
5. So instability appears five epochs before the sentence says it does.

"Its three loss terms -- GIoU, classification and L1 -- took finite values
through epoch 6" is true of training and false of validation. Recommend naming
the pass. The validation behaviour arguably strengthens the argument: the run
was already unstable at epoch 2, and the checkpoint selected as "best" at epoch
4 sits in a gap between two NaN stretches.

## Flag 2 -- zero mAP is not exclusive to the post-divergence regime

Validation mAP@50 is exactly zero at epochs 5, 7, 8, ..., 19. The claim as
written -- zero from epoch 7 onward -- is true. But epoch **5** is also exactly
zero, before the training losses diverged. Zero mAP therefore cannot by itself
date the divergence, and a reader who takes "exactly zero" as the signature of
the NaN regime would misread epoch 5.

## Flag 3 -- mAP@50 reported without mAP@50-95, twice

CLAUDE.md: "Report mAP@50 AND mAP@50-95. Never mAP@50 alone." 5.3 reports only
mAP@50 in both places:

- "That checkpoint reaches 0.0039 mAP@50 on validation and 0.0057 on test"
  -- the 50-95 figures are 0.0016 and 0.0026, both verified.
- "reaching 0.938 mAP@50 on validation and 0.9171 on test" for the converged
  run -- the 50-95 figures are 0.6016 and 0.6045, both already in
  master_results.csv.

Not edited. Flagged because it is a project rule rather than a matter of taste.

## Ingestion notes

- The file arrived as `results_rtdetr_l_pub.json.txt` -- Windows appended `.txt`
  with the extension hidden, exactly as anticipated. No BOM; CRLF endings,
  normalised to LF to match the ten sibling JSONs. Parsed before and after
  writing, and the parsed content compared for equality across the round trip.
- `status: complete` in the JSON means the run finished without raising, NOT
  that it succeeded. Which is why divergence is declared by slug in
  `ec61.DIVERGED_RUNS` and never inferred from a status field or from the
  numbers.
