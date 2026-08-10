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
