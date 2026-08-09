"""
scaffold_config_provenance.py -- build the empty shell of data/config_provenance.csv

T3, the training-configuration table, needs a column saying whether each
setting was copied from prior work or added by this study. That is a CITATION,
not a measurement: nothing in this repository records it, and grepping every
committed CSV, JSON and YAML for such a marker returns nothing.

So the values are read from the committed args.yaml files and the source and
citation columns are left blank to be filled by hand, against the prior-work
PDFs. make_tables.py then reads the finished file like any other source, and
still types nothing itself.

REFUSES TO OVERWRITE

The point of the file is the hand-written half. Regenerating over a filled-in
copy would destroy exactly the work this script cannot do, so it exits without
writing if the target already exists.

WHAT IS INCLUDED

Every key present in any committed args.yaml, except:

  - keys whose value is null or empty in every run, which have nothing to
    attribute;
  - the four run-identity keys (name, save_dir, project, data), which record
    where a run wrote its files rather than how it was configured.

Keys whose value differs between runs carry every distinct value, joined by
" | ", so a divergence cannot be hidden by picking one run to read.

ORDERING

The settings that also appear as top-level fields in the results JSONs come
first, in the order those files list them: they are the ones a configuration
table normally reports. Everything else follows alphabetically. Nothing is
dropped -- the ordering is a convenience for triage, not a judgement about
what matters.

Run with no arguments:

    python scripts/scaffold_config_provenance.py

Writes data/config_provenance.csv and a record under
runs/<YYYYMMDD>_scaffold_config_provenance/.
"""

import glob
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


OUT = os.path.join(ec61.DATA_DIR, "config_provenance.csv")
KAGGLE = os.path.join(ec61.DATA_DIR, "kaggle")

# Recorded where the run wrote its files, not how it was configured.
IDENTITY_KEYS = ("name", "save_dir", "project", "data")

NULLISH = ("null", "none", "", "~")

KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


def main():
    if os.path.exists(OUT):
        sys.stderr.write(
            "REFUSING: %s already exists.\n"
            "Its value is the hand-written source and citation columns, which\n"
            "this script cannot regenerate. Delete it yourself if you really\n"
            "mean to start over.\n" % OUT)
        return 1

    paths = sorted(glob.glob(os.path.join(KAGGLE, "artifacts", "*", "*args.yaml"))
                   + glob.glob(os.path.join(KAGGLE, "artifacts", "*", "runs",
                                            "*", "args.yaml")))
    if not paths:
        sys.stderr.write("no args.yaml found under %s\n" % KAGGLE)
        return 1

    values = defaultdict(dict)
    for p in paths:
        run = os.path.basename(os.path.dirname(p))
        if run == os.path.basename(os.path.dirname(os.path.dirname(p))):
            run = os.path.basename(os.path.dirname(p))
        with open(p, "r", encoding="utf-8") as fh:
            for line in fh:
                m = KEY_RE.match(line.rstrip("\n"))
                if m:
                    values[m.group(1)][run] = m.group(2).strip()

    # Order: the curated set the results JSONs report, then everything else.
    # The unified latency file matches results_*.json but is not a training
    # run: its top-level keys are protocol blocks, so reading it here would
    # produce an ordering based on nothing.
    curated = []
    per_run = [p for p in sorted(glob.glob(os.path.join(KAGGLE, "results_*.json")))
               if "latency_unified" not in os.path.basename(p)]
    if not per_run:
        sys.stderr.write("no per-run results_*.json found\n")
        return 1
    with open(per_run[0], "r", encoding="utf-8-sig") as fh:
        d = json.load(fh)
    for k in d:
        if not isinstance(d[k], (dict, list)):
            curated.append(k)

    rows = []
    skipped_null, skipped_identity = [], []
    for key in values:
        vs = values[key]
        distinct = sorted(set(vs.values()))
        if all(v.lower() in NULLISH for v in distinct):
            skipped_null.append(key)
            continue
        if key in IDENTITY_KEYS:
            skipped_identity.append(key)
            continue
        rows.append((key, " | ".join(distinct)))

    def rank(item):
        key = item[0]
        return (0, curated.index(key)) if key in curated else (1, key)

    rows.sort(key=rank)

    ec61.write_csv(OUT, ["setting", "value", "source", "citation"],
                   [[k, v, "", ""] for k, v in rows])

    run_dir = ec61.make_run_dir("scaffold_config_provenance")
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"output": OUT, "args_yaml_files": len(paths),
                "identity_keys_excluded": list(IDENTITY_KEYS)},
        extra={"rows_written": len(rows),
               "skipped_null_everywhere": sorted(skipped_null),
               "skipped_identity": sorted(skipped_identity),
               "settings_varying_between_runs":
                   sorted(k for k in values
                          if len(set(values[k].values())) > 1)})

    varying = sorted(k for k in values if len(set(values[k].values())) > 1
                     and k not in IDENTITY_KEYS
                     and not all(v.lower() in NULLISH
                                 for v in set(values[k].values())))

    print("wrote %s" % os.path.relpath(OUT, ec61.REPO_ROOT).replace("\\", "/"))
    print("  args.yaml files read     : %d" % len(paths))
    print("  settings written         : %d" % len(rows))
    print("  skipped, null everywhere : %d" % len(skipped_null))
    print("  skipped, run identity    : %d (%s)"
          % (len(skipped_identity), ", ".join(sorted(skipped_identity))))
    print("  values differing by run  : %s" % (", ".join(varying) or "none"))
    print()
    print("  source and citation are blank by design -- fill them by hand.")
    print("  record: %s" % os.path.relpath(run_dir, ec61.REPO_ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
