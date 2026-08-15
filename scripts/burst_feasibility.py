"""
burst_feasibility.py -- can the 15 rescued classes be moved as WHOLE BURSTS?

THE OBJECTION THIS ANSWERS

The Stage 3 allocator minimised images moved and never considered duplicates.
It therefore moved IMG_20240220_115315 to test while its near-twin
IMG_20240220_115316 stayed in train -- a one-second-apart pair, split across
the boundary (see figures/near_duplicate_pair.png).

A burst-aware allocator would move whole bursts instead: if a scene was shot N
times, all N frames go to the same split, so no burst can straddle.

That is only possible for a class if the class appears in MORE THAN ONE burst
inside the train-only groups. With one burst, the class exists in exactly one
continuous shooting session; sending it to valid leaves test empty and sending
it to test leaves valid empty. Splitting it is then unavoidable, and no
allocator can fix that -- it is a property of how the data was collected.

WHAT COUNTS AS "ENOUGH"

To rescue a class cleanly the allocator needs TWO distinct bursts that each
carry at least MIN_PER_SPLIT instances: one to send to valid, a different one
to send to test. So the feasibility question is not "how many bursts" alone but
"how many bursts with >= 5 instances". Both are reported.

TWO REGIMES, BECAUSE TWO OF THE CLASSES HAVE NO TIMESTAMPS

  TIMESTAMPED groups (20240219, 20240220)
      Bursts come from burst_clusters.cluster_by_device -- single-linkage on
      consecutive within-device time gaps, tau swept. Imported, not
      reimplemented, so these bursts are the same objects as in
      runs/20260802_burst_clusters.

  UNTIMESTAMPED group (the 189 `counter` images)
      These filenames encode no capture time, so a burst is UNDEFINED for them
      and cluster_by_device cannot even sort them. The analogue used here is
      the connected component of the near-duplicate graph, exactly as in
      runs/20260802_counter_duplicates -- images linked when their label
      geometry says same scene, then transitively closed.

      This is a weaker instrument and is labelled as such in every table. A
      scene component is not a burst: it groups by appearance, not by time.

TAU AND EPSILON ARE SWEPT, NOT CHOSEN

Larger tau merges more frames into each burst: fewer bursts, so fewer
alternatives, but stronger duplicate isolation. Smaller tau gives more
alternatives that may still be near-duplicates of each other. There is no
single correct value, so the answer is reported as a function of tau and the
conclusion is only quoted where it is stable across the sweep.

Run with no arguments:

    python scripts/burst_feasibility.py

Writes runs/<YYYYMMDD>_burst_feasibility/ (auto-suffixed, never overwriting).
"""

import ast
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
import burst_clusters  # noqa: E402
import counter_duplicates  # noqa: E402
import scene_signature  # noqa: E402


MIN_PER_SPLIT = 5
TAUS = burst_clusters.TAUS
UNTIMESTAMPED = "<untimestamped:counter>"
UNPARSED = "<unparsed-filename>"

# Scene-component epsilons for the untimestamped regime. The LOOSEST value
# merges the most images into each component, which is the conservative
# direction here: over-merging risks saying "one group, unavoidable" when two
# genuinely separable groups exist, and that error is safe. Under-merging would
# claim alternatives that are actually duplicates of each other.
SCENE_EPSILONS = scene_signature.EPSILONS


