"""
verify_efficiency_claims.py -- verify the efficiency/latency claims for 5.5

Checks, each against the source that actually carries it:

  1. the fused/unfused complexity figures quoted for YOLO26s and RT-DETR-l,
     and the claimed 0.2%-to-5.1% range of parameter reduction across the
     five architectures
  2. the measurement protocol: batch size, image size, GPU, warmup count,
     synchronisation, percentile choice, and the file pre-read
  3. the duplicate-measurement resolution: the largest end-to-end p50 gap
     between the two runs of one architecture
  4. the claim that an earlier per-session set of measurements varied by up
     to 23% for the same architecture

WHY CLAIM 4 USES A SOURCE THE REST OF THE PIPELINE REFUSES

collect_results.py deliberately never reads the per-run `latency_ms` fields:
they were measured inside ten separate Kaggle sessions under unknown
contention, which makes them useless for comparing models. That is exactly
what makes them the right source here. The claim is not about how fast the
models are; it is about how much per-session measurement disagrees with
itself. The unusable numbers are the evidence for their own unusability.

Run with no arguments:

    python scripts/verify_efficiency_claims.py

Writes runs/<YYYYMMDD>_verify_efficiency_claims/.
"""

import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


MASTER_CSV = os.path.join(ec61.DATA_DIR, "master_results.csv")
BY_ARCH_CSV = os.path.join(ec61.DATA_DIR, "latency_by_arch.csv")
KAGGLE_DIR = os.path.join(ec61.DATA_DIR, "kaggle")
LATENCY_JSON = os.path.join(KAGGLE_DIR, "results_latency_unified.json")

# Figures quoted verbatim in the prose, checked as exact strings against the
# CSV so a transcription slip cannot pass as a rounding difference.
QUOTED = {
    "yolo26s": {"params_unfused": "9995078", "gflops_unfused": "22.998",
                "params_fused": "9488787", "gflops_fused": "20.892"},
    "rtdetr-l": {"params_unfused": "32931431", "gflops_unfused": "110.159",
                 "params_fused": "32109095", "gflops_fused": "105.6"},
}
CLAIMED_RANGE = (0.2, 5.1)        # percent parameter reduction, 1 decimal
CLAIMED_MAX_GAP_MS = 0.24
CLAIMED_MAX_GAP_PCT = 1.75
CLAIMED_SESSION_SPREAD_PCT = 23.0


