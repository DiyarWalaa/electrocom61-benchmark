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
