"""
citation_verification.py -- one sitting's worth of citation checking, assembled

WHAT THIS IS FOR

Section 8 concedes that every bibliography entry except the three prior studies
is registry-resolved but UNREAD. `citation_audit.py` makes that checkable by
listing all 80 citation uses with their sentences. This script goes one step
further and assembles the material needed to actually do the check: for each
entry, the paper's own abstract set beside every sentence in this paper that
cites it, so a reader can decide in one pass whether our sentence is supported.

It does not verify anything. It removes the fetching and cross-referencing so
that the judgement -- the only part that cannot be automated -- is all that is
left.

ORDERED BY RISK, NOT ALPHABETICALLY

The ordering is the point. A citation that says "this paper reports X" can be
wrong in a way that matters; a citation that says "this architecture comes from
this paper" essentially cannot. Entries are grouped into four tiers, hardest
first, so that a reader who stops halfway has checked the claims worth checking.

  tier 1  our sentence asserts a FINDING of theirs
  tier 2  our sentence describes their work, but not a numeric result
  tier 3  the paper is cited as the source of a model or a piece of software
  tier 0  already verified against the source; listed for completeness

WHERE THE ABSTRACT COMES FROM, AND WHERE IT DOES NOT

Three registries, tried in the order most likely to hold the text:

  Crossref   for ordinary DOIs -- but only if the publisher deposited an
             abstract, and most do not. On this bibliography Crossref ALONE
             returned 4 of 36.
  OpenAlex   the fallback that does the work. It reconstructs an abstract from
             an inverted index and covers Elsevier, Nature and IEEE, which
             deposit nothing to Crossref.
  DataCite   authoritative for arXiv's 10.48550/arXiv.* DOIs, which Crossref
             does not hold at all.

The arXiv API is attempted last and fails on this machine: export.arxiv.org and
arxiv.org both fail certificate verification here, while all three registries
above verify fine. Certificate verification is deliberately NOT disabled to work
around that. It costs nothing, because every arXiv entry in this bibliography
also carries a 10.48550 DOI that DataCite serves.

An entry with no fetchable abstract gets a block saying so and a DOI link,
because a silent gap in this file would read as "nothing to check here".

NOTHING HERE IS EVIDENCE. An abstract is the authors' summary of their own
paper, so it can support a decision to READ the paper and can flag a citation
that is plainly wrong. It cannot confirm that a specific claim is correct. Any
entry whose sentence rests on a number or a specific finding needs the full
text, and this file is where to start rather than where to stop.

Run with no arguments:

    python scripts/citation_verification.py

Writes notes/citation-verification.md and runs/<YYYYMMDD>_citation_verification/.
Requires network access for the fetches; entries that fail are reported as
failures rather than skipped.
"""

import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from xml.etree import ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec61  # noqa: E402
import citation_audit  # noqa: E402


BIB = os.path.join(ec61.REPO_ROOT, "paper", "references.bib")
AUX = os.path.join(ec61.REPO_ROOT, "paper", "main.aux")
OUT = os.path.join(ec61.REPO_ROOT, "notes", "citation-verification.md")

# Crossref asks for a contact address and rewards it with the polite pool.
USER_AGENT = ("ec61-citation-verification/1.0 "
              "(https://github.com/DiyarWalaa/electrocom61-benchmark; "
              "mailto:diyarwala@gmail.com)")
CROSSREF = "https://api.crossref.org/works/%s"
OPENALEX = "https://api.openalex.org/works/doi:%s"
DATACITE = "https://api.datacite.org/dois/%s"
ARXIV = "https://export.arxiv.org/api/query?id_list=%s"
TIMEOUT = 30
PAUSE = 1.0          # one request a second; Crossref's stated courtesy rate

