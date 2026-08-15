"""
fix_rtdetr_corr_label.py -- correct one mislabelled field, traceably

THE DEFECT

data/kaggle/results_rtdetr_l_corr.json carries "split_set": "published", but
the run it describes was trained and evaluated on the CORRECTED split. Left
alone, the master table would report RT-DETR-l twice on the published split and
never on the corrected one, and every downstream figure would inherit that.

WHY A SCRIPT AND NOT A HAND-EDIT

A hand-edit of a results file is indistinguishable, afterwards, from the data
having always said that. The provenance rule for this project is that a number
must be traceable to what produced it, and a silently altered input breaks the
chain at its very first link. This script leaves three things behind: the
change itself, a run directory recording the before and after SHA-256 of the
file, and the evidence it checked before touching anything.

THE EVIDENCE, CHECKED NOT ASSUMED

The script refuses to run unless the file itself corroborates the claim:

    val.classes_evaluated == 61 and test.classes_evaluated == 61

Only the corrected split can evaluate all 61 classes. The published split
leaves 15 classes with zero instances in both valid and test and 16 with none
in valid (runs/20260802_class_date_provenance), so a genuinely published run
reports at most 46. A file claiming "published" while evaluating 61 classes is
self-contradictory, and that contradiction -- not an assertion in a prompt --
is what licenses the change.

Corroborated independently by the artifact CSV: the corrected run's
per_class.csv holds 123 lines (61 val + 61 test + header) against the published
RT-DETR run's 92 (45 + 46 + header).

THE EDIT IS TEXTUAL, NOT A REWRITE

json.load followed by json.dump would reformat the whole file, burying a
one-field change in a whole-file diff. Instead the exact substring is replaced
once, after asserting it occurs exactly once, so the committed diff is a single
line and a reviewer can see the entire change at a glance. The result is parsed
back to prove it is still valid JSON and still differs in exactly that field.

IDEMPOTENT

Run twice and the second run reports "already corrected" and changes nothing.

Run with no arguments:

    python scripts/fix_rtdetr_corr_label.py

Writes runs/<YYYYMMDD>_fix_rtdetr_corr_label/ (auto-suffixed, never overwriting).
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


TARGET = os.path.join(ec61.DATA_DIR, "kaggle", "results_rtdetr_l_corr.json")

FIELD = "split_set"
WRONG = "published"
RIGHT = "corrected"

# The exact substrings. Written out rather than built by json.dumps so that the
# thing being searched for is visible in the source.
OLD_TEXT = '"%s": "%s"' % (FIELD, WRONG)
NEW_TEXT = '"%s": "%s"' % (FIELD, RIGHT)

# Only the corrected split can evaluate every class.
EXPECTED_CLASSES = 61


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if not os.path.isfile(TARGET):
        sys.stderr.write("target not found: %s\n" % TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as fh:
        original = fh.read()

    data = json.loads(original)
    current = data.get(FIELD)

    # --- idempotence ------------------------------------------------------
    if current == RIGHT:
        print("already corrected: %s is %r -- nothing to do" % (FIELD, RIGHT))
        return 0
    if current != WRONG:
        sys.stderr.write(
            "REFUSING: expected %s == %r before the fix, found %r.\n"
            "The file is not in the state this script was written for.\n"
            % (FIELD, WRONG, current))
        return 1

    # --- evidence ---------------------------------------------------------
    val_classes = data.get("val", {}).get("classes_evaluated")
    test_classes = data.get("test", {}).get("classes_evaluated")
    if val_classes != EXPECTED_CLASSES or test_classes != EXPECTED_CLASSES:
        sys.stderr.write(
            "REFUSING: the evidence for this fix is absent.\n"
            "  val.classes_evaluated  = %r (expected %d)\n"
            "  test.classes_evaluated = %r (expected %d)\n"
            "Only the corrected split evaluates all %d classes. Without that,\n"
            "there is no self-contradiction to resolve and no licence to edit.\n"
            % (val_classes, EXPECTED_CLASSES, test_classes, EXPECTED_CLASSES,
               EXPECTED_CLASSES))
        return 1

    # --- the edit ---------------------------------------------------------
    occurrences = original.count(OLD_TEXT)
    if occurrences != 1:
        sys.stderr.write(
            "REFUSING: found %d occurrences of %s, expected exactly 1.\n"
            "A blind replace could change a field this script does not own.\n"
            % (occurrences, OLD_TEXT))
        return 1

    updated = original.replace(OLD_TEXT, NEW_TEXT, 1)

    # Prove the result is still valid JSON and differs in exactly one field.
    reparsed = json.loads(updated)
    differing = [k for k in set(list(data) + list(reparsed))
                 if data.get(k) != reparsed.get(k)]
    if differing != [FIELD]:
        sys.stderr.write("REFUSING: edit changed %r, expected only [%r]\n"
                         % (sorted(differing), FIELD))
        return 1

    run_dir = ec61.make_run_dir("fix_rtdetr_corr_label")
    before_sha = sha256_bytes(original.encode("utf-8"))
    after_sha = sha256_bytes(updated.encode("utf-8"))

    with open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(updated)

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"target": TARGET, "field": FIELD,
                "from": WRONG, "to": RIGHT,
                "edit": "single textual substitution, one occurrence"},
        extra={"sha256_before": before_sha, "sha256_after": after_sha,
               "evidence": {"val_classes_evaluated": val_classes,
                            "test_classes_evaluated": test_classes,
                            "expected": EXPECTED_CLASSES}})

    lines = []
    lines.append("# Corrected the split label on the RT-DETR-l corrected run")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("`%s`" % TARGET.replace("\\", "/"))
    lines.append("")
    lines.append("```diff")
    lines.append("- %s" % OLD_TEXT)
    lines.append("+ %s" % NEW_TEXT)
    lines.append("```")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append("| field | `%s` |" % FIELD)
    lines.append("| before | `%s` |" % WRONG)
    lines.append("| after | `%s` |" % RIGHT)
    lines.append("| sha256 before | `%s` |" % before_sha)
    lines.append("| sha256 after | `%s` |" % after_sha)
    lines.append("| other fields changed | none (asserted) |")
    lines.append("")
    lines.append("## Evidence checked before editing")
    lines.append("")
    lines.append("- `val.classes_evaluated` = **%d**" % val_classes)
    lines.append("- `test.classes_evaluated` = **%d**" % test_classes)
    lines.append("")
    lines.append("Only the corrected split evaluates all 61 classes. The "
                 "published split leaves 15 classes with zero instances in both "
                 "valid and test and 16 with none in valid "
                 "(`runs/20260802_class_date_provenance`), so a genuinely "
                 "published run reports at most 46. The file contradicted "
                 "itself, and resolving that contradiction is what licensed the "
                 "edit.")
    lines.append("")
    lines.append("Corroborated by the artifact CSVs: this run's `per_class.csv` "
                 "holds 123 lines (61 + 61 + header) against the published "
                 "RT-DETR run's 92 (45 + 46 + header).")
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- The script proves the file was self-contradictory. It does "
                 "not independently prove which dataset the GPU actually read; "
                 "that rests on classes_evaluated being a faithful record of "
                 "the evaluation.")
    lines.append("- `args.yaml` cannot corroborate: both RT-DETR runs point at "
                 "the same generic `/kaggle/working/electrocom61.yaml`, whose "
                 "contents differed between sessions but were not captured.")
    lines.append("- Only `%s` was changed. If the same session mislabelled "
                 "anything else, this script neither detects nor fixes it." % FIELD)
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("fixed %s" % TARGET)
    print("  - %s" % OLD_TEXT)
    print("  + %s" % NEW_TEXT)
    print("  sha256 %s -> %s" % (before_sha[:16], after_sha[:16]))
    print("  evidence: val/test classes_evaluated = %d/%d" % (val_classes, test_classes))
    print("  record: %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
