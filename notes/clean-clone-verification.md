# Clean-checkout verification

Two runs. The first (2026-08-15, against `0024dd7`) was the first time this
repository had been run anywhere but the author's machine; it found four
defects. The second (2026-08-16, against `85b74b3`) confirms the fixes and
records what still differs and why.

## How the clean tree is made

`git clone` from a local path is now allowed by `scripts/deny_guard.py` — the
rule was narrowed on 2026-08-15 — but is **still refused by the permission layer
in `.claude/settings.json`**, which carries `Bash(git clone *)` and
`PowerShell(git clone *)`. Until those are narrowed the same way, use a
worktree, which materialises exactly the tracked files at a commit and nothing
`.gitignore` excludes:

    git worktree add --detach C:\research\ec61-verify HEAD
    ...
    git worktree remove --force C:\research\ec61-verify

## Result of the second run

Twelve generator and verifier scripts, all exit 0. Every script in `scripts/`
run: **34 scripts, 0 tracebacks.** Paper builds cold in four passes, 35 pages,
0 overfull and 0 underfull boxes, 0 rerun requests.

| Output | Result |
|---|---|
| `tables/t1`–`t7` (7 files) | **byte-identical** |
| `data/master_results.csv`, `data/latency_by_arch.csv` | **byte-identical** |
| `figures/*.png` (7 files) | **byte-identical** |
| `figures/near_duplicate_pair.pdf` | **byte-identical** |
| `figures/f1,f2,f4,f5,f6 .pdf` | differ, 5–6 bytes each |
| `notes/citation-audit.md` | differs, 1 line of 141 |

**17 identical, 6 differing, and both differences are self-inflicted
timestamps rather than content.**

### The PDF timestamps — FIXED 2026-08-16

Five PDFs differed in five or six bytes each, at one offset, inside matplotlib's
`/CreationDate (D:...)`. Nothing else in any of them changed, and every PNG
matched exactly, because the PNG writer emits no such field.

`ec61.pdf_metadata()` now pins it: `SOURCE_DATE_EPOCH` is honoured when set
(the cross-project convention, Unix seconds UTC), and otherwise the date falls
back to a fixed `PDF_EPOCH` of 2026-08-16 UTC rather than to `now` — the point
being a byte-identical rebuild on a machine that has configured nothing. It
lives in `ec61` because two scripts write PDFs; `figure_near_duplicate.py` had
the same defect and was untested only because it needs the dataset.

Omitting `/CreationDate` altogether would also be reproducible. A fixed date was
preferred because a PDF with no creation date looks damaged to some readers.

### `notes/citation-audit.md` is left as it is, deliberately

It differs on **line 3 of 141**, which names the run directory that produced it
— `runs/20260816_citation_audit/` against `_02/` on the next run. The other 140
lines are identical.

**This is not a defect and is not being fixed.** The file records where its own
provenance record lives, and every run writes a new directory, so the line is
correct on the run that wrote it and stale on any other. It cannot be
byte-reproducible while it keeps that line, and the line is worth more than the
reproducibility: without it the note does not say which run's audit it is.

Compare this file by line, not by byte offset. A positional comparison
overstates it wildly — 27806 of 29137 bytes "differ" — because the longer
directory name shifts everything after it.

## The four defects from the first run, and their fixes

### 1. Fifteen scripts crashed on the missing dataset — FIXED

They raised an unhandled `OSError`/`FileNotFoundError`, among them
`build_corrected_dataset.py`, which is the script the well-behaved ones tell the
reader to run next — so following the repository's own instructions produced a
stack trace.

`ec61.require_inputs()` now holds one message per required input
(`dataset_v2`, `corrected`, `metadata`), naming the missing tree and the command
or DOI that produces it. Every script that needs one calls it first. The three
scripts that hand-rolled the same check were routed through it too. Six of the
fifteen also called `main()` and discarded its return value, so they would have
exited 0 on a clean failure; they now `sys.exit(main())`.

Second run: **20 scripts exit non-zero, 0 with a traceback.** Nineteen want the
git-ignored dataset, which is correct and by design; `scaffold_config_provenance.py`
refuses to overwrite a hand-filled file, also by design.

### 2. Regenerating a text file showed as modified when its bytes matched — FIXED, and it exposed a second defect

`.gitattributes` pins `*.tex`, `*.md`, `*.csv`, `*.json` to `text eol=lf`.

That fixed the tables and immediately uncovered what the old arrangement had
hidden. `make_tables.py` passed `newline="\n"` explicitly; **nothing else did**,
so with the checkout pinned to LF the CSVs and every `summary.md` came out CRLF
and `master_results.csv` differed from HEAD in 1904 of its 2351 bytes. Two
causes:

- `csv.writer` defaults to `lineterminator="\r\n"` on every platform regardless
  of how the file was opened, so `ec61.write_csv`'s `newline=""` was not enough.
  It now passes `lineterminator="\n"`.
- 31 writers used `open(..., "w", encoding="utf-8")` with no `newline=`, so the
  text layer translated to `os.linesep`. All now pass `newline="\n"`.

This is worth keeping in view: the line-ending fix was not cosmetic, and it did
not *cause* the CSV problem — it *revealed* one that had been invisible because
two wrongs matched.

### 3. `check_figures_readme.py` fired on every fresh checkout — FIXED

It read the file with `newline=""` and matched ` ```latex\n `, so under CRLF it
reported "5 fences opened but 0 closed" — indistinguishable from the corruption
it exists to detect. Structural checks now run on normalised text; check 1 still
reads raw bytes, since a stray control character is the entire point.

Re-tested against eight injections after the change: baseline LF, CRLF and
CR-only files all pass; a backspace (the original corruption), a backspace in a
CRLF file, an unclosed fence, a dropped `\end{figure}`, a vertical tab, and an
`\includegraphics` naming a file that does not exist all still fail. Exit 0 in
the clean checkout.

### 4. Two verifiers had been failing, here as well as in a clean checkout — FIXED

`verify_eval_protocol.py` and `verify_efficiency_claims.py` counted raw rows of
`master_results.csv`, so they saw 11 where they expected 10 and three RT-DETR-l
measurements where they expected two. The eleventh row is the diverged
`rtdetr_l_pub` run, marked `inclusion=diverged`. Both now read through
`ec61.load_benchmark_rows`, as every table and figure already did. No paper
number was affected — nothing reads their output. Both exit 0.

### Also fixed: the build depended on state it exists to be independent of

`build_paper.ps1` ran three pdflatex passes and relied on a rerun loop to catch
the rest. Three sufficed only because stale `.aux` files carried the
cross-references in; a fresh checkout needed the fallback. It now runs four
passes by default, and the second run's cold build reported **0 rerun
requests** — the fallback is a backstop again rather than part of the normal
path.

### Also narrowed: the deny guard

`scripts/deny_guard.py` matched `^git\s+clone` unconditionally and called a
local clone a "network clone", which is what stopped the first verification from
cloning at all. `clone_verdict()` now blocks `https://`, `http://`, `ssh://`,
`git://`, `ftp(s)://` and both scp-style spellings, and allows local paths and
`file://`. `git worktree remove` was never blocked by the guard — the earlier
note that it was is wrong. Selftest: 39 must-block, 33 must-allow, 0 failures.

## Still untested, and why

Three committed figures — `near_duplicate_pair.pdf`, `near_duplicate_pair.png`
and `split_verification_sheet.png` — are produced by scripts that need the
dataset, so they were never regenerated. They match only because nothing
rewrote them. Their reproducibility stays untested until a checkout has the
dataset beside it.