# ---------------------------------------------------------------------------
# The risk ordering.
#
# Tier 1 is every entry whose citing sentence asserts something the cited paper
# FOUND -- a result, a measured relationship, a demonstrated effect. These are
# the ones where being wrong changes what this paper claims, and they are what
# a single sitting should spend itself on.
#
# THE ORDER WITHIN TIER 1 IS ALSO DELIBERATE. kong2026edge is first because it
# is cited three times for three DIFFERENT claims, so one reading settles three
# risks at once and a single misreading would have propagated three ways.
# ---------------------------------------------------------------------------
TIER1 = [
    "kong2026edge",           # 3 uses, 3 distinct claims
    "kapoor2023leakage",
    "vasu2023mobileone",      # efficiency proxy
    "chen2023run",            # efficiency proxy
    "picard2021seed",         # seed / variance
    "gundersen2023reporting", # seed / variance
    "akesson2024random",      # seed / variance -- see the note in the file
    "rosenblatt2024leakage",  # group structure
    "bernett2024guiding",     # group structure
    "joeres2025datasail",
    "figueiredo2024leakage",  # group-aware splitting applied to detection
    "gupta2019lvis",          # long-tail rarity; the acknowledged complement
    "yolov12notebook",        # what the released training code actually runs
]

# Tier 0: checked against the source already, so no re-reading is needed.
TIER0 = ["graber2025resolving", "graber2025addendum"]

# ---------------------------------------------------------------------------
# WHAT HAS ACTUALLY BEEN CHECKED, AND AGAINST WHAT.
#
# Filled by hand as the reading pass proceeds. It is a record of the author's
# judgement, not a measurement, so nothing here can be derived and nothing here
# should be inferred -- an entry absent from this table has NOT been checked.
#
# THE DISTINCTION BETWEEN full text AND abstract only IS THE REASON THIS EXISTS.
# An abstract is the authors' summary of their own work: it can expose a
# citation that is plainly wrong, and it cannot confirm that a specific claim is
# right. An entry verified from an abstract alone is in a weaker state than one
# verified from the full text, and if this study ever describes its own
# verification method it must not present the two as equivalent.
# ---------------------------------------------------------------------------
FULL_TEXT = "full text"
ABSTRACT_ONLY = "abstract only"
CORRECTED = "corrected"

STATUS_TEXT = {
    FULL_TEXT: "**Verified against the full text.** Passing, no action.",
    ABSTRACT_ONLY: ("**Verified from the ABSTRACT ONLY.** The full text is "
                    "paywalled and was not available. An abstract can expose a "
                    "citation that is plainly wrong but cannot confirm that a "
                    "specific claim is right, so this entry is in a weaker "
                    "state than the ones checked against a full text."),
    CORRECTED: ("**Checked against the full text; the citation was WRONG and "
                "has been corrected.**"),
}

