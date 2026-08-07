"""
verify_master_results.py -- check the master table against known-good values

Six values were supplied independently of the pipeline that built
data/master_results.csv. This script asserts them. It exits non-zero on any
mismatch, so it can gate a build rather than merely inform one.

A script rather than a one-off comparison because the table will be rebuilt --
when the unified latency pass lands, when a run is re-trained -- and a check
that only ran once is a check that stops being true without anyone noticing.

Expectations are declared as data at the top of the file. Adding one means
adding a row there, not editing logic.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


TABLE = os.path.join(ec61.DATA_DIR, "master_results.csv")

# (label, model, split_set or None for "every row of this model", column, expected)
# split_set is None for model-level properties that must not vary by split.
EXPECTATIONS = [
    ("YOLO26s corrected test mAP@50",     "yolo26s",  "corrected", "test_mAP50",    0.9427),
    ("YOLO26s corrected test mAP@50-95",  "yolo26s",  "corrected", "test_mAP50_95", 0.6317),
    ("RT-DETR-l published test mAP@50",   "rtdetr-l", "published", "test_mAP50",    0.9171),
    ("YOLOv12s published test mAP@50-95", "yolo12s",  "published", "test_mAP50_95", 0.5842),
    ("YOLO11s params_fused",              "yolo11s",  None,        "params_fused",  9436407),
    ("RT-DETR-l gflops",                  "rtdetr-l", None,        "gflops",        105.6),
]

# Floats are compared exactly after parsing, not with a tolerance: these are
# values copied from a results file, not the output of a fresh computation, so
# any difference at all is a discrepancy worth seeing rather than smoothing.
def parse(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def _fmt(v):
    if isinstance(v, int):
        return "{:,}".format(v)
    return str(v)


def main():
    if not os.path.isfile(TABLE):
        sys.stderr.write("table not found: %s\nRun scripts/collect_results.py\n" % TABLE)
        return 1

    with open(TABLE, "r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    results = []
    for label, model, split, column, expected in EXPECTATIONS:
        matching = [r for r in rows
                    if r["model"] == model
                    and (split is None or r["split_set"] == split)]
        if not matching:
            results.append((label, column, expected, None, "NO ROW", False))
            continue

        found = sorted({parse(r[column]) for r in matching}, key=str)
        if len(found) > 1:
            # A model-level property that differs between splits is itself a
            # defect, whichever value happens to match.
            results.append((label, column, expected,
                            " / ".join(_fmt(f) for f in found),
                            "VARIES BY SPLIT", False))
            continue

        actual = found[0]
        results.append((label, column, expected, actual, "", actual == expected))

    n_pass = sum(1 for r in results if r[5])
    n_fail = len(results) - n_pass

    width = max(len(r[0]) for r in results)
    print("Cross-check of %s against %d known values"
          % (os.path.basename(TABLE), len(EXPECTATIONS)))
    print()
    for label, column, expected, actual, note, ok in results:
        print("  [%s] %-*s  expected %-12s  found %-12s %s"
              % ("PASS" if ok else "FAIL", width, label,
                 _fmt(expected), _fmt(actual) if actual is not None else "-", note))
    print()
    print("%d passed, %d FAILED" % (n_pass, n_fail))

    run_dir = ec61.make_run_dir("verify_master_results")
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"table": TABLE, "n_expectations": len(EXPECTATIONS),
                "comparison": "exact, no tolerance"},
        extra={"passed": n_pass, "failed": n_fail})

    ec61.write_csv(
        os.path.join(run_dir, "verification.csv"),
        ["check", "column", "expected", "found", "note", "result"],
        [[label, column, expected,
          "" if actual is None else actual, note, "PASS" if ok else "FAIL"]
         for label, column, expected, actual, note, ok in results])

    lines = []
    lines.append("# Master table verification")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("**%d passed, %d failed** of %d known values."
                 % (n_pass, n_fail, len(results)))
    lines.append("")
    lines.append("| result | check | expected | found |")
    lines.append("|---|---|---|---|")
    for label, column, expected, actual, note, ok in results:
        lines.append("| %s | %s | `%s` | `%s`%s |"
                     % ("PASS" if ok else "**FAIL**", label, _fmt(expected),
                        _fmt(actual) if actual is not None else "-",
                        (" — " + note) if note else ""))
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("record: %s" % run_dir)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
