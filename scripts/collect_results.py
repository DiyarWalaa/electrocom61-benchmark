"""
collect_results.py -- one master table from the Kaggle results JSONs

Reads data/kaggle/results_*.json (ten per-run training results) and
data/kaggle/results_latency_unified.json (one unified timing pass over all ten
checkpoints), joins them on the run slug, and writes data/master_results.csv --
one row per (model, split).

LATENCY NOW COMES FROM THE UNIFIED PASS

Earlier versions of this script left the latency columns empty. They were empty
because the only numbers available were measured inside ten separate Kaggle
sessions, on whatever P100 each was allotted, under unknown contention -- fine
for spotting a regression inside one session, useless for a cross-model claim.
Those per-session `latency_ms`, `fps` and `speed_ms` fields are STILL not read
by this script and never will be.

What is read is results_latency_unified.json, whose protocol block records what
makes it publication-grade: 20 warmup iterations, batch 1, imgsz 640, a
30-image burn-in discarded before the loop, all 205 test images read once so no
timing includes a cold file read, and perf_counter with cuda.synchronize()
around per-image end-to-end predict(). One session, one GPU, all ten models.

FUSED AND UNFUSED ARE NOW SEPARATE COLUMNS

The previous table had a column named `params_fused` fed from the training
JSON's `params`, and a `gflops` column fed from `gflops`. Verification against
known values showed both were UNFUSED counts: 9,451,399 against an expected
9,436,407 for yolo11s, and 110.16 against 105.6 for rtdetr-l. The difference is
BatchNorm folding -- fusing BN into the preceding convolution removes its
parameters and the work of applying it.

The unified JSON measures complexity both before and after model.fuse(), so all
four figures are now carried explicitly and no column is ambiguous:

    params_unfused  gflops_unfused  params_fused  gflops_fused

The training JSONs' own `params` and `gflops` are cross-checked against the
unfused pair rather than emitted, and any disagreement is reported.

layers_fused IS RENAMED layers_modules

The unified JSON's `layers_fused` counts nn.Module objects. Ultralytics' own
model summary prints a "layers" number computed differently, and the two are
not interchangeable. Storing this under the same name would invite a reader to
compare it against a published Ultralytics layer count and conclude something
false, so the column is `layers_modules`.

FIELD MAPPING, STATED

    model            <- results: model (".pt" stripped)
    run              <- results: run              (join key)
    split_set        <- results: split_set
    val_*, test_*    <- results: val.*, test.*
    classes_*        <- results: val/test.classes_evaluated
    epochs_run       <- results: epochs_completed
    train_time_min   <- results: train_minutes
    params_*         <- latency: params_unfused, params_fused
    gflops_*         <- latency: gflops_unfused, gflops_fused
    layers_modules   <- latency: layers_fused
    e2e_ms_p50/p95   <- latency: e2e_ms_p50, e2e_ms_p95
    fps_p50          <- latency: fps_p50
    pre/inf/post_ms  <- latency: pre_ms, inf_ms, post_ms

`classes_evaluated` is two columns because val and test genuinely differ on the
published split -- 45 evaluable in valid against 46 in test. Collapsing them
would erase the finding this study is built on.

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
LATENCY_JSON = os.path.join(KAGGLE_DIR, "results_latency_unified.json")
OUT_CSV = os.path.join(ec61.DATA_DIR, "master_results.csv")

LATENCY_SOURCE = "unified_pass_v3_single_P100_session_committed"

ACCURACY_COLUMNS = ["model", "run", "split_set",
                    "val_mAP50", "val_mAP50_95",
                    "test_mAP50", "test_mAP50_95",
                    "classes_evaluated_val", "classes_evaluated_test",
                    "epochs_run", "train_time_min"]
COMPLEXITY_COLUMNS = ["params_unfused", "gflops_unfused",
                      "params_fused", "gflops_fused", "layers_modules"]
LATENCY_COLUMNS = ["e2e_ms_p50", "e2e_ms_p95", "fps_p50",
                   "pre_ms", "inf_ms", "post_ms"]
COLUMNS = (ACCURACY_COLUMNS + COMPLEXITY_COLUMNS + LATENCY_COLUMNS
           + ["latency_source", "inclusion"])

# GFLOPs are reported to 3 decimals in the unified pass and 2 in the training
# JSONs, so the cross-check allows rounding but nothing more.
GFLOPS_TOLERANCE = 0.01


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def load_latency(path):
    """Index the unified pass by run slug.

    `models` is a LIST of objects each carrying a `run` field, not an object
    keyed by slug, so the index is built rather than assumed.
    """
    with open(path, "r", encoding="utf-8-sig") as fh:
        d = json.load(fh)
    entries = d.get("models", [])
    by_run = {}
    for e in entries:
        if not isinstance(e, dict) or "run" not in e:
            raise ValueError("latency entry without a `run` field: %r" % (e,))
        if e["run"] in by_run:
            raise ValueError("duplicate run slug in latency JSON: %s" % e["run"])
        by_run[e["run"]] = e
    return d, by_run


def main():
    paths = sorted(p for p in glob.glob(os.path.join(KAGGLE_DIR, "results_*.json"))
                   if os.path.basename(p) != os.path.basename(LATENCY_JSON))
    if not paths:
        sys.stderr.write("no per-run results_*.json under %s\n" % KAGGLE_DIR)
        return 1
    if not os.path.isfile(LATENCY_JSON):
        sys.stderr.write("unified latency file not found: %s\n" % LATENCY_JSON)
        return 1

    lat_doc, lat_by_run = load_latency(LATENCY_JSON)

    run_dir = ec61.make_run_dir("collect_results")

    rows = []
    missing = []
    unjoined = []
    complexity_conflicts = []
    # Runs whose training JSON was actually compared against the unified pass.
    # Not every row qualifies: a run with no latency entry has nothing to
    # compare to, so claiming the check covered it would be false.
    crosschecked = []

    for p in paths:
        with open(p, "r", encoding="utf-8-sig") as fh:
            d = json.load(fh)

        run = d.get("run")
        # Declared membership, from ec61.DIVERGED_RUNS. Never inferred from the
        # numbers in this file.
        diverged = run in ec61.DIVERGED_RUNS
        inclusion = (ec61.INCLUSION_DIVERGED if diverged
                     else ec61.INCLUSION_BENCHMARK)

        lat = lat_by_run.get(run)
        # A diverged run has no latency row because the unified timing pass
        # covered the ten benchmark checkpoints and not this one. That is the
        # correct state, not a gap to be reported as a defect.
        if lat is None and not diverged:
            unjoined.append((os.path.basename(p), run))

        row = {
            "model": (d.get("model") or "").rsplit(".", 1)[0] or None,
            "run": run,
            "split_set": d.get("split_set"),
            "val_mAP50": get(d, "val", "mAP50"),
            "val_mAP50_95": get(d, "val", "mAP50_95"),
            "test_mAP50": get(d, "test", "mAP50"),
            "test_mAP50_95": get(d, "test", "mAP50_95"),
            "classes_evaluated_val": get(d, "val", "classes_evaluated"),
            "classes_evaluated_test": get(d, "test", "classes_evaluated"),
            "epochs_run": d.get("epochs_completed"),
            "train_time_min": d.get("train_minutes"),
            "latency_source": LATENCY_SOURCE if lat else "",
            "inclusion": inclusion,
        }
        for c in COMPLEXITY_COLUMNS:
            row[c] = None
        for c in LATENCY_COLUMNS:
            row[c] = None

        if lat:
            row["params_unfused"] = lat.get("params_unfused")
            row["gflops_unfused"] = lat.get("gflops_unfused")
            row["params_fused"] = lat.get("params_fused")
            row["gflops_fused"] = lat.get("gflops_fused")
            # Deliberately renamed: this counts nn.Module objects, which is NOT
            # the "layers" figure Ultralytics prints.
            row["layers_modules"] = lat.get("layers_fused")
            for c in LATENCY_COLUMNS:
                row[c] = lat.get(c)

            # The training JSON's own complexity figures should equal the
            # unified pass's UNFUSED pair. Checked, not assumed -- a mismatch
            # would mean the two files describe different weights.
            crosschecked.append(run)
            tp, tg = d.get("params"), d.get("gflops")
            if tp is not None and lat.get("params_unfused") is not None \
                    and tp != lat["params_unfused"]:
                complexity_conflicts.append(
                    (run, "params", tp, lat["params_unfused"]))
            if tg is not None and lat.get("gflops_unfused") is not None \
                    and abs(tg - lat["gflops_unfused"]) > GFLOPS_TOLERANCE:
                complexity_conflicts.append(
                    (run, "gflops", tg, lat["gflops_unfused"]))

        # Latency and complexity are legitimately absent for a diverged run, so
        # reporting them as missing would train the reader to ignore this list.
        skip = set(COMPLEXITY_COLUMNS + LATENCY_COLUMNS) if diverged else set()
        for k, v in row.items():
            if v is None and k not in skip:
                missing.append((os.path.basename(p), k))
        rows.append(row)

    # `run` is part of the sort key, not decoration: the diverged run shares
    # (model, split_set) with rtdetr_l_pub_lr1e4, so without it the order of
    # those two rows would depend on the glob order of the input directory.
    rows.sort(key=lambda r: (str(r["model"]), str(r["split_set"]), str(r["run"])))

    ec61.write_csv(OUT_CSV, COLUMNS,
                   [["" if r.get(c) is None else r.get(c) for c in COLUMNS]
                    for r in rows])

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"input_dir": KAGGLE_DIR, "latency_json": LATENCY_JSON,
                "output": OUT_CSV, "n_runs": len(rows),
                "latency_source_value": LATENCY_SOURCE,
                "join_key": "run slug",
                "gflops_tolerance": GFLOPS_TOLERANCE},
        extra={"inputs": {os.path.basename(p): sha256_file(p) for p in paths},
               "latency_input_sha256": sha256_file(LATENCY_JSON),
               "latency_protocol": lat_doc.get("protocol", {}),
               "latency_environment": lat_doc.get("environment", {}),
               "unjoined_runs": ["%s:%s" % (f, r) for f, r in unjoined],
               "complexity_conflicts": ["%s %s train=%s unified_unfused=%s"
                                        % c for c in complexity_conflicts],
               "missing_fields": ["%s:%s" % (f, k) for f, k in missing]})

    # ---- print -------------------------------------------------------------
    def fmt(c, v):
        if v is None or v == "":
            return "-"
        if c in ("params_unfused", "params_fused"):
            return "{:,}".format(v)
        return str(v)

    def block(cols, heads, title):
        widths = {c: max(len(heads.get(c, c)),
                         max(len(fmt(c, r.get(c))) for r in rows)) for c in cols}
        line = "  ".join(heads.get(c, c).ljust(widths[c]) for c in cols)
        print(title)
        print(line)
        print("-" * len(line))
        for r in rows:
            print("  ".join(fmt(c, r.get(c)).ljust(widths[c]) for c in cols))
        print()

    h1 = {"split_set": "split", "val_mAP50": "val@50", "val_mAP50_95": "val@50-95",
          "test_mAP50": "test@50", "test_mAP50_95": "test@50-95",
          "classes_evaluated_val": "cls_val", "classes_evaluated_test": "cls_test",
          "epochs_run": "epochs", "train_time_min": "train_min"}
    h2 = {"params_unfused": "params_unfused", "gflops_unfused": "gflops_unf",
          "params_fused": "params_fused", "gflops_fused": "gflops_fused",
          "layers_modules": "layers_mod"}
    h3 = {"e2e_ms_p50": "p50_ms", "e2e_ms_p95": "p95_ms", "fps_p50": "fps",
          "pre_ms": "pre_ms", "inf_ms": "inf_ms", "post_ms": "post_ms"}

    block(["model", "split_set", "val_mAP50", "val_mAP50_95", "test_mAP50",
           "test_mAP50_95", "classes_evaluated_val", "classes_evaluated_test",
           "epochs_run", "train_time_min"], h1,
          "MASTER TABLE (1/3) -- accuracy")
    block(["model", "split_set"] + COMPLEXITY_COLUMNS, h2,
          "MASTER TABLE (2/3) -- complexity")
    block(["model", "split_set"] + LATENCY_COLUMNS, h3,
          "MASTER TABLE (3/3) -- latency, unified pass")

    print("latency_source = %s" % LATENCY_SOURCE)
    print("wrote %s  (%d rows, %d columns)" % (OUT_CSV, len(rows), len(COLUMNS)))
    if unjoined:
        print("UNJOINED RUNS (no latency row):")
        for f, r in unjoined:
            print("  %s -> %r" % (f, r))
    if complexity_conflicts:
        print("COMPLEXITY CONFLICTS (training JSON vs unified unfused):")
        for run, field, a, b in complexity_conflicts:
            print("  %-20s %-7s train=%s  unified=%s" % (run, field, a, b))
    else:
        print("complexity cross-check: training JSONs agree with the unified "
              "unfused figures on all %d runs that have one" % len(crosschecked))
    if missing:
        print("MISSING FIELDS:")
        for f, k in missing:
            print("  %s -> %s" % (f, k))

    # ---- summary -----------------------------------------------------------
    lines = []
    lines.append("# Master results table")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("`data/master_results.csv` — %d rows, %d columns, from %d "
                 "per-run files joined to the unified latency pass on the run "
                 "slug." % (len(rows), len(COLUMNS), len(paths)))
    lines.append("")
    for title, cols, heads in [
            ("Accuracy", ["model", "split_set", "val_mAP50", "val_mAP50_95",
                          "test_mAP50", "test_mAP50_95", "classes_evaluated_val",
                          "classes_evaluated_test", "epochs_run",
                          "train_time_min"], h1),
            ("Complexity", ["model", "split_set"] + COMPLEXITY_COLUMNS, h2),
            ("Latency (unified pass)", ["model", "split_set"] + LATENCY_COLUMNS, h3)]:
        lines.append("## %s" % title)
        lines.append("")
        lines.append("| " + " | ".join(heads.get(c, c) for c in cols) + " |")
        lines.append("|" + "|".join("---" for _ in cols) + "|")
        for r in rows:
            lines.append("| " + " | ".join(fmt(c, r.get(c)) for c in cols) + " |")
        lines.append("")
    lines.append("## Latency provenance")
    lines.append("")
    lines.append("`latency_source` = `%s`" % LATENCY_SOURCE)
    lines.append("")
    for k, v in sorted(lat_doc.get("protocol", {}).items()):
        lines.append("- **%s**: %s" % (k, v))
    lines.append("")
    lines.append("The per-run JSONs' own `latency_ms`, `fps` and `speed_ms` "
                 "fields are still not read. They were measured in ten separate "
                 "sessions under unknown contention and cannot support a "
                 "cross-model claim.")
    lines.append("")
    lines.append("## Complexity cross-check")
    lines.append("")
    if complexity_conflicts:
        lines.append("**%d conflicts** between the training JSONs and the "
                     "unified pass's unfused figures:" % len(complexity_conflicts))
        lines.append("")
        for run, field, a, b in complexity_conflicts:
            lines.append("- `%s` %s: training %s, unified unfused %s"
                         % (run, field, a, b))
    else:
        lines.append("The training JSONs' `params` and `gflops` agree with the "
                     "unified pass's `params_unfused` and `gflops_unfused` on "
                     "all %d runs carrying both (GFLOPs to within %.2f, the "
                     "reporting precision). The two files describe the same "
                     "weights." % (len(crosschecked), GFLOPS_TOLERANCE))
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- `layers_modules` counts nn.Module objects and is NOT the "
                 "\"layers\" figure Ultralytics prints. Do not compare it "
                 "against a published layer count.")
    lines.append("- Rows are not comparable across splits by accuracy alone: "
                 "the published split evaluates ~46 of 61 classes, the "
                 "corrected split all 61, so a lower corrected mAP may reflect "
                 "harder coverage rather than a worse model.")
    lines.append("- Latency was measured on one Tesla P100. Ranking may not "
                 "hold on other hardware, and transformer and CNN detectors do "
                 "not scale alike across GPUs.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
