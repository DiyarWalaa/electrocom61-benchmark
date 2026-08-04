# ElectroCom61 Benchmark Study

A controlled benchmark study of the **ElectroCom61** object detection dataset
(61 electronic component classes, 2121 images, 12937 annotations).

Prior work reports contradictory results on this dataset. The purpose of this
repository is to produce a benchmark where every reported number is traceable
to a split, a seed, a set of weights and a machine — and where the dataset
itself has been audited before any model is trained on it.

**Current stage: dataset audit complete; a corrected split released.** No
detector has been trained yet. Everything in `runs/` so far concerns the
*integrity of the data*: whether the train/valid/test split is clean, whether
the shipped metadata describes the shipped images, and whether near-duplicate
photo bursts straddle the split boundary. Those questions have to be answered
first, because a leaked split inflates test scores no matter which model is
trained on it.

---

## The released split

The split published by this repository is **burst-aware, τ = 15 s, seed
20260804**.

| Property | Value |
|---|---|
| Manifest | `runs/20260804_burst_aware_split_04/split_manifest.csv` |
| Built dataset | `data/ElectroCom-61_corrected/` (rebuild with `build_corrected_dataset.py`) |
| Build verification | `runs/20260804_build_corrected_dataset_02/` — 8/8 checks pass |
| Images moved vs published | **68** |
| Split sizes | **1478 / 438 / 205** — unchanged from the published split |
| Class coverage | all **61** classes hold ≥5 instances in **both** valid and test |
| test↔train near-duplicate pairs | **0** at every epsilon, under both scorings |
| Total annotations | 12937 — every image and label copied unmodified from v2 |

**Why it exists.** In the published v2 split, 15 of the 61 classes have zero
instances in *both* valid and test, so they cannot be evaluated at all — they
were photographed only in sessions that landed entirely in train
(`runs/20260802_class_date_provenance/`). Fixing that requires moving images
out of those sessions.

**Why bursts, not images.** An earlier allocator minimised images moved and was
blind to duplicates. It split `IMG_20240220_115315` from `IMG_20240220_115316`
— shot one second apart, same five components — putting one in test and one in
train, and creating 2 raw / 4 aligned test↔train near-duplicate pairs where the
published split had none. The released allocator moves whole bursts, so a burst
cannot straddle the boundary. See `figures/near_duplicate_pair.png`.

**Why τ = 15 s.** `runs/20260804_burst_aware_tau_sweep/` swept 15/20/25/30/35/45/60.
Class feasibility holds at every value, so it does not decide. What decides is
how many images the test split can give back: 59 available at τ=15 against 10
at τ=30. Only 15/20/25 hold the frozen sizes, and τ=15 moves the fewest images.

### One thing not to overstate

**Zero contamination refers to test↔train.** The `valid↔train` count is
**1 pair (raw) / 3 pairs (aligned)** at ε=0.05 — and it is *identical in the
published split and in the released one*. Those pairs are pre-existing in the
data as distributed; neither allocator created them and neither removed them.
`valid↔test` is zero in both. Quote the three relationships separately:
test contamination biases the headline metric, valid contamination biases model
selection, and they are not interchangeable. Full breakdown in
`runs/20260804_duplicate_contamination/`.

The split makes all 61 classes *measurable*, not *well measured*. Five
instances is a floor for existence, not a sample size to quote a confident
per-class AP from.

---

## Data

The dataset is **not** stored in this repository. It is publicly archived, it is
large, and it is an input to this study rather than a product of it. Download
it yourself and place it as shown below.

### Versions and DOIs

| Version | Mendeley DOI | Direct URL |
|---|---|---|
| v1 | `10.17632/6scy6h8sjz.1` | https://data.mendeley.com/datasets/6scy6h8sjz/1 |
| v2 | `10.17632/6scy6h8sjz.2` | https://data.mendeley.com/datasets/6scy6h8sjz/2 |

The v2 DOI is the one given in the published paper's Specifications Table
("Data identification number"). **v2 is the version this study analyses**; v1 is
downloaded only for `v1_provenance.py`, which tests whether the metadata CSV
shipped inside v2 was ever regenerated for v2 or is v1's metadata unchanged.

### Byte provenance of v2

The v2 Mendeley archive does not contain raw camera files. The authors uploaded
a **Roboflow export**, and its manifest travels inside the archive as
`README.roboflow.txt` / `README.dataset.txt`:

| Field | Value |
|---|---|
| Roboflow workspace | `datasetsynthesis` |
| Roboflow project | `electrocom-61` |
| Version | 9 |
| Export date | 2024-11-21 |
| License | CC BY 4.0 |
| Annotation format | YOLO |

