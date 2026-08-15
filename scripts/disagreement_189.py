"""
disagreement_189.py -- what are the 189 rows where CSV says train but the
image actually lives in valid/?

`csv_coverage.py` found 600 joined rows whose DATA_TYPE disagrees with the
directory the file is in. The largest single cell of that confusion matrix is
(csv=train, actual=valid) = 189, which is numerically identical to the 189
`counter`-family (iPhone-style IMG_5126) images that carry no timestamp.

This script exists to settle whether that is the SAME 189 images or a
coincidence, and to characterise the cell either way.

The test is a set intersection, not a count comparison. Two sets can both have
189 members and share none of them; quoting "both are 189" as if it were
evidence of a common cause would be exactly the kind of unforced error this
project is trying to avoid.

Also emitted, so the cell is never read in isolation:
  - the full confusion matrix broken down by filename family and by device
  - the capture-date and background composition of the cell
  - whether the cell is a contiguous run in capture order (one mis-assigned
    session) or scattered (per-file relabelling)

Run with no arguments:

    python scripts/disagreement_189.py

Writes runs/<YYYYMMDD>_disagreement_189/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


# The cell under investigation: what the CSV claims, vs where the file is.
CELL_CLAIMED = "train"
CELL_ACTUAL = "valid"


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def _normalise_claim(csv_row):
    """CSV DATA_TYPE lowercased to match directory names; '<blank>' if empty.

    Identical normalisation to csv_coverage.py -- if the two scripts normalised
    differently their confusion matrices would not reconcile.
    """
    raw = (csv_row.get("DATA_TYPE") or "").strip()
    return raw.lower() if raw else "<blank>"


def _count_by(records, key_fn):
    """{key: count} over records."""
    out = {}
    for r in records:
        k = key_fn(r)
        out[k] = out.get(k, 0) + 1
    return out


def _contiguous_runs(cell, all_records):
    """How many unbroken stretches the cell occupies in per-device capture order.

    A single run means one continuous shooting session was assigned one way in
    the CSV and another way on disk -- a bulk relabelling. Many short runs mean
    the assignment was made per-image, which is a different story entirely.

    Only timestamped images can be placed in capture order, so images without a
    timestamp are excluded here and counted separately by the caller.
    """
    runs_by_device = {}
    cell_stems = {r.stem for r in cell}

    # Build the full capture-order timeline per device, over ALL images (not
    # just the cell), so a gap in the cell is measured against what was actually
    # shot in between rather than against the cell alone.
    by_device = {}
    for r in all_records:
        if r.epoch is None:
            continue
        by_device.setdefault(r.device_key, []).append(r)

    for device, seq in by_device.items():
        seq.sort(key=lambda r: (r.epoch, r.stem))
        positions = [i for i, r in enumerate(seq) if r.stem in cell_stems]
        if not positions:
            continue
        n_runs = 1
        for a, b in zip(positions, positions[1:]):
            if b - a != 1:
                n_runs += 1
        runs_by_device[device] = (len(positions), n_runs, len(seq))
    return runs_by_device


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("disagreement_189")

    records = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    n_joined, n_missing = ec61.attach_metadata(records, rows_by_key)

    joined = [r for r in records if r.csv_row is not None]

    # ---- rebuild the confusion matrix -------------------------------------
    # Recomputed here rather than read from the csv_coverage run, so this
    # script's numbers stand on their own and any drift between the two is
    # visible as a contradiction instead of being inherited silently.
    confusion = {}
    for r in joined:
        confusion[(_normalise_claim(r.csv_row), r.split)] = \
            confusion.get((_normalise_claim(r.csv_row), r.split), 0) + 1

    # ---- the cell under investigation -------------------------------------
    cell = [r for r in joined
            if _normalise_claim(r.csv_row) == CELL_CLAIMED and r.split == CELL_ACTUAL]

    # ---- the comparison set: timestamp-less `counter` images ---------------
    counter_set = [r for r in records if r.family == "counter"]

    cell_stems = {r.stem for r in cell}
    counter_stems = {r.stem for r in counter_set}
    overlap = cell_stems & counter_stems

    ec61.write_config(
        run_dir,
        __file__,
        params={
            "cell_csv_DATA_TYPE": CELL_CLAIMED,
            "cell_actual_split": CELL_ACTUAL,
            "comparison_set": "filename_family == 'counter'",
        },
        extra={
            "n_images_on_disk": len(records),
            "n_csv_data_rows": n_csv_rows,
            "n_joined": n_joined,
            "n_cell": len(cell),
            "n_counter_family": len(counter_set),
            "n_overlap": len(overlap),
            "sets_are_identical": cell_stems == counter_stems,
            "sets_are_disjoint": len(overlap) == 0,
        },
    )

    # ---- full membership of the cell --------------------------------------
    ec61.write_csv(
        os.path.join(run_dir, "cell_members.csv"),
        ["stem", "actual_split", "csv_DATA_TYPE", "filename_family",
         "DEVICE_NAME", "BACKGROUND", "date", "time", "in_counter_family"],
        [[r.stem, r.split, _normalise_claim(r.csv_row), r.family,
          r.device_csv or "", (r.csv_row.get("BACKGROUND") or ""),
          r.date_str or "", r.time_str or "",
          r.stem in counter_stems]
         for r in sorted(cell, key=lambda x: (x.date_str or "", x.time_str or "", x.stem))],
    )

    # ---- composition of the cell, on four axes ----------------------------
    axes = (
        ("filename_family", lambda r: r.family),
        ("DEVICE_NAME", lambda r: r.device_csv or "<none>"),
        ("capture_date", lambda r: r.date_str or "<no timestamp>"),
        ("BACKGROUND", lambda r: (r.csv_row.get("BACKGROUND") or "<blank>")),
    )
    comp_rows = []
    for axis_name, key_fn in axes:
        counts = _count_by(cell, key_fn)
        for value in sorted(counts, key=str):
            comp_rows.append([axis_name, value, counts[value]])
    ec61.write_csv(
        os.path.join(run_dir, "cell_composition.csv"),
        ["axis", "value", "n"],
        comp_rows,
    )

    # ---- the same axes over the counter family, for side-by-side reading ---
    counter_rows = []
    for axis_name, key_fn in axes:
        # The counter family has no timestamp and may have no CSV row, so the
        # accessors must tolerate a missing csv_row -- unlike the cell above,
        # which is joined by construction.
        def safe(r, fn=key_fn, name=axis_name):
            if name == "BACKGROUND":
                return (r.csv_row.get("BACKGROUND") or "<blank>") if r.csv_row else "<no csv row>"
            if name == "DEVICE_NAME":
                return r.device_csv or "<none>"
            return fn(r)
        counts = _count_by(counter_set, safe)
        for value in sorted(counts, key=str):
            counter_rows.append([axis_name, value, counts[value]])
    ec61.write_csv(
        os.path.join(run_dir, "counter_family_composition.csv"),
        ["axis", "value", "n"],
        counter_rows,
    )

    # ---- where the counter family actually lives --------------------------
    counter_by_split = _count_by(counter_set, lambda r: r.split)
    counter_by_claim = _count_by(
        counter_set,
        lambda r: _normalise_claim(r.csv_row) if r.csv_row else "<no csv row>")

    # ---- contiguity of the cell in capture order --------------------------
    runs = _contiguous_runs(cell, records)
    n_cell_no_ts = sum(1 for r in cell if r.epoch is None)
    ec61.write_csv(
        os.path.join(run_dir, "cell_contiguity.csv"),
        ["device_key", "n_cell_images", "n_contiguous_runs", "n_device_timeline"],
        [[dev, n_cell_dev, n_runs, n_timeline]
         for dev, (n_cell_dev, n_runs, n_timeline) in sorted(runs.items())],
    )

    # ---- full confusion matrix by family ----------------------------------
    # Shows whether the 189 cell is family-homogeneous or mixed, and whether
    # the other 411 disagreements share its shape.
    fam_rows = []
    fam_conf = {}
    for r in joined:
        key = (_normalise_claim(r.csv_row), r.split, r.family)
        fam_conf[key] = fam_conf.get(key, 0) + 1
    for (claimed, actual, family) in sorted(fam_conf):
        fam_rows.append([claimed, actual, family, fam_conf[(claimed, actual, family)],
                         claimed != actual])
    ec61.write_csv(
        os.path.join(run_dir, "confusion_by_family.csv"),
        ["csv_DATA_TYPE", "actual_split", "filename_family", "n", "is_disagreement"],
        fam_rows,
    )

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# The 189 rows where CSV says `train` but the file is in `valid/`")
    lines.append("")
    lines.append("- rows in the (csv=%s, actual=%s) cell: **%d**"
                 % (CELL_CLAIMED, CELL_ACTUAL, len(cell)))
    lines.append("- images in the `counter` family (no timestamp, iPhone-style): **%d**"
                 % len(counter_set))
    lines.append("- **images in BOTH sets: %d**" % len(overlap))
    lines.append("")

    if cell_stems == counter_stems:
        verdict = ("**SAME SET.** The two 189s are the same images. The cell and "
                   "the timestamp-less family have a common cause.")
    elif not overlap:
        verdict = ("**DISJOINT -- the matching counts are a coincidence.** No image "
                   "appears in both sets. The `counter` family lives in a different "
                   "directory than this cell, so they cannot overlap by construction.")
    else:
        verdict = ("**PARTIAL OVERLAP: %d images.** Neither a coincidence nor a "
                   "common cause; the relationship needs resolving before either "
                   "set is described." % len(overlap))
    lines.append(verdict)
    lines.append("")

    lines.append("## Where the `counter` family actually lives")
    lines.append("")
    lines.append("| axis | value | n |")
    lines.append("|---|---|---|")
    for s in ec61.SPLITS:
        lines.append("| actual directory | %s | %d |" % (s, counter_by_split.get(s, 0)))
    for c in sorted(counter_by_claim, key=str):
        lines.append("| csv DATA_TYPE | %s | %d |" % (c, counter_by_claim[c]))
    lines.append("")
    lines.append("If the `counter` images are all in `train/` then they cannot be "
                 "in a cell defined by `actual=valid`, whatever their count.")
    lines.append("")

    lines.append("## What the 189 cell is made of")
    lines.append("")
    lines.append(_fmt_markdown_table(["axis", "value", "n"], comp_rows))
    lines.append("")

    lines.append("## Contiguity in capture order")
    lines.append("")
    lines.append("One run per device = a whole session relabelled in bulk. Many "
                 "runs = per-image assignment.")
    lines.append("")
    if runs:
        lines.append(_fmt_markdown_table(
            ["device_key", "n_cell_images", "n_contiguous_runs", "n_device_timeline"],
            [[dev, a, b, c] for dev, (a, b, c) in sorted(runs.items())]))
    else:
        lines.append("No cell image carries a timestamp; contiguity is undefined.")
    if n_cell_no_ts:
        lines.append("")
        lines.append("%d of the %d cell images have no timestamp and are excluded "
                     "from the contiguity table above." % (n_cell_no_ts, len(cell)))
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    for name in sorted(os.listdir(run_dir)):
        print("  %s" % name)


if __name__ == "__main__":
    sys.exit(main())