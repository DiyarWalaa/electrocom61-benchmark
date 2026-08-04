"""
build_corrected_dataset.py -- materialise the corrected split as real folders

Reads a split manifest (image_name, split) and COPIES each image and its
matching YOLO label out of data/ElectroCom-61_v2/ into a new tree:

    data/ElectroCom-61_corrected/
        train/images  train/labels
        valid/images  valid/labels
        test/images   test/labels
        data.yaml

SOURCE IS NEVER MODIFIED
    Every file operation is a copy. Nothing under data/ElectroCom-61_v2/ is
    moved, renamed, deleted or written to. The v2 tree remains exactly as
    downloaded from Mendeley, which is what makes every earlier run in runs/
    still reproducible after this script has been executed.

REFUSES TO OVERWRITE
    If the destination already exists the script exits without writing
    anything. A half-rebuilt dataset that silently merged two different
    manifests would be undetectable afterwards -- the folder would look
    complete and every count would still add up.

VERIFICATION READS THE BUILT TREE, NOT THE COPY LOOP
    It would be easy, and worthless, to verify by counting what the copy loop
    believed it did. Every check below re-enumerates the destination from disk
    and re-parses the copied label files. The copy loop's own bookkeeping is
    used for exactly one thing: comparing against what verification found, so
    a disagreement between intent and outcome is itself reported.

    Content is checked by SHA-256 against the source, not just by filename.
    A truncated or zero-length copy has the right name and the right count and
    would pass every structural check while corrupting a training run.

Run with no arguments:

    python scripts/build_corrected_dataset.py

Writes the dataset to data/ElectroCom-61_corrected/ and a verification report
to runs/<YYYYMMDD>_build_corrected_dataset/ (auto-suffixed, never overwriting).
"""

import hashlib
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


# The manifest this build is materialising. Named explicitly rather than
# globbed for "the latest run": a build that silently picked up a different
# manifest than the one cited in the paper would be undetectable.
MANIFEST = os.path.join(
    ec61.RUNS_DIR, "20260803_corrected_split_02", "split_manifest.csv")

DEST_DIR = os.path.join(ec61.DATA_DIR, "ElectroCom-61_corrected")

# Expected values, asserted rather than assumed. These come from the Stage 3
# run and from the dataset's published annotation count.
EXPECTED_SIZES = {"train": 1478, "valid": 438, "test": 205}
EXPECTED_TOTAL_INSTANCES = 12937
MIN_PER_SPLIT = 5

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path):
    """Read (image_name, split) rows. Returns {image_name: split}.

    Duplicate image names are fatal: two rows assigning one image to two
    splits would silently produce whichever the loop saw last, and the counts
    would still come out right.
    """
    import csv
    assignment = {}
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "image_name" not in reader.fieldnames \
                or "split" not in reader.fieldnames:
            raise ValueError("manifest must have image_name,split columns: %s" % path)
        for row in reader:
            name = row["image_name"].strip()
            split = row["split"].strip()
            if name in assignment:
                raise ValueError("duplicate image_name in manifest: %s" % name)
            if split not in ec61.SPLITS:
                raise ValueError("unknown split %r for %s" % (split, name))
            assignment[name] = split
    return assignment


def index_source(dataset_dir):
    """Map every source image to its (image_path, label_path).

    The manifest gives an image's DESTINATION split, which says nothing about
    where it currently lives, so the whole source tree is indexed first.
    """
    index = {}
    for split in ec61.SPLITS:
        img_dir = os.path.join(dataset_dir, split, "images")
        lbl_dir = os.path.join(dataset_dir, split, "labels")
        if not os.path.isdir(img_dir):
            raise IOError("missing source image directory: %s" % img_dir)
        for fname in sorted(os.listdir(img_dir)):
            if not fname.lower().endswith(IMAGE_EXTS):
                continue
            base = fname.rsplit(".", 1)[0]
            lbl = os.path.join(lbl_dir, base + ".txt")
            index[fname] = (
                os.path.join(img_dir, fname),
                lbl if os.path.isfile(lbl) else None,
                split,
            )
    return index


def read_class_names(data_yaml):
    """Parse `nc` and `names` from a Roboflow data.yaml (see other scripts)."""
    import ast
    import re
    with open(data_yaml, "r", encoding="utf-8") as fh:
        text = fh.read()
    m_nc = re.search(r"^nc:\s*(\d+)\s*$", text, re.MULTILINE)
    if m_nc is None:
        raise ValueError("could not find `nc:` in %s" % data_yaml)
    nc = int(m_nc.group(1))
    m_names = re.search(r"^names:\s*(\[.*?\])", text, re.MULTILINE | re.DOTALL)
    if m_names is None:
        raise ValueError("could not find `names:` in %s" % data_yaml)
    names = ast.literal_eval(m_names.group(1))
    if len(names) != nc:
        raise ValueError("data.yaml disagrees with itself: nc=%d, %d names" % (nc, len(names)))
    return names, nc


def main():
    # --- Refuse to overwrite ------------------------------------------------
    if os.path.exists(DEST_DIR):
        sys.stderr.write(
            "REFUSING TO BUILD: %s already exists.\n"
            "Delete or rename it yourself if you intend to rebuild. This script\n"
            "will not merge into or overwrite an existing dataset tree.\n" % DEST_DIR)
        return 1

    if not os.path.isfile(MANIFEST):
        sys.stderr.write("manifest not found: %s\n" % MANIFEST)
        return 1

    run_dir = ec61.make_run_dir("build_corrected_dataset")

    assignment = load_manifest(MANIFEST)
    source = index_source(ec61.DATASET_DIR)
    names, nc = read_class_names(os.path.join(ec61.DATASET_DIR, "data.yaml"))

    ec61.write_config(
        run_dir,
        os.path.abspath(__file__),
        params={
            "manifest": MANIFEST,
            "manifest_sha256": sha256_file(MANIFEST),
            "destination": DEST_DIR,
            "operation": "copy (source never modified)",
            "expected_sizes": EXPECTED_SIZES,
            "expected_total_instances": EXPECTED_TOTAL_INSTANCES,
            "min_per_split": MIN_PER_SPLIT,
        },
        extra={"source_dataset": ec61.DATASET_DIR, "declared_nc": nc},
    )

    # --- Reconcile manifest against source before copying anything ----------
    missing_from_source = sorted(set(assignment) - set(source))
    missing_from_manifest = sorted(set(source) - set(assignment))
    no_label = sorted(f for f in assignment
                      if f in source and source[f][1] is None)

    if missing_from_source or missing_from_manifest or no_label:
        # Stop before writing a single file. A partially built tree is worse
        # than none: it looks like a dataset.
        ec61.write_csv(
            os.path.join(run_dir, "preflight_failures.csv"),
            ["problem", "image_name"],
            ([["in manifest, not in source", f] for f in missing_from_source]
             + [["in source, not in manifest", f] for f in missing_from_manifest]
             + [["no matching label file in source", f] for f in no_label]),
        )
        sys.stderr.write(
            "PREFLIGHT FAILED -- nothing was written to %s\n"
            "  in manifest but not in source : %d\n"
            "  in source but not in manifest : %d\n"
            "  missing label file in source  : %d\n"
            "  see %s/preflight_failures.csv\n"
            % (DEST_DIR, len(missing_from_source), len(missing_from_manifest),
               len(no_label), run_dir))
        return 1

    # --- Copy ---------------------------------------------------------------
    for split in ec61.SPLITS:
        os.makedirs(os.path.join(DEST_DIR, split, "images"))
        os.makedirs(os.path.join(DEST_DIR, split, "labels"))

    intended = {s: 0 for s in ec61.SPLITS}
    copied_pairs = []   # (dest_split, image_name, src_img, src_lbl)
    for fname in sorted(assignment):
        split = assignment[fname]
        src_img, src_lbl, _orig_split = source[fname]
        base = fname.rsplit(".", 1)[0]
        dst_img = os.path.join(DEST_DIR, split, "images", fname)
        dst_lbl = os.path.join(DEST_DIR, split, "labels", base + ".txt")
        # copy2 preserves mtime, so a later `ls -l` on the built tree still
        # shows when the original was created rather than when it was copied.
        shutil.copy2(src_img, dst_img)
        shutil.copy2(src_lbl, dst_lbl)
        intended[split] += 1
        copied_pairs.append((split, fname, src_img, src_lbl))

    # --- data.yaml ----------------------------------------------------------
    # Paths mirror v2's relative form so the file is a drop-in replacement.
    # The Roboflow block from v2 is deliberately NOT reproduced: this tree is
    # not a Roboflow export and labelling it as one would misstate its
    # provenance. A comment header records where it actually came from.
    yaml_path = os.path.join(DEST_DIR, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# ElectroCom-61 -- CORRECTED SPLIT\n")
        fh.write("#\n")
        fh.write("# Derived from ElectroCom61 v2 (doi:10.17632/6scy6h8sjz.2) by\n")
        fh.write("# reassigning images between splits. No image or label was\n")
        fh.write("# altered; only which split each one belongs to.\n")
        fh.write("#\n")
        fh.write("# Manifest : %s\n" % os.path.basename(MANIFEST))
        fh.write("# Run      : %s\n" % os.path.basename(os.path.dirname(MANIFEST)))
        fh.write("# Built by : scripts/build_corrected_dataset.py\n")
        fh.write("#\n")
        fh.write("# Class names and their order are copied verbatim from v2's\n")
        fh.write("# data.yaml, so class ids in the label files stay valid.\n")
        fh.write("\n")
        fh.write("train: ../train/images\n")
        fh.write("val: ../valid/images\n")
        fh.write("test: ../test/images\n")
        fh.write("\n")
        fh.write("nc: %d\n" % nc)
        fh.write("names: %s\n" % (names,))

    # ----------------------------------------------------------------------
    # VERIFY -- everything below re-reads the destination from disk.
    # ----------------------------------------------------------------------
    built = {}          # split -> sorted image filenames actually present
    label_missing = []  # images in the built tree with no label beside them
    orphan_labels = []  # labels in the built tree with no image
    for split in ec61.SPLITS:
        img_dir = os.path.join(DEST_DIR, split, "images")
        lbl_dir = os.path.join(DEST_DIR, split, "labels")
        imgs = sorted(f for f in os.listdir(img_dir)
                      if f.lower().endswith(IMAGE_EXTS))
        built[split] = imgs
        lbls = set(f for f in os.listdir(lbl_dir) if f.endswith(".txt"))
        for f in imgs:
            base = f.rsplit(".", 1)[0]
            if base + ".txt" not in lbls:
                label_missing.append((split, f))
        img_bases = {f.rsplit(".", 1)[0] for f in imgs}
        for l in sorted(lbls):
            if l[:-4] not in img_bases:
                orphan_labels.append((split, l))

    built_sizes = {s: len(built[s]) for s in ec61.SPLITS}

    # Content integrity: every copied file must be byte-identical to its source.
    content_mismatches = []
    for split, fname, src_img, src_lbl in copied_pairs:
        base = fname.rsplit(".", 1)[0]
        dst_img = os.path.join(DEST_DIR, split, "images", fname)
        dst_lbl = os.path.join(DEST_DIR, split, "labels", base + ".txt")
        if sha256_file(src_img) != sha256_file(dst_img):
            content_mismatches.append((split, fname, "image"))
        if sha256_file(src_lbl) != sha256_file(dst_lbl):
            content_mismatches.append((split, fname, "label"))

    # Per-class instance counts, parsed from the COPIED label files.
    counts = {c: {s: 0 for s in ec61.SPLITS} for c in range(nc)}
    total_instances = 0
    bad_class_ids = {}
    for split in ec61.SPLITS:
        lbl_dir = os.path.join(DEST_DIR, split, "labels")
        for fname in built[split]:
            base = fname.rsplit(".", 1)[0]
            for (cid, _cx, _cy, _w, _h) in ec61.load_boxes(
                    os.path.join(lbl_dir, base + ".txt")):
                total_instances += 1
                if 0 <= cid < nc:
                    counts[cid][split] += 1
                else:
                    bad_class_ids[cid] = bad_class_ids.get(cid, 0) + 1

    below_min = [(c, s, counts[c][s]) for c in range(nc)
                 for s in ("valid", "test") if counts[c][s] < MIN_PER_SPLIT]

    ec61.write_csv(
        os.path.join(run_dir, "class_counts_built.csv"),
        ["class_id", "class_name", "inst_train", "inst_valid", "inst_test",
         "inst_total", "meets_min"],
        [[c, names[c], counts[c]["train"], counts[c]["valid"], counts[c]["test"],
          sum(counts[c].values()),
          "yes" if (counts[c]["valid"] >= MIN_PER_SPLIT
                    and counts[c]["test"] >= MIN_PER_SPLIT) else "NO"]
         for c in range(nc)],
    )

    anomalies = ([["label missing for image", s, f] for (s, f) in label_missing]
                 + [["orphan label file", s, f] for (s, f) in orphan_labels]
                 + [["content mismatch (%s)" % w, s, f]
                    for (s, f, w) in content_mismatches])
    ec61.write_csv(
        os.path.join(run_dir, "anomalies.csv"),
        ["problem", "split", "name"], anomalies)

    # --- checks -------------------------------------------------------------
    checks = [
        ["image counts per split",
         "%d / %d / %d" % (built_sizes["train"], built_sizes["valid"], built_sizes["test"]),
         "1478 / 438 / 205",
         built_sizes == EXPECTED_SIZES],
        ["copy loop intent matches disk",
         "%d / %d / %d" % (intended["train"], intended["valid"], intended["test"]),
         "same as disk", intended == built_sizes],
        ["every image has a label", "%d missing" % len(label_missing), "0",
         not label_missing],
        ["no orphan labels", "%d orphans" % len(orphan_labels), "0",
         not orphan_labels],
        ["copies byte-identical to source", "%d mismatches" % len(content_mismatches),
         "0", not content_mismatches],
        ["total instances", total_instances, EXPECTED_TOTAL_INSTANCES,
         total_instances == EXPECTED_TOTAL_INSTANCES],
        ["all 61 classes >= %d in valid AND test" % MIN_PER_SPLIT,
         "%d of %d" % (nc - len({c for (c, _s, _n) in below_min}), nc), nc,
         not below_min],
        ["class ids within 0..%d" % (nc - 1),
         "%d out of range" % len(bad_class_ids), "0", not bad_class_ids],
    ]
    all_pass = all(c[3] for c in checks)

    # --- summary.md ---------------------------------------------------------
    lines = []
    lines.append("# Corrected-split dataset build")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("- manifest: `%s`" % MANIFEST.replace("\\", "/"))
    lines.append("- destination: `%s`" % DEST_DIR.replace("\\", "/"))
    lines.append("- source (unmodified): `%s`" % ec61.DATASET_DIR.replace("\\", "/"))
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["check", "measured", "expected", "result"],
        [[c[0], c[1], c[2], "PASS" if c[3] else "**FAIL**"] for c in checks]))
    lines.append("")
    lines.append("**%s**" % ("All checks passed." if all_pass
                             else "AT LEAST ONE CHECK FAILED -- do not upload this tree."))
    lines.append("")
    if below_min:
        lines.append("### Classes below the minimum")
        lines.append("")
        lines.append(_fmt_markdown_table(
            ["class_id", "class_name", "split", "instances"],
            [[c, names[c], s, n] for (c, s, n) in below_min]))
        lines.append("")
    lines.append("## Per-class instance counts (from the copied labels)")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["class_id", "class_name", "train", "valid", "test", "total"],
        [[c, names[c], counts[c]["train"], counts[c]["valid"], counts[c]["test"],
          sum(counts[c].values())] for c in range(nc)]))
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- These checks prove the tree MATCHES THE MANIFEST. They say "
                 "nothing about whether the manifest is a good split. The "
                 "leakage cost of this split is in "
                 "`runs/20260803_corrected_split_02/summary.md` and travels with it.")
    lines.append("- Class ids are inherited from v2. If a v2 label is wrong, it "
                 "is copied here unchanged and wrong in the same way.")
    lines.append("- >= %d instances makes a class measurable, not well measured. "
                 "Classes sitting near the floor still cannot support a "
                 "confident per-class AP." % MIN_PER_SPLIT)
    lines.append("- The build copies; it does not deduplicate. Near-duplicate "
                 "images identified in earlier runs are all still present.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("built %s" % DEST_DIR)
    print("  report: %s" % run_dir)
    for c in checks:
        print("  [%s] %-45s measured=%s expected=%s"
              % ("PASS" if c[3] else "FAIL", c[0], c[1], c[2]))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
