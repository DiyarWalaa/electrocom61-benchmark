"""
verify_diverged_run.py -- verify the recovered RT-DETR-l divergence (5.3)

The run is rtdetr_l_pub: RT-DETR-l on the published split at lr0 = 0.01, the
learning rate both prior studies state for their YOLO models. It is the
evidence behind the learning-rate deviation described in section 5.3, and is
marked `diverged` in master_results.csv so it can never be aggregated with the
benchmark.

Two things are checked:

  1. the summary figures in results_rtdetr_l_pub.json -- best epoch, stopping
     epoch, wall-clock minutes, and both mAP figures on both partitions with
     the class counts they were computed over

  2. the per-epoch behaviour in rtdetr_l_pub_training_curves.csv -- the exact
     epoch at which EACH loss term first became NaN, reported separately

WHY EACH LOSS TERM IS REPORTED SEPARATELY

Three loss terms going NaN in the same epoch is a claim, not a given. They are
computed from different quantities and could fail independently -- an L1 term
diverging several epochs before a classification term would describe a
different failure. The script therefore finds the first NaN epoch per column
and never assumes the answer is shared.

There are SIX loss columns, not three: giou, cls and l1 are recorded for both
the training and the validation pass. They do not behave alike, and reporting
only the training three would omit that.

WHY "REMAINED NaN" IS CHECKED RATHER THAN ASSUMED

A first-NaN epoch says nothing about what followed. A term that went NaN and
recovered would not be divergence. So for every column the script also records
which epochs after the first NaN were finite -- ideally none.

Run with no arguments:

    python scripts/verify_diverged_run.py

Writes runs/<YYYYMMDD>_verify_diverged_run/.
"""

import csv
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


RUN = "rtdetr_l_pub"
JSON_PATH = os.path.join(ec61.DATA_DIR, "kaggle", "results_%s.json" % RUN)
CURVES = os.path.join(ec61.DATA_DIR, "kaggle", "artifacts", RUN,
                      "%s_training_curves.csv" % RUN)

# Ultralytics selects best.pt by this weighted sum, not by mAP@50 alone.
FITNESS = lambda m50, m5095: 0.1 * m50 + 0.9 * m5095  # noqa: E731

CLAIMED = {
    "best_epoch": 4,
    "stopped_at": 19,
    "train_minutes": 43.7,
    "val_mAP50": 0.0039, "val_mAP50_95": 0.0016, "val_classes": 45,
    "test_mAP50": 0.0057, "test_mAP50_95": 0.0026, "test_classes": 46,
    "first_nan_epoch": 7,
}


def is_nan(s):
    s = (s or "").strip()
    if s.lower().lstrip("+-") == "nan":
        return True
    try:
        return math.isnan(float(s))
    except ValueError:
        return False