VERIFICATION = {
    "yolov12notebook": (
        FULL_TEXT,
        "Read in full, August 2026 -- all six source cells and all 234 outputs "
        "of the training cell, as JSON rather than as a render. Full derivation "
        "in reports/C15-elhenidy-notebook.txt. Cited in 5.2 for the optimizer "
        "override (AdamW at lr 0.000154 while the supplied 0.01 is reported "
        "ignored) and in 7.2 for the class count the framework prints (45 "
        "classes with validation instances, 16 with none). NOT CITED, AND MUST "
        "NOT BE, FOR WHAT PRODUCED THE PUBLISHED TABLE: of the five quantities "
        "comparable with that paper's TABLE I row for YOLOv12S, only mAP@0.5 "
        "matches. It has no author field of its own; the entry records the "
        "publishing account, taken from the URL."),
    "figueiredo2024leakage": (
        FULL_TEXT,
        "Read in full, August 2026. Cited in 2.3 and 4.2 for a construction, "
        "not a figure. It clusters video frames by image feature and allocates "
        "whole clusters rather than individual frames, and reports that "
        "detection scores fall against the corrected split -- which is the "
        "same direction as the binding-affinity correction and the OPPOSITE of "
        "this paper's. It also fixed a factual error: 4.2 had called "
        "group-aware splitting something \"leakage-avoiding tools apply in "
        "other domains\", when object detection is this paper's own domain. "
        "Author count resolved from Crossref: TWO, not \"et al.\""),
    "gupta2019lvis": (
        FULL_TEXT,
        "Read in full, August 2026. Cited in 2.3 and 3.1 for two statements "
        "that paper makes about itself: that rarity in a long tail is defined "
        "by how many training images a category appears in, and that the "
        "categories reaching its validation and test partitions may be a "
        "strict subset of those in training (its Section 2.3 footnote). THE "
        "SECOND IS THE DELICATE ONE. It is an acknowledgement of the "
        "possibility, not a measurement of it: that paper states the breakdown "
        "is not reported. Neither sentence here gives a count, and neither "
        "says that benchmark exhibits the defect. Do not add a figure to "
        "either; there is no published one to add."),
    "apicella2025leakage": (FULL_TEXT, ""),
    "rosenblatt2024leakage": (
        FULL_TEXT,
        "The phrase \"samples from the same source\" does not appear in the "
        "source and does not need to: it is this paper's own framing of the "
        "general condition, not an attributed claim. The citation sits on "
        "\"shown directly for connectome-based models\", which is exact."),
    "kapoor2023leakage": (FULL_TEXT, ""),
    "picard2021seed": (FULL_TEXT, ""),
    "gundersen2023reporting": (
        FULL_TEXT,
        "Reading it also supplied the clause now in Section 8: the paper "
        "declines to recommend a seed count because running enough of them is "
        "impractical for most laboratories, and treats initialisation seeds as "
        "a reasonable proxy for exploratory studies. Section 8 had been citing "
        "its severity while omitting its stated practical limit."),
    "kong2026edge": (FULL_TEXT, ""),
    "graber2025resolving": (
        FULL_TEXT,
        "Reading it found a claim that had to be REMOVED. 2.3 and 7.3 said "
        "\"two groups independently\" corrected this benchmark, citing this "
        "paper together with its addendum -- but an addendum is not a second "
        "group, being the same six authors in the same journal. The genuinely "
        "independent work is a preprint the addendum acknowledges, which is "
        "not in this bibliography, so the claim was removed rather than "
        "sourced. Also: the drop was NOT uniform. The authors' own GEMS model "
        "held on the corrected split and GenScore fell by much less than "
        "Pafnucy. Both sentences are scoped to PREVIOUSLY REPORTED "
        "performance, which excludes GEMS by construction, and 2.3 says \"by "
        "margins that differed between models\"."),
    "graber2025addendum": (
        FULL_TEXT,
        "Read, and then DELIBERATELY UNCITED. With the two-groups clause gone "
        "it carries no claim of its own. The entry is kept so the resolved "
        "bibliographic record survives; BibTeX prints only cited entries, so "
        "it costs nothing in the PDF. Re-citing it is how the removed error "
        "would come back."),
    "bernett2024guiding": (
        ABSTRACT_ONLY,
        "The abstract was enough to find a real defect: the framework is scoped "
        "to \"constructing machine learning models in biological domains\" and "
        "its seven questions concern homology, shared patients and "
        "experimental batches, while 2.3 had cited it for a domain-general "
        "claim. 2.3 now says \"for biological domains\". What the abstract "
        "CANNOT settle is whether the checklist framing itself is described "
        "accurately; that needs the full text."),
    "vasu2023mobileone": (
        CORRECTED,
        "2.4 and 7.4 said \"parameter counts and FLOPs both correlate poorly "
        "with measured on-device latency\" and co-cited this with chen2023run. "
        "This paper reports an ASYMMETRY -- Spearman 0.30 (p = 0.18) for "
        "parameter count against 0.47 (p = 0.03) for FLOPs -- which \"both "
        "poorly\" flattened. Values recorded in "
        "data/published_proxy_claims.csv."),
    "chen2023run": (
        CORRECTED,
        "Carried half of the same false co-citation. It says nothing about "
        "parameter counts and reports no correlation coefficients at all; its "
        "claim is that reducing FLOPs does not reduce latency proportionally, "
        "because latency is FLOPs over an achieved FLOPS rate that collapses "
        "for memory-bound operators. Both sentences were rewritten so each "
        "citation carries only what its paper states."),
}

