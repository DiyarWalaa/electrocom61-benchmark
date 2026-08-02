"""
csv_coverage.py -- PRIORITY 2

Resolves the mismatch between the images on disk (2121) and the rows in
Metadata_ElectroCom61.csv (2071 data rows).

Answers three questions:

  1. WHICH images have no metadata row? (full list, not a sample)
  2. Is there a PATTERN -- by family, device, date, or split?
  3. Do the CSV's own DATA_TYPE labels agree with the directory each image
     actually lives in?

Question 3 is not part of the stated mismatch but follows from it: the CSV
claims Train=1454 while train/ holds 1478 files, and the unjoined rows alone
may not account for the difference. If DATA_TYPE disagrees with disk on any
JOINED row then the CSV cannot be used as a source of split assignment, which
matters for any later analysis that groups by CSV fields.

Run with no arguments:

    python scripts/csv_coverage.py

Writes runs/<YYYYMMDD>_csv_coverage/ (auto-suffixed, never overwriting).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


# The CSV spells splits with initial capitals; directories are lowercase.
DATA_TYPE_TO_SPLIT = {"train": "train", "valid": "valid", "test": "test"}


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def main():
    run_dir = ec61.make_run_dir("csv_coverage")

    records = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    n_joined, n_missing = ec61.attach_metadata(records, rows_by_key)

    ec61.write_config(
        run_dir,
        __file__,
        params={"splits": list(ec61.SPLITS)},
        extra={
            "n_images_on_disk": len(records),
            "n_csv_data_rows": n_csv_rows,
            "n_joined": n_joined,
            "n_images_without_csv_row": n_missing,
            "n_duplicate_csv_keys": len(dup_keys),
        },
    )

    splits = list(ec61.SPLITS)

    # ---- direction 1: images with no CSV row ------------------------------
    missing = [r for r in records if r.csv_row is None]
    ec61.write_csv(
        os.path.join(run_dir, "images_missing_csv.csv"),
        ["split", "filename_family", "stem", "date", "time", "filename"],
        [[r.split, r.family, r.stem, r.date_str or "", r.time_str or "", r.filename]
         for r in missing],
    )

    # ---- direction 2: CSV rows with no image on disk ----------------------
    stems_on_disk = {r.stem for r in records}
    orphan_keys = sorted(k for k in rows_by_key if k not in stems_on_disk)
    ec61.write_csv(
        os.path.join(run_dir, "csv_rows_missing_image.csv"),
        ["csv_key", "IMAGE_NAME", "DEVICE_NAME", "BACKGROUND", "DATA_TYPE"],
        [[k,
          rows_by_key[k].get("IMAGE_NAME", ""),
          rows_by_key[k].get("DEVICE_NAME", ""),
          rows_by_key[k].get("BACKGROUND", ""),
          rows_by_key[k].get("DATA_TYPE", "")] for k in orphan_keys],
    )

    # ---- pattern breakdown of the missing set -----------------------------
    # Aggregated three ways, because a pattern may be visible on one axis only.
    by_family = {}
    by_split = {}
    by_date = {}
    for r in missing:
        by_family[r.family] = by_family.get(r.family, 0) + 1
        by_split[r.split] = by_split.get(r.split, 0) + 1
        d = r.date_str or "<no timestamp>"
        by_date[d] = by_date.get(d, 0) + 1

    # Cross-tab of family x split restricted to the missing images, which is
    # where a systematic cause (one export batch, one device) would show up.
    fam_split = {}
    for r in missing:
        fam_split[(r.family, r.split)] = fam_split.get((r.family, r.split), 0) + 1
    fam_keys = sorted({f for f, _ in fam_split})
    breakdown_rows = []
    for f in fam_keys:
        counts = [fam_split.get((f, s), 0) for s in splits]
        breakdown_rows.append([f] + counts + [sum(counts)])
    breakdown_rows.append(["TOTAL"]
                          + [by_split.get(s, 0) for s in splits]
                          + [len(missing)])
    ec61.write_csv(
        os.path.join(run_dir, "missing_breakdown.csv"),
        ["filename_family"] + splits + ["total"],
        breakdown_rows,
    )

    # Per-date detail, to see whether whole capture sessions are absent.
    date_rows = []
    for d in sorted(by_date):
        per_split = {s: 0 for s in splits}
        for r in missing:
            if (r.date_str or "<no timestamp>") == d:
                per_split[r.split] += 1
        date_rows.append([d] + [per_split[s] for s in splits] + [by_date[d]])
    ec61.write_csv(
        os.path.join(run_dir, "missing_by_date.csv"),
        ["capture_date"] + splits + ["total"],
        date_rows,
    )

    # Are the missing images a CONTIGUOUS timestamp range? If they are, the
    # cause is almost certainly one un-exported capture session rather than
    # scattered per-file failures. Reported per (family, date) block.
    contiguity_rows = []
    ts_missing = [r for r in missing if r.epoch is not None]
    by_fam_date = {}
    for r in ts_missing:
        by_fam_date.setdefault((r.family, r.date_str), []).append(r)
    for (fam, date), group in sorted(by_fam_date.items()):
        group.sort(key=lambda r: r.epoch)
        # All images on disk in the same family+date, to measure what fraction
        # of that session is missing and whether the gap is one solid block.
        session = sorted(
            (r for r in records
             if r.family == fam and r.date_str == date and r.epoch is not None),
            key=lambda r: r.epoch,
        )
        idx = {r.stem: i for i, r in enumerate(session)}
        positions = sorted(idx[r.stem] for r in group)
        # A run is contiguous if consecutive positions differ by exactly 1.
        n_runs = 1
        for a, b in zip(positions, positions[1:]):
            if b - a != 1:
                n_runs += 1
        contiguity_rows.append([
            fam, date, len(session), len(group),
            group[0].time_str, group[-1].time_str, n_runs,
        ])
    ec61.write_csv(
        os.path.join(run_dir, "missing_contiguity.csv"),
        ["filename_family", "capture_date", "n_in_session_on_disk",
         "n_missing_from_csv", "first_missing_time", "last_missing_time",
         "n_contiguous_runs"],
        contiguity_rows,
    )

    # ---- direction 3: does CSV DATA_TYPE agree with the actual directory? --
    joined = [r for r in records if r.csv_row is not None]
    confusion = {}
    disagreements = []
    for r in joined:
        claimed_raw = (r.csv_row.get("DATA_TYPE") or "").strip()
        claimed = DATA_TYPE_TO_SPLIT.get(claimed_raw.lower(), claimed_raw or "<blank>")
        confusion[(claimed, r.split)] = confusion.get((claimed, r.split), 0) + 1
        if claimed != r.split:
            disagreements.append((r, claimed_raw))

    claimed_keys = sorted({c for c, _ in confusion})
    conf_rows = []
    for c in claimed_keys:
        counts = [confusion.get((c, s), 0) for s in splits]
        conf_rows.append([c] + counts + [sum(counts)])
    conf_rows.append(["TOTAL"]
                     + [sum(confusion.get((c, s), 0) for c in claimed_keys) for s in splits]
                     + [len(joined)])
    ec61.write_csv(
        os.path.join(run_dir, "split_agreement.csv"),
        ["csv_DATA_TYPE"] + ["actual_" + s for s in splits] + ["total"],
        conf_rows,
    )
    ec61.write_csv(
        os.path.join(run_dir, "split_disagreements.csv"),
        ["stem", "csv_DATA_TYPE", "actual_split", "filename_family", "DEVICE_NAME"],
        [[r.stem, claimed, r.split, r.family, r.device_csv or ""]
         for r, claimed in disagreements],
    )

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# Metadata CSV coverage")
    lines.append("")
    lines.append("- images on disk: **%d**" % len(records))
    lines.append("- CSV data rows: **%d**" % n_csv_rows)
    lines.append("- joined: **%d**" % n_joined)
    lines.append("- images with no CSV row: **%d**" % len(missing))
    lines.append("- CSV rows with no image on disk: **%d**" % len(orphan_keys))
    lines.append("- duplicate CSV IMAGE_NAME keys: **%d**" % len(dup_keys))
    lines.append("")
    lines.append("Arithmetic check: %d on disk - %d missing = %d joined; "
                 "%d CSV rows - %d orphans = %d joined."
                 % (len(records), len(missing), len(records) - len(missing),
                    n_csv_rows, len(orphan_keys), n_csv_rows - len(orphan_keys)))
    lines.append("")

    lines.append("## Images missing a CSV row, by family and split")
    lines.append("")
    lines.append(_fmt_markdown_table(["filename_family"] + splits + ["total"],
                                     breakdown_rows))
    lines.append("")
    lines.append("## Same, by capture date")
    lines.append("")
    lines.append(_fmt_markdown_table(["capture_date"] + splits + ["total"], date_rows))
    lines.append("")
    lines.append("## Contiguity")
    lines.append("")
    lines.append("`n_contiguous_runs` = 1 means every missing image in that")
    lines.append("family+date block is a single unbroken stretch in capture order,")
    lines.append("which points at one un-exported session rather than scattered loss.")
    lines.append("")
    if contiguity_rows:
        lines.append(_fmt_markdown_table(
            ["family", "date", "n_on_disk", "n_missing", "first", "last", "runs"],
            contiguity_rows))
    else:
        lines.append("No timestamped images are missing from the CSV.")
    lines.append("")

    lines.append("## Does CSV DATA_TYPE match the directory the file is in?")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["csv_DATA_TYPE"] + ["actual_" + s for s in splits] + ["total"], conf_rows))
    lines.append("")
    if disagreements:
        lines.append("**%d joined rows disagree with their actual directory.** "
                     "The CSV must NOT be used to assign splits; use the directory."
                     % len(disagreements))
    else:
        lines.append("All joined rows agree with their actual directory. The %d-row "
                     "shortfall is fully explained by the %d images with no CSV row."
                     % (n_csv_rows, len(missing)))
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    for name in sorted(os.listdir(run_dir)):
        print("  %s" % name)


if __name__ == "__main__":
    main()