This matters for interpreting any result here. Roboflow applied
auto-orientation (EXIF stripped), a **stretch resize to 640x640**, and
auto-contrast to every image before export. Every filename was also rewritten as
`<stem>_JPG.rf.<32 hex>.jpg`. Geometric analyses in this repo therefore work in
normalised 0–1 coordinates, because pixel distances are not comparable across
images that were stretched by different factors.

Cite the Mendeley DOI. Quote the Roboflow row when you need to say *which bytes*
a number came from.

### Where to put it

Unpack the downloads so the tree looks exactly like this. The paths are hard
coded in `scripts/ec61.py` (`DATASET_DIR`, `METADATA_CSV`) and
`scripts/v1_provenance.py` (`V1_DIR`):

```
electrocom61/
├── data/                                  <- git-ignored, you create this
│   ├── Metadata_ElectroCom61.csv          <- ships inside the v2 archive
│   ├── ElectroCom-61_v2/                  <- v2, doi:10.17632/6scy6h8sjz.2
│   │   ├── data.yaml
│   │   ├── README.roboflow.txt
│   │   ├── train/   (images/ + labels/)
│   │   ├── valid/   (images/ + labels/)
│   │   └── test/    (images/ + labels/)
│   └── v1/                                <- v1, doi:10.17632/6scy6h8sjz.1
│       └── ElectroCom61 A Multiclass Dataset for Detection of Electronic Components/
│           ├── ElectroCom61/
│           └── Metadata_ElectroCom61.csv
├── scripts/
├── runs/
├── reference/                             <- third-party material, see below
└── notes/
```

Two things worth knowing before you unpack:

- `Metadata_ElectroCom61.csv` sits at `data/`, one level **above**
  `ElectroCom-61_v2/`. Both dataset archives contain a copy; the one the scripts
  read is the v2 copy, moved up to `data/`.
- `data/v1/` keeps the long directory name exactly as Mendeley ships it.
  `v1_provenance.py` also accepts a path argument if you unpacked it elsewhere.

Only `v1_provenance.py` needs `data/v1/`. Every other script runs with v2 alone.

---

## Requirements

**Every analysis script is standard library only** — no pandas, no numpy, no
PyTorch. This is deliberate: reproducing any number in `runs/` requires nothing
but a Python 3 interpreter.

The one exception is figure rendering. `scripts/figure_near_duplicate.py`
imports `matplotlib` and `pillow` (which pulls `numpy`):

```bash
pip install matplotlib pillow    # needed ONLY for figure scripts
```

Nothing that produces a number depends on those packages. If they are missing,
every analysis script still runs and every result in `runs/` is still
reproducible; only the figures under `figures/` cannot be rebuilt.

Developed and run on Python 3.12.10 (Windows 11); every `config.json` records
the interpreter and platform that produced that run. Older Python 3 versions
are untested here.

---

## How to run the scripts

Run from the repository root. No script takes required arguments, and no script
depends on another script's output — each reads `data/` directly and writes its
own timestamped folder under `runs/`. Run them in any order.

```bash
python scripts/device_split_table.py     # images per capture device per split
python scripts/csv_coverage.py           # 2121 images on disk vs 2071 CSV rows
python scripts/disagreement_189.py       # the (csv=train, actual=valid) cell
python scripts/burst_clusters.py         # photo bursts across the split boundary
python scripts/scene_signature.py        # duplicate detection from label files
python scripts/counter_duplicates.py     # redundancy inside the `counter` family
python scripts/class_date_provenance.py  # why 15 classes are never evaluated
python scripts/corrected_split.py        # build a split where all 61 are evaluable
python scripts/duplicate_contamination_addendum.py   # published vs corrected, 3-way
python scripts/build_corrected_dataset.py            # materialise the split as folders
python scripts/figure_near_duplicate.py              # figure (needs matplotlib)
python scripts/burst_feasibility.py                  # can classes move as whole bursts?
python scripts/burst_aware_split.py                  # burst-atomic split (tau=15)
python scripts/burst_aware_tau_sweep.py              # which tau satisfies both constraints?
python scripts/v1_provenance.py          # requires data/v1/ (see below)
```

### What each one does

