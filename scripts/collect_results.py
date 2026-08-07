"""
collect_results.py -- one master table from the ten Kaggle results JSONs

Reads data/kaggle/results_*.json and writes data/master_results.csv, one row per
(model, split). This is the table the paper's accuracy figures are built from,
so every column states where it came from and nothing is silently derived.

LATENCY IS DELIBERATELY LEFT EMPTY

Every one of these JSONs already carries a `latency_ms` block (p50, p95, mean,
batch_size, runs, warmup) and an `fps` figure, and each `val`/`test` section
carries a `speed_ms` breakdown. NONE of it is copied here, and the omission is
the point rather than an oversight.

Those numbers were measured inside ten separate Kaggle sessions, on whatever
P100 that session was allotted, under whatever contention the host had at the
time, with the model that had just finished training still resident. They are
fine for spotting a gross regression inside one session and useless for a
cross-model comparison in a paper: a 2x difference between two rows could be
scheduling noise rather than architecture.

The project rule for latency is explicit -- warmup first, torch.cuda.synchronize(),
report p50 AND p95, state the batch size -- and it can only be honoured by one
unified pass over all ten checkpoints on one machine with nothing else running.
Until that exists the columns stay empty and `latency_source` reads
`pending_unified_pass`, so a half-populated table can never be mistaken for a
finished one.

FIELD MAPPING, STATED

    model            <- model            (".pt" stripped)
    run              <- run              (the slug; joins to data/kaggle/artifacts/)
    split_set        <- split_set
    val_mAP50        <- val.mAP50
    val_mAP50_95     <- val.mAP50_95
    test_mAP50       <- test.mAP50
    test_mAP50_95    <- test.mAP50_95
    classes_*        <- val.classes_evaluated, test.classes_evaluated
    params_fused     <- params
    gflops           <- gflops
    epochs_run       <- epochs_completed
    train_time_min   <- train_minutes

`classes_evaluated` is emitted as TWO columns rather than the one requested.
They genuinely differ on the published split -- 45 classes evaluable in valid
against 46 in test, because 15 classes have no instances in either and a 16th
has none in valid. Collapsing them to a single number would erase the finding
this whole study is built on.

`params_fused` is sourced from the JSON's `params`. The JSON does not say
whether that count is fused or unfused; the column is named as requested and
this note is the caveat.

Run with no arguments:

    python scripts/collect_results.py

Writes data/master_results.csv and runs/<YYYYMMDD>_collect_results/.
"""

import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


KAGGLE_DIR = os.path.join(ec61.DATA_DIR, "kaggle")
OUT_CSV = os.path.join(ec61.DATA_DIR, "master_results.csv")

LATENCY_SOURCE = "pending_unified_pass"

# Emitted empty, on purpose. See the module docstring.
LATENCY_COLUMNS = ("latency_p50_ms", "latency_p95_ms", "fps",
                   "preprocess_ms", "inference_ms", "postprocess_ms")