# Tier 3: the citation asserts only that this paper is where a model or a piece
# of software comes from. Wrong attribution is possible but would be obvious,
# and no sentence here rests on a finding.
TIER3 = ["yolov9", "yolo11", "yolov12", "yolov13", "yolo26", "rtdetr",
         "ultralytics", "yolov13repo"]

TIER_TITLE = {
    1: "Tier 1 --- our sentence asserts a finding of theirs",
    2: "Tier 2 --- our sentence describes their work",
    3: "Tier 3 --- cited as the source of a model or software",
    0: "Tier 0 --- already verified",
}
TIER_NOTE = {
    1: ("Read these first. Each sentence below claims the cited paper "
        "established something. If the abstract does not support the claim, "
        "the sentence has to change or the citation has to go."),
    2: ("These describe someone else's work without resting on one of their "
        "numbers. A mismatch here is usually a wording fix rather than a "
        "retraction."),
    3: ("The claim is only that this paper is where the architecture or the "
        "software comes from. Check the attribution, not a finding; this tier "
        "is last because it is the one that essentially cannot be wrong."),
    0: ("Verified against the source already. Listed so the file covers the "
        "whole bibliography and nothing looks skipped."),
}


def read_bib():
    """key -> {title, doi, arxiv} for every entry in references.bib."""
    src = io.open(BIB, encoding="utf-8").read()
    out = {}
    for block in re.split(r"(?m)^@", src)[1:]:
        m = re.match(r"\w+\s*\{\s*([^,]+),", block)
        if not m:
            continue
        key = m.group(1).strip()

        def field(name):
            f = re.search(r"(?im)^\s*%s\s*=\s*[{\"](.+?)[}\"],?\s*$" % name,
                          block)
            return re.sub(r"[{}]", "", f.group(1)).strip() if f else ""

        doi = field("doi")
        arxiv = field("eprint") or field("arxivid")
        if not arxiv:
            # A 10.48550/arXiv.NNNN.NNNNN DOI carries the identifier already.
            m2 = re.match(r"(?i)10\.48550/arxiv\.(.+)$", doi)
            if m2:
                arxiv = m2.group(1)
        if not arxiv:
            url = field("url")
            m3 = re.search(r"arxiv\.org/abs/([\d.]+)", url, re.IGNORECASE)
            if m3:
                arxiv = m3.group(1)
        out[key] = {"title": field("title"), "doi": doi, "arxiv": arxiv}
    return out


def read_aux_numbers():
    """Heading title -> printed number, from main.aux.

    citation_audit reports the section and subsection a citation sits in by
    TITLE. The printed number is what a reader navigates by, and only LaTeX
    knows it, so it is read from the .aux rather than counted here. Titles are
    unique in this document; the assertion below is what keeps that true.
    """
    if not os.path.isfile(AUX):
        return {}
    numbers = {}
    pattern = re.compile(r"\\newlabel\{[^}]*\}\{\{([^}]*)\}\{[^}]*\}"
                         r"\{([^}]*)\}\{(?:sub)*section\.[^}]*\}")
    for m in pattern.finditer(io.open(AUX, encoding="utf-8",
                                      errors="replace").read()):
        number, title = m.group(1).strip(), m.group(2).strip()
        title = re.sub(r"\\[a-zA-Z]+\s*", "", title).strip()
        if title and title not in numbers:
            numbers[title] = number
    return numbers


