# Corrections to carry into the writing phase

Claims in the handoff documents that the repository's own evidence contradicts
or narrows. Each entry names the document, the claim as written, and the
replacement.

These are recorded here because the handoff markdown files are not in this
repository — they cannot be corrected in place, so the correction has to travel
separately.

---

## `03-models-and-config.md` — software versions in prior work

**As written:** no prior paper states versions.

**Too strong.** Both the YOLOv12 and YOLOv13 papers state **PyTorch 2.0.0**.
What neither states is the **Ultralytics version**.

**Replace with:** *prior work states the PyTorch version but not the
Ultralytics version.*

**Why the distinction carries weight.** The Ultralytics version is what fixes
the model definitions — the layer composition, the head, the loss, the default
augmentation pipeline and the NMS behaviour all move between releases under the
same model name. Two papers can both say "YOLOv8s, PyTorch 2.0.0" and train
architectures that differ. PyTorch pins the tensor library; Ultralytics pins the
model. Reporting the first without the second identifies the least
consequential half.

This study records both, in every one of the ten results JSONs:

| | |
|---|---|
| torch | `2.5.1+cu121` |
| ultralytics | `8.4.115` |

Source: `data/kaggle/results_*.json`, fields `torch` and `ultralytics`.

**Verification status.** The claim about what the YOLOv12 and YOLOv13 papers
state comes from the author's reading of those PDFs; the PDFs are not in this
repository and the statement has not been checked here. Re-confirm against the
sources when the sentence is written.

---

## `04-corrected-split.md` — "moves the fewest images"

**As written:** tau = 15 "moves the fewest images".

**False as stated.** tau = 30 moves 64 images against tau = 15's 68.

**Replace with:** *the fewest among the values that hold the split sizes* —
68 at tau=15, against 78 at tau=20 and 80 at tau=25.

tau = 30 does move fewer, but ends at 1458/438/225 instead of 1478/438/205, so
it is not a candidate. Source: `runs/20260804_burst_aware_tau_sweep/tau_sweep.csv`,
column `images_moved`, read against `sizes_held`.

The equivalent sentence in this repository's own `README.md` has been
corrected. Also recorded in the F4 section of the figure run summary, together
with two related points: the criteria do not fail monotonically, and the pair
criterion is the strict one across both scorings.

---

# Findings about prior work

Sourced from the prior-work PDFs, which are **not** in this repository. Nothing
here was checked against the papers by the tooling — re-verify each against the
sources when the sentence is written.

## Their augmentation pipeline is unreproducible, and it is a confound

Both prior papers describe augmentation **qualitatively** — rotations, flips,
cropping, scaling, brightness, contrast, saturation, hue, noise, blur — and
state **no parameter values**: no probabilities, no ranges, no magnitudes.

Their pipeline therefore cannot be reproduced, and it may differ substantially
from the Ultralytics defaults this study runs under. Those defaults are
recorded in full in `data/config_provenance.csv` (89 settings marked
`default`), so what this study did is specified; what prior work did is not.

**Why this matters for the comparison.** Copying their stated hyperparameters —
epochs, batch, optimizer, lr0, weight decay — closes the gap on the settings
they report and leaves the augmentation gap wide open. An accuracy difference
between this study and theirs cannot be attributed to architecture or split
while the augmentation pipelines are unmatched and one of them is unknown. The
config table (`tables/t3_training_config.tex`) shows six settings marked
`copied`; that column should not be read as "the configurations match".

State the limitation explicitly rather than letting the `copied` rows imply a
controlled comparison.

## The YOLOv13 paper compares across two different evaluation protocols

The YOLOv13 paper states that its **proposed model** was evaluated by
**3-fold cross-validation over the entire dataset**, with results averaged
across folds. The **comparison rows in the same table** match the YOLOv12
paper's **single-split** figures.

The two protocols differ in at least two ways that move the numbers:

- **Evaluated image set.** Cross-validation over the whole dataset evaluates
  every image across the folds; a single split evaluates only the held-out
  portion. Under the published split that portion is 205 test images of 2121.
- **Number of evaluable classes.** This repository establishes that the
  published split leaves 15 classes with no validation or test instances and
  16 with none in validation, so a single-split evaluation scores at most 46 of
  61 classes. Cross-validation over the entire dataset would encounter all 61.
  A mean over 61 classes and a mean over 46 are not the same quantity, and the
  missing 15 are not a random sample — they are the largest classes by
  annotation count (`tables/t1_unevaluable_classes.tex`).

**The table does not state this.** A reader comparing a cross-validated row
against single-split rows would take the difference as a result about the
models.

This is the strongest available argument for why a controlled benchmark was
needed, and it belongs wherever the paper motivates the study. It is also a
claim about someone else's work: state exactly what each paper says, cite the
section, and let the reader draw the conclusion.
