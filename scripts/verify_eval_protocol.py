"""
verify_eval_protocol.py -- verify the evaluation-protocol claims for section 5.4

Four claims, each checked against a source that does not depend on the others:

  1. ten training runs, twenty evaluations
  2. 45 classes evaluated on validation and 46 on test under the published
     split; 61 on both under the corrected split
  3. ESP32 is exactly the class that accounts for the 45-vs-46 difference,
     with two test instances and none in validation
  4. what the ten args.yaml record for conf, iou and max_det, and whether
     those values are identical across all ten runs

WHY CLAIM 3 IS DERIVED RATHER THAN LOOKED UP

It would be easy to grep for ESP32 and report that it appears under test but
not val. That confirms ESP32 is *a* class in the difference, not that it is the
*only* one. The difference set is therefore computed from scratch for every
published run -- test classes minus val classes -- and the claim passes only if
that set is exactly {ESP32} in all five. A second class would make 45-vs-46
arithmetic that happens to work while the explanation is wrong.

WHAT args.yaml IS, AND IS NOT

Each artifacts/<run>/<run>_args.yaml is the argument snapshot Ultralytics
writes for a run whose `mode` is `train`. Its conf/iou/max_det are the values
that sat in the training configuration. They are NOT a record of the arguments
passed to the separate end-of-run validation and test passes -- no args.yaml is
emitted for those. This script reports what the files contain and states the
mode, so the distinction survives into whatever is written from it.

Run with no arguments:

    python scripts/verify_eval_protocol.py

Writes runs/<YYYYMMDD>_verify_eval_protocol/.
"""

import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


MASTER_CSV = os.path.join(ec61.DATA_DIR, "master_results.csv")
KAGGLE_DIR = os.path.join(ec61.DATA_DIR, "kaggle")
ARTIFACTS = os.path.join(KAGGLE_DIR, "artifacts")
CLASS_COUNTS = os.path.join(ec61.RUNS_DIR, "20260802_class_date_provenance",
                            "class_split_counts.csv")


def find_args_yaml(run):
    """Locate a run's args.yaml across the two artifact layouts in this repo.

    Eight runs were extracted flattened, with every file prefixed by the run
    slug. The two yolov9s runs kept Kaggle's original tree instead -- their
    zips are the ones named `_artifacts_loose.zip` -- so their args.yaml sits
    unprefixed at runs/<run>/args.yaml. Checking only the flat form silently
    drops two of the ten, which would turn "identical across all ten runs"
    into a claim about eight.
    """
    for cand in (os.path.join(ARTIFACTS, run, "%s_args.yaml" % run),
                 os.path.join(ARTIFACTS, run, "runs", run, "args.yaml")):
        if os.path.isfile(cand):
            return cand
    return None


def per_class_from_json(run):
    """Class name -> AP, for val and test, from the committed results JSON.

    This is the source used for the class-difference check because it exists
    for all ten runs. The per-run per_class.csv covers only the eight
    flattened runs and is used as a cross-check, not as the basis.
    """
    path = os.path.join(KAGGLE_DIR, "results_%s.json" % run)
    if not os.path.isfile(path):
        return None, path
    with io.open(path, encoding="utf-8-sig") as fh:
        d = json.load(fh)
    out = {}
    for split in ("val", "test"):
        block = d.get(split) or {}
        out[split] = set((block.get("per_class_AP50_95") or {}).keys())
    return out, path

# The three validation thresholds section 5.4 wants to state explicitly.
THRESHOLD_KEYS = ["conf", "iou", "max_det"]

EXPECTED = {"n_runs": 10, "n_evaluations": 20,
            "published_val": 45, "published_test": 46,
            "corrected_val": 61, "corrected_test": 61,
            "esp32_valid_instances": 0, "esp32_test_instances": 2}