def main():
    for p in (JSON_PATH, CURVES):
        if not os.path.isfile(p):
            sys.stderr.write("missing input: %s\n" % p)
            return 1

    run_dir = ec61.make_run_dir("verify_diverged_run")
    problems = []
    notes = []

    with io.open(JSON_PATH, encoding="utf-8-sig") as fh:
        d = json.load(fh)
    rows = list(csv.DictReader(io.open(CURVES, encoding="utf-8-sig")))

    # ---- 1. summary figures ------------------------------------------------
    checks = [
        ("stopped at epoch", d.get("epochs_completed"), CLAIMED["stopped_at"]),
        ("training minutes", d.get("train_minutes"), CLAIMED["train_minutes"]),
        ("val mAP@50", d["val"]["mAP50"], CLAIMED["val_mAP50"]),
        ("val mAP@50-95", d["val"]["mAP50_95"], CLAIMED["val_mAP50_95"]),
        ("val classes evaluated", d["val"]["classes_evaluated"],
         CLAIMED["val_classes"]),
        ("test mAP@50", d["test"]["mAP50"], CLAIMED["test_mAP50"]),
        ("test mAP@50-95", d["test"]["mAP50_95"], CLAIMED["test_mAP50_95"]),
        ("test classes evaluated", d["test"]["classes_evaluated"],
         CLAIMED["test_classes"]),
    ]
    for label, got, want in checks:
        if got != want:
            problems.append("%s: file has %r, claimed %r" % (label, got, want))

    # The JSON carries no best_epoch field, so it is derived the way
    # Ultralytics derives it and cross-checked against the patience rule.
    fit = [(int(r["epoch"]),
            FITNESS(float(r["metrics/mAP50(B)"]),
                    float(r["metrics/mAP50-95(B)"]))) for r in rows]
    best_epoch, best_fit = max(fit, key=lambda t: t[1])
    if best_epoch != CLAIMED["best_epoch"]:
        problems.append("best epoch by fitness is %d, claimed %d"
                        % (best_epoch, CLAIMED["best_epoch"]))
    patience = d.get("patience")
    last_epoch = int(rows[-1]["epoch"])
    if patience is not None and best_epoch + patience != last_epoch:
        notes.append("best epoch %d + patience %s != last epoch %d"
                     % (best_epoch, patience, last_epoch))
    else:
        notes.append("best epoch %d + patience %s = last epoch %d, so the "
                     "stopping epoch corroborates the best epoch independently"
                     % (best_epoch, patience, last_epoch))

    # ---- 2. per-column NaN onset -------------------------------------------
    loss_cols = [c for c in rows[0] if c.endswith("_loss")]
    onset = {}
    for c in loss_cols:
        first = None
        finite_after = []
        for r in rows:
            e = int(r["epoch"])
            if is_nan(r[c]):
                if first is None:
                    first = e
            elif first is not None:
                finite_after.append(e)
        onset[c] = {"first_nan_epoch": first, "finite_epochs_after": finite_after}

    train_cols = sorted(c for c in loss_cols if c.startswith("train/"))
    val_cols = sorted(c for c in loss_cols if c.startswith("val/"))

    train_onsets = set(onset[c]["first_nan_epoch"] for c in train_cols)
    if train_onsets != {CLAIMED["first_nan_epoch"]}:
        problems.append("training loss terms first go NaN at %s, claimed all "
                        "at %d" % (sorted(train_onsets),
                                   CLAIMED["first_nan_epoch"]))
    for c in train_cols:
        if onset[c]["finite_epochs_after"]:
            problems.append("%s recovers to finite at epochs %s -- not a "
                            "monotone divergence"
                            % (c, onset[c]["finite_epochs_after"]))

    # The validation losses are the finding the prose does not describe.
    val_onsets = sorted(set(onset[c]["first_nan_epoch"] for c in val_cols))
    if val_onsets and val_onsets != [CLAIMED["first_nan_epoch"]]:
        notes.append("the VALIDATION loss terms first go NaN at epoch %s, "
                     "well before the training terms at %d, and recover at "
                     "epochs %s. Any claim covering 'its three loss terms' "
                     "without saying which pass is at best ambiguous."
                     % (val_onsets, CLAIMED["first_nan_epoch"],
                        sorted(set(tuple(onset[c]["finite_epochs_after"])
                                   for c in val_cols))[0]))

    # ---- 3. mAP after divergence -------------------------------------------
    zero_epochs = [int(r["epoch"]) for r in rows
                   if float(r["metrics/mAP50(B)"]) == 0.0]
    after = [e for e in zero_epochs if e >= CLAIMED["first_nan_epoch"]]
    expected_after = list(range(CLAIMED["first_nan_epoch"], last_epoch + 1))
    if after != expected_after:
        problems.append("mAP@50 is not exactly zero for every epoch from %d "
                        "to %d; zero at %s"
                        % (CLAIMED["first_nan_epoch"], last_epoch, after))
    before = [e for e in zero_epochs if e < CLAIMED["first_nan_epoch"]]
    if before:
        notes.append("mAP@50 is ALSO exactly zero at epoch(s) %s, before "
                     "divergence. Zero mAP is therefore not exclusive to the "
                     "post-divergence regime, and cannot on its own be used "
                     "to date the divergence." % before)

    # ---- outputs -----------------------------------------------------------
    ec61.write_csv(
        os.path.join(run_dir, "nan_onset_by_column.csv"),
        ["column", "pass", "first_nan_epoch", "finite_epochs_after"],
        [[c, c.split("/")[0], onset[c]["first_nan_epoch"],
          "|".join(str(e) for e in onset[c]["finite_epochs_after"])]
         for c in sorted(loss_cols)])

    ec61.write_csv(
        os.path.join(run_dir, "per_epoch.csv"),
        ["epoch"] + sorted(loss_cols) + ["mAP50", "mAP50_95", "fitness"],
        [[r["epoch"]] + [r[c] for c in sorted(loss_cols)]
         + [r["metrics/mAP50(B)"], r["metrics/mAP50-95(B)"],
            round(FITNESS(float(r["metrics/mAP50(B)"]),
                          float(r["metrics/mAP50-95(B)"])), 8)]
         for r in rows])

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"run": RUN, "json": JSON_PATH, "curves": CURVES,
                "claimed": CLAIMED,
                "fitness": "0.1*mAP50 + 0.9*mAP50-95 (Ultralytics)"},
        extra={"inputs": {os.path.relpath(p, ec61.REPO_ROOT):
                          ec61._sha256_file(p) for p in (JSON_PATH, CURVES)},
               "derived_best_epoch": best_epoch,
               "derived_best_fitness": best_fit,
               "lr0": d.get("lr0"), "seed": d.get("seed"),
               "status_field": d.get("status"),
               "gpu": d.get("gpu"), "ultralytics": d.get("ultralytics"),
               "torch": d.get("torch"),
               "nan_onset": onset, "zero_map_epochs": zero_epochs,
               "problems": problems, "notes": notes})

    # ---- print -------------------------------------------------------------
    print("RUN %s  lr0=%s  seed=%s  status=%s" % (RUN, d.get("lr0"),
                                                  d.get("seed"), d.get("status")))
    print("  %s / ultralytics %s / torch %s"
          % (d.get("gpu"), d.get("ultralytics"), d.get("torch")))
    print()
    print("1  SUMMARY FIGURES")
    for label, got, want in checks:
        print("   [%s] %-24s file=%-9s claimed=%s"
              % ("PASS" if got == want else "FAIL", label, got, want))
    print("   [%s] %-24s derived=%-9s claimed=%s   (fitness %.8f)"
          % ("PASS" if best_epoch == CLAIMED["best_epoch"] else "FAIL",
             "best epoch", best_epoch, CLAIMED["best_epoch"], best_fit))
    print()
    print("2  FIRST NaN EPOCH, PER LOSS COLUMN")
    for c in sorted(loss_cols):
        o = onset[c]
        print("   %-18s first NaN epoch %-6s finite after: %s"
              % (c, o["first_nan_epoch"],
                 ", ".join(str(e) for e in o["finite_epochs_after"]) or "none"))
    print()
    print("3  VALIDATION mAP@50")
    print("   exactly zero at epochs: %s"
          % ", ".join(str(e) for e in zero_epochs))
    print("   epochs %d..%d all zero: %s"
          % (CLAIMED["first_nan_epoch"], last_epoch, after == expected_after))
    print()
    if notes:
        print("NOTES")
        for n in notes:
            print("   - %s" % n)
        print()
    if problems:
        print("PROBLEMS (%d)" % len(problems))
        for p in problems:
            print("   - %s" % p)
    else:
        print("Every claimed figure matches the committed files.")
    print()
    print("wrote %s" % run_dir)

    # ---- summary -----------------------------------------------------------
    L = ["# Diverged run: %s" % RUN, "",
         "Run directory: `%s`" % os.path.basename(run_dir), "",
         "RT-DETR-l on the published split at **lr0 = %s**, seed %s, %s. "
         "Marked `diverged` in `master_results.csv`; never aggregated with the "
         "benchmark." % (d.get("lr0"), d.get("seed"), d.get("gpu")), "",
         "## Summary figures", "",
         "| quantity | file | claimed | |", "|---|---|---|---|"]
    for label, got, want in checks:
        L.append("| %s | `%s` | `%s` | %s |"
                 % (label, got, want, "PASS" if got == want else "**FAIL**"))
    L.append("| best epoch (derived) | `%d` | `%d` | %s |"
             % (best_epoch, CLAIMED["best_epoch"],
                "PASS" if best_epoch == CLAIMED["best_epoch"] else "**FAIL**"))
    L += ["", "The JSON carries no `best_epoch` field. It is derived as the "
          "argmax of Ultralytics fitness (0.1*mAP@50 + 0.9*mAP@50-95) over the "
          "training curve.", "",
          "## First NaN epoch, per loss column", "",
          "| column | pass | first NaN | finite epochs after |",
          "|---|---|---|---|"]
    for c in sorted(loss_cols):
        o = onset[c]
        L.append("| `%s` | %s | %s | %s |"
                 % (c, c.split("/")[0], o["first_nan_epoch"],
                    ", ".join(str(e) for e in o["finite_epochs_after"])
                    or "none"))
    L += ["", "## Notes", ""]
    for n in notes:
        L.append("- %s" % n)
    L += ["", "## What could make this misleading", "",
          "- `status: complete` in the JSON means the run finished without "
          "raising, NOT that it succeeded. It completed uselessly.",
          "- The reported mAP figures come from a separate validation pass on "
          "`best.pt` (epoch %d), not from the training curve row for that "
          "epoch, so the two differ slightly and neither is wrong."
          % best_epoch,
          "- Latency and complexity columns are empty for this run because the "
          "unified timing pass covered the ten benchmark checkpoints only.", ""]
    with io.open(os.path.join(run_dir, "summary.md"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
