"""
compare_published_complexity.py -- prior papers' complexity figures against ours

WHAT THIS IS FOR

Section 7.1 argues that published results on ElectroCom61 are not comparable
with one another. The accuracy half of that argument rests on properties the
papers do not state. This is the complexity half, and it is different in kind:
the papers DO state layer counts and parameter counts, so those can be set
beside measured values directly.

THE INPUT IS HAND-TRANSCRIBED, AND THAT IS THE WEAK LINK

`data/published_complexity.csv` was typed from the PDFs. The PDFs are not in
this repository, nothing in the tooling can check the transcription, and a
mis-keyed digit would propagate silently into a claim about someone else's work.
It carries a `table_location` column for exactly that reason: every row names
the table it came from, so each value can be re-checked against its source in
one step. Treat it the way `data/config_provenance.csv` is treated -- a reading
of the literature, not a measurement, and the one file in `data/` that no script
can regenerate.

WHAT IS COMPARED, AND WHAT IS NOT

Only the three architectures this study also trained: YOLOv9s, YOLO11s and
YOLOv12s. The other rows in the published tables are architectures not evaluated
here, and no measured counterpart for them exists.

Both fused and unfused measured values are reported against each published
figure. Section 5.5 establishes that fusion moves parameter counts by up to
5.1%, so if a published figure sat between the two it would be explained by the
fusion question alone. Printing both is what lets that explanation be tested
rather than assumed.

Run with no arguments:

    python scripts/compare_published_complexity.py

Writes runs/<YYYYMMDD>_compare_published_complexity/.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


PUBLISHED = os.path.join(ec61.DATA_DIR, "published_complexity.csv")

# Published name -> the model key used in master_results.csv. Only the three
# architectures this study trained appear; everything else in the published
# tables has no measured counterpart here.
NAME_MAP = {
    "YOLOv9s": "yolov9s",
    "YOLOv11s": "yolo11s",
    "YOLOv12S": "yolo12s",
}


def main():
    if not os.path.isfile(PUBLISHED):
        sys.stderr.write("missing %s\n" % PUBLISHED)
        return 1

    with open(PUBLISHED, "r", encoding="utf-8", newline="") as fh:
        pub = list(csv.DictReader(fh))

    # Measured values: one row per architecture, taken from the corrected-split
    # run. Complexity is a property of the architecture, so the two runs of each
    # model carry identical figures; load_benchmark_rows already asserts that.
    measured = {}
    for r in ec61.load_benchmark_rows():
        if r["split_set"] == "corrected":
            measured[r["model"]] = r

    run_dir = ec61.make_run_dir("compare_published_complexity")
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"published_rows": len(pub), "compared": sorted(NAME_MAP),
                "measured_source": "data/master_results.csv, corrected split"},
        extra={"published_input": "data/published_complexity.csv -- HAND "
                                  "TRANSCRIBED from the prior-work PDFs, not "
                                  "measured and not machine-checkable",
               "fusion_note": "both fused and unfused measured values are "
                              "reported so the fused/unfused question can be "
                              "tested as an explanation rather than assumed"},
    )

    rows = []
    for p in pub:
        key = NAME_MAP.get(p["model"])
        if key is None or key not in measured:
            continue
        m = measured[key]
        pub_m = float(p["params_millions"])
        fused = int(m["params_fused"]) / 1e6
        unfused = int(m["params_unfused"]) / 1e6
        rows.append([
            p["model"], key, p["source"], p["table_location"],
            p["layers"], m["layers_modules"],
            "%.1f" % pub_m, "%.2f" % fused, "%.2f" % unfused,
            "%.2f" % (pub_m / fused),
            "%+.2f" % (pub_m - fused),
            "yes" if min(fused, unfused) <= pub_m <= max(fused, unfused) else "no",
        ])

    header = ["published_model", "our_model", "source", "table_location",
              "published_layers", "measured_layers",
              "published_params_m", "measured_fused_m", "measured_unfused_m",
              "ratio_pub_over_fused", "diff_m", "explained_by_fusion"]
    ec61.write_csv(os.path.join(run_dir, "published_vs_measured.csv"),
                   header, rows)

    lines = [
        "# Published complexity figures against measured ones",
        "",
        "Run directory: `%s`" % os.path.basename(run_dir),
        "",
        "Input `data/published_complexity.csv` is **hand-transcribed from the "
        "prior-work PDFs**. It is not measured and nothing here can check it; "
        "each row names its table so every value can be re-checked in one step.",
        "",
        "Measured values are from `data/master_results.csv`, corrected split.",
        "",
        "| model | source | published layers | ours | published params (M) | "
        "ours fused (M) | ratio | explained by fusion? |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %sx | %s |"
                     % (r[0], r[2], r[4], r[5], r[6], r[7], r[9], r[11]))

    lines += [
        "",
        "## What could make this misleading",
        "",
        "- The input is a hand transcription of a PDF table. A mis-keyed digit "
        "would propagate into a claim about someone else's work, and no check "
        "here would catch it.",
        "- A published figure may describe a variant, an input resolution or a "
        "class count that differs from this study's. The papers state the "
        "architecture name and the number; they do not state what else was held "
        "fixed when the number was produced.",
        "- `explained_by_fusion` asks only whether the published value falls "
        "between the fused and unfused measurements. A `no` rules fusion out as "
        "the whole explanation; it does not identify what the explanation is.",
        "- Layer counts are framework-dependent in a way parameter counts are "
        "not: what counts as a layer differs between implementations and "
        "between Ultralytics releases, so a layer-count difference is weaker "
        "evidence than a parameter-count difference.",
    ]

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print("\nwrote %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