def read_csv(path):
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_flat_yaml(path):
    """Read the top-level `key: value` pairs of an Ultralytics args.yaml.

    These files are flat -- no nesting, no lists, no multi-line strings -- so a
    line parser is enough and avoids adding a YAML dependency. Values are
    returned as strings exactly as written; `null` is preserved rather than
    coerced, because "unset" is itself the finding for `conf`.
    """
    out = {}
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line[0].isspace():          # a nested key; these files have none
                continue
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    problems = []
    notes = []

    for p in (MASTER_CSV, CLASS_COUNTS):
        if not os.path.isfile(p):
            sys.stderr.write("missing input: %s\n" % p)
            return 1

    run_dir = ec61.make_run_dir("verify_eval_protocol")
    rows = read_csv(MASTER_CSV)

    # ---- claim 1: ten runs, twenty evaluations -----------------------------
    n_runs = len(rows)
    if n_runs != EXPECTED["n_runs"]:
        problems.append("master_results.csv has %d rows, expected %d"
                        % (n_runs, EXPECTED["n_runs"]))

    # Twenty evaluations is 10 x 2 ONLY if every run really produced both a
    # validation and a test evaluation, each with both mAP figures. Counted,
    # not multiplied.
    n_eval = 0
    for r in rows:
        for split in ("val", "test"):
            a = r.get("%s_mAP50" % split, "")
            b = r.get("%s_mAP50_95" % split, "")
            if a not in ("", None) and b not in ("", None):
                n_eval += 1
            else:
                problems.append("run %s: %s evaluation missing mAP50 or "
                                "mAP50-95" % (r.get("run"), split))
    if n_eval != EXPECTED["n_evaluations"]:
        problems.append("counted %d complete evaluations, expected %d"
                        % (n_eval, EXPECTED["n_evaluations"]))

    # ---- claim 2: classes evaluated per split ------------------------------
    by_split = {}
    for r in rows:
        by_split.setdefault(r["split_set"], []).append(r)

    class_counts = {}
    for split_set, rs in sorted(by_split.items()):
        vals = set(r["classes_evaluated_val"] for r in rs)
        tests = set(r["classes_evaluated_test"] for r in rs)
        # Unanimity matters: a single disagreeing run would be invisible in a
        # mean but fatal to the claim.
        if len(vals) != 1 or len(tests) != 1:
            problems.append("%s split: runs disagree on classes evaluated "
                            "(val=%s, test=%s)" % (split_set, sorted(vals),
                                                   sorted(tests)))
        class_counts[split_set] = {"val": sorted(vals), "test": sorted(tests),
                                   "n_runs": len(rs)}
        for which, got in (("val", vals), ("test", tests)):
            key = "%s_%s" % (split_set, which)
            if key in EXPECTED and got == {str(EXPECTED[key])}:
                pass
            elif key in EXPECTED:
                problems.append("%s: got %s, expected %d"
                                % (key, sorted(got), EXPECTED[key]))

    # ---- claim 3: ESP32 accounts for the difference ------------------------
    diff_by_run = {}
    json_inputs = {}
    for r in rows:
        if r["split_set"] != "published":
            continue
        run = r["run"]
        seen, jpath = per_class_from_json(run)
        if seen is None:
            problems.append("results JSON not found for %s (%s)" % (run, jpath))
            continue
        json_inputs[run] = jpath
        diff_by_run[run] = {
            "n_val": len(seen["val"]),
            "n_test": len(seen["test"]),
            "test_not_val": sorted(seen["test"] - seen["val"]),
            "val_not_test": sorted(seen["val"] - seen["test"]),
            "csv_crosscheck": "absent",
        }

        # Independent cross-check against the derived per-class CSV, where the
        # layout provides one. Disagreement would mean the CSV and the JSON
        # describe different evaluations.
        pc = os.path.join(ARTIFACTS, run, "%s_per_class.csv" % run)
        if os.path.isfile(pc):
            csv_seen = {"val": set(), "test": set()}
            for row in read_csv(pc):
                if row["split"] in csv_seen:
                    csv_seen[row["split"]].add(row["class"])
            same = (csv_seen["val"] == seen["val"]
                    and csv_seen["test"] == seen["test"])
            diff_by_run[run]["csv_crosscheck"] = "agrees" if same else "DIFFERS"
            if not same:
                problems.append("%s: per_class.csv disagrees with the results "
                                "JSON on which classes were evaluated" % run)

    for run, d in sorted(diff_by_run.items()):
        if d["test_not_val"] != ["ESP32"]:
            problems.append("%s: classes in test but not val = %s, expected "
                            "exactly ['ESP32']" % (run, d["test_not_val"]))
        if d["val_not_test"]:
            problems.append("%s: classes in val but not test = %s, expected "
                            "none" % (run, d["val_not_test"]))

    esp = [r for r in read_csv(CLASS_COUNTS) if r["class_name"] == "ESP32"]
    esp_row = esp[0] if esp else None
    if esp_row is None:
        problems.append("ESP32 not found in %s" % CLASS_COUNTS)
    else:
        for field, key in (("inst_valid", "esp32_valid_instances"),
                           ("inst_test", "esp32_test_instances")):
            if int(esp_row[field]) != EXPECTED[key]:
                problems.append("ESP32 %s = %s, expected %d"
                                % (field, esp_row[field], EXPECTED[key]))
        # ESP32-CAM is a DIFFERENT class and is evaluated normally. Recorded
        # here because the two names differ by a suffix and are easy to
        # conflate when reading a per-class table.
        cam = [r for r in read_csv(CLASS_COUNTS)
               if r["class_name"] == "ESP32-CAM"]
        if cam:
            notes.append("ESP32-CAM is a separate class: %s train / %s valid "
                         "/ %s test instances, evaluated on both splits."
                         % (cam[0]["inst_train"], cam[0]["inst_valid"],
                            cam[0]["inst_test"]))

    # ---- claim 4: validation thresholds ------------------------------------
    thresholds = {}
    args_paths = {}
    for r in rows:
        run = r["run"]
        ay = find_args_yaml(run)
        if ay is None:
            problems.append("args.yaml not found for %s in either layout" % run)
            continue
        args_paths[run] = ay
        d = parse_flat_yaml(ay)
        thresholds[run] = dict([(k, d.get(k, "<absent>")) for k in THRESHOLD_KEYS]
                               + [("mode", d.get("mode", "<absent>")),
                                  ("split", d.get("split", "<absent>"))])

    agreement = {}
    for k in THRESHOLD_KEYS + ["mode", "split"]:
        vals = sorted(set(t[k] for t in thresholds.values()))
        agreement[k] = {"values": vals, "identical": len(vals) == 1}

    modes = agreement["mode"]["values"]
    if modes != ["train"]:
        notes.append("args.yaml mode is not uniformly `train`: %s" % modes)

    # ---- write outputs -----------------------------------------------------
    ec61.write_csv(
        os.path.join(run_dir, "thresholds_by_run.csv"),
        ["run", "mode", "split"] + THRESHOLD_KEYS,
        [[run, t["mode"], t["split"]] + [t[k] for k in THRESHOLD_KEYS]
         for run, t in sorted(thresholds.items())])

    ec61.write_csv(
        os.path.join(run_dir, "class_difference_by_run.csv"),
        ["run", "n_val", "n_test", "test_not_val", "val_not_test"],
        [[run, d["n_val"], d["n_test"], "|".join(d["test_not_val"]),
          "|".join(d["val_not_test"])] for run, d in sorted(diff_by_run.items())])

    inputs = {os.path.relpath(MASTER_CSV, ec61.REPO_ROOT): ec61._sha256_file(MASTER_CSV),
              os.path.relpath(CLASS_COUNTS, ec61.REPO_ROOT): ec61._sha256_file(CLASS_COUNTS)}
    for p in list(args_paths.values()) + list(json_inputs.values()):
        inputs[os.path.relpath(p, ec61.REPO_ROOT)] = ec61._sha256_file(p)

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"master_csv": MASTER_CSV, "class_counts_csv": CLASS_COUNTS,
                "artifacts_dir": ARTIFACTS, "threshold_keys": THRESHOLD_KEYS,
                "expected": EXPECTED},
        extra={"inputs": inputs,
               "n_runs": n_runs, "n_evaluations": n_eval,
               "classes_evaluated": class_counts,
               "class_difference_by_run": diff_by_run,
               "esp32": esp_row, "thresholds": thresholds,
               "threshold_agreement": agreement,
               "problems": problems, "notes": notes})

    # ---- print -------------------------------------------------------------
    print("CLAIM 1  ten runs, twenty evaluations")
    print("  runs in master_results.csv : %d" % n_runs)
    print("  complete evaluations       : %d  (each = both mAP50 and mAP50-95)"
          % n_eval)
    print()
    print("CLAIM 2  classes evaluated per split")
    for split_set in sorted(class_counts):
        c = class_counts[split_set]
        print("  %-10s val %s   test %s   (%d runs, unanimous: %s)"
              % (split_set, ",".join(c["val"]), ",".join(c["test"]),
                 c["n_runs"], len(c["val"]) == 1 and len(c["test"]) == 1))
    print()
    print("CLAIM 3  ESP32 accounts for the 45-vs-46 difference")
    for run, d in sorted(diff_by_run.items()):
        print("  %-20s val %2d  test %2d  test-not-val %-8s val-not-test %-4s "
              "csv %s"
              % (run, d["n_val"], d["n_test"],
                 ",".join(d["test_not_val"]) or "-",
                 ",".join(d["val_not_test"]) or "-", d["csv_crosscheck"]))
    if esp_row:
        print("  ESP32 instances: train %s / valid %s / test %s   "
              "images: train %s / valid %s / test %s"
              % (esp_row["inst_train"], esp_row["inst_valid"],
                 esp_row["inst_test"], esp_row["imgs_train"],
                 esp_row["imgs_valid"], esp_row["imgs_test"]))
    print()
    print("CLAIM 4  validation thresholds recorded in args.yaml")
    print("  (%d of %d args.yaml found; two runs use the unflattened layout)"
          % (len(thresholds), n_runs))
    print("  %-20s %-7s %-7s %-8s %-8s %s"
          % ("run", "mode", "split", "conf", "iou", "max_det"))
    for run, t in sorted(thresholds.items()):
        print("  %-20s %-7s %-7s %-8s %-8s %s"
              % (run, t["mode"], t["split"], t["conf"], t["iou"], t["max_det"]))
    print()
    for k in THRESHOLD_KEYS:
        a = agreement[k]
        print("  %-8s identical across all %d runs: %-5s  value(s): %s"
              % (k, len(thresholds), a["identical"], ", ".join(a["values"])))
    print()
    if notes:
        print("NOTES")
        for n in notes:
            print("  - %s" % n)
        print()
    if problems:
        print("PROBLEMS (%d)" % len(problems))
        for p in problems:
            print("  - %s" % p)
    else:
        print("All four claims verified.")
    print()
    print("wrote %s" % run_dir)

    # ---- summary -----------------------------------------------------------
    L = []
    L.append("# Evaluation-protocol verification (section 5.4)")
    L.append("")
    L.append("Run directory: `%s`" % os.path.basename(run_dir))
    L.append("")
    L.append("## 1. Ten runs, twenty evaluations")
    L.append("")
    L.append("`master_results.csv` has **%d rows**. Every row carries mAP@50 "
             "and mAP@50-95 for both validation and test, giving **%d complete "
             "evaluations**. The count is taken from the presence of all four "
             "figures per run, not from multiplying by two." % (n_runs, n_eval))
    L.append("")
    L.append("## 2. Classes evaluated")
    L.append("")
    L.append("| split | classes on val | classes on test | runs | unanimous |")
    L.append("|---|---|---|---|---|")
    for split_set in sorted(class_counts):
        c = class_counts[split_set]
        L.append("| %s | %s | %s | %d | %s |"
                 % (split_set, ",".join(c["val"]), ",".join(c["test"]),
                    c["n_runs"], len(c["val"]) == 1 and len(c["test"]) == 1))
    L.append("")
    L.append("## 3. ESP32")
    L.append("")
    L.append("For each of the %d published-split runs, the set of classes "
             "appearing in the test per-class table minus those appearing in "
             "the validation table:" % len(diff_by_run))
    L.append("")
    L.append("| run | val | test | test - val | val - test |")
    L.append("|---|---|---|---|---|")
    for run, d in sorted(diff_by_run.items()):
        L.append("| `%s` | %d | %d | %s | %s |"
                 % (run, d["n_val"], d["n_test"],
                    ", ".join(d["test_not_val"]) or "(none)",
                    ", ".join(d["val_not_test"]) or "(none)"))
    L.append("")
    if esp_row:
        L.append("ESP32 instance counts from `class_split_counts.csv`: "
                 "**%s train, %s valid, %s test** across %s / %s / %s images."
                 % (esp_row["inst_train"], esp_row["inst_valid"],
                    esp_row["inst_test"], esp_row["imgs_train"],
                    esp_row["imgs_valid"], esp_row["imgs_test"]))
    L.append("")
    L.append("## 4. Validation thresholds")
    L.append("")
    L.append("| run | mode | split | conf | iou | max_det |")
    L.append("|---|---|---|---|---|---|")
    for run, t in sorted(thresholds.items()):
        L.append("| `%s` | %s | %s | %s | %s | %s |"
                 % (run, t["mode"], t["split"], t["conf"], t["iou"],
                    t["max_det"]))
    L.append("")
    for k in THRESHOLD_KEYS:
        a = agreement[k]
        L.append("- **%s**: %s across all %d runs; value(s) `%s`"
                 % (k, "identical" if a["identical"] else "NOT identical",
                    len(thresholds), "`, `".join(a["values"])))
    L.append("")
    L.append("## What could make this misleading")
    L.append("")
    L.append("- **These args.yaml describe `mode: train`.** They are the "
             "argument snapshot of the training run. Ultralytics writes no "
             "args.yaml for the end-of-run validation and test passes, so "
             "these files are evidence of what was configured, not a record "
             "of what those passes were called with.")
    L.append("- **`conf: null` means unset, not zero.** Ultralytics resolves "
             "it at runtime by mode, and the value it resolves to in "
             "validation is not written to any file in this repository. "
             "Quoting `null` as though it were a threshold would state the "
             "opposite of what the file says.")
    L.append("- The class difference is computed from per-class tables, which "
             "list a class only when it has ground-truth instances in that "
             "split. A class present but never predicted still appears; a "
             "class with no instances does not.")
    L.append("- ESP32 and ESP32-CAM are different classes whose names differ "
             "by a suffix.")
    L.append("")
    with io.open(os.path.join(run_dir, "summary.md"), "w",
                 encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