| Script | Question it answers | Writes |
|---|---|---|
| `ec61.py` | *(not run directly)* Shared filename parsing, CSV normalisation and the image↔CSV join. Every script imports it so that all numbers reconcile. | — |
| `device_split_table.py` | How many images per capture device per split? Device is derived two independent ways — filename family, and `DEVICE_NAME` in the CSV — and the two are cross-checked. | `runs/<date>_device_split/` |
| `csv_coverage.py` | Which images have no metadata row, is there a pattern, and does the CSV's `DATA_TYPE` agree with the directory each image actually sits in? | `runs/<date>_csv_coverage/` |
| `disagreement_189.py` | Are the 189 rows where CSV says *train* but the file is in *valid/* the same 189 untimestamped `counter` images, or a coincidence? Tested by set intersection, not by comparing counts. | `runs/<date>_disagreement_189/` |
| `burst_clusters.py` | Clusters images into photo bursts from filename timestamps (per device, single-linkage, gap threshold τ swept over 3/5/10/30/60 s) and counts test images sharing a burst with a train image. | `runs/<date>_burst_clusters/` |
| `scene_signature.py` | Duplicate detection needing no pixels and no model: bucket by exact class multiset, then score geometric agreement of box centres. Reaches the untimestamped images that `burst_clusters.py` structurally cannot see. | `runs/<date>_scene_signature/` |
| `counter_duplicates.py` | How much of the `counter` family is redundant *within itself*? Counts connected components of the near-duplicate graph, because pairs are the wrong unit — three shots of one scene are three pairs but only two redundant images. | `runs/<date>_counter_duplicates/` |
| `class_date_provenance.py` | Why are 15 of 61 classes never evaluated? Recomputes per-class instances per split from the label files, then tests whether those classes are *session-confined* (only photographed on dates that landed entirely in train) or merely *rare* — a per-class verdict, not an aggregate assertion. Also reports test-instance counts for every class. | `runs/<date>_class_date_provenance/` |
| `corrected_split.py` | **Superseded** by `burst_aware_split.py`. Builds a split where all 61 classes hold ≥5 instances in both valid and test, with image counts frozen at 1478/438/205 so training-set size cannot explain any later accuracy difference. Emits a manifest only — **no image file is moved or copied**. Prices the cost in broken bursts, smallest cross-split time gap, and (for the untimestamped images, where time gaps do not exist) label-geometry duplicates. | `runs/<date>_corrected_split/` |
| `duplicate_contamination_addendum.py` | Near-duplicate contamination, published vs corrected split, broken out three ways (test↔train, valid↔train, valid↔test). Scores every candidate pair **once** and classifies it under both assignments, so the two states share buckets, pairs and scorer by construction. Reconciles with `20260802_scene_signature`. | `runs/<date>_duplicate_contamination/` |
| `build_corrected_dataset.py` | Materialises the released manifest into real folders under `data/ElectroCom-61_corrected/` by **copying** from v2 (source never modified). Refuses to overwrite an existing tree, preflights before writing, and verifies by re-reading the built tree from disk — including SHA-256 of every copy against its source. | `runs/<date>_build_corrected_dataset/` |
| `figure_near_duplicate.py` | Renders `figures/near_duplicate_pair.png`: the near-duplicate pair the released split keeps together, two panels, boxes labelled, per-box centre shift in pixels. Splits are read from the built tree, so the figure tracks whatever split is released. **Requires matplotlib + pillow.** | `runs/<date>_figure_near_duplicate/` |
| `burst_feasibility.py` | Answers whether the never-evaluated classes can be rescued by moving whole bursts: how many distinct groups inside the train-only sessions carry each class, and how many carry ≥5 instances. Two regimes, because the untimestamped images have no bursts — scene components stand in. τ and ε swept. | `runs/<date>_burst_feasibility/` |
| `burst_aware_split.py` | **Produces the released split** (τ=15 s, seed 20260804). A split whose atomic unit of movement is a whole burst (or scene component), so no group can straddle the boundary. Reports images moved, three-way near-duplicate contamination, classes unrescued, and whether 1478/438/205 survives. | `runs/<date>_burst_aware_split/` |
| `burst_aware_tau_sweep.py` | Runs the burst-aware allocator at τ = 15/20/25/30/35/45/60 and reports, per τ: whether all 15 rescued classes keep ≥2 qualifying groups, how many test↔train near-duplicate pairs survive, and whether 1478/438/205 holds. Imports the allocator rather than copying it. | `runs/<date>_burst_aware_tau_sweep/` |
| `v1_provenance.py` | Was the metadata CSV shipped in v2 ever regenerated for v2, or is it v1's metadata unchanged? Four tests of increasing strength against an actual v1 download. | `runs/<date>_v1_provenance/` |

`v1_provenance.py` is the only script with an optional argument:

```bash
python scripts/v1_provenance.py                    # expects data/v1/
python scripts/v1_provenance.py D:/downloads/v1    # or point it anywhere
```

If `data/v1/` is missing it exits cleanly without creating a run folder — an
empty run directory would later be indistinguishable from a real result that
happened to find nothing.

---

## Reading `runs/`

Every script call creates `runs/<YYYYMMDD>_<name>/`. If that folder already
exists a numeric suffix is appended (`_02`, `_03`, …). **Runs are never
overwritten** — that is why `20260802_burst_clusters` and
`20260802_burst_clusters_02` both exist.

Each run folder contains:

- `summary.md` — the findings in prose, with the tables inline. **Start here.**
- `config.json` — provenance for that exact run: input file hashes, dataset
  counts, parameter values, Python version, platform. This is what makes a
  number in `summary.md` checkable rather than merely quoted.
- `*.csv` — the full underlying tables, never a sample, so any headline figure
  can be recomputed by hand.

Numbers are quoted from `summary.md` **with the run folder named**. A figure
without a run folder attached has no provenance and should not be trusted.

---

## Reference material

`reference/electrocom61-yolov9.ipynb` is the ElectroCom61 **first author's own
public Kaggle notebook**, archived here **unmodified**. It is not part of this
study's analysis and nothing in `scripts/` reads it.

**Why it is archived.** It is the source of the paper's headline **95.9%**
figure, and a Kaggle notebook can be edited or deleted by its owner at any time.
If it disappears, the claim loses the only public artifact showing how it was
produced. A frozen copy keeps that checkable.

**What it actually contains.** Read it before quoting anything from it:

- **The 95.9% is a hand-typed dict, not a measurement.** Cell 33 assigns 61
  per-class values as a Python literal; their arithmetic mean is 0.9593. The
  notebook stores **no cell outputs at all**, so there is nothing in it showing
  which run produced those values, or which metric they are — the dict is
  unlabelled as to mAP@50, mAP@50-95, precision or recall.
- **It trains on a different dataset version than this study analyses.** Cell 29
  downloads Roboflow `datasetsynthesis/electrocom-61` **version 5**. The archive
  published at `doi:10.17632/6scy6h8sjz.2` is Roboflow **version 9** (see *Byte
  provenance* above). Numbers from this notebook are not automatically
  comparable to anything computed over `data/ElectroCom-61_v2/`.
- **No test split is ever evaluated.** Cell 41 runs `val.py` without `--task
  test`, and YOLOv9's `val.py` defaults to the `val` split. The `test/`
  directory is never passed to an evaluation command anywhere in the notebook.
- **Two different models are trained and neither is tied to a result.** Cell 31
  trains `gelan-c`, cell 49 trains `yolov9-e` — both 25 epochs, batch 8, 640px,
  `hyp.scratch-high.yaml`. Which of the two the per-class dict came from is not
  stated.
- **The author flags annotation problems in their own data.** Cell 45 notes
  keypad/servo-motor relabelling, buzzer↔inductor confusion, and double
  labelling.
- **Environment is inconsistent with the saved state.** Paths are Colab
  (`/content/…`) and cells request `--device 0`, while the Kaggle metadata
  records `accelerator: none`, `isGpuEnabled: false`. As saved, it would not run
  end to end.

None of the above is a claim about whether 95.9% is *correct*. It is a statement
about what the notebook does and does not evidence, which is the part that
matters when deciding how much weight the figure can carry.

> **Provenance gap:** the source URL and retrieval date of this copy are not yet
> recorded here. Both should be, or the archive cannot be tied back to what was
> public and when.

## Project rules

`CLAUDE.md` holds the working rules for this study and is committed
deliberately. In short: every result states its split, seed, hardware and exact
weights; no number is reported without saving the config that produced it; runs
are never overwritten; detection results always report mAP@50 **and** mAP@50-95;
latency is measured after warm-up with `torch.cuda.synchronize()` and reported
as p50 and p95 with the batch size stated.

## License

The analysis code in `scripts/` is released under the **MIT License** — see
[`LICENSE`](LICENSE). Copyright © 2026 Diyar Walaa.

That grant covers the code written for this study. It does **not** extend to
the data:

- **The ElectroCom61 dataset** is © its authors, distributed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It is not
  redistributed here — `data/` is git-ignored and you download it yourself from
  the Mendeley DOIs above. Cite the DOI if you use it.
- **`runs/`** holds measurements derived from that dataset (filenames, counts,
  cluster memberships). Reuse them freely, but the CC BY attribution to the
  dataset authors travels with anything derived from their data — so credit
  both this repository and the ElectroCom61 DOI.
- **`reference/`** is **third-party material, not covered by the MIT grant
  above.** `electrocom61-yolov9.ipynb` is the ElectroCom61 first author's work,
  archived unmodified for the reasons given in *Reference material*. Its
  copyright rests with its author under whatever licence the original Kaggle
  notebook carries; that licence has not been recorded here yet.