def read_csv(path):
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    problems = []
    notes = []

    for p in (MASTER_CSV, BY_ARCH_CSV, LATENCY_JSON):
        if not os.path.isfile(p):
            sys.stderr.write("missing input: %s\n" % p)
            return 1

    run_dir = ec61.make_run_dir("verify_efficiency_claims")
    rows = read_csv(MASTER_CSV)

    # ---- 1. complexity and fusion ------------------------------------------
    # One entry per architecture. Both runs of an architecture share weights,
    # so the complexity figures must agree between them; disagreement would
    # mean the two rows describe different models.
    by_model = {}
    for r in rows:
        m = r["model"]
        rec = dict((k, r[k]) for k in ("params_unfused", "gflops_unfused",
                                       "params_fused", "gflops_fused"))
        if m in by_model and by_model[m] != rec:
            problems.append("%s: the two runs disagree on complexity figures"
                            % m)
        by_model[m] = rec

    for model, quoted in sorted(QUOTED.items()):
        got = by_model.get(model)
        if got is None:
            problems.append("%s not present in master_results.csv" % model)
            continue
        for field, want in sorted(quoted.items()):
            if got[field] != want:
                problems.append("%s %s: prose quotes %s, CSV has %s"
                                % (model, field, want, got[field]))

    fusion = {}
    for model, rec in sorted(by_model.items()):
        pu, pf = int(rec["params_unfused"]), int(rec["params_fused"])
        gu, gf = float(rec["gflops_unfused"]), float(rec["gflops_fused"])
        fusion[model] = {
            "params_unfused": pu, "params_fused": pf,
            "params_drop": pu - pf,
            "params_drop_pct": 100.0 * (pu - pf) / pu,
            "gflops_unfused": gu, "gflops_fused": gf,
            "gflops_drop_pct": 100.0 * (gu - gf) / gu,
        }

    pcts = sorted(v["params_drop_pct"] for v in fusion.values())
    lo, hi = pcts[0], pcts[-1]
    # The prose states the range to one decimal, so compare at that precision
    # rather than demanding the raw values match.
    if round(lo, 1) != CLAIMED_RANGE[0]:
        problems.append("smallest parameter reduction is %.4f%% (rounds to "
                        "%.1f%%), prose claims %.1f%%"
                        % (lo, round(lo, 1), CLAIMED_RANGE[0]))
    if round(hi, 1) != CLAIMED_RANGE[1]:
        problems.append("largest parameter reduction is %.4f%% (rounds to "
                        "%.1f%%), prose claims %.1f%%"
                        % (hi, round(hi, 1), CLAIMED_RANGE[1]))

    # ---- 2. protocol -------------------------------------------------------
    with io.open(LATENCY_JSON, encoding="utf-8-sig") as fh:
        lat_doc = json.load(fh)
    protocol = lat_doc.get("protocol", {})
    environment = lat_doc.get("environment", {})
    n_models = len(lat_doc.get("models", []))

    checks = [
        ("batch size 1", str(protocol.get("batch")) == "1"),
        ("imgsz 640", str(protocol.get("imgsz")) == "640"),
        ("warmup 20", str(protocol.get("warmup")) == "20"),
        ("Tesla P100", "P100" in str(environment.get("gpu", ""))),
        ("cuda.synchronize in timer",
         "synchronize" in str(protocol.get("timer", ""))),
        ("p50 and p95 reported", "p50" in str(protocol.get("timer", ""))
         and "p95" in str(protocol.get("timer", ""))),
        ("end-to-end predict()", "predict()" in str(protocol.get("timer", ""))),
        ("all 205 images pre-read",
         "205" in str(protocol.get("file_cache", ""))),
        ("ten checkpoints in one pass", n_models == 10),
    ]
    for label, ok in checks:
        if not ok:
            problems.append("protocol check failed: %s" % label)

    # The protocol records a burn-in SEPARATE from the 20-iteration warmup.
    # The prose describes the warmup and the file pre-read but not this.
    if protocol.get("burn_in"):
        notes.append("protocol records an additional precaution the prose does "
                     "not mention -- burn_in: %r" % protocol["burn_in"])

    # ---- 3. duplicate-measurement resolution -------------------------------
    arch = read_csv(BY_ARCH_CSV)
    worst = max(arch, key=lambda r: float(r["e2e_ms_p50_gap"]))
    max_gap = float(worst["e2e_ms_p50_gap"])
    max_gap_pct = float(worst["e2e_ms_p50_gap_pct"])
    if round(max_gap, 2) != CLAIMED_MAX_GAP_MS:
        problems.append("largest e2e p50 gap is %.2f ms, prose claims %.2f"
                        % (max_gap, CLAIMED_MAX_GAP_MS))
    if round(max_gap_pct, 2) != CLAIMED_MAX_GAP_PCT:
        problems.append("largest e2e p50 gap is %.4f%%, prose claims %.2f%%"
                        % (max_gap_pct, CLAIMED_MAX_GAP_PCT))
    if len(arch) != 5:
        problems.append("latency_by_arch.csv has %d architectures, prose says "
                        "five" % len(arch))
    # The percentage and the millisecond figure must describe the SAME pair,
    # or the sentence pairs a gap with someone else's percentage.
    worst_pct = max(arch, key=lambda r: float(r["e2e_ms_p50_gap_pct"]))
    if worst_pct["model"] != worst["model"]:
        problems.append("the largest gap in ms (%s) and in %% (%s) are "
                        "different architectures"
                        % (worst["model"], worst_pct["model"]))

    # Establish which denominator latency_by_arch.csv uses, rather than assume
    # it: gap_pct == gap / mean is checkable directly from its own columns.
    arch_convention = "unknown"
    ok_mean = all(abs(float(r["e2e_ms_p50_gap_pct"])
                      - 100.0 * float(r["e2e_ms_p50_gap"])
                      / float(r["e2e_ms_p50_mean"])) < 0.01
                  for r in arch if float(r["e2e_ms_p50_mean"]))
    if ok_mean:
        arch_convention = "gap / mean"
    notes.append("latency_by_arch.csv expresses its gap percentages as %s."
                 % arch_convention)

    # ---- 4. per-session spread ---------------------------------------------
    # Deliberately reading the per-run latency_ms that collect_results.py
    # refuses to read. See the module docstring.
    session = {}
    for r in rows:
        path = os.path.join(KAGGLE_DIR, "results_%s.json" % r["run"])
        if not os.path.isfile(path):
            problems.append("results JSON not found for %s" % r["run"])
            continue
        with io.open(path, encoding="utf-8-sig") as fh:
            d = json.load(fh)
        p50 = (d.get("latency_ms") or {}).get("p50")
        if p50 is None:
            problems.append("%s: no latency_ms.p50 in its results JSON"
                            % r["run"])
            continue
        session.setdefault(r["model"], []).append((r["run"], float(p50)))

    spread = {}
    for model, pairs in sorted(session.items()):
        vals = [v for _, v in pairs]
        if len(vals) != 2:
            problems.append("%s: expected 2 per-session measurements, got %d"
                            % (model, len(vals)))
            continue
        lo_v, hi_v = min(vals), max(vals)
        gap = hi_v - lo_v
        # A gap can be expressed against three different denominators, and they
        # differ by several points at this magnitude. Which one is used has to
        # be stated, or two figures in the same paragraph can be computed on
        # different bases without either being wrong.
        spread[model] = {"runs": dict(pairs), "min": lo_v, "max": hi_v,
                         "gap_ms": gap,
                         "gap_pct": 100.0 * gap / lo_v,          # of smaller
                         "gap_pct_of_max": 100.0 * gap / hi_v,   # of larger
                         "gap_pct_of_mean": 100.0 * gap / ((lo_v + hi_v) / 2.0)}

    worst_session = max(spread.values(), key=lambda v: v["gap_pct"]) if spread else None
    worst_session_model = None
    convention = None
    if spread:
        worst_session_model = max(spread, key=lambda m: spread[m]["gap_pct"])
        # Which denominator, if any, reproduces the figure the prose states?
        for key, label in (("gap_pct", "the smaller of the pair"),
                           ("gap_pct_of_max", "the larger of the pair"),
                           ("gap_pct_of_mean", "the mean of the pair")):
            if round(worst_session[key]) == round(CLAIMED_SESSION_SPREAD_PCT):
                convention = (key, label, worst_session[key])
        if convention is None:
            problems.append(
                "no denominator reproduces the claimed %.0f%%: of-min %.2f%%, "
                "of-max %.2f%%, of-mean %.2f%%"
                % (CLAIMED_SESSION_SPREAD_PCT, worst_session["gap_pct"],
                   worst_session["gap_pct_of_max"],
                   worst_session["gap_pct_of_mean"]))
        else:
            notes.append(
                "the claimed %.0f%% is reproduced only by dividing the gap by "
                "%s (%.2f%%). The same paragraph's %.2f%% pair-gap figure comes "
                "from latency_by_arch.csv, which divides by the MEAN -- on that "
                "basis the cross-session figure is %.2f%%, and on the smaller "
                "value it is %.2f%%. The two percentages in this subsection are "
                "computed on different bases."
                % (CLAIMED_SESSION_SPREAD_PCT, convention[1], convention[2],
                   CLAIMED_MAX_GAP_PCT, worst_session["gap_pct_of_mean"],
                   worst_session["gap_pct"]))

    # ---- outputs -----------------------------------------------------------
    ec61.write_csv(
        os.path.join(run_dir, "fusion_reduction.csv"),
        ["model", "params_unfused", "params_fused", "params_drop",
         "params_drop_pct", "gflops_unfused", "gflops_fused", "gflops_drop_pct"],
        [[m, v["params_unfused"], v["params_fused"], v["params_drop"],
          round(v["params_drop_pct"], 4), v["gflops_unfused"],
          v["gflops_fused"], round(v["gflops_drop_pct"], 4)]
         for m, v in sorted(fusion.items())])

    ec61.write_csv(
        os.path.join(run_dir, "per_session_spread.csv"),
        ["model", "run_a", "p50_a", "run_b", "p50_b", "gap_ms",
         "gap_pct_of_min", "gap_pct_of_max", "gap_pct_of_mean"],
        [[m] + [x for pair in sorted(v["runs"].items()) for x in pair]
         + [round(v["gap_ms"], 4), round(v["gap_pct"], 4),
            round(v["gap_pct_of_max"], 4), round(v["gap_pct_of_mean"], 4)]
         for m, v in sorted(spread.items())])

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"master_csv": MASTER_CSV, "by_arch_csv": BY_ARCH_CSV,
                "latency_json": LATENCY_JSON, "quoted": QUOTED,
                "claimed_range_pct": CLAIMED_RANGE,
                "claimed_max_gap_ms": CLAIMED_MAX_GAP_MS,
                "claimed_max_gap_pct": CLAIMED_MAX_GAP_PCT,
                "claimed_session_spread_pct": CLAIMED_SESSION_SPREAD_PCT},
        extra={"inputs": {
                   os.path.relpath(p, ec61.REPO_ROOT): ec61._sha256_file(p)
                   for p in (MASTER_CSV, BY_ARCH_CSV, LATENCY_JSON)},
               "protocol": protocol, "environment": environment,
               "fusion": fusion, "per_session_spread": spread,
               "largest_pair_gap": {"model": worst["model"],
                                    "ms": max_gap, "pct": max_gap_pct},
               "problems": problems, "notes": notes})

    # ---- print -------------------------------------------------------------
    print("1  COMPLEXITY AND FUSION")
    print("   %-10s %12s %12s %8s   %8s %8s %8s"
          % ("model", "params_unf", "params_fus", "drop%",
             "gflops_u", "gflops_f", "drop%"))
    for m, v in sorted(fusion.items(), key=lambda kv: kv[1]["params_drop_pct"]):
        print("   %-10s %12d %12d %7.3f%%   %8.3f %8.3f %7.3f%%"
              % (m, v["params_unfused"], v["params_fused"],
                 v["params_drop_pct"], v["gflops_unfused"], v["gflops_fused"],
                 v["gflops_drop_pct"]))
    print("   parameter reduction range: %.4f%% to %.4f%%  "
          "(1 dp: %.1f%% to %.1f%%)  prose claims %.1f%% to %.1f%%"
          % (lo, hi, round(lo, 1), round(hi, 1), CLAIMED_RANGE[0],
             CLAIMED_RANGE[1]))
    print()
    print("2  PROTOCOL")
    for label, ok in checks:
        print("   [%s] %s" % ("ok " if ok else "FAIL", label))
    for k in sorted(protocol):
        print("   %-12s %s" % (k, protocol[k]))
    print("   gpu          %s" % environment.get("gpu"))
    print()
    print("3  DUPLICATE-MEASUREMENT RESOLUTION")
    for r in sorted(arch, key=lambda r: -float(r["e2e_ms_p50_gap"])):
        print("   %-10s gap %5.2f ms  %6.4f%%"
              % (r["model"], float(r["e2e_ms_p50_gap"]),
                 float(r["e2e_ms_p50_gap_pct"])))
    print("   largest: %s at %.2f ms / %.4f%%" % (worst["model"], max_gap,
                                                  max_gap_pct))
    print()
    print("4  PER-SESSION SPREAD (the measurements the pipeline refuses to use)")
    print("   %-10s %8s %8s %8s   %8s %8s %8s"
          % ("model", "min_ms", "max_ms", "gap_ms",
             "of_min%", "of_max%", "of_mean%"))
    for m, v in sorted(spread.items(), key=lambda kv: -kv[1]["gap_pct"]):
        print("   %-10s %8.2f %8.2f %8.2f   %7.2f%% %7.2f%% %7.2f%%"
              % (m, v["min"], v["max"], v["gap_ms"], v["gap_pct"],
                 v["gap_pct_of_max"], v["gap_pct_of_mean"]))
    if worst_session:
        print("   largest spread: %s" % worst_session_model)
        print("   prose claims 'up to %.0f%%'; that figure is reproduced by: %s"
              % (CLAIMED_SESSION_SPREAD_PCT,
                 convention[1] if convention else "NO denominator"))
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
        print("No contradictions found.")
    print()
    print("wrote %s" % run_dir)

    # ---- summary -----------------------------------------------------------
    L = ["# Efficiency-claim verification (section 5.5)", "",
         "Run directory: `%s`" % os.path.basename(run_dir), "",
         "## 1. Complexity and fusion", "",
         "| model | params unfused | params fused | drop | GFLOPs unfused | "
         "GFLOPs fused | drop |", "|---|---|---|---|---|---|---|"]
    for m, v in sorted(fusion.items(), key=lambda kv: kv[1]["params_drop_pct"]):
        L.append("| `%s` | %d | %d | %.3f%% | %.3f | %.3f | %.3f%% |"
                 % (m, v["params_unfused"], v["params_fused"],
                    v["params_drop_pct"], v["gflops_unfused"],
                    v["gflops_fused"], v["gflops_drop_pct"]))
    L += ["", "Parameter reduction spans **%.4f%% to %.4f%%**, which to one "
          "decimal is %.1f%% to %.1f%%." % (lo, hi, round(lo, 1), round(hi, 1)),
          "", "## 2. Protocol", ""]
    for k in sorted(protocol):
        L.append("- **%s**: %s" % (k, protocol[k]))
    L.append("- **gpu**: %s" % environment.get("gpu"))
    L += ["", "## 3. Duplicate-measurement resolution", "",
          "| model | e2e p50 gap (ms) | gap (%) |", "|---|---|---|"]
    for r in sorted(arch, key=lambda r: -float(r["e2e_ms_p50_gap"])):
        L.append("| `%s` | %.2f | %.4f |" % (r["model"],
                                             float(r["e2e_ms_p50_gap"]),
                                             float(r["e2e_ms_p50_gap_pct"])))
    L += ["", "Largest: `%s`, %.2f ms / %.4f%%." % (worst["model"], max_gap,
                                                    max_gap_pct),
          "", "## 4. Per-session spread", "",
          "These are the per-run `latency_ms` figures that `collect_results.py` "
          "refuses to read, because each was measured in its own Kaggle session. "
          "They are cited here as evidence of their own unreliability, which is "
          "the only claim they can support.", "",
          "| model | min p50 | max p50 | gap (ms) | gap (%) |",
          "|---|---|---|---|---|"]
    for m, v in sorted(spread.items(), key=lambda kv: -kv[1]["gap_pct"]):
        L.append("| `%s` | %.2f | %.2f | %.2f | %.2f |"
                 % (m, v["min"], v["max"], v["gap_ms"], v["gap_pct"]))
    L += ["", "## What could make this misleading", "",
          "- The per-session figures in section 4 are not comparable to the "
          "unified pass's numbers and must never be quoted as latencies. They "
          "measure session conditions as much as models.",
          "- Fusion percentages are computed from the unified pass's own "
          "before/after pair. They are not a claim about what any particular "
          "deployment toolchain would produce.",
          "- The pair gap is a resolution floor for THIS hardware and session. "
          "It does not bound run-to-run variation on other hardware.", ""]
    with io.open(os.path.join(run_dir, "summary.md"), "w",
                 encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