COLUMNS = (["model", "run", "split_set",
            "val_mAP50", "val_mAP50_95",
            "test_mAP50", "test_mAP50_95",
            "classes_evaluated_val", "classes_evaluated_test",
            "params_fused", "gflops", "epochs_run", "train_time_min"]
           + list(LATENCY_COLUMNS) + ["latency_source"])


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get(d, *keys):
    """Nested lookup returning None rather than raising on a missing branch."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def main():
    paths = sorted(glob.glob(os.path.join(KAGGLE_DIR, "results_*.json")))
    if not paths:
        sys.stderr.write("no results_*.json under %s\n" % KAGGLE_DIR)
        return 1

    run_dir = ec61.make_run_dir("collect_results")

    rows = []
    missing = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as fh:
            d = json.load(fh)

        model = (d.get("model") or "").rsplit(".", 1)[0] or None
        row = {
            "model": model,
            "run": d.get("run"),
            "split_set": d.get("split_set"),
            "val_mAP50": get(d, "val", "mAP50"),
            "val_mAP50_95": get(d, "val", "mAP50_95"),
            "test_mAP50": get(d, "test", "mAP50"),
            "test_mAP50_95": get(d, "test", "mAP50_95"),
            "classes_evaluated_val": get(d, "val", "classes_evaluated"),
            "classes_evaluated_test": get(d, "test", "classes_evaluated"),
            "params_fused": d.get("params"),
            "gflops": d.get("gflops"),
            "epochs_run": d.get("epochs_completed"),
            "train_time_min": d.get("train_minutes"),
            "latency_source": LATENCY_SOURCE,
        }
        # Latency stays empty. Written explicitly so a reader of this code can
        # see the blanks are chosen, not the result of a lookup that failed.
        for c in LATENCY_COLUMNS:
            row[c] = ""

        for k, v in row.items():
            if v is None:
                missing.append((os.path.basename(p), k))
        rows.append(row)

    # Sort by model then split so the two splits of one model sit adjacent.
    rows.sort(key=lambda r: (str(r["model"]), str(r["split_set"])))

    ec61.write_csv(OUT_CSV, COLUMNS,
                   [[r.get(c, "") if r.get(c) is not None else "" for c in COLUMNS]
                    for r in rows])

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"input_dir": KAGGLE_DIR, "output": OUT_CSV,
                "n_runs": len(rows),
                "latency_policy": "left empty; see docstring",
                "latency_source_value": LATENCY_SOURCE},
        extra={"inputs": {os.path.basename(p): sha256_file(p) for p in paths},
               "missing_fields": ["%s:%s" % (f, k) for f, k in missing]})

    # ---- print ------------------------------------------------------------
    show = ["model", "split_set", "val_mAP50", "val_mAP50_95", "test_mAP50",
            "test_mAP50_95", "classes_evaluated_val", "classes_evaluated_test",
            "params_fused", "gflops", "epochs_run", "train_time_min"]
    head = {"split_set": "split", "val_mAP50": "val@50", "val_mAP50_95": "val@50-95",
            "test_mAP50": "test@50", "test_mAP50_95": "test@50-95",
            "classes_evaluated_val": "cls_val", "classes_evaluated_test": "cls_test",
            "params_fused": "params_fused", "gflops": "gflops",
            "epochs_run": "epochs", "train_time_min": "train_min"}

    def fmt(c, v):
        if v is None or v == "":
            return "-"
        if c == "params_fused":
            return "{:,}".format(v)
        return str(v)

    widths = {}
    for c in show:
        widths[c] = max(len(head.get(c, c)),
                        max(len(fmt(c, r.get(c))) for r in rows))

    line = "  ".join(head.get(c, c).ljust(widths[c]) for c in show)
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(fmt(c, r.get(c)).ljust(widths[c]) for c in show))
    print()
    print("latency columns (%s) are empty; latency_source = %s"
          % (", ".join(LATENCY_COLUMNS), LATENCY_SOURCE))
    print("wrote %s  (%d rows)" % (OUT_CSV, len(rows)))
    if missing:
        print("MISSING FIELDS:")
        for f, k in missing:
            print("  %s -> %s" % (f, k))

    # ---- summary ----------------------------------------------------------
    lines = []
    lines.append("# Master results table")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("Output: `data/master_results.csv` — %d rows from %d input files."
                 % (len(rows), len(paths)))
    lines.append("")
    lines.append("| " + " | ".join(head.get(c, c) for c in show) + " |")
    lines.append("|" + "|".join("---" for _ in show) + "|")
    for r in rows:
        lines.append("| " + " | ".join(fmt(c, r.get(c)) for c in show) + " |")
    lines.append("")
    lines.append("## Latency")
    lines.append("")
    lines.append("All six latency columns are **empty** and `latency_source` is "
                 "`%s`." % LATENCY_SOURCE)
    lines.append("")
    lines.append("The inputs do carry `latency_ms`, `fps` and per-section "
                 "`speed_ms`, and none of it was copied. Those were measured in "
                 "ten separate Kaggle sessions on whatever P100 each was "
                 "allotted, under unknown contention. They cannot support a "
                 "cross-model claim: a 2x gap between two rows could be "
                 "scheduling noise. A unified pass over all ten checkpoints on "
                 "one machine — warmup, `torch.cuda.synchronize()`, p50 and p95, "
                 "batch size stated — is required before these columns are "
                 "filled.")
    lines.append("")
    if missing:
        lines.append("## Missing fields")
        lines.append("")
        for f, k in missing:
            lines.append("- `%s` has no `%s`" % (f, k))
        lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- `params_fused` is copied from the JSON's `params`. The "
                 "inputs do not state whether that count is fused or unfused.")
    lines.append("- `classes_evaluated` is split into val and test columns "
                 "because they differ on the published split (45 vs 46). One "
                 "column would have hidden that.")
    lines.append("- Rows are not comparable across splits by accuracy alone: "
                 "the published split evaluates ~46 of 61 classes, the "
                 "corrected split all 61, so a lower corrected mAP may reflect "
                 "harder coverage rather than a worse model.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
