"""
check_prose.py -- check the manuscript's PROSE, which nothing else in the suite does

WHY THIS EXISTS

Every other verification script checks numbers against committed files. None of
them reads a sentence. On 2026-08-18 a doubled verb -- "What it does does not
state" -- was found in Section 7.1 by eye, having survived several commits and
several clean builds. LaTeX compiles a doubled word without complaint, the
citation tools do not look at it, and the build script only greps the printed
bibliography. There was no check that could have caught it.

There is a second gap this closes. notes/writing-plan.md records wording that
must not drift and figures that have a single home, and every one of those rules
was enforced by a human remembering it. Several are recorded precisely because
they were broken once already.

HOW THE PLAN AND THIS SCRIPT ARE KEPT IN STEP

The single-homes table is PARSED from writing-plan.md, so adding a row there adds
a check here with no edit to this file.

The prose rules cannot be parsed -- they are English sentences, and a parser that
pretended otherwise would fail silently in both directions. Instead each rule
carries a `plan_anchor`: an exact substring that must still appear in
writing-plan.md. If someone rewrites the plan, the anchor stops matching and this
script FAILS with the rule that lost its basis. The rules are hand-written; what
is mechanical is that none of them can outlive the plan text it came from.

WHAT IS A FAILURE AND WHAT IS A WARNING

Deterministic checks FAIL: a doubled word, a missing protected phrase, a present
forbidden phrase, a figure absent from its stated home, a broken anchor.

The bare-mAP@50 rule WARNS. Rule 4 of the plan forbids a bare mAP@50, but
quotations of prior work legitimately carry one -- 01-introduction.tex's header
says so explicitly, because no published mAP@50-95 exists on this dataset to pair
with. A hard failure there would be wrong more often than right, so the check
reports each unpaired occurrence with its context and leaves the judgement to a
reader.

WHAT IS SKIPPED, AND WHY IT IS COUNTED

Comments, math mode and verbatim environments are removed before any check runs.
A skip that is silent can hide a failure -- a doubled word inside a stripped
region would simply never be looked at -- so the counts are printed.
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


PAPER_DIR = os.path.join(ec61.REPO_ROOT, "paper")
MAIN_TEX = os.path.join(PAPER_DIR, "main.tex")
SECTIONS_DIR = os.path.join(PAPER_DIR, "sections")
PLAN = os.path.join(ec61.REPO_ROOT, "notes", "writing-plan.md")

# Words that may legitimately repeat in English prose. Kept deliberately short:
# a long allowlist is how a real doubled word gets waved through. Each entry
# needs a reason, and "it looked fine" is not one.
#   had   -- "the split had had no test instances" (past perfect)
#   that  -- "the fact that that column is derived"
#   long  -- "a long long-tail" style hyphenation is not used here, but the
#            token pair is harmless and appears in no failure we would want
# Nothing else is allowed. If a new pair is genuinely correct, add it WITH the
# sentence that justified it.
DOUBLED_ALLOW = {"had", "that"}


# ---------------------------------------------------------------------------
# THE PROSE RULES.
#
# Each carries plan_anchor: text that must still be present in
# notes/writing-plan.md. The anchor is what stops this table drifting away from
# the plan it encodes -- if the plan is rewritten, the anchor fails and the rule
# is flagged as having lost its basis rather than quietly enforcing a rule
# nobody agreed to any more.
#
# kind:
#   present  -- pattern must appear, `count` times if given, in `where`
#   absent   -- pattern must appear nowhere
# where: None means the whole paper; otherwise a list of section ids ("1",
#   "2.1", "abstract").
# ---------------------------------------------------------------------------
RULES = [
    dict(
        rid="deviation-phrasing",
        kind="present",
        pattern=r"with a single documented deviation",
        where=["abstract", "1", "9"],
        count=3,
        why="The exact phrasing replaced a bare 'under a single configuration', "
            "which flattened 5.3.",
        plan_anchor='**"under one configuration, with a single documented '
                    'deviation."**',
    ),
    dict(
        rid="deviation-bare-form",
        kind="absent",
        pattern=r"under a single configuration",
        where=None,
        why="The bare form is the regression the plan records.",
        plan_anchor='it replaced a bare "under a single\n   configuration"',
    ),
    dict(
        rid="section9-otherwise-holds",
        kind="present",
        pattern=r"otherwise holds",
        where=["9"],
        count=1,
        why="Section 9 said 'holds every setting but the architecture fixed', "
            "which 5.3 contradicts.",
        plan_anchor='it now reads "otherwise holds"',
    ),
    dict(
        rid="section9-contradicted-form",
        kind="absent",
        # The phrase itself is fine once "otherwise" qualifies it -- that IS the
        # repair the plan records, and Section 9 legitimately reads "otherwise
        # holds every setting but the architecture fixed". What is forbidden is
        # the unqualified form. Matching the bare phrase failed Section 9 for
        # containing its own fix, on this script's first run.
        pattern=r"(?<!otherwise )holds every setting but the architecture fixed",
        where=None,
        why="The unqualified form 5.3 flatly contradicts; 'otherwise holds' is "
            "the repair and is correct.",
        plan_anchor='Section 9 additionally said "holds every setting but the '
                    'architecture fixed"',
    ),
    dict(
        rid="tabulate-wording",
        kind="present",
        pattern=r"none of which the three prior studies tabulate",
        where=["1"],
        count=1,
        why="Exact wording for the mAP@50-95 claim; the loose form reached a "
            "built PDF once.",
        plan_anchor='The wording "none of\nwhich the three prior studies '
                    'tabulate" is exact',
    ),
    dict(
        rid="tabulate-loose-form",
        kind="absent",
        pattern=r"no prior study reports",
        where=None,
        why="The false generalisation the plan names.",
        plan_anchor='must not drift back to "no prior study reports"',
    ),
    dict(
        rid="quarter-never-bare",
        kind="absent",
        # "a quarter" NOT preceded by "more than". 27.0% is more than a quarter,
        # so the bare form understates the finding.
        pattern=r"(?<!more than )(?<!More than )a quarter",
        where=None,
        why="27.0% is more than a quarter; the bare form understates it.",
        plan_anchor='Never "a quarter" — 27.0% is more.',
    ),
    dict(
        rid="abstract-names-no-model",
        kind="absent",
        pattern=r"RT-DETR|YOLO26s|YOLOv9s|YOLO11s",
        where=["abstract"],
        why="The abstract names no model, which removes the "
            "'most accurate' hazard entirely.",
        plan_anchor="The abstract names no model, which removes the hazard "
                    "entirely.",
    ),
    dict(
        rid="most-accurate-forbidden",
        kind="absent",
        pattern=r"most accurate",
        # ABSTRACT ONLY. The plan lists this under the abstract's constraints,
        # and the hazard it names is calling the mAP@50 leader "most accurate".
        # Section 1 legitimately contains "the model that can be deployed is not
        # necessarily the most accurate one available" -- the motivating
        # observation, about no model in particular, and the premise the whole
        # deployment argument rests on. Scoping this to 1 and 9 failed that
        # sentence on the script's first run.
        where=["abstract"],
        why="RT-DETR-l leads mAP@50 only; YOLO26s leads mAP@50-95.",
        plan_anchor='Any\n   phrasing like "most accurate" is wrong.',
    ),
    # INVERTED 2026-08-18, when the Zenodo DOI was minted. This rule used to
    # assert that Section 10 contained exactly two \fbox placeholders, because
    # the plan recorded them as deliberately unmissable in a proof. Filling them
    # correctly failed the rule, which is the drift guard working: the rule had
    # outlived the decision behind it. It now asserts the opposite -- that no
    # placeholder survives anywhere -- which is the thing worth protecting once
    # a DOI is published and cannot be withdrawn.
    dict(
        rid="no-placeholder-survives",
        kind="absent",
        pattern=r"\\fbox\{",
        where=None,
        why="The DOI and release tag are minted and filled; a returning "
            "placeholder would ship an unfilled availability statement.",
        plan_anchor="no `\\fbox` placeholder remains\n   anywhere in the "
                    "document",
    ),
]


# ---------------------------------------------------------------------------
# Section -> file. Derived from main.tex's \input order rather than hardcoded,
# so renaming or reordering a section file cannot leave this stale.
# ---------------------------------------------------------------------------
def section_files():
    with io.open(MAIN_TEX, "r", encoding="utf-8") as fh:
        main = fh.read()
    inputs = re.findall(r"\\input\{sections/([0-9a-zA-Z-]+)\}", main)
    mapping = {}
    n = 0
    for stem in inputs:
        path = os.path.join(SECTIONS_DIR, stem + ".tex")
        if not os.path.exists(path):
            continue
        with io.open(path, "r", encoding="utf-8") as fh:
            body = fh.read()
        if not re.search(r"^\\section\{", body, re.M):
            continue          # appendix-style file with no numbered section
        n += 1
        mapping[str(n)] = path
    mapping["abstract"] = MAIN_TEX
    return mapping


SKIPS = {"comment_lines": 0, "inline_comments": 0, "math_spans": 0,
         "verbatim_blocks": 0}


def prose_lines(path):
    """Return [(lineno, text)] of prose only, counting everything removed.

    Line numbers are preserved through the stripping so a failure can name the
    line in the file rather than in some cleaned copy of it.
    """
    with io.open(path, "r", encoding="utf-8") as fh:
        raw = fh.read().split("\n")

    out = []
    in_verbatim = False
    for i, line in enumerate(raw, start=1):
        if re.match(r"\s*\\begin\{(verbatim|lstlisting)\}", line):
            in_verbatim = True
            SKIPS["verbatim_blocks"] += 1
            continue
        if re.match(r"\s*\\end\{(verbatim|lstlisting)\}", line):
            in_verbatim = False
            continue
        if in_verbatim:
            continue
        if line.lstrip().startswith("%"):
            SKIPS["comment_lines"] += 1
            continue
        # strip an inline comment: a % that is not escaped as \%
        m = re.search(r"(?<!\\)%", line)
        if m:
            SKIPS["inline_comments"] += 1
            line = line[:m.start()]
        # strip math
        line, k1 = re.subn(r"\$[^$]*\$", " ", line)
        line, k2 = re.subn(r"\\\[.*?\\\]", " ", line)
        line, k3 = re.subn(r"\\\(.*?\\\)", " ", line)
        SKIPS["math_spans"] += k1 + k2 + k3
        out.append((i, line))
    return out


def prose_text(path):
    return "\n".join(t for _, t in prose_lines(path))


def subsection_text(path, index):
    """Text of the index-th (1-based) \\subsection of a section file."""
    lines = prose_lines(path)
    blocks, cur, seen = [], [], 0
    for _, t in lines:
        if re.match(r"\s*\\subsection\{", t):
            seen += 1
            if seen > 1:
                blocks.append("\n".join(cur))
            cur = [t]
        elif seen >= 1:
            cur.append(t)
    if cur:
        blocks.append("\n".join(cur))
    return blocks[index - 1] if 0 < index <= len(blocks) else ""


def scope_text(sec_id, files):
    """Text for a section id: '1', '2.1', 'abstract'."""
    if sec_id == "abstract":
        whole = prose_text(MAIN_TEX)
        m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", whole, re.S)
        return m.group(1) if m else ""
    if "." in sec_id:
        top, sub = sec_id.split(".", 1)
        path = files.get(top)
        return subsection_text(path, int(sub)) if path else ""
    path = files.get(sec_id)
    return prose_text(path) if path else ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_doubled(files, results):
    """Doubled words, joining consecutive lines so a break cannot hide one."""
    seen_paths = sorted(set(files.values()))
    hits = 0
    for path in seen_paths:
        lines = prose_lines(path)
        for (n1, a), (n2, b) in zip(lines, lines[1:]):
            joined = a.rstrip() + " " + b.lstrip()
            for m in re.finditer(r"\b([A-Za-z]{2,})\s+\1\b", joined,
                                 re.IGNORECASE):
                if m.group(1).lower() in DOUBLED_ALLOW:
                    continue
                hits += 1
                ctx = joined[max(0, m.start() - 40):m.end() + 30].strip()
                results.append(
                    (False, "doubled-word",
                     "%s L%d-%d: ...%s..." % (os.path.basename(path), n1, n2,
                                              ctx)))
    if not hits:
        results.append((True, "doubled-word",
                        "no doubled word in %d file(s)" % len(seen_paths)))


def parse_single_homes():
    """Parse the single-homes table out of writing-plan.md.

    Returns [(figure_label, [tokens], [home_section_ids])]. Tokens are the
    numeric strings that identify the figure; home ids are the bolded section
    numbers in the Home column.
    """
    with io.open(PLAN, "r", encoding="utf-8") as fh:
        plan = fh.read()
    m = re.search(r"### Single homes for repeated figures.*?\n\|.*?\n\|[-|\s]+\n(.*?)\n\n",
                  plan, re.S)
    if not m:
        return []
    rows = []
    for line in m.group(1).strip().split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        figure, home = cells[0], cells[1]
        tokens = re.findall(r"\d+\.\d+|\d{2,}", figure)
        homes = re.findall(r"\*\*([0-9]+(?:\.[0-9]+)?)\*\*", home)
        if tokens and homes:
            rows.append((figure, tokens, homes))
    return rows


def check_single_homes(files, results):
    rows = parse_single_homes()
    if not rows:
        results.append((False, "single-homes",
                        "could not parse the table out of notes/writing-plan.md"
                        " -- has its heading or shape changed?"))
        return
    for figure, tokens, homes in rows:
        for home in homes:
            text = scope_text(home, files)
            if not text:
                results.append((False, "single-homes",
                                "%s: home %s resolves to no text"
                                % (figure[:40], home))); continue
            missing = [t for t in tokens if t not in text]
            if missing:
                results.append(
                    (False, "single-homes",
                     "%s: %s absent from its stated home %s"
                     % (figure[:40], ", ".join(missing), home)))
            else:
                results.append(
                    (True, "single-homes",
                     "%s: %s present in %s"
                     % (figure[:40], ", ".join(tokens), home)))


def check_rules(files, results):
    with io.open(PLAN, "r", encoding="utf-8") as fh:
        plan = fh.read()
    plan_flat = re.sub(r"\s+", " ", plan)

    for rule in RULES:
        anchor = re.sub(r"\s+", " ", rule["plan_anchor"])
        if anchor not in plan_flat:
            results.append(
                (False, "plan-anchor",
                 "%s: its basis is no longer in writing-plan.md -- looked for "
                 "%r" % (rule["rid"], rule["plan_anchor"][:60])))
            continue

        # Whitespace is normalised before matching. A protected phrase is
        # wrapped by the source at whatever column it lands on -- Section 9's
        # "with a single documented\ndeviation" is a real example -- and a rule
        # that matched raw text would report a phrase missing because of where
        # the line broke. This cost one false FAIL on the script's first run.
        if rule["where"] is None:
            scopes = [(sid, scope_text(sid, files))
                      for sid in sorted(set(files) - {"abstract"},
                                        key=lambda s: int(s))]
        else:
            scopes = [(sid, scope_text(sid, files)) for sid in rule["where"]]
        scopes = [(sid, re.sub(r"\s+", " ", text)) for sid, text in scopes]

        total = 0
        where_found = []
        for sid, text in scopes:
            n = len(re.findall(rule["pattern"], text))
            total += n
            if n:
                where_found.append("%s x%d" % (sid, n))

        if rule["kind"] == "absent":
            ok = total == 0
            results.append(
                (ok, rule["rid"],
                 "absent as required" if ok
                 else "PRESENT in %s -- %s" % (", ".join(where_found),
                                               rule["why"])))
        else:
            want = rule.get("count")
            ok = total > 0 and (want is None or total == want)
            results.append(
                (ok, rule["rid"],
                 "found %d in %s" % (total, ", ".join(where_found) or "-")
                 if ok else
                 "found %d, expected %s (%s) -- %s"
                 % (total, want if want is not None else ">0",
                    ", ".join(where_found) or "nowhere", rule["why"])))


def check_bare_map(files, warnings):
    """Rule 4: never a bare mAP@50. WARNS -- prior-work quotations carry one."""
    for sid in sorted(set(files) - {"abstract"}, key=lambda s: int(s)):
        path = files[sid]
        lines = prose_lines(path)
        # paragraph-level: a bare mAP@50 is acceptable if the paragraph pairs it
        para, start = [], None
        paras = []
        for n, t in lines:
            if t.strip() == "":
                if para:
                    paras.append((start, " ".join(para)))
                para, start = [], None
            else:
                if start is None:
                    start = n
                para.append(t)
        if para:
            paras.append((start, " ".join(para)))
        for start, text in paras:
            if "mAP@50" not in text:
                continue
            bare = len(re.findall(r"mAP@50(?!--95|-95)", text))
            paired = len(re.findall(r"mAP@50--95|mAP@50-95", text))
            if bare and not paired:
                warnings.append(
                    "%s L%d: mAP@50 x%d with no mAP@50--95 in the paragraph"
                    % (os.path.basename(path), start, bare))


def main():
    files = section_files()
    results, warnings = [], []

    check_doubled(files, results)
    check_single_homes(files, results)
    check_rules(files, results)
    check_bare_map(files, warnings)

    print("PROSE CHECKS")
    print()
    width = max(len(r[1]) for r in results)
    n_pass = n_fail = 0
    for ok, rid, msg in results:
        print("  [%s] %-*s  %s" % ("PASS" if ok else "FAIL", width, rid, msg))
        if ok:
            n_pass += 1
        else:
            n_fail += 1

    print()
    print("SKIPPED BEFORE CHECKING (counted so a silent skip cannot hide a "
          "failure)")
    for k in sorted(SKIPS):
        print("  %-18s %d" % (k, SKIPS[k]))

    print()
    print("WARNINGS -- rule 4, bare mAP@50. Prior-work quotations legitimately")
    print("carry one, so these are reported and not failed.")
    if warnings:
        for w in warnings:
            print("  %s" % w)
    else:
        print("  none")

    print()
    print("%d passed, %d FAILED" % (n_pass, n_fail))

    run_dir = ec61.make_run_dir("check_prose")
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"plan": PLAN, "n_rules": len(RULES),
                "sections_checked": len(files) - 1,
                "doubled_allowlist": sorted(DOUBLED_ALLOW)},
        extra={"passed": n_pass, "failed": n_fail,
               "warnings": len(warnings), "skips": SKIPS})
    ec61.write_csv(
        os.path.join(run_dir, "prose_checks.csv"),
        ["result", "check", "detail"],
        [["PASS" if ok else "FAIL", rid, msg] for ok, rid, msg in results])

    print("record: %s" % run_dir)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
