# ElectroCom61 Benchmark Study

A controlled benchmark study of the **ElectroCom61** object detection dataset
(61 electronic component classes, 2121 images, 12937 annotations).

Prior work reports contradictory results on this dataset. The purpose of this
repository is to produce a benchmark where every reported number is traceable
to a split, a seed, a set of weights and a machine — and where the dataset
itself has been audited before any model is trained on it.

**Current stage: dataset audit (Stage 1).** No detector has been trained yet.
Everything in `runs/` so far concerns the *integrity of the data*: whether the
train/valid/test split is clean, whether the shipped metadata describes the
shipped images, and whether near-duplicate photo bursts straddle the split
boundary. Those questions have to be answered first, because a leaked split
inflates test scores no matter which model is trained on it.

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

Python 3 and nothing else. **Standard library only** — no pandas, no numpy, no
PyTorch at this stage. This is deliberate: a reviewer needs only an interpreter
to reproduce any number in `runs/`.

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
