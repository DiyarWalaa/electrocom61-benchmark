"""
latency_by_arch.py -- collapse the ten timed runs to five architectures

Each architecture was timed twice in the unified pass: once on the checkpoint
trained on the published split, once on the corrected-split checkpoint. The two
share an architecture, so they should time the same. Whatever separates them is
measurement noise, not a property of the model.

That makes this table do two jobs at once.

  1. A per-architecture latency figure for the paper -- the mean of the pair.
  2. A REPEATABILITY STATEMENT. The gap between two runs of the same
     architecture, on the same GPU, in the same session, is a direct estimate
     of how much this rig's timings wobble. Any latency difference BETWEEN
     architectures smaller than that gap is not a difference at all.

The gap is reported in absolute units and as a percentage of the pair mean.
Percent-of-mean rather than percent-of-either-run, so the figure does not
change depending on which of the two is put in the denominator.

TWO RUNS IS TWO RUNS

A gap from n=2 is an observation, not a confidence interval. It bounds nothing
formally; it says "these two differed by this much". Quoted as a repeatability
claim it should carry that caveat, which is why the summary states n and does
not compute a standard deviation from a pair.

Weights differ between the two runs of a pair -- same architecture, different
training data -- so the gap also absorbs any real timing effect of the learned
weights. For these detectors that should be nil (identical graph, identical
shapes) but it is not zero by construction.

Run with no arguments:

    python scripts/latency_by_arch.py

Reads data/master_results.csv, writes data/latency_by_arch.csv.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


MASTER = os.path.join(ec61.DATA_DIR, "master_results.csv")
OUT_CSV = os.path.join(ec61.DATA_DIR, "latency_by_arch.csv")

# Units per column, so the gap column is never read in the wrong one.
LATENCY_COLUMNS = [("e2e_ms_p50", "ms"), ("e2e_ms_p95", "ms"),
                   ("fps_p50", "fps"), ("pre_ms", "ms"),
                   ("inf_ms", "ms"), ("post_ms", "ms")]


def _fmt(v, nd=2):
    return "-" if v is None else ("%.*f" % (nd, v))


def main():
    if not os.path.isfile(MASTER):
        sys.stderr.write("not found: %s\nRun scripts/collect_results.py first\n"
                         % MASTER)
        return 1

    # Benchmark rows only. A diverged run has no latency measurement at
    # all, and pairing logic below expects exactly two rows per model --
    # an unfiltered read would make rtdetr-l a group of three.
    rows = ec61.load_benchmark_rows(MASTER)

    run_dir = ec61.make_run_dir("latency_by_arch")

    by_model = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)

    out = []
    warnings = []
    for model, group in by_model.items():
        if len(group) != 2:
            # The whole point is a pair. Anything else is reported, not averaged
            # silently into a number that looks like the others.
            warnings.append("%s has %d runs, expected 2" % (model, len(group)))
        rec = {"model": model, "n_runs": len(group),
               "splits": ";".join(sorted(g["split_set"] for g in group))}
        for col, unit in LATENCY_COLUMNS:
            vals = []
            for g in group:
                v = g.get(col, "")
                if v not in ("", None):
                    vals.append(float(v))
            if not vals:
                rec[col + "_mean"] = None
                rec[col + "_gap"] = None
                rec[col + "_gap_pct"] = None
                continue
            mean = sum(vals) / len(vals)
            gap = (max(vals) - min(vals)) if len(vals) > 1 else 0.0
            rec[col + "_mean"] = round(mean, 4)
            rec[col + "_gap"] = round(gap, 4)
            rec[col + "_gap_pct"] = round(100.0 * gap / mean, 4) if mean else None
        out.append(rec)

    # Fastest first: the ordering a reader wants, and the one the paper will use.
    out.sort(key=lambda r: (r.get("e2e_ms_p50_mean") is None,
                            r.get("e2e_ms_p50_mean")))

    columns = ["model", "n_runs", "splits"]
    for col, _unit in LATENCY_COLUMNS:
        columns += [col + "_mean", col + "_gap", col + "_gap_pct"]

    ec61.write_csv(OUT_CSV, columns,
                   [["" if r.get(c) is None else r.get(c) for c in columns]
                    for r in out])

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"source": MASTER, "output": OUT_CSV,
                "gap": "max - min of the pair",
                "gap_pct_basis": "percent of the pair mean",
                "columns": [c for c, _ in LATENCY_COLUMNS]},
        extra={"warnings": warnings})

    # ---- print -------------------------------------------------------------
    print("LATENCY BY ARCHITECTURE (mean of the 2 runs; gap = |run difference|)")
    head = ["model", "n", "p50_mean", "p50_gap", "p50_gap%", "p95_mean",
            "p95_gap", "fps_mean", "pre_mean", "inf_mean", "inf_gap", "post_mean"]
    keys = ["model", "n_runs", "e2e_ms_p50_mean", "e2e_ms_p50_gap",
            "e2e_ms_p50_gap_pct", "e2e_ms_p95_mean", "e2e_ms_p95_gap",
            "fps_p50_mean", "pre_ms_mean", "inf_ms_mean", "inf_ms_gap",
            "post_ms_mean"]

    def cell(k, r):
        v = r.get(k)
        if k == "model":
            return str(v)
        if k == "n_runs":
            return str(v)
        return _fmt(v)

    widths = [max(len(h), max(len(cell(k, r)) for r in out))
              for h, k in zip(head, keys)]
    print("  ".join(h.ljust(w) for h, w in zip(head, widths)))
    print("-" * (sum(widths) + 2 * (len(widths) - 1)))
    for r in out:
        print("  ".join(cell(k, r).ljust(w) for k, w in zip(keys, widths)))
    print()

    worst = max((r for r in out if r.get("e2e_ms_p50_gap_pct") is not None),
                key=lambda r: r["e2e_ms_p50_gap_pct"], default=None)
    if worst:
        print("repeatability: largest p50 pair gap is %s at %.2f ms (%.2f%% of "
              "its mean)" % (worst["model"], worst["e2e_ms_p50_gap"],
                             worst["e2e_ms_p50_gap_pct"]))
    print("wrote %s  (%d rows)" % (OUT_CSV, len(out)))
    for w in warnings:
        print("WARNING: %s" % w)

    # ---- summary -----------------------------------------------------------
    lines = []
    lines.append("# Latency by architecture")
    lines.append("")
    lines.append("Run directory: `%s`" % os.path.basename(run_dir))
    lines.append("")
    lines.append("`data/latency_by_arch.csv` — %d architectures, each the mean "
                 "of its two timed runs." % len(out))
    lines.append("")
    lines.append("| model | n | p50 mean (ms) | p50 gap (ms) | p50 gap % | "
                 "p95 mean | fps mean | pre | inf | post |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in out:
        lines.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (r["model"], r["n_runs"],
                        _fmt(r.get("e2e_ms_p50_mean")), _fmt(r.get("e2e_ms_p50_gap")),
                        _fmt(r.get("e2e_ms_p50_gap_pct")),
                        _fmt(r.get("e2e_ms_p95_mean")), _fmt(r.get("fps_p50_mean")),
                        _fmt(r.get("pre_ms_mean")), _fmt(r.get("inf_ms_mean")),
                        _fmt(r.get("post_ms_mean"))))
    lines.append("")
    lines.append("## Repeatability")
    lines.append("")
    if worst:
        lines.append("The two runs of an architecture share a graph and differ "
                     "only in learned weights, so the gap between them is this "
                     "rig's measurement wobble. The largest p50 gap is "
                     "**%s at %.2f ms (%.2f%% of its mean)**."
                     % (worst["model"], worst["e2e_ms_p50_gap"],
                        worst["e2e_ms_p50_gap_pct"]))
        lines.append("")
        lines.append("**Any latency difference between architectures smaller "
                     "than that is not a difference.**")
    lines.append("")
    lines.append("## What could make this misleading")
    lines.append("")
    lines.append("- n = 2. A gap from two observations is an observation, not a "
                 "confidence interval. No standard deviation is computed from a "
                 "pair and none should be quoted.")
    lines.append("- The pair differs in learned weights as well as in run "
                 "order, so the gap absorbs any real weight-dependent timing "
                 "effect. For these detectors that should be nil — identical "
                 "graph, identical shapes — but it is not zero by construction.")
    lines.append("- One Tesla P100, one session. The ranking may not hold on "
                 "other hardware; transformer and CNN detectors do not scale "
                 "alike across GPUs.")
    lines.append("- `fps_p50` is derived from the p50 latency, so its gap is "
                 "not independent evidence.")
    lines.append("")
    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