def _fmt_markdown_table(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |"]
    out.append("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def date_bucket(rec):
    if rec.family == "counter":
        return UNTIMESTAMPED
    if rec.date_str:
        return rec.date_str
    return UNPARSED


def read_class_names(data_yaml):
    with open(data_yaml, "r", encoding="utf-8") as fh:
        text = fh.read()
    nc = int(re.search(r"^nc:\s*(\d+)\s*$", text, re.MULTILINE).group(1))
    names = ast.literal_eval(
        re.search(r"^names:\s*(\[.*?\])", text, re.MULTILINE | re.DOTALL).group(1))
    return names, nc


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    run_dir = ec61.make_run_dir("burst_feasibility")
    names, nc = read_class_names(os.path.join(ec61.DATASET_DIR, "data.yaml"))

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={
            "min_per_split": MIN_PER_SPLIT,
            "taus": list(TAUS),
            "scene_epsilons": list(SCENE_EPSILONS),
            "burst_definition": "burst_clusters.cluster_by_device (imported)",
            "untimestamped_analogue": "connected components of the "
                                      "near-duplicate graph (counter_duplicates)",
        },
        extra={"question": "how many distinct bursts in the train-only groups "
                           "contain each never-evaluated class?"},
    )

    records = ec61.load_images()
    boxes_by_name = {r.filename: ec61.load_boxes(r.label_path) for r in records}
    boxes_by_stem = {r.stem: boxes_by_name[r.filename] for r in records}

    # --- per-class counts, to identify the never-evaluated classes ---------
    counts = {c: {s: 0 for s in ec61.SPLITS} for c in range(nc)}
    for r in records:
        for (cid, _cx, _cy, _w, _h) in boxes_by_name[r.filename]:
            if 0 <= cid < nc:
                counts[cid][r.split] += 1
    never_eval = [c for c in range(nc)
                  if counts[c]["valid"] == 0 and counts[c]["test"] == 0]

    # --- which date groups are train-only? computed, not assumed ----------
    group_splits = {}
    for r in records:
        group_splits.setdefault(date_bucket(r), set()).add(r.split)
    train_only_groups = {g for g, ss in group_splits.items() if ss == {"train"}}

    # --- TIMESTAMPED regime: bursts per tau -------------------------------
    timed = [r for r in records if r.epoch is not None]

    # burst_rows[(tau)] -> list of dicts describing bursts inside train-only groups
    bursts_by_tau = {}
    for tau in TAUS:
        clusters = burst_clusters.cluster_by_device(
            timed, tau, lambda r: r.device_key)
        keep = []
        for cl in clusters:
            groups = {date_bucket(r) for r in cl}
            # Only bursts living wholly inside train-only groups are candidates:
            # a burst that already spans a mixed date is not what this question
            # is about.
            if not groups.issubset(train_only_groups):
                continue
            per_class = {}
            for r in cl:
                for (cid, _cx, _cy, _w, _h) in boxes_by_name[r.filename]:
                    if 0 <= cid < nc:
                        per_class[cid] = per_class.get(cid, 0) + 1
            keep.append({
                "images": [r.filename for r in cl],
                "n_images": len(cl),
                "groups": sorted(groups),
                "device": cl[0].device_key,
                "per_class": per_class,
            })
        bursts_by_tau[tau] = keep

    # --- UNTIMESTAMPED regime: scene components ---------------------------
    counter_recs = [r for r in records if r.family == "counter"]
    pair_rows, _largest = counter_duplicates.score_pairs(counter_recs, boxes_by_stem)
    stem_to_name = {r.stem: r.filename for r in counter_recs}
    all_stems = [r.stem for r in counter_recs]

    comps_by_eps = {}
    for eps in SCENE_EPSILONS:
        # Aligned scoring, low-information pairs excluded -- the row Stage 1
        # says to quote. Aligned merges drifted re-shoots that raw would miss,
        # which is the conservative direction for this question.
        edges = [(a, b) for (a, b, _nb, _raw, ali, low, _ri, _ai) in pair_rows
                 if not low and ali <= eps]
        comps = counter_duplicates.connected_components(all_stems, edges)
        out = []
        for comp in comps:
            per_class = {}
            for stem in comp:
                for (cid, _cx, _cy, _w, _h) in boxes_by_stem[stem]:
                    if 0 <= cid < nc:
                        per_class[cid] = per_class.get(cid, 0) + 1
            out.append({
                "images": [stem_to_name[s] for s in comp],
                "n_images": len(comp),
                "groups": [UNTIMESTAMPED],
                "device": "FAMILY:counter",
                "per_class": per_class,
            })
        comps_by_eps[eps] = out

    # --- the answer table --------------------------------------------------
    rows = []
    for cid in never_eval:
        for tau in TAUS:
            groups = [b for b in bursts_by_tau[tau] if b["per_class"].get(cid)]
            qualifying = [b for b in groups
                          if b["per_class"][cid] >= MIN_PER_SPLIT]
            rows.append([
                cid, names[cid], "timestamp", "tau=%ds" % tau,
                len(groups), len(qualifying),
                min((b["n_images"] for b in qualifying), default=0),
                max((b["n_images"] for b in qualifying), default=0),
                sum(b["per_class"][cid] for b in groups),
                verdict_for(len(groups), len(qualifying)),
            ])
        for eps in SCENE_EPSILONS:
            groups = [b for b in comps_by_eps[eps] if b["per_class"].get(cid)]
            if not groups:
                continue   # class does not appear among the untimestamped images
            qualifying = [b for b in groups
                          if b["per_class"][cid] >= MIN_PER_SPLIT]
            rows.append([
                cid, names[cid], "scene-component", "eps=%.2f" % eps,
                len(groups), len(qualifying),
                min((b["n_images"] for b in qualifying), default=0),
                max((b["n_images"] for b in qualifying), default=0),
                sum(b["per_class"][cid] for b in groups),
                verdict_for(len(groups), len(qualifying)),
            ])

    ec61.write_csv(
        os.path.join(run_dir, "class_group_counts.csv"),
        ["class_id", "class_name", "regime", "setting",
         "n_groups_with_class", "n_groups_with_ge_%d" % MIN_PER_SPLIT,
         "min_images_in_qualifying_group", "max_images_in_qualifying_group",
         "total_instances", "verdict"],
        rows,
    )

    # Burst inventory, so a reader can see the size budget the allocator faces.
    inv = []
    for tau in TAUS:
        for i, b in enumerate(bursts_by_tau[tau]):
            inv.append(["tau=%ds" % tau, i, b["device"], ";".join(b["groups"]),
                        b["n_images"], sum(b["per_class"].values()),
                        len(b["per_class"])])
    for eps in SCENE_EPSILONS:
        for i, b in enumerate(comps_by_eps[eps]):
            inv.append(["eps=%.2f" % eps, i, b["device"], ";".join(b["groups"]),
                        b["n_images"], sum(b["per_class"].values()),
                        len(b["per_class"])])
    ec61.write_csv(
        os.path.join(run_dir, "group_inventory.csv"),
        ["setting", "group_index", "device", "date_groups",
         "n_images", "n_instances", "n_distinct_classes"],
        inv,
    )

    # --- summary -----------------------------------------------------------
    def tally(setting_label, regime):
        got = {}
        for r in rows:
            if r[3] == setting_label and r[2] == regime:
                got[r[9]] = got.get(r[9], 0) + 1
        return got

    lines = []
    lines.append("# Can the rescued classes be moved as whole bursts?")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("Never-evaluated classes: **%d**. Train-only groups: %s."
                 % (len(never_eval), ", ".join(sorted(train_only_groups))))
    lines.append("")
    lines.append("A class can be rescued cleanly only if it appears in **two or "
                 "more distinct groups each carrying >= %d instances** -- one to "
                 "send to valid, a different one to test." % MIN_PER_SPLIT)
    lines.append("")

    lines.append("## Verdict counts by setting")
    lines.append("")
    tally_rows = []
    for tau in TAUS:
        t = tally("tau=%ds" % tau, "timestamp")
        tally_rows.append(["timestamp", "tau=%ds" % tau,
                           t.get("absent_from_regime", 0),
                           t.get("single_group", 0), t.get("insufficient", 0),
                           t.get("has_alternatives", 0)])
    for eps in SCENE_EPSILONS:
        t = tally("eps=%.2f" % eps, "scene-component")
        tally_rows.append(["scene-component", "eps=%.2f" % eps,
                           t.get("absent_from_regime", 0),
                           t.get("single_group", 0), t.get("insufficient", 0),
                           t.get("has_alternatives", 0)])
    lines.append(_fmt_markdown_table(
        ["regime", "setting", "absent from regime", "single group (unavoidable)",
         "several groups but < 2 qualifying", "has alternatives"], tally_rows))
    lines.append("")

    # --- the combined answer, which is what the question actually asked ----
    # A class is rescuable cleanly if EITHER regime offers it two qualifying
    # groups. Judging each regime in isolation would condemn the two classes
    # that live only among the untimestamped images.
    PRIMARY_TAU = 10
    PRIMARY_EPS = 0.05
    combined = []
    n_clean = 0
    for cid in never_eval:
        ts = next((r for r in rows if r[0] == cid and r[3] == "tau=%ds" % PRIMARY_TAU
                   and r[2] == "timestamp"), None)
        sc = next((r for r in rows if r[0] == cid and r[3] == "eps=%.2f" % PRIMARY_EPS
                   and r[2] == "scene-component"), None)
        ts_v = ts[9] if ts else "absent_from_regime"
        sc_v = sc[9] if sc else "absent_from_regime"
        ok = "has_alternatives" in (ts_v, sc_v)
        if ok:
            n_clean += 1
        combined.append([names[cid], ts_v, sc_v,
                         "YES" if ok else "**NO**",
                         "timestamped bursts" if ts_v == "has_alternatives"
                         else ("scene components" if sc_v == "has_alternatives"
                               else "-")])
    lines.append("## Combined answer (tau=%ds, epsilon=%.2f)" % (PRIMARY_TAU, PRIMARY_EPS))
    lines.append("")
    lines.append("**%d of %d** never-evaluated classes can be rescued by moving "
                 "whole groups." % (n_clean, len(never_eval)))
    lines.append("")
    lines.append(_fmt_markdown_table(
        ["class", "timestamped regime", "scene-component regime",
         "rescuable cleanly?", "via"], combined))
    lines.append("")

    lines.append("## Per class, timestamped regime")
    lines.append("")
    for tau in TAUS:
        lines.append("**tau = %ds**" % tau)
        lines.append("")
        lines.append(_fmt_markdown_table(
            ["class", "groups w/ class", "groups w/ >=%d" % MIN_PER_SPLIT,
             "smallest qualifying (imgs)", "largest (imgs)", "verdict"],
            [[r[1], r[4], r[5], r[6], r[7], r[9]] for r in rows
             if r[3] == "tau=%ds" % tau and r[2] == "timestamp"]))
        lines.append("")

    lines.append("## Per class, untimestamped regime (scene components)")
    lines.append("")
    lines.append("Bursts are undefined for these images. Components group by "
                 "appearance, not time, and are a weaker instrument.")
    lines.append("")
    for eps in SCENE_EPSILONS:
        sub = [[r[1], r[4], r[5], r[6], r[7], r[9]] for r in rows
               if r[3] == "eps=%.2f" % eps and r[2] == "scene-component"]
        if not sub:
            continue
        lines.append("**epsilon = %.2f**" % eps)
        lines.append("")
        lines.append(_fmt_markdown_table(
            ["class", "components w/ class", "components w/ >=%d" % MIN_PER_SPLIT,
             "smallest qualifying (imgs)", "largest (imgs)", "verdict"], sub))
        lines.append("")

    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- Two distinct bursts can still be near-duplicates of each "
                 "other. Separate bursts are a NECESSARY condition for a clean "
                 "rescue, not a sufficient one; the allocator would still have "
                 "to check geometry.")
    lines.append("- Capture date is a proxy for session and tau is a proxy for "
                 "burst. A pause longer than tau inside one continuous shoot "
                 "splits it into two groups that are not really alternatives.")
    lines.append("- Scene components are appearance-based. Under-merging invents "
                 "alternatives that are duplicates; over-merging hides real ones. "
                 "The epsilon sweep is there so this is visible.")
    lines.append("- Group SIZE is a hard budget the allocator must respect: test "
                 "holds only 205 images, so a large burst may be unusable even "
                 "when it qualifies on instance count.")
    lines.append("")

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("wrote %s" % run_dir)
    print("  never-evaluated classes: %d" % len(never_eval))
    for tau in TAUS:
        t = tally("tau=%ds" % tau, "timestamp")
        print("  tau=%-3ds  single=%d  insufficient=%d  alternatives=%d"
              % (tau, t.get("single_group", 0), t.get("insufficient", 0),
                 t.get("has_alternatives", 0)))
    for eps in SCENE_EPSILONS:
        t = tally("eps=%.2f" % eps, "scene-component")
        if sum(t.values()):
            print("  eps=%.2f  single=%d  insufficient=%d  alternatives=%d"
                  % (eps, t.get("single_group", 0), t.get("insufficient", 0),
                     t.get("has_alternatives", 0)))
    return 0


def verdict_for(n_groups, n_qualifying):
    """Classify a class's prospects under one setting.

    `absent_from_regime` and `single_group` must not be conflated. A class with
    ZERO groups here does not live in this regime at all -- LED-Light and
    OLED-Display appear only among the untimestamped images, so they have no
    timestamped bursts by definition. Calling that "one session holds it all,
    unavoidable" would report a measurement artefact as a fact about the data,
    and would condemn two classes that the scene-component regime can rescue.
    """
    if n_groups == 0:
        return "absent_from_regime"  # judge this class in the other regime
    if n_groups == 1:
        return "single_group"        # genuinely unavoidable: one session holds it
    if n_qualifying >= 2:
        return "has_alternatives"    # two distinct groups can be chosen
    return "insufficient"            # several groups, but not two big enough


if __name__ == "__main__":
    sys.exit(main())
