"""
device_split_table.py -- PRIORITY 1

Produces a clean, verifiable table of images per capture device per split.

The device is determined TWO independent ways and the two are cross-checked
against each other:

  (a) from the filename family, which depends only on directory listings and
      is therefore checkable by a reviewer with `ls`;
  (b) from DEVICE_NAME in Metadata_ElectroCom61.csv.

If the two agree the contingency table family_vs_device.csv is near-diagonal.
Off-diagonal mass means one of the two signals is wrong, and that is reported
explicitly rather than averaged away.

Run with no arguments:

    python scripts/device_split_table.py

Writes runs/<YYYYMMDD>_device_split/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


# Label used in output tables for images that have no matching metadata row.
NO_CSV = "<no CSV row>"


def _fmt_markdown_table(header, rows):
    """Render a list-of-lists as a GitHub-flavoured markdown table."""
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("device_split")

    # ---- load -------------------------------------------------------------
    records = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    n_joined, n_missing = ec61.attach_metadata(records, rows_by_key)

    ec61.write_config(
        run_dir,
        __file__,
        params={
            "splits": list(ec61.SPLITS),
            "family_patterns": [name for name, _ in ec61.FAMILY_PATTERNS],
        },
        extra={
            "n_images_on_disk": len(records),
            "n_csv_data_rows": n_csv_rows,
            "n_joined": n_joined,
            "n_images_without_csv_row": n_missing,
            "n_duplicate_csv_keys": len(dup_keys),
        },
    )

    splits = list(ec61.SPLITS)

    # ---- table 1: filename family x split ---------------------------------
    # Filename-only, so a reviewer can reproduce this with shell tools alone.
    fam_keys, fam_table = ec61.counts_table(records, lambda r: r.family)
    fam_rows = []
    for k in fam_keys:
        counts = [fam_table[k][s] for s in splits]
        fam_rows.append([k] + counts + [sum(counts)])
    fam_rows.append(["TOTAL"] + [sum(fam_table[k][s] for k in fam_keys) for s in splits]
                    + [len(records)])
    ec61.write_csv(
        os.path.join(run_dir, "family_by_split.csv"),
        ["filename_family"] + splits + ["total"],
        fam_rows,
    )

    # ---- table 2: CSV device x split --------------------------------------
    dev_keys, dev_table = ec61.counts_table(
        records, lambda r: r.device_csv or NO_CSV
    )
    dev_rows = []
    for k in dev_keys:
        counts = [dev_table[k][s] for s in splits]
        dev_rows.append([k] + counts + [sum(counts)])
    dev_rows.append(["TOTAL"] + [sum(dev_table[k][s] for k in dev_keys) for s in splits]
                   + [len(records)])
    ec61.write_csv(
        os.path.join(run_dir, "device_by_split.csv"),
        ["device_name_csv"] + splits + ["total"],
        dev_rows,
    )

    # ---- table 3: family x device contingency (the cross-check) -----------
    contingency = {}
    for rec in records:
        key = (rec.family, rec.device_csv or NO_CSV)
        contingency[key] = contingency.get(key, 0) + 1

    device_cols = sorted({d for (_, d) in contingency})
    cont_rows = []
    for fam in fam_keys:
        row = [fam] + [contingency.get((fam, d), 0) for d in device_cols]
        cont_rows.append(row)
    ec61.write_csv(
        os.path.join(run_dir, "family_vs_device.csv"),
        ["filename_family"] + device_cols,
        cont_rows,
    )

    # ---- consistency findings ---------------------------------------------
    # A family is "clean" if all its images with a CSV row name one device.
    # Ambiguity in either direction undermines using family as a device proxy.
    fam_to_devices = {}
    dev_to_families = {}
    for (fam, dev), n in contingency.items():
        if dev == NO_CSV:
            continue  # unknown device tells us nothing about consistency
        fam_to_devices.setdefault(fam, {})[dev] = n
        dev_to_families.setdefault(dev, {})[fam] = n

    ambiguous_families = {f: d for f, d in fam_to_devices.items() if len(d) > 1}
    ambiguous_devices = {d: f for d, f in dev_to_families.items() if len(f) > 1}

    # ---- device-exclusivity finding ---------------------------------------
    # The headline question: is any device confined to a single split? A device
    # present only in train is never evaluated; a device only in test is never
    # trained on. Both are distribution gaps worth reporting.
    exclusive = []
    for k in dev_keys:
        present = [s for s in splits if dev_table[k][s] > 0]
        if len(present) == 1:
            exclusive.append((k, present[0], sum(dev_table[k][s] for s in splits)))

    fam_exclusive = []
    for k in fam_keys:
        present = [s for s in splits if fam_table[k][s] > 0]
        if len(present) == 1:
            fam_exclusive.append((k, present[0], sum(fam_table[k][s] for s in splits)))

    ec61.write_csv(
        os.path.join(run_dir, "single_split_devices.csv"),
        ["kind", "key", "only_split", "n_images"],
        [["device", k, s, n] for k, s, n in exclusive]
        + [["family", k, s, n] for k, s, n in fam_exclusive],
    )

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# Device x split coverage (ElectroCom-61 v9)")
    lines.append("")
    lines.append("Dataset dir: `%s`" % ec61.DATASET_DIR)
    lines.append("")
    lines.append("- images on disk: **%d**" % len(records))
    lines.append("- metadata CSV data rows: **%d**" % n_csv_rows)
    lines.append("- images joined to a CSV row: **%d**" % n_joined)
    lines.append("- images with NO CSV row: **%d**" % n_missing)
    if dup_keys:
        lines.append("- duplicate CSV IMAGE_NAME keys: **%d**" % len(dup_keys))
    lines.append("")

    lines.append("## Filename family x split")
    lines.append("")
    lines.append("Derived from filenames only -- reproducible with `ls`.")
    lines.append("")
    lines.append(_fmt_markdown_table(["filename_family"] + splits + ["total"], fam_rows))
    lines.append("")

    lines.append("## CSV DEVICE_NAME x split")
    lines.append("")
    lines.append("All fields whitespace-stripped on load.")
    lines.append("")
    lines.append(_fmt_markdown_table(["device_name_csv"] + splits + ["total"], dev_rows))
    lines.append("")

    lines.append("## Cross-check: filename family vs CSV device")
    lines.append("")
    lines.append(_fmt_markdown_table(["filename_family"] + device_cols, cont_rows))
    lines.append("")
    if ambiguous_families:
        lines.append("**Families mapping to more than one device:**")
        for f, d in sorted(ambiguous_families.items()):
            lines.append("- `%s` -> %s" % (f, ", ".join("%s (%d)" % (k, v)
                                                        for k, v in sorted(d.items()))))
    else:
        lines.append("Every filename family maps to exactly one CSV device.")
    lines.append("")
    if ambiguous_devices:
        lines.append("**Devices mapping to more than one family:**")
        for d, f in sorted(ambiguous_devices.items()):
            lines.append("- `%s` -> %s" % (d, ", ".join("%s (%d)" % (k, v)
                                                        for k, v in sorted(f.items()))))
    else:
        lines.append("Every CSV device maps to exactly one filename family.")
    lines.append("")

    lines.append("## Devices / families confined to a single split")
    lines.append("")
    if exclusive or fam_exclusive:
        lines.append(_fmt_markdown_table(
            ["kind", "key", "only_split", "n_images"],
            [["device", k, s, n] for k, s, n in exclusive]
            + [["family", k, s, n] for k, s, n in fam_exclusive],
        ))
        lines.append("")
        lines.append("A device present in only one split is a coverage gap: if it is")
        lines.append("train-only it is never evaluated; if it is test-only it is never")
        lines.append("trained on. This is a distribution problem, distinct from leakage.")
    else:
        lines.append("No device or family is confined to a single split.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    for name in sorted(os.listdir(run_dir)):
        print("  %s" % name)


if __name__ == "__main__":
    sys.exit(main())