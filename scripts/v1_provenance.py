"""
v1_provenance.py -- does the CSV shipped with v2 actually describe v1?

HYPOTHESIS UNDER TEST
    Metadata_ElectroCom61.csv distributed inside ElectroCom-61_v2 was never
    regenerated for v2. It is v1's metadata, shipped unchanged.

Circumstantial evidence already in hand (runs/20260801_csv_coverage,
runs/20260802_disagreement_189):
    - 2121 images on disk, 2071 CSV rows, and 2121 - 50 = 2071 exactly
    - all 50 unmatched images are one contiguous session dated 20241118,
      five days before the paper's stated revision date of 23 Nov 2024
    - 600 joined rows have a DATA_TYPE that disagrees with the directory the
      file is in, and the largest such cell is scattered across dozens of
      non-contiguous runs -- the signature of a per-image re-split rather than
      a moved folder

None of that is proof. This script tests the hypothesis against an actual v1
download (Mendeley doi:10.17632/6scy6h8sjz.1, placed in data/v1/).

FOUR TESTS, in increasing order of strength:

  T1  COUNT      |v1 images| == |CSV rows|
                 Weak on its own. Two collections can both hold 2071 files
                 without being the same 2071 files, so a pass here is
                 necessary but nowhere near sufficient.

  T2  IDENTITY   {v1 stems} == {CSV keys}, element for element
                 THIS IS THE REAL TEST. Two sets of 2071 names agreeing
                 member-by-member is not something that happens by chance.
                 If T2 passes, the hypothesis is established and T1 is a
                 footnote. If T2 fails, T1 passing means nothing.

  T3  DATE       no v1 image is dated 20241118
                 Predicts that the un-metadata'd session postdates v1. The
                 full date histogram of v1 and v2 is emitted side by side, so
                 a partial result (a handful of 20241118 images rather than
                 zero) is visible as a shape rather than collapsing to FAIL.

  T4  STRUCTURE  csv_DATA_TYPE matches the folder each image sits in under v1
                 The 600 disagreements against v2 should become 0 against v1.
                 Requires v1 to be organised into split folders at all -- if
                 it is not, this test is UNANSWERABLE and is reported as such
                 rather than being quietly scored as a pass.

TWO PARSING HAZARDS THIS SCRIPT IS EXPLICIT ABOUT

  1. v2 is a Roboflow export (`<stem>_JPG.rf.<32hex>.jpg`); a Mendeley
     download almost certainly is not. `ec61.parse_stem` returns None for
     non-Roboflow names, which would make every v1 filename look like a parse
     failure. `ec61.parse_stem_tolerant` is used instead and the route taken
     ('roboflow' / 'raw') is counted and reported for both datasets. Comparing
     stems read by two different routes is legitimate -- that is the whole
     point -- but it must be visible, not assumed.

  2. If v1 ships the same image twice (say a flat copy alongside a split copy)
     its stem set would be smaller than its file count and T1 and T2 would
     disagree for a reason that has nothing to do with the hypothesis.
     Duplicate stems are detected and reported before any test is scored.

Run with no arguments once data/v1/ exists:

    python scripts/v1_provenance.py
    python scripts/v1_provenance.py <path-to-v1>   # optional override

Writes runs/<YYYYMMDD>_v1_provenance/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


V1_DIR = os.path.join(ec61.DATA_DIR, "v1")

IMAGE_EXTS = (".jpg", ".jpeg", ".png")

# The session that the hypothesis predicts is absent from v1.
PREDICTED_ABSENT_DATE = "20241118"

# Directory names that count as a split folder, matched case-insensitively
# against every component of each image's relative path. Mendeley archives are
# not required to use the same casing as the Roboflow export.
SPLIT_ALIASES = {
    "train": "train", "training": "train",
    "valid": "valid", "validation": "valid", "val": "valid",
    "test": "test", "testing": "test",
}


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


class V1Image(object):
    """One image found under the v1 tree."""

    __slots__ = ("relpath", "filename", "stem", "route", "family",
                 "date_str", "time_str", "split_dir")

    def __init__(self, relpath, filename, stem, route, family,
                 date_str, time_str, split_dir):
        self.relpath = relpath
        self.filename = filename
        self.stem = stem
        self.route = route
        self.family = family
        self.date_str = date_str
        self.time_str = time_str
        self.split_dir = split_dir


def _split_from_relpath(relpath):
    """Find a split folder name among the path components, or None.

    Scans every component rather than just the first, because the archive may
    nest the splits under a project directory (v1/ElectroCom61/train/images/).
    The LAST match wins: a path like `train/images` has one match, but a
    hypothetical `dataset/test/train/` should be read as the innermost folder.
    """
    found = None
    parts = relpath.replace("\\", "/").split("/")[:-1]  # drop the filename
    for part in parts:
        alias = SPLIT_ALIASES.get(part.strip().lower())
        if alias is not None:
            found = alias
    return found


def load_v1(v1_dir):
    """Walk the v1 tree and parse every image filename found anywhere in it."""
    images = []
    for dirpath, dirnames, filenames in os.walk(v1_dir):
        dirnames.sort()   # deterministic traversal order
        for filename in sorted(filenames):
            if not filename.lower().endswith(IMAGE_EXTS):
                continue
            full = os.path.join(dirpath, filename)
            relpath = os.path.relpath(full, v1_dir)
            stem, route = ec61.parse_stem_tolerant(filename)
            family, m = ec61.classify_stem(stem)
            date_str = time_str = None
            if family in ec61.TIMESTAMPED_FAMILIES:
                date_str = m.group("date")
                time_str = m.group("time")
            images.append(V1Image(relpath, filename, stem, route, family,
                                  date_str, time_str,
                                  _split_from_relpath(relpath)))
    return images


def main():
    v1_dir = sys.argv[1] if len(sys.argv) > 1 else V1_DIR

    # Refuse to produce a run at all if the input is not there. An empty or
    # half-populated run directory in runs/ would later be indistinguishable
    # from a real result that happened to find nothing.
    if not os.path.isdir(v1_dir):
        sys.stderr.write(
            "v1 dataset not found at: %s\n\n"
            "Download doi:10.17632/6scy6h8sjz.1 from Mendeley and unpack it\n"
            "there, then re-run. Any directory layout is fine -- the script\n"
            "walks the tree recursively and reports the layout it finds.\n"
            "No run directory has been created.\n" % v1_dir)
        return 2

    v1 = load_v1(v1_dir)
    if not v1:
        sys.stderr.write(
            "no image files found under: %s\n"
            "Expected files ending in %s. No run directory has been created.\n"
            % (v1_dir, ", ".join(IMAGE_EXTS)))
        return 2

    run_dir = ec61.make_run_dir("v1_provenance")

    v2 = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    ec61.attach_metadata(v2, rows_by_key)

    # ---- integrity of the v1 side before any test is scored ---------------
    v1_stems = {}
    v1_dup_stems = []
    for img in v1:
        if img.stem in v1_stems:
            v1_dup_stems.append(img.stem)
        v1_stems.setdefault(img.stem, []).append(img)

    v1_routes = {}
    for img in v1:
        v1_routes[img.route] = v1_routes.get(img.route, 0) + 1
    v2_routes = {}
    for r in v2:
        _, route = ec61.parse_stem_tolerant(r.filename)
        v2_routes[route] = v2_routes.get(route, 0) + 1

    v1_layout = sorted({img.split_dir or "<no split folder>" for img in v1})
    has_split_folders = any(img.split_dir is not None for img in v1)

    csv_keys = set(rows_by_key)
    v1_stem_set = set(v1_stems)
    v2_stem_set = {r.stem for r in v2}

    # ---- T1  count --------------------------------------------------------
    t1_pass = len(v1) == n_csv_rows

    # ---- T2  set identity -------------------------------------------------
    csv_only = sorted(csv_keys - v1_stem_set)
    v1_only = sorted(v1_stem_set - csv_keys)
    t2_pass = (not csv_only) and (not v1_only)

    # ---- T3  the 20241118 session ----------------------------------------
    v1_on_date = [img for img in v1 if img.date_str == PREDICTED_ABSENT_DATE]
    t3_pass = not v1_on_date

    # v2 images with no CSV row -- the 50 the hypothesis says are v2-only.
    v2_missing_csv = [r for r in v2 if r.csv_row is None]
    v2_only_stems = sorted(v2_stem_set - v1_stem_set)
    # Does the v2-minus-v1 difference land exactly on the un-metadata'd 50?
    t3b_pass = set(v2_only_stems) == {r.stem for r in v2_missing_csv}

    # ---- T4  DATA_TYPE vs v1 folder --------------------------------------
    t4_confusion = {}
    t4_disagreements = []
    t4_checked = 0
    if has_split_folders:
        for key, row in sorted(rows_by_key.items()):
            entries = v1_stems.get(key)
            if not entries:
                continue  # counted by T2; not this test's business
            claimed = (row.get("DATA_TYPE") or "").strip().lower() or "<blank>"
            actual = entries[0].split_dir or "<no split folder>"
            t4_confusion[(claimed, actual)] = t4_confusion.get((claimed, actual), 0) + 1
            t4_checked += 1
            if claimed != actual:
                t4_disagreements.append((key, claimed, actual))
        t4_status = "PASS" if not t4_disagreements else "FAIL"
    else:
        t4_status = "UNANSWERABLE"

    ec61.write_config(
        run_dir,
        __file__,
        params={
            "v1_dir": os.path.abspath(v1_dir),
            "predicted_absent_date": PREDICTED_ABSENT_DATE,
            "split_aliases": sorted(set(SPLIT_ALIASES.values())),
        },
        extra={
            "n_v1_image_files": len(v1),
            "n_v1_unique_stems": len(v1_stem_set),
            "n_v1_duplicate_stems": len(v1_dup_stems),
            "v1_stem_parse_routes": v1_routes,
            "v2_stem_parse_routes": v2_routes,
            "v1_split_folders_found": v1_layout,
            "n_v2_image_files": len(v2),
            "n_csv_data_rows": n_csv_rows,
            "n_csv_duplicate_keys": len(dup_keys),
            "T1_count_pass": t1_pass,
            "T2_set_identity_pass": t2_pass,
            "T2_n_csv_rows_without_v1_image": len(csv_only),
            "T2_n_v1_images_without_csv_row": len(v1_only),
            "T3_date_pass": t3_pass,
            "T3_n_v1_images_on_predicted_absent_date": len(v1_on_date),
            "T3b_v2_minus_v1_equals_the_unjoined_set": t3b_pass,
            "T4_status": t4_status,
            "T4_n_rows_checked": t4_checked,
            "T4_n_disagreements": len(t4_disagreements),
        },
    )

    # ---- tables -----------------------------------------------------------
    ec61.write_csv(
        os.path.join(run_dir, "v1_inventory.csv"),
        ["relpath", "split_dir", "stem", "parse_route", "family", "date", "time"],
        [[img.relpath, img.split_dir or "", img.stem, img.route, img.family,
          img.date_str or "", img.time_str or ""]
         for img in sorted(v1, key=lambda x: x.relpath)],
    )

    ec61.write_csv(
        os.path.join(run_dir, "t2_csv_rows_without_v1_image.csv"),
        ["csv_key", "IMAGE_NAME", "DATA_TYPE", "DEVICE_NAME"],
        [[k, rows_by_key[k].get("IMAGE_NAME", ""),
          rows_by_key[k].get("DATA_TYPE", ""),
          rows_by_key[k].get("DEVICE_NAME", "")] for k in csv_only],
    )
    ec61.write_csv(
        os.path.join(run_dir, "t2_v1_images_without_csv_row.csv"),
        ["stem", "relpath", "split_dir", "date", "time"],
        [[s, v1_stems[s][0].relpath, v1_stems[s][0].split_dir or "",
          v1_stems[s][0].date_str or "", v1_stems[s][0].time_str or ""]
         for s in v1_only],
    )

    # Date histogram, v1 against v2, so T3 is readable as a distribution.
    v1_by_date = {}
    for img in v1:
        d = img.date_str or "<no timestamp>"
        v1_by_date[d] = v1_by_date.get(d, 0) + 1
    v2_by_date = {}
    for r in v2:
        d = r.date_str or "<no timestamp>"
        v2_by_date[d] = v2_by_date.get(d, 0) + 1
    all_dates = sorted(set(v1_by_date) | set(v2_by_date))
    date_rows = [[d, v1_by_date.get(d, 0), v2_by_date.get(d, 0),
                  v2_by_date.get(d, 0) - v1_by_date.get(d, 0)] for d in all_dates]
    ec61.write_csv(
        os.path.join(run_dir, "t3_date_histogram.csv"),
        ["capture_date", "n_v1", "n_v2", "v2_minus_v1"],
        date_rows,
    )

    ec61.write_csv(
        os.path.join(run_dir, "t3b_v2_only_stems.csv"),
        ["stem", "v2_split", "has_csv_row", "date", "time"],
        [[r.stem, r.split, r.csv_row is not None, r.date_str or "", r.time_str or ""]
         for r in sorted(v2, key=lambda x: x.stem) if r.stem in set(v2_only_stems)],
    )

    if has_split_folders:
        claimed_keys = sorted({c for c, _ in t4_confusion})
        actual_keys = sorted({a for _, a in t4_confusion})
        t4_rows = []
        for c in claimed_keys:
            counts = [t4_confusion.get((c, a), 0) for a in actual_keys]
            t4_rows.append([c] + counts + [sum(counts)])
        ec61.write_csv(
            os.path.join(run_dir, "t4_datatype_vs_v1_folder.csv"),
            ["csv_DATA_TYPE"] + ["v1_" + a for a in actual_keys] + ["total"],
            t4_rows,
        )
        ec61.write_csv(
            os.path.join(run_dir, "t4_disagreements.csv"),
            ["stem", "csv_DATA_TYPE", "v1_folder"],
            [[k, c, a] for k, c, a in t4_disagreements],
        )
    else:
        t4_rows = []

    # ---- summary ----------------------------------------------------------
    def mark(ok):
        return "**PASS**" if ok else "**FAIL**"

    lines = []
    lines.append("# Is the v2 CSV actually v1's metadata?")
    lines.append("")
    lines.append("Hypothesis: `Metadata_ElectroCom61.csv` shipped in v2 was never "
                 "regenerated and still describes v1.")
    lines.append("")
    lines.append("- v1 image files found: **%d**" % len(v1))
    lines.append("- v1 unique stems: **%d** (duplicate stems: %d)"
                 % (len(v1_stem_set), len(v1_dup_stems)))
    lines.append("- v2 image files: **%d**" % len(v2))
    lines.append("- CSV data rows: **%d**" % n_csv_rows)
    lines.append("- v1 split folders detected: %s" % ", ".join("`%s`" % s for s in v1_layout))
    lines.append("- v1 filename parse routes: %s"
                 % ", ".join("%s=%d" % (k, v) for k, v in sorted(v1_routes.items())))
    lines.append("- v2 filename parse routes: %s"
                 % ", ".join("%s=%d" % (k, v) for k, v in sorted(v2_routes.items())))
    lines.append("")
    if v1_dup_stems:
        lines.append("> **%d duplicate stems in v1.** T1 counts FILES and T2 counts "
                     "NAMES, so they can disagree for this reason alone, "
                     "independently of the hypothesis. Resolve before reading the "
                     "verdict." % len(v1_dup_stems))
        lines.append("")

    lines.append("## Verdict")
    lines.append("")
    verdict_rows = [
        ["T1", "count: |v1| == |CSV rows|",
         "%d vs %d" % (len(v1), n_csv_rows), mark(t1_pass)],
        ["T2", "identity: {v1 stems} == {CSV keys}",
         "csv-only %d, v1-only %d" % (len(csv_only), len(v1_only)), mark(t2_pass)],
        ["T3", "no v1 image dated %s" % PREDICTED_ABSENT_DATE,
         "%d found" % len(v1_on_date), mark(t3_pass)],
        ["T3b", "v2 minus v1 == the un-metadata'd images",
         "%d vs %d" % (len(v2_only_stems), len(v2_missing_csv)), mark(t3b_pass)],
        ["T4", "csv DATA_TYPE == v1 folder",
         ("%d disagreements of %d" % (len(t4_disagreements), t4_checked)
          if has_split_folders else "v1 has no split folders"),
         "**%s**" % t4_status],
    ]
    lines.append(_fmt_markdown_table(["test", "prediction", "observed", "result"],
                                     verdict_rows))
    lines.append("")
    lines.append("**T2 is the test that decides this.** T1 can pass by arithmetic "
                 "coincidence -- two collections of 2071 files need not be the same "
                 "files. If T2 passes, the CSV describes v1's contents exactly and "
                 "the hypothesis is established. If T2 fails, a passing T1 means "
                 "nothing on its own.")
    lines.append("")
    if t4_status == "UNANSWERABLE":
        lines.append("T4 could not be evaluated: no `train`/`valid`/`test` folder "
                     "appears anywhere in v1's tree, so there is no v1 split "
                     "assignment to compare DATA_TYPE against. This is NOT a pass. "
                     "It also means the DATA_TYPE column may be recording a split "
                     "that never existed as a directory in either release.")
        lines.append("")

    lines.append("## Capture dates, v1 vs v2")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["capture_date", "n_v1", "n_v2", "v2_minus_v1"], date_rows))
    lines.append("")

    if has_split_folders:
        lines.append("## csv DATA_TYPE vs the folder the image sits in under v1")
        lines.append("")
        actual_keys = sorted({a for _, a in t4_confusion})
        lines.append(_fmt_markdown_table(
            ["csv_DATA_TYPE"] + ["v1_" + a for a in actual_keys] + ["total"], t4_rows))
        lines.append("")
        lines.append("Compare against the same table built on v2 "
                     "(`runs/20260801_csv_coverage/split_agreement.csv`), which has "
                     "600 off-diagonal rows. A clean diagonal here means the CSV's "
                     "splits are v1's splits and v2 re-partitioned without updating "
                     "the metadata.")
        lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    for name in sorted(os.listdir(run_dir)):
        print("  %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
