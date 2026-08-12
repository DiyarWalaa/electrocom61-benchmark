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

    # ---- structural checks on the master table -----------------------------
    # These run BEFORE the value expectations. A value can be correct in a
    # table that is structurally wrong: a duplicated (model, split_set) pair
    # still yields the right number for whichever row is read first, so
    # checking values alone would pass a table no consumer can use safely.
    structural = []
    master_rows = tables[MASTER]

    if not master_rows or "inclusion" not in master_rows[0]:
        structural.append(("inclusion column present", "yes", "MISSING", False))
    else:
        n_bench = sum(1 for r in master_rows
                      if r["inclusion"] == ec61.INCLUSION_BENCHMARK)
        structural.append(("benchmark rows", ec61.N_BENCHMARK_ROWS, n_bench,
                           n_bench == ec61.N_BENCHMARK_ROWS))

        # Every declared diverged run must be present and labelled as such.
        for slug in ec61.DIVERGED_RUNS:
            got = [r for r in master_rows if r.get("run") == slug]
            ok = len(got) == 1 and got[0]["inclusion"] == ec61.INCLUSION_DIVERGED
            structural.append(("run %s labelled diverged" % slug, "yes",
                               "yes" if ok else "no (%d row(s))" % len(got), ok))

        # Duplicate (model, split_set) among BENCHMARK rows -- not across all
        # rows. The diverged run legitimately shares its pair with
        # rtdetr_l_pub_lr1e4, which is precisely why it must be excluded
        # before anything indexes by that pair.
        seen, dupes = {}, []
        for r in master_rows:
            if r.get("inclusion") != ec61.INCLUSION_BENCHMARK:
                continue
            key = (r.get("model"), r.get("split_set"))
            if key in seen:
                dupes.append("%s/%s: %s and %s" % (key[0], key[1], seen[key],
                                                   r.get("run")))
            seen[key] = r.get("run")
        structural.append(("unique (model, split_set) among benchmark rows",
                           "yes", "yes" if not dupes else "; ".join(dupes),
                           not dupes))

        # The guarded loader must accept the table. This is the check that
        # matters most -- it is the code path every figure and table uses.
        try:
            ec61.load_benchmark_rows(MASTER)
            structural.append(("ec61.load_benchmark_rows() accepts the table",
                               "yes", "yes", True))
        except Exception as exc:
            structural.append(("ec61.load_benchmark_rows() accepts the table",
                               "yes", "%s: %s" % (type(exc).__name__, exc),
                               False))

    # Value expectations are checked against BENCHMARK rows only. The diverged
    # run shares (model, split_set) with rtdetr_l_pub_lr1e4, so an unfiltered
    # lookup for "RT-DETR-l published test mAP@50" matches two rows and reports
    # a disagreement that is not a defect -- the two runs are supposed to
    # differ. Structural checks above still see every row.
    value_tables = dict(tables)
    try:
        value_tables[MASTER] = ec61.load_benchmark_rows(MASTER)
    except Exception:
        pass  # already reported as a structural failure; leave rows unfiltered

    results = []
    for label, table, model, split, column, expected, tol in EXPECTATIONS:
        rows = [r for r in value_tables[table]
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

    # Structural failures are counted alongside value failures so a broken
    # table cannot exit 0 on the strength of its numbers being right.
    results = [(label, expected, actual, "structural", ok)
               for label, expected, actual, ok in structural] + results

    n_pass = sum(1 for r in results if r[4])
    n_fail = len(results) - n_pass

    width = max(len(r[0]) for r in results)
    print("Structure of master_results.csv, then %d known values across "
          "master_results.csv and latency_by_arch.csv" % len(EXPECTATIONS))
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
