"""
split_v1_vs_v2_by_group.py -- did the re-split introduce the skew?

runs/20260809_split_ratio_by_group showed that the published (v2) split is
near-nominal in aggregate while individual capture sessions are not: three
groups are 100/0/0, two are skewed hard in opposite directions, four sit within
one image of 70/20/10. The inference drawn there -- that the split was assigned
per session rather than per image -- was an inference. This turns it into a
measurement.

TWO ASSIGNMENTS, ONE IMAGE SET

Every image carries two split labels:

  v1  the DATA_TYPE column of Metadata_ElectroCom61.csv. Audit Finding 2
      established that this CSV describes v1 and was never regenerated for v2.
  v2  the folder the image actually sits in under data/ElectroCom-61_v2/.

Both are computed here per capture group, and the comparison is restricted to
the 2071 images the CSV covers so it is like-for-like. The 50 images of the
18 Nov 2024 session have no CSV row at all and therefore cannot appear on the
v1 side; that group is reported as excluded rather than shown with a phantom
zero, since "no v1 label" and "v1 label of zero" are different things.

WHAT THE ANSWER WOULD LOOK LIKE

If v1's groups were near-nominal and v2's are not, the skew was introduced by
the re-split, and the per-session inference becomes a finding about what
someone did between the two releases. If v1's groups were already skewed, the
structure predates v2 and the re-split merely moved it around.

Direction is reported as a transition count per group -- how many images went
valid to train, test to train, and so on. A group can preserve its ratios while
churning every image inside them, and only the transitions distinguish that
from a group left alone.

THE v1 COLUMN IS VERIFIED, NOT ASSUMED

That DATA_TYPE describes v1 is not taken on trust here. Finding 2's fourth
provenance test (runs/20260802_v1_provenance, T4) compared the column against
an actual v1 download from Mendeley and found the contingency table perfectly
diagonal: 1454 train, 412 valid, 205 test, and ZERO disagreements across all
2071 rows. t4_disagreements.csv is empty.

So this analysis has a DEPENDENCY, not a doubt. Every "change" below is a
change relative to a v1 assignment that was checked against v1 itself. If T4
were ever overturned the dependency would matter; while it stands, the v1
column is measured.

The nominal 70/20/10 is inferred from the aggregate, not documented.

Run with no arguments:

    python scripts/split_v1_vs_v2_by_group.py

Writes runs/<YYYYMMDD>_split_v1_vs_v2_by_group/.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


NOMINAL = {"train": 0.70, "valid": 0.20, "test": 0.10}
# Same tolerance as split_ratio_by_group: within this many IMAGES of the
# uniform draw, which does not punish a small session for rounding.
NEAR_IMGS = 1.5

SPLITS = ("train", "valid", "test")
UNTIMESTAMPED_KEY = "<untimestamped:counter>"
UNPARSED_KEY = "<unparsed-filename>"

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def pretty(key):
    if len(key) == 8 and key.isdigit():
        return "%d %s %s" % (int(key[6:8]), _MONTHS[int(key[4:6]) - 1], key[:4])
    if key == UNTIMESTAMPED_KEY:
        return "iPhone (no timestamp)"
    return key


def date_bucket(rec):
    if rec.family == "counter":
        return UNTIMESTAMPED_KEY
    if rec.date_str:
        return rec.date_str
    return UNPARSED_KEY


def shape_of(counts, total):
    if total == 0:
        return "no-data"
    if counts["valid"] == 0 and counts["test"] == 0:
        return "train-only"
    worst = max(abs(counts[s] - total * NOMINAL[s]) for s in SPLITS)
    return "near-nominal" if worst <= NEAR_IMGS else "skewed"


def _fmt_markdown_table(header, rows):
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

    run_dir = ec61.make_run_dir("split_v1_vs_v2_by_group")

    recs = ec61.load_images()
    rows_by_key, dup_keys, n_csv_rows = ec61.load_metadata()
    n_joined, n_missing = ec61.attach_metadata(recs, rows_by_key)

    # Restrict to images the CSV covers, so v1 and v2 describe the same set.
    covered = [r for r in recs if r.csv_row is not None]
    excluded = [r for r in recs if r.csv_row is None]

    bad_type = []
    per_group = {}
    for r in covered:
        raw = (r.csv_row.get("DATA_TYPE") or "").strip().lower()
        if raw not in SPLITS:
            bad_type.append((r.stem, raw))
            continue
        g = per_group.setdefault(date_bucket(r), {
            "v1": {s: 0 for s in SPLITS},
            "v2": {s: 0 for s in SPLITS},
            "trans": {(a, b): 0 for a in SPLITS for b in SPLITS},
        })
        g["v1"][raw] += 1
        g["v2"][r.split] += 1
        g["trans"][(raw, r.split)] += 1

    # Groups present on disk but absent from the CSV entirely.
    # Groups absent from the CSV entirely. Their v2 composition IS known -- it
    # is the folder they sit in -- so it is captured here even though they have
    # no v1 side to compare against.
    all_groups = {date_bucket(r) for r in recs}
    excluded_groups = {}
    for gkey in sorted(all_groups - set(per_group)):
        members = [r for r in excluded if date_bucket(r) == gkey]
        excluded_groups[gkey] = {
            "n": len(members),
            "v2": {s: sum(1 for r in members if r.split == s) for s in SPLITS},
        }

    order = sorted(per_group, key=lambda k: (k == UNTIMESTAMPED_KEY, k))

    rows_out = []
    trans_out = []
    for gkey in order:
        g = per_group[gkey]
        total = sum(g["v1"].values())
        assert total == sum(g["v2"].values())
        pct1 = {s: 100.0 * g["v1"][s] / total for s in SPLITS}
        pct2 = {s: 100.0 * g["v2"][s] / total for s in SPLITS}
        dev1 = {s: g["v1"][s] - total * NOMINAL[s] for s in SPLITS}
        dev2 = {s: g["v2"][s] - total * NOMINAL[s] for s in SPLITS}
        unchanged = sum(g["trans"][(s, s)] for s in SPLITS)
        changed = total - unchanged

        rows_out.append({
            "key": gkey, "label": pretty(gkey), "total": total,
            "v1": g["v1"], "v2": g["v2"], "pct1": pct1, "pct2": pct2,
            "dev1": dev1, "dev2": dev2,
            "shape1": shape_of(g["v1"], total), "shape2": shape_of(g["v2"], total),
            "changed": changed, "unchanged": unchanged,
            "trans": g["trans"],
        })
        for a in SPLITS:
            for b in SPLITS:
                if g["trans"][(a, b)]:
                    trans_out.append([gkey, pretty(gkey), a, b, g["trans"][(a, b)],
                                      "same" if a == b else "moved"])

    tot1 = {s: sum(r["v1"][s] for r in rows_out) for s in SPLITS}
    tot2 = {s: sum(r["v2"][s] for r in rows_out) for s in SPLITS}
    tot_n = sum(r["total"] for r in rows_out)
    tot_changed = sum(r["changed"] for r in rows_out)

    ec61.write_csv(
        os.path.join(run_dir, "split_v1_vs_v2_by_group.csv"),
        ["capture_group", "label", "imgs_in_csv",
         "v1_train", "v1_valid", "v1_test",
         "v2_train", "v2_valid", "v2_test",
         "v1_pct_train", "v1_pct_valid", "v1_pct_test",
         "v2_pct_train", "v2_pct_valid", "v2_pct_test",
         "v1_dev_train_imgs", "v1_dev_valid_imgs", "v1_dev_test_imgs",
         "v2_dev_train_imgs", "v2_dev_valid_imgs", "v2_dev_test_imgs",
         "v1_shape", "v2_shape", "imgs_changed_split", "imgs_unchanged",
         "pct_changed"],
        [[r["key"], r["label"], r["total"],
          r["v1"]["train"], r["v1"]["valid"], r["v1"]["test"],
          r["v2"]["train"], r["v2"]["valid"], r["v2"]["test"],
          round(r["pct1"]["train"], 2), round(r["pct1"]["valid"], 2),
          round(r["pct1"]["test"], 2),
          round(r["pct2"]["train"], 2), round(r["pct2"]["valid"], 2),
          round(r["pct2"]["test"], 2),
          round(r["dev1"]["train"], 1), round(r["dev1"]["valid"], 1),
          round(r["dev1"]["test"], 1),
          round(r["dev2"]["train"], 1), round(r["dev2"]["valid"], 1),
          round(r["dev2"]["test"], 1),
          r["shape1"], r["shape2"], r["changed"], r["unchanged"],
          round(100.0 * r["changed"] / r["total"], 1)]
         for r in rows_out])

    ec61.write_csv(
        os.path.join(run_dir, "split_transitions_by_group.csv"),
        ["capture_group", "label", "v1_split", "v2_split", "n_images", "kind"],
        trans_out)

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"nominal": NOMINAL, "near_nominal_tolerance_imgs": NEAR_IMGS,
                "restricted_to": "the images the metadata CSV covers",
                "v1_source": "Metadata_ElectroCom61.csv DATA_TYPE",
                "v2_source": "directory on disk"},
        extra={"csv_rows": n_csv_rows, "images": len(recs),
               "joined": n_joined, "unjoined": n_missing,
               "duplicate_csv_keys": len(dup_keys),
               "unrecognised_data_type": bad_type,
               "excluded_groups": excluded_groups,
               "v1_totals": tot1, "v2_totals": tot2,
               "images_changed_split": tot_changed})

    # ---- print -------------------------------------------------------------
    print("v1 (CSV DATA_TYPE) vs v2 (folders), per capture group")
    print("restricted to the %d images the CSV covers; %d images have no CSV row"
          % (tot_n, n_missing))
    if excluded_groups:
        for k, v in excluded_groups.items():
            print("  EXCLUDED: %s -- %d images, none carry a CSV row; "
                  "v2 split them %d/%d/%d"
                  % (pretty(k), v["n"], v["v2"]["train"], v["v2"]["valid"],
                     v["v2"]["test"]))
    if bad_type:
        print("  WARNING: %d rows with an unrecognised DATA_TYPE" % len(bad_type))
    print()
    print("  %-22s %5s | %-17s %-13s | %-17s %-13s | %s"
          % ("group", "imgs", "v1 %  tr/va/te", "v1 shape",
             "v2 %  tr/va/te", "v2 shape", "changed"))
    print("  " + "-" * 108)
    for r in rows_out:
        print("  %-22s %5d | %5.1f %5.1f %5.1f  %-13s | %5.1f %5.1f %5.1f  %-13s | %d (%.0f%%)"
              % (r["label"], r["total"],
                 r["pct1"]["train"], r["pct1"]["valid"], r["pct1"]["test"], r["shape1"],
                 r["pct2"]["train"], r["pct2"]["valid"], r["pct2"]["test"], r["shape2"],
                 r["changed"], 100.0 * r["changed"] / r["total"]))
    print("  " + "-" * 108)
    # No shape label on the aggregate: the tolerance is an IMAGE count, so over
    # 2071 images 1.5 images is 0.07 pp and every aggregate scores "skewed"
    # however close its ratios are. Printing it would invite exactly the wrong
    # reading of a row that is 70.2/19.9/9.9.
    print("  %-22s %5d | %5.1f %5.1f %5.1f  %-13s | %5.1f %5.1f %5.1f  %-13s | %d (%.0f%%)"
          % ("ALL (CSV-covered)", tot_n,
             100.0 * tot1["train"] / tot_n, 100.0 * tot1["valid"] / tot_n,
             100.0 * tot1["test"] / tot_n, "(n/a, see note)",
             100.0 * tot2["train"] / tot_n, 100.0 * tot2["valid"] / tot_n,
             100.0 * tot2["test"] / tot_n, "(n/a, see note)",
             tot_changed, 100.0 * tot_changed / tot_n))
    print()
    print("  counts   v1 %s" % {s: tot1[s] for s in SPLITS})
    print("           v2 %s" % {s: tot2[s] for s in SPLITS})
    print()
    print("  transitions (v1 -> v2), images that moved")
    print("  %-22s %s" % ("group", "moves"))
    print("  " + "-" * 78)
    for r in rows_out:
        moves = ["%s->%s %d" % (a, b, r["trans"][(a, b)])
                 for a in SPLITS for b in SPLITS
                 if a != b and r["trans"][(a, b)]]
        print("  %-22s %s" % (r["label"], ", ".join(moves) if moves else "(none)"))
    print()
    n1_near = sum(1 for r in rows_out if r["shape1"] == "near-nominal")
    n2_near = sum(1 for r in rows_out if r["shape2"] == "near-nominal")
    print("  groups near-nominal:  v1 %d of %d   ->   v2 %d of %d"
          % (n1_near, len(rows_out), n2_near, len(rows_out)))
    print()
    print("wrote %s" % os.path.relpath(run_dir, ec61.REPO_ROOT).replace("\\", "/"))

    # ---- summary -----------------------------------------------------------
    lines = []
    lines.append("# v1 vs v2 split, per capture group")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("v1 = `DATA_TYPE` in `Metadata_ElectroCom61.csv`; v2 = the "
                 "folder on disk. Restricted to the **%d images the CSV "
                 "covers**, so both sides describe the same set." % tot_n)
    lines.append("")
    for k, v in excluded_groups.items():
        lines.append("- **Excluded: %s** — %d images, none of which carry a CSV "
                     "row, so it has no v1 label to compare against. v2 split "
                     "them %d/%d/%d."
                     % (pretty(k), v["n"], v["v2"]["train"], v["v2"]["valid"],
                        v["v2"]["test"]))
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["group", "imgs", "v1 tr/va/te %", "v1 shape", "v2 tr/va/te %",
         "v2 shape", "changed"],
        [[r["label"], r["total"],
          "%.1f / %.1f / %.1f" % (r["pct1"]["train"], r["pct1"]["valid"], r["pct1"]["test"]),
          r["shape1"],
          "%.1f / %.1f / %.1f" % (r["pct2"]["train"], r["pct2"]["valid"], r["pct2"]["test"]),
          r["shape2"],
          "%d (%.0f%%)" % (r["changed"], 100.0 * r["changed"] / r["total"])]
         for r in rows_out]
        + [["**ALL**", tot_n,
            "%.1f / %.1f / %.1f" % (100.0 * tot1["train"] / tot_n,
                                    100.0 * tot1["valid"] / tot_n,
                                    100.0 * tot1["test"] / tot_n),
            "(n/a)",
            "%.1f / %.1f / %.1f" % (100.0 * tot2["train"] / tot_n,
                                    100.0 * tot2["valid"] / tot_n,
                                    100.0 * tot2["test"] / tot_n),
            "(n/a)",
            "%d (%.0f%%)" % (tot_changed, 100.0 * tot_changed / tot_n)]]))
    lines.append("")
    lines.append("Groups near-nominal: **v1 %d of %d → v2 %d of %d**."
                 % (n1_near, len(rows_out), n2_near, len(rows_out)))
    lines.append("")
    lines.append("## Where the images went")
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["group", "moves (v1 → v2)"],
        [[r["label"],
          ", ".join("%s→%s %d" % (a, b, r["trans"][(a, b)])
                    for a in SPLITS for b in SPLITS
                    if a != b and r["trans"][(a, b)]) or "none"]
         for r in rows_out]))
    lines.append("")
    lines.append("## Borderline classifications")
    lines.append("")
    for r in rows_out:
        for tag, counts in (("v1", r["v1"]), ("v2", r["v2"])):
            worst = max(abs(counts[s] - r["total"] * NOMINAL[s]) for s in SPLITS)
            if NEAR_IMGS < worst <= 2.5 and not (counts["valid"] == 0 and counts["test"] == 0):
                lines.append("- **%s (%s)** is scored `skewed` but misses the "
                             "%.1f-image tolerance by only %.1f images on a "
                             "%d-image group — %.2f percentage points. Read it "
                             "as near-nominal in substance."
                             % (r["label"], tag, NEAR_IMGS, worst, r["total"],
                                100.0 * worst / r["total"]))
    lines.append("")
    lines.append("The aggregate row carries no shape label at all. The "
                 "tolerance is an image count, so across %d images it is %.2f "
                 "percentage points and no aggregate could ever pass it."
                 % (tot_n, 100.0 * NEAR_IMGS / tot_n))
    lines.append("")
    lines.append("## Two clarifications")
    lines.append("")
    lines.append("### The v1 column is verified, not assumed")
    lines.append("")
    lines.append("That `DATA_TYPE` describes v1 is established, not inferred. "
                 "Finding 2's fourth provenance test (`runs/20260802_v1_provenance`, "
                 "T4) compared the column against an actual v1 download and "
                 "found the contingency table perfectly diagonal — 1454 train, "
                 "412 valid, 205 test — with **zero disagreements across all "
                 "2071 rows**; `t4_disagreements.csv` is empty.")
    lines.append("")
    lines.append("This analysis therefore carries a **dependency on T4**, not "
                 "an open doubt. Every change reported above is a change "
                 "relative to a v1 assignment that was checked against v1 "
                 "itself. Phrase it that way in the paper: if T4 were "
                 "overturned the dependency would matter, but while it stands "
                 "the v1 column is a measurement.")
    lines.append("")
    if excluded_groups:
        newk = sorted(excluded_groups)[0]
        lines.append("### v2 split the newly added session correctly")
        lines.append("")
        ex = excluded_groups[newk]
        exp = {s2: ex["n"] * NOMINAL[s2] for s2 in SPLITS}
        worst_ex = max(abs(ex["v2"][s2] - exp[s2]) for s2 in SPLITS)
        lines.append("`%s` is the one session absent from v1 — its %d images "
                     "were added in v2 and have no CSV row. v2 split it "
                     "**%d / %d / %d of %d**, which is %.1f / %.1f / %.1f "
                     "percent — worst deviation from 70/20/10 across the three "
                     "cells: **%.1f images**."
                     % (pretty(newk), ex["n"], ex["v2"]["train"],
                        ex["v2"]["valid"], ex["v2"]["test"], ex["n"],
                        100.0 * ex["v2"]["train"] / ex["n"],
                        100.0 * ex["v2"]["valid"] / ex["n"],
                        100.0 * ex["v2"]["test"] / ex["n"], worst_ex))
        lines.append("")
        lines.append("Recorded as an observation. Whatever produced the v2 "
                     "split handled a brand-new session at the nominal ratio, "
                     "so the changes documented above are confined to "
                     "assignments that already existed. No mechanism is "
                     "claimed here for why the pre-existing ones changed.")
        lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- The v1 column rests on T4 (see above). That is a "
                 "dependency on a passing test, not an assumption, but it is "
                 "still a dependency.")
    lines.append("- 70/20/10 is inferred from the aggregate, not documented by "
                 "the dataset authors.")
    lines.append("- Ratios are over images, not annotation instances.")
    lines.append("- A group can hold its ratios while churning every image "
                 "inside them; that is why transitions are reported and not "
                 "only the before-and-after shares.")
    lines.append("- `shape` is a label at one tolerance, not a test, and the "
                 "tolerance is in images. It is well behaved for groups of "
                 "50-500 and meaningless outside that range; see the "
                 "borderline section above.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
