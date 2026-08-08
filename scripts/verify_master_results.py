"""
verify_master_results.py -- check both derived tables against known-good values

Values supplied independently of the pipeline that built them are asserted
here. The script exits non-zero on any mismatch, so it can gate a rebuild
rather than merely inform one.

A script rather than a one-off comparison because the tables get rebuilt --
they already have been, twice -- and a check that ran once is a check that
stops being true without anyone noticing. Two of these expectations FAILED on
the previous table and pass now only because the source of the complexity
columns changed; keeping them in place is what makes that visible.

Expectations are declared as data. Adding one means adding a row, not editing
logic.

TOLERANCE IS PER-EXPECTATION AND EXPLICIT

Most values are compared exactly: they are copied from a results file, not
recomputed, so any difference at all is worth seeing. The per-architecture
means are the exception -- they are computed here from two runs and quoted
rounded, so they carry an explicit +/- 0.01.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


MASTER = os.path.join(ec61.DATA_DIR, "master_results.csv")
BY_ARCH = os.path.join(ec61.DATA_DIR, "latency_by_arch.csv")

# (label, table, model, split_set|None, column, expected, tolerance|None)
# split_set None means "every row of this model must agree on this value",
# which is how a model-level property is checked -- and how "in both runs" is
# expressed for post_ms.
EXPECTATIONS = [
    # --- accuracy, unchanged since the first verification -------------------
    ("YOLO26s corrected test mAP@50",     MASTER, "yolo26s",  "corrected", "test_mAP50",    0.9427, None),
    ("YOLO26s corrected test mAP@50-95",  MASTER, "yolo26s",  "corrected", "test_mAP50_95", 0.6317, None),
    ("RT-DETR-l published test mAP@50",   MASTER, "rtdetr-l", "published", "test_mAP50",    0.9171, None),
    ("YOLOv12s published test mAP@50-95", MASTER, "yolo12s",  "published", "test_mAP50_95", 0.5842, None),

    # --- complexity: both of these FAILED before the unified pass landed -----
    ("YOLO11s params_fused",              MASTER, "yolo11s",  None, "params_fused", 9436407, None),
    ("RT-DETR-l gflops_fused",            MASTER, "rtdetr-l", None, "gflops_fused", 105.6,   None),
    ("YOLOv9s gflops_fused",              MASTER, "yolov9s",  None, "gflops_fused", 26.855,  None),

    # --- latency: post_ms must be identical across the pair -----------------
    ("YOLO26s post_ms (both runs)",       MASTER, "yolo26s",  None, "post_ms", 0.38, None),

    # --- per-architecture means, rounded, so +/- 0.01 -----------------------
    ("yolo11s mean p50",  BY_ARCH, "yolo11s",  None, "e2e_ms_p50_mean", 13.68, 0.01),
    ("yolo26s mean p50",  BY_ARCH, "yolo26s",  None, "e2e_ms_p50_mean", 14.65, 0.01),
    ("yolo12s mean p50",  BY_ARCH, "yolo12s",  None, "e2e_ms_p50_mean", 18.95, 0.01),
    ("yolov9s mean p50",  BY_ARCH, "yolov9s",  None, "e2e_ms_p50_mean", 21.05, 0.01),
    ("rtdetr-l mean p50", BY_ARCH, "rtdetr-l", None, "e2e_ms_p50_mean", 47.21, 0.01),
]


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


def load(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main():
    tables = {}
    for path in (MASTER, BY_ARCH):
        if not os.path.isfile(path):
            sys.stderr.write("table not found: %s\n"
                             "Run collect_results.py and latency_by_arch.py\n" % path)
            return 1
        tables[path] = load(path)

    results = []
    for label, table, model, split, column, expected, tol in EXPECTATIONS:
        rows = [r for r in tables[table]
                if r.get("model") == model
                and (split is None or r.get("split_set") == split)]
        if not rows:
            results.append((label, expected, None, "NO ROW", False))
            continue
        if column not in rows[0]:
            results.append((label, expected, None, "NO COLUMN %s" % column, False))
            continue

        found = sorted({parse(r[column]) for r in rows}, key=str)
        if len(found) > 1:
            # For a model-level property, disagreement between the rows is
            # itself the defect -- whichever value happens to match.
            results.append((label, expected,
                            " / ".join(_fmt(f) for f in found),
                            "DISAGREES ACROSS %d ROWS" % len(rows), False))
            continue

        actual = found[0]
        if actual is None:
            results.append((label, expected, None, "EMPTY", False))
            continue
        if tol is None:
            ok = (actual == expected)
            note = ""
        else:
            ok = abs(float(actual) - float(expected)) <= tol
            note = "within +/-%.2f" % tol if ok else "off by %.4f" % abs(
                float(actual) - float(expected))
        results.append((label, expected, actual, note, ok))

    n_pass = sum(1 for r in results if r[4])
    n_fail = len(results) - n_pass

    width = max(len(r[0]) for r in results)
    print("Cross-check of master_results.csv and latency_by_arch.csv "
          "against %d known values" % len(EXPECTATIONS))
    print()
    for label, expected, actual, note, ok in results:
        print("  [%s] %-*s  expected %-12s  found %-12s %s"
              % ("PASS" if ok else "FAIL", width, label, _fmt(expected),
                 _fmt(actual) if actual is not None else "-", note))
    print()
    print("%d passed, %d FAILED" % (n_pass, n_fail))

    run_dir = ec61.make_run_dir("verify_master_results")
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"tables": [MASTER, BY_ARCH],
                "n_expectations": len(EXPECTATIONS),
                "comparison": "exact unless a tolerance is declared"},
        extra={"passed": n_pass, "failed": n_fail})

    ec61.write_csv(
        os.path.join(run_dir, "verification.csv"),
        ["check", "expected", "found", "note", "result"],
        [[label, expected, "" if actual is None else actual, note,
          "PASS" if ok else "FAIL"]
         for label, expected, actual, note, ok in results])

    lines = ["# Table verification", "",
             "Run directory: `%s`" % os.path.basename(run_dir), "",
             "**%d passed, %d failed** of %d known values."
             % (n_pass, n_fail, len(results)), "",
             "| result | check | expected | found | note |",
             "|---|---|---|---|---|"]
    for label, expected, actual, note, ok in results:
        lines.append("| %s | %s | `%s` | `%s` | %s |"
                     % ("PASS" if ok else "**FAIL**", label, _fmt(expected),
                        _fmt(actual) if actual is not None else "-", note))
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("record: %s" % run_dir)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