def strip_jats(text):
    """Crossref abstracts arrive as JATS XML. Reduce to readable plain text."""
    if not text:
        return ""
    text = re.sub(r"(?is)<jats:title>.*?</jats:title>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&quot;", '"')
                .replace("&#x2013;", "-").replace("&#x2014;", "--"))
    text = re.sub(r"\s+", " ", text).strip()
    # Publishers often prefix a literal "Abstract".
    return re.sub(r"^abstract[:.\s]*", "", text, flags=re.IGNORECASE).strip()


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def fetch_crossref(doi):
    """(abstract, error). An empty abstract with no error means none deposited."""
    try:
        body = http_get(CROSSREF % urllib.request.quote(doi, safe="/"))
    except Exception as exc:                    # noqa: BLE001 -- reported, not raised
        return "", "crossref: %s" % type(exc).__name__
    try:
        msg = json.loads(body.decode("utf-8", "replace")).get("message", {})
    except ValueError:
        return "", "crossref: unparseable JSON"
    return strip_jats(msg.get("abstract", "")), ""


def fetch_arxiv(ident):
    try:
        body = http_get(ARXIV % urllib.request.quote(ident))
    except Exception as exc:                    # noqa: BLE001
        return "", "arxiv: %s" % type(exc).__name__
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return "", "arxiv: unparseable XML"
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in root.findall(ns + "entry"):
        node = entry.find(ns + "summary")
        if node is not None and node.text:
            return re.sub(r"\s+", " ", node.text).strip(), ""
    return "", ""


def fetch_openalex(doi):
    """OpenAlex stores abstracts as an inverted index; rebuild the text.

    This is the fallback that matters. Crossref only has an abstract if the
    publisher deposited one and most do not -- on this bibliography Crossref
    alone returned 4 of 36. OpenAlex carries them for Elsevier, Nature, IEEE and
    others that deposit nothing to Crossref.
    """
    try:
        body = http_get(OPENALEX % urllib.request.quote(doi, safe="/"))
    except Exception as exc:                    # noqa: BLE001
        return "", "openalex: %s" % type(exc).__name__
    try:
        doc = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return "", "openalex: unparseable JSON"
    index = doc.get("abstract_inverted_index")
    if not index:
        return "", ""
    # {token: [positions]} -> text. Positions are absolute, so the longest
    # position decides the length and gaps would show as blanks (there are none
    # in practice, but a missing slot must not silently shift the rest).
    slots = {}
    for token, positions in index.items():
        for pos in positions:
            slots[pos] = token
    if not slots:
        return "", ""
    text = " ".join(slots.get(i, "") for i in range(max(slots) + 1))
    return re.sub(r"\s+", " ", text).strip(), ""


def fetch_datacite(doi):
    """DataCite holds arXiv's 10.48550 DOIs, which Crossref does not."""
    try:
        body = http_get(DATACITE % urllib.request.quote(doi, safe="/"))
    except Exception as exc:                    # noqa: BLE001
        return "", "datacite: %s" % type(exc).__name__
    try:
        attrs = json.loads(body.decode("utf-8", "replace")).get(
            "data", {}).get("attributes", {})
    except ValueError:
        return "", "datacite: unparseable JSON"
    for desc in attrs.get("descriptions") or []:
        if desc.get("descriptionType") in (None, "Abstract"):
            text = strip_jats(desc.get("description", ""))
            if text:
                return text, ""
    return "", ""


