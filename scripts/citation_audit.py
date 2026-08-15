"""
citation_audit.py -- one row per citation USE, for checking against sources

WHY PER USE AND NOT PER ENTRY

A bibliography check that lists each paper once answers "does this reference
exist". That is not the question that matters here. The same paper can genuinely
support one sentence and not another: `kong2026edge` supports a claim about edge
hardware in Section 8 and a claim about proxy metrics in Section 7, and either
could be right while the other is wrong. So every \\citep instance gets its own
row, carrying the sentence it actually sits in.

A multi-key citation such as \\citep{a,b} is expanded into one row per key, for
the same reason -- a pair of citations attached to one sentence is two claims.

THE THREE PRIOR STUDIES ARE LISTED SEPARATELY

electrocom61, yolov12paper and yolov13paper are the studies this paper argues
with, their PDFs are held, and they have already been checked. Everything else
in the bibliography is registry-resolved but unread, which is the state Section 8
concedes. Mixing the two in one table would hide that difference behind a uniform
list.

WHAT THIS CANNOT DO

It reports where a citation sits, not whether the citation is right. Reading the
sentence beside the source is the check; this only makes that check enumerable.

Run with no arguments:

    python scripts/citation_audit.py

Writes notes/citation-audit.md and a provenance record under
runs/<YYYYMMDD>_citation_audit/.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402


SECTIONS_DIR = os.path.join(ec61.REPO_ROOT, "paper", "sections")
BIB = os.path.join(ec61.REPO_ROOT, "paper", "references.bib")
OUT = os.path.join(ec61.REPO_ROOT, "notes", "citation-audit.md")

# The studies this paper argues with. PDFs held, already checked by the author.
PRIOR_STUDIES = ("electrocom61", "yolov12paper", "yolov13paper")

# Abbreviations whose full stop does not end a sentence. Without these the
# splitter cuts "et al." in half and reports a fragment as the citing sentence.
ABBREV = ("et al.", "e.g.", "i.e.", "cf.", "vs.", "Fig.", "Sec.", "Eq.",
          "approx.", "Dr.", "Mr.", "St.")


def strip_comments(text):
    """Remove LaTeX comment lines and trailing comments.

    Section headers in this project carry long % blocks that quote prose and
    name bib keys. Leaving them in would produce rows for citations that are
    not in the paper at all.
    """
    out = []
    for line in text.split("\n"):
        # A % escaped as \% is a literal percent sign, not a comment.
        idx = None
        for m in re.finditer(r"%", line):
            if m.start() == 0 or line[m.start() - 1] != "\\":
                idx = m.start()
                break
        out.append(line if idx is None else line[:idx])
    return "\n".join(out)


def split_sentences(text):
    """Split flowed text into sentences, protecting known abbreviations."""
    guarded = text
    for i, ab in enumerate(ABBREV):
        guarded = guarded.replace(ab, ab.replace(".", "\x00%d\x00" % i))
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z`\\(])", guarded)
    restored = []
    for p in parts:
        for i, ab in enumerate(ABBREV):
            p = p.replace(ab.replace(".", "\x00%d\x00" % i), ab)
        restored.append(p.strip())
    return [p for p in restored if p]


def tidy(sentence):
    """Light cleanup for reading. Citation commands are LEFT IN PLACE.

    They mark where in the sentence the citation actually sits, which is part of
    what is being checked -- a citation at the end of a compound sentence may be
    attached to the wrong clause.
    """
    # \label follows a heading, so it lands at the start of the first sentence
    # of a subsection and would otherwise appear inside the quoted text.
    s = re.sub(r"\\label\{[^}]*\}", "", sentence)
    s = s.replace("~", " ").replace("---", "\u2014")
    s = re.sub(r"``|''", '"', s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\texttt\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\%", "%", s)
    s = re.sub(r"\{,\}", ",", s)          # 12{,}937 -> 12,937
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def collect():
    """Every citation use, as (key, section, subsection, sentence, file)."""
    rows = []
    for fname in sorted(os.listdir(SECTIONS_DIR)):
        if not fname.endswith(".tex"):
            continue
        path = os.path.join(SECTIONS_DIR, fname)
        with open(path, "r", encoding="utf-8") as fh:
            body = strip_comments(fh.read())

        section = subsection = "(none)"
        # Walk the file in order so the most recent heading before a citation is
        # the one it belongs to. Splitting on headings first would lose that.
        chunks = re.split(r"(\\(?:sub)?section\*?\{[^}]*\})", body)
        for chunk in chunks:
            m = re.match(r"\\section\*?\{([^}]*)\}", chunk)
            if m:
                section, subsection = m.group(1), "(section opening)"
                continue
            m = re.match(r"\\subsection\*?\{([^}]*)\}", chunk)
            if m:
                subsection = m.group(1)
                continue
            flowed = " ".join(chunk.split())
            for sent in split_sentences(flowed):
                for keys in re.findall(r"\\cite[pt]?\{([^}]*)\}", sent):
                    for key in [k.strip() for k in keys.split(",") if k.strip()]:
                        rows.append((key, section, subsection,
                                     tidy(sent), fname))
    return rows


def table(rows):
    out = ["| bib key | section | subsection | sentence |",
           "|---|---|---|---|"]
    for key, sec, sub, sent, _f in rows:
        cell = sent.replace("|", "\\|")
        out.append("| `%s` | %s | %s | %s |" % (key, sec, sub, cell))
    return "\n".join(out)


def main():
    rows = collect()
    with open(BIB, "r", encoding="utf-8") as fh:
        bib_keys = set(re.findall(r"^@\w+\{([^,]+),", fh.read(), re.M))

    unknown = sorted({r[0] for r in rows} - bib_keys)
    if unknown:
        sys.stderr.write("cited but absent from references.bib: %s\n"
                         % ", ".join(unknown))
        return 1

    rows.sort(key=lambda r: (r[0], r[4], r[2]))
    prior = [r for r in rows if r[0] in PRIOR_STUDIES]
    rest = [r for r in rows if r[0] not in PRIOR_STUDIES]

    used = sorted({r[0] for r in rows})
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    multi = sorted(((k, n) for k, n in counts.items() if n > 1),
                   key=lambda t: (-t[1], t[0]))
    uncited = sorted(bib_keys - set(used))

    run_dir = ec61.make_run_dir("citation_audit")
    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"citation_instances": len(rows), "entries_cited": len(used),
                "entries_in_bib": len(bib_keys), "uncited": uncited,
                "prior_study_instances": len(prior)},
        extra={"output": os.path.relpath(OUT, ec61.REPO_ROOT),
               "unit": "one row per citation USE, not per entry"},
    )
    ec61.write_csv(
        os.path.join(run_dir, "citation_instances.csv"),
        ["bib_key", "section", "subsection", "sentence", "file"],
        [list(r) for r in rows],
    )

    lines = [
        "# Citation audit",
        "",
        "Generated by `scripts/citation_audit.py`; run record in "
        "`runs/%s/`. Regenerate after any change to the prose or the "
        "bibliography rather than editing this file." % os.path.basename(run_dir),
        "",
        "**One row per citation USE, not per entry.** The same paper can support "
        "one sentence and not another, so each `\\citep` instance is listed "
        "separately and a multi-key citation is expanded into one row per key. "
        "Citation commands are left inside the sentences: where in a sentence a "
        "citation sits is part of what needs checking.",
        "",
        "This sheet records where each citation sits. It cannot record whether "
        "the citation is correct --- that is what reading the sentence beside "
        "the source is for.",
        "",
        "## Counts",
        "",
        "| | |",
        "|---|---|",
        "| citation instances | **%d** |" % len(rows),
        "| distinct entries cited | **%d** |" % len(used),
        "| entries in `references.bib` | %d |" % len(bib_keys),
        "| entries cited but never re-used (one instance) | %d |"
        % (len(used) - len(multi)),
        "| entries cited in more than one place | **%d** |" % len(multi),
        "| entries in the bibliography with no citation | %d%s |"
        % (len(uncited), (" (`%s`)" % "`, `".join(uncited)) if uncited else ""),
        "",
        "### Entries cited in more than one place",
        "",
        "These need the most care: each use is a separate claim, and the sheet "
        "below lists them together so a paper's uses can be worked through in "
        "one pass.",
        "",
        "| bib key | uses |",
        "|---|---|",
    ]
    for k, n in multi:
        lines.append("| `%s` | %d |" % (k, n))

    lines += [
        "",
        "## The three prior studies",
        "",
        "PDFs held and already checked. These are the studies this paper argues "
        "with; every claim about them should be verifiable against a page.",
        "",
        table(prior),
        "",
        "## Everything else",
        "",
        "Registry-resolved but **not read from within this repository**, which "
        "is the state Section 8 concedes. Each row is a sentence that asserts "
        "something about the cited work.",
        "",
        table(rest),
        "",
    ]

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("citation instances : %d" % len(rows))
    print("entries cited      : %d of %d in references.bib"
          % (len(used), len(bib_keys)))
    print("cited >1 place     : %d" % len(multi))
    for k, n in multi:
        print("    %-24s %d" % (k, n))
    if uncited:
        print("uncited entries    : %s" % ", ".join(uncited))
    print("\nwrote %s" % os.path.relpath(OUT, ec61.REPO_ROOT))
    print("run  %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
