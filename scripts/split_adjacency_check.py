"""
split_adjacency_check.py -- did the allocator change temporal adjacency?

WHAT THIS MEASURES

Two images shot by the same camera within TAU seconds of each other form a
temporally adjacent pair. This script counts how many such pairs STRADDLE a
partition boundary, under the published split and under the released corrected
split, and reports whether they are the same pairs.

WHY IT IS WORTH MEASURING SEPARATELY

The contamination figures in runs/20260804_duplicate_contamination/ are computed
from annotation geometry: two images count as near-duplicates when their class
multisets match and their box centres agree. That measure under-detects by
construction -- one occluded component changes the multiset and the pair is
never compared.

Temporal adjacency is an independent signal with the opposite failure mode. It
needs no labels and cannot be defeated by occlusion, but it says nothing about
what the two frames contain: a photographer can turn to a new scene in three
seconds. Neither measure subsumes the other, so agreement between them is worth
more than either alone.

WHAT A CHANGE WOULD MEAN

The released allocator moves whole bursts, so in principle it cannot separate
two images inside one burst. This script tests that from outside the allocator,
against the assignment it actually produced, rather than trusting the grouping
logic to have done what it claims.

DEFINITIONS, BOTH REPORTED

  all-pairs     every unordered pair with |gap| <= TAU. A burst of five frames
                contributes ten pairs. This is the headline.
  consecutive   only pairs adjacent in time order within a camera. A burst of
                five frames contributes four pairs. Reported alongside because
                "pairs within 15 seconds" is ambiguous between the two and the
                ambiguity should be visible rather than resolved silently.

Device keying is done BOTH ways, exactly as burst_clusters.py does it: the CSV
DEVICE_NAME where a row exists, and the filename family otherwise. If the two
keyings disagree the device attribution needs settling before any number here is
quoted.

THE 189 UNTIMESTAMPED IMAGES ARE OUT OF SCOPE. They carry no capture time, so
no temporal gap exists for them and they cannot appear in any pair below. That
is a limit of this measure, not a finding about those images; the scene-content
measure reaches them instead.

Run with no arguments:

    python scripts/split_adjacency_check.py

Writes runs/<YYYYMMDD>_split_adjacency_check/ (auto-suffixed, never overwriting).
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


# The grouping threshold the released split was built at. Not swept: this
# script asks whether the allocator disturbed adjacency AT THE THRESHOLD IT
# USED, which is a different question from how adjacency behaves in general.
TAU = 15

MANIFEST = os.path.join(ec61.RUNS_DIR, "20260804_burst_aware_split_04",
                        "split_manifest.csv")

KEYINGS = (
    ("csv_device", lambda r: r.device_key),
    ("family_only", lambda r: "FAMILY:" + r.family),
)


def load_manifest(path):
    """image_name -> split, from the released manifest."""
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return {row["image_name"]: row["split"] for row in csv.DictReader(fh)}


def adjacent_pairs(records, key_fn, tau):
    """Every same-camera pair within `tau` seconds.

    Returns (all_pairs, consecutive_pairs), each a set of (filename_a,
    filename_b) tuples ordered by filename so the pair identity does not depend
    on which image happened to be first in time.

    The inner loop breaks as soon as the gap exceeds tau. Records are sorted by
    epoch within a camera, so everything after that point is further away still
    -- without the break this is quadratic in the size of a session.
    """
    by_dev = {}
    for r in records:
        if r.epoch is None:
            continue          # untimestamped: no gap exists, see module docstring
        by_dev.setdefault(key_fn(r), []).append(r)

    all_pairs, consec = set(), set()
    for _dev, recs in by_dev.items():
        recs.sort(key=lambda r: (r.epoch, r.filename))
        for i, a in enumerate(recs):
            for b in recs[i + 1:]:
                if b.epoch - a.epoch > tau:
                    break
                all_pairs.add(tuple(sorted((a.filename, b.filename))))
        for a, b in zip(recs, recs[1:]):
            if b.epoch - a.epoch <= tau:
                consec.add(tuple(sorted((a.filename, b.filename))))
    return all_pairs, consec


def relationship(split_a, split_b):
    """Canonical name for a cross-split relationship, or None if same split."""
    if split_a == split_b:
        return None
    return "<->".join(sorted((split_a, split_b)))


def cross_split(pairs, assign):
    """Subset of `pairs` straddling a boundary, plus per-relationship counts."""
    crossing, counts = set(), {}
    for a, b in pairs:
        rel = relationship(assign[a], assign[b])
        if rel is None:
            continue
        crossing.add((a, b))
        counts[rel] = counts.get(rel, 0) + 1
    return crossing, counts


def main():
    # A fresh checkout does not have the dataset -- it is git-ignored and
    # downloaded, not committed. Exit with the remedy rather than a traceback.
    rc = ec61.require_inputs("dataset_v2")
    if rc:
        return rc

    records = ec61.load_images()
    # load_metadata returns (rows_by_key, duplicate_keys, n_data_rows); only the
    # first is the join table.
    rows_by_key, _dupes, _n_rows = ec61.load_metadata()
    n_joined, n_missing = ec61.attach_metadata(records, rows_by_key)

    published = {r.filename: r.split for r in records}
    corrected = load_manifest(MANIFEST)

    missing = set(published) ^ set(corrected)
    if missing:
        raise ValueError(
            "manifest and disk describe different image sets; %d differ, e.g. %s"
            % (len(missing), sorted(missing)[:3]))

    timed = [r for r in records if r.epoch is not None]
    untimed = len(records) - len(timed)

    run_dir = ec61.make_run_dir("split_adjacency_check")
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"tau_seconds": TAU, "manifest": MANIFEST,
                "keyings": [name for name, _ in KEYINGS],
                "images": len(records), "timestamped": len(timed),
                "untimestamped_excluded": untimed,
                "csv_rows_joined": n_joined, "csv_rows_missing": n_missing},
        extra={"published_split": "directory on disk under data/ElectroCom-61_v2",
               "corrected_split": "runs/20260804_burst_aware_split_04/split_manifest.csv"},
    )

    rows, summary_blocks, verdicts = [], [], []
    for key_name, key_fn in KEYINGS:
        all_pairs, consec = adjacent_pairs(records, key_fn, TAU)
        block = ["", "### Keying: `%s`" % key_name, "",
                 "- same-camera pairs within %d s: **%d** (all-pairs), "
                 "**%d** (consecutive only)" % (TAU, len(all_pairs), len(consec)),
                 ""]
        header = ["definition", "state", "total_pairs", "cross_split",
                  "test<->train", "train<->valid", "test<->valid"]
        table = []
        for defn, pairs in (("all-pairs", all_pairs), ("consecutive", consec)):
            per_state = {}
            for state, assign in (("published", published),
                                  ("corrected", corrected)):
                crossing, counts = cross_split(pairs, assign)
                per_state[state] = crossing
                row = [defn, state, len(pairs), len(crossing),
                       counts.get("test<->train", 0),
                       counts.get("train<->valid", 0),
                       counts.get("test<->valid", 0)]
                table.append(row)
                rows.append([key_name] + row)
            same = per_state["published"] == per_state["corrected"]
            verdicts.append((key_name, defn, same,
                             len(per_state["corrected"] - per_state["published"]),
                             len(per_state["published"] - per_state["corrected"])))
        block.append(_md(header, table))
        summary_blocks.append("\n".join(block))

    ec61.write_csv(
        os.path.join(run_dir, "adjacent_cross_split.csv"),
        ["keying", "definition", "state", "total_pairs", "cross_split",
         "pairs_test_train", "pairs_train_valid", "pairs_test_valid"],
        rows,
    )

    lines = [
        "# Temporal adjacency across the split boundary",
        "",
        "Run directory: `%s`  |  tau=%d s" % (os.path.basename(run_dir), TAU),
        "",
        "Same-camera pairs captured within %d s, counted as cross-split under the"
        " published assignment (the directory on disk) and under the released"
        " corrected assignment (`%s`)." % (TAU, os.path.relpath(MANIFEST, ec61.REPO_ROOT)),
        "",
        "- images: **%d**; timestamped: **%d**; untimestamped and therefore"
        " OUT OF SCOPE: **%d**" % (len(records), len(timed), untimed),
    ]
    lines.extend(summary_blocks)

    lines.extend(["", "## Verdict", "",
                  "| keying | definition | identical pair sets | created by allocator | removed by allocator |",
                  "|---|---|---|---|---|"])
    for key_name, defn, same, created, removed in verdicts:
        lines.append("| `%s` | %s | %s | %d | %d |"
                     % (key_name, defn, "**yes**" if same else "**NO**",
                        created, removed))

    lines.extend([
        "", "## What could make this misleading", "",
        "- Adjacency is not similarity. Two frames three seconds apart can show"
        " different scenes if the photographer moved on; two frames of the same"
        " scene can be minutes apart. This measure and the label-geometry one in"
        " `runs/20260804_duplicate_contamination/` fail in opposite directions,"
        " which is the only reason running both is informative.",
        "- The 189 untimestamped images cannot appear in any count here. Whatever"
        " adjacency exists among them is invisible to this script.",
        "- A pre-existing cross-split pair is not evidence against the allocator."
        " The published split already separates frames inside a burst; the"
        " question this run answers is whether the corrected split separates"
        " ANY THAT THE PUBLISHED ONE DID NOT.",
        "- tau is fixed at %d s to match the released split. A different tau"
        " gives a different pair population and different counts." % TAU,
    ])

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print("\nwrote %s" % run_dir)
    return 0


def _md(header, rows):
    out = ["| " + " | ".join(str(h) for h in header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