def fetch_abstract(rec):
    """Try sources in the order most likely to have the abstract.

    ARXIV IS NOT REACHABLE FROM THIS MACHINE. export.arxiv.org and arxiv.org
    both fail certificate verification here ("unable to get local issuer
    certificate"), while api.crossref.org, api.openalex.org and
    api.datacite.org all verify fine, so it is host-specific rather than a
    broken trust store. Verification is deliberately NOT disabled to work
    around it: fetching an abstract is not worth turning off certificate
    checking in a script that is meant to be run by other people.

    It costs nothing here. Every arXiv entry in this bibliography carries a
    10.48550/arXiv.* DOI, and DataCite is authoritative for those. The arXiv
    call is kept last so it starts working by itself on a machine that can
    reach it.
    """
    doi, errors = rec["doi"], []
    is_arxiv_doi = bool(re.match(r"(?i)10\.48550/arxiv\.", doi or ""))

    sources = []
    if is_arxiv_doi:
        sources.append(("DataCite %s" % doi, lambda: fetch_datacite(doi)))
    elif doi:
        sources.append(("Crossref %s" % doi, lambda: fetch_crossref(doi)))
    if doi:
        sources.append(("OpenAlex %s" % doi, lambda: fetch_openalex(doi)))
    if rec["arxiv"]:
        sources.append(("arXiv:%s" % rec["arxiv"],
                        lambda: fetch_arxiv(rec["arxiv"])))

    for label, call in sources:
        text, err = call()
        if text:
            return text, label, "; ".join(errors)
        if err:
            errors.append(err)
        time.sleep(PAUSE)
    return "", "", "; ".join(errors)


def unchecked_tier1_keys(unchecked, tier1):
    """Tier-1 entries with no verification status, in tier-1's own order.

    Kept in TIER1 order rather than sorted: that order is the risk ordering, so
    the first name printed is the one to read next.
    """
    return [k for k in TIER1 if k in set(unchecked) and k in tier1]


def wrap(text, width=78, indent="> "):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(indent + cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(indent + cur)
    return "\n".join(lines)


def main():
    uses = citation_audit.collect()
    numbers = read_aux_numbers()
    bib = read_bib()

    by_key = {}
    for row in uses:
        by_key.setdefault(row[0], []).append(row)

    # Assign a tier to every entry in the bibliography, cited or not.
    tiers = {}
    for key in bib:
        if key in TIER0:
            tiers[key] = 0
        elif key in TIER1:
            tiers[key] = 1
        elif key in TIER3:
            tiers[key] = 3
        else:
            tiers[key] = 2

    unknown = [k for k in TIER1 + TIER0 + TIER3 if k not in bib]
    if unknown:
        raise ValueError("tier lists name entries not in references.bib: %s"
                         % unknown)

    run_dir = ec61.make_run_dir("citation_verification")

    order = ([(1, k) for k in TIER1]
             + sorted((2, k) for k in tiers if tiers[k] == 2)
             + sorted((3, k) for k in tiers if tiers[k] == 3)
             + [(0, k) for k in TIER0])

    fetched, results = 0, {}
    for i, (_tier, key) in enumerate(order, 1):
        rec = bib[key]
        if tiers[key] == 0:
            results[key] = {"abstract": "", "source": "", "error": "",
                            "skipped": "already verified"}
            continue
        sys.stderr.write("  [%2d/%d] %s\n" % (i, len(order), key))
        abstract, source, error = fetch_abstract(rec)
        if abstract:
            fetched += 1
        results[key] = {"abstract": abstract, "source": source,
                        "error": error, "skipped": ""}
        time.sleep(PAUSE)

    # ---- write the note ---------------------------------------------------
    need_reading = [k for k, r in results.items()
                    if not r["abstract"] and not r["skipped"]]

    # ---- verification state, counted rather than asserted -----------------
    def with_status(state):
        return sorted(k for k in bib
                      if VERIFICATION.get(k, ("", ""))[0] == state)

    full = with_status(FULL_TEXT)
    abstract_only = with_status(ABSTRACT_ONLY)
    corrected = with_status(CORRECTED)
    unchecked = sorted(k for k in bib if k not in VERIFICATION)
    n_full, n_abstract = len(full), len(abstract_only)
    n_corrected, n_unchecked = len(corrected), len(unchecked)
    t1 = set(TIER1)
    n_full_t1 = len([k for k in full if k in t1])
    n_abstract_t1 = len([k for k in abstract_only if k in t1])
    n_corrected_t1 = len([k for k in corrected if k in t1])
    n_unchecked_t1 = len([k for k in unchecked if k in t1])

    # Phrased from the counts so the sentence cannot go stale against the table.
    if not abstract_only:
        abstract_only_line = ("Every checked entry was checked against a full "
                              "text.")
    else:
        abstract_only_line = (
            "**%s verified from an abstract alone**, %s tier 1: %s. The full "
            "text was paywalled and not available. If this study ever "
            "describes its own verification method, these must not be "
            "presented as equivalent to a full-text check."
            % ("%d entry is" % n_abstract if n_abstract == 1
               else "%d entries are" % n_abstract,
               "%d of them" % n_abstract_t1 if n_abstract_t1 else "none",
               ", ".join("`%s`" % k for k in abstract_only)))

    if not unchecked_tier1_keys(unchecked, t1):
        tier1_outstanding_line = "**Every tier-1 entry has been checked.**"
    else:
        remaining = unchecked_tier1_keys(unchecked, t1)
        tier1_outstanding_line = (
            "**%d tier-1 entr%s still unchecked: %s.** Tier 1 is where a wrong "
            "citation changes what this paper claims, so these come before "
            "anything in tiers 2 and 3."
            % (len(remaining), "y is" if len(remaining) == 1 else "ies are",
               ", ".join("`%s`" % k for k in remaining)))
    L = ["# Citation verification",
         "",
         "Generated by `scripts/citation_verification.py`; run record in "
         "`runs/%s/`. Regenerate after any change to the prose or the "
         "bibliography." % os.path.basename(run_dir),
         "",
         "One block per bibliography entry: the paper's own abstract, then "
         "every sentence in this paper that cites it, with the section number "
         "it appears in. **Ordered by risk, hardest first.** A reader who "
         "stops halfway has checked the claims worth checking.",
         "",
         "**An abstract is not evidence.** It is the authors' summary of their "
         "own work, so it can justify reading the paper and can expose a "
         "citation that is plainly wrong. It cannot confirm that a specific "
         "claim is correct. Every tier-1 entry whose sentence rests on a "
         "number needs the full text; this file is where that starts.",
         "",
         "| | count |",
         "|---|---|",
         "| entries in the bibliography | %d |" % len(bib),
         "| abstract fetched | %d |" % fetched,
         "| no abstract available --- open the DOI yourself | %d |"
         % len(need_reading),
         "| already verified, not re-fetched | %d |" % len(TIER0),
         "",
         "## Verification state",
         "",
         "Filled by hand as the reading pass proceeds. **An entry absent from "
         "the table below has not been checked**, and nothing here is derived "
         "from the fetches above.",
         "",
         "| state | entries | of which tier 1 |",
         "|---|---|---|",
         "| verified against the full text | %d | %d |"
         % (n_full, n_full_t1),
         "| verified from the abstract only | %d | %d |"
         % (n_abstract, n_abstract_t1),
         "| citation was wrong, now corrected | %d | %d |"
         % (n_corrected, n_corrected_t1),
         "| not yet checked | %d | %d |" % (n_unchecked, n_unchecked_t1),
         "",
         abstract_only_line,
         "",
         tier1_outstanding_line,
         "",
         "Note on tier 1: the brief named *two* seed papers. Three entries are "
         "grouped there --- `picard2021seed`, `gundersen2023reporting` and "
         "`akesson2024random` --- because all three are cited in one sentence "
         "of 2.4 and each asserts a finding about run-to-run variation. "
         "Checking two of the three would leave the third unchecked in the "
         "same sentence.",
         ""]

    last_tier = None
    for tier, key in order:
        if tier != last_tier:
            L += ["", "---", "", "## %s" % TIER_TITLE[tier], "",
                  TIER_NOTE[tier], ""]
            last_tier = tier

        rec, res = bib[key], results[key]
        rows = by_key.get(key, [])
        L.append("### `%s`" % key)
        L.append("")
        if rec["title"]:
            L.append("*%s*" % rec["title"])
            L.append("")
        link = ("https://doi.org/%s" % rec["doi"]) if rec["doi"] else ""
        bits = []
        if link:
            bits.append("[%s](%s)" % (rec["doi"], link))
        if rec["arxiv"]:
            bits.append("[arXiv:%s](https://arxiv.org/abs/%s)"
                        % (rec["arxiv"], rec["arxiv"]))
        L.append(" | ".join(bits) if bits
                 else "**No DOI and no arXiv id.** Nothing to fetch; this is a "
                      "software or repository citation.")
        L.append("")

        L.append("**Cited in %d place%s.**"
                 % (len(rows), "" if len(rows) == 1 else "s"))
        L.append("")

        status, status_note = VERIFICATION.get(key, ("", ""))
        if status:
            L.append(STATUS_TEXT[status])
            if status_note:
                L.append("")
                L.append(status_note)
        else:
            L.append("_Not yet checked._")
        L.append("")

        if res["skipped"]:
            L.append("**Abstract not fetched --- %s.**" % res["skipped"])
        elif res["abstract"]:
            L.append("**Abstract** (%s):" % res["source"])
            L.append("")
            L.append(wrap(res["abstract"]))
        else:
            reason = res["error"] or ("no abstract is deposited for this DOI"
                                      if rec["doi"] else "no identifier")
            L.append("**No abstract available from the registries --- %s.**"
                     % reason)
            if status:
                # Without this the block contradicts itself: a status of
                # "abstract only" beside "no abstract available" reads as an
                # error rather than as two different sources. The registries
                # are not the only place an abstract exists.
                L.append("")
                L.append("The status above was reached by reading it at the "
                         "publisher's page rather than through a registry.")
            if link:
                L.append("")
                L.append("Open it yourself: <%s>" % link)
        L.append("")

        if not rows:
            L.append("_Not cited anywhere in the paper._")
            L.append("")
            continue

        L.append("**Our sentences:**")
        L.append("")
        for _key, section, subsection, sentence, _f in rows:
            num = numbers.get(subsection) or numbers.get(section) or "?"
            where = subsection or section
            L.append("- **%s %s**" % (num, where))
            L.append("")
            L.append(wrap(sentence, indent="  > "))
            L.append("")

    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

    ec61.write_config(
        run_dir, os.path.abspath(__file__),
        params={"crossref": CROSSREF, "arxiv": ARXIV, "pause_seconds": PAUSE,
                "tier1": TIER1, "tier0_already_verified": TIER0,
                "tier3": TIER3},
        extra={"entries": len(bib), "abstracts_fetched": fetched,
               "no_abstract": sorted(need_reading),
               "citation_uses": len(uses),
               "caveat": "an abstract is the authors' own summary; it can "
                         "justify reading a paper and can expose a plainly "
                         "wrong citation, but it cannot confirm a specific "
                         "claim"})

    ec61.write_csv(
        os.path.join(run_dir, "fetch_outcomes.csv"),
        ["bib_key", "tier", "doi", "arxiv", "uses", "abstract_chars",
         "source", "error"],
        [[k, tiers[k], bib[k]["doi"], bib[k]["arxiv"], len(by_key.get(k, [])),
          len(results[k]["abstract"]), results[k]["source"],
          results[k]["error"] or results[k]["skipped"]]
         for _t, k in order])

    print()
    print("entries              : %d" % len(bib))
    print("abstract fetched     : %d" % fetched)
    print("no abstract, open it : %d" % len(need_reading))
    print("already verified     : %d" % len(TIER0))
    if need_reading:
        print()
        print("Open these yourself:")
        for k in sorted(need_reading):
            print("  %-24s https://doi.org/%s" % (k, bib[k]["doi"] or "-"))
    print()
    print("wrote %s" % os.path.relpath(OUT, ec61.REPO_ROOT))
    print("record: %s" % os.path.relpath(run_dir, ec61.REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
