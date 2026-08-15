# Clean-checkout verification, 2026-08-15

First time this has been done. Everything below is about the repository at
commit `0024dd7`, checked out into a directory with no local state.

## How the clean tree was made

`git clone` is refused by `scripts/deny_guard.py`, which matches `^git\s+clone`
and reports "network clone" — it does not distinguish a local path from a
remote. A worktree was used instead:

    git worktree add --detach C:\research\ec61-verify HEAD

For this purpose the two are equivalent: both materialise exactly the tracked
files at `HEAD` and nothing that `.gitignore` excludes. The worktree is still
registered; remove it with `git worktree remove C:\research\ec61-verify`.

**The clean tree is HEAD, not the working tree.** At the time of the run the
working tree carried uncommitted changes to 14 files plus 3 new ones
(`data/published_accuracy.csv`, `paper/sections/10-availability.tex`,
`tables/t7_allocation_deviation.tex` and T7's generator). None of that was
tested here. Re-run after committing.

## Byte-for-byte comparison of regenerated outputs

| Output | Result |
|---|---|
| `data/master_results.csv` | **identical** |
| `data/latency_by_arch.csv` | **identical** |
| `tables/t1`–`t6` (6 files) | **identical** |
| `figures/*.png` (7 files) | **identical** |
| `figures/f1,f2,f4,f5,f6 .pdf` (5 files) | **differ — 6 bytes each** |
| `notes/citation-audit.md` | **differs — 1 line** |
| `figures/near_duplicate_pair.*`, `split_verification_sheet.png` | **not regenerable** (see below) |

Both differences are benign and both are self-inflicted timestamps.

- **The PDFs differ in exactly six bytes**, at one offset, inside matplotlib's
  `/CreationDate (D:20260814170330+03'00')`. Nothing else in any of the five
  files changes. The PNGs of the same figures are byte-identical, because the
  PNG writer emits no creation date. Set `SOURCE_DATE_EPOCH`, or
  `matplotlib.rcParams["pdf....")` metadata, if byte-reproducible PDFs are
  wanted.
- **`citation-audit.md` differs only in the run directory it names** — it
  records `runs/20260815_citation_audit_05` and a re-run writes `_06`. The line
  is self-referential provenance, so this file can never be byte-reproducible by
  construction. The 79 citation rows below it are identical.

## Defects found

### 1. `check_figures_readme.py` fails on any fresh checkout

Exit 1 in the clean tree, exit 0 here, same file. It reports "5 ```latex fences
opened but 0 closed" and "no figure environments found at all" — which reads
exactly like the corruption it exists to detect.

The cause is line endings, not corruption. Line 65 opens the file with
`newline=""`, which disables universal-newline translation, and line 82 matches
```` ```latex\n ````. `core.autocrlf` is `true`, so a fresh checkout materialises
`figures/README.md` with 479 CRLFs where the generator wrote 479 LFs, and every
`\n`-anchored pattern misses.

This is the worst of the findings because the check is a corruption alarm: on a
fresh checkout it fires unconditionally, and an alarm that always fires is one
nobody reads. Fix by opening with `newline=None` (or normalising `\r\n` before
matching).

### 2. Two verification scripts fail, and they fail here too

`verify_efficiency_claims.py` and `verify_eval_protocol.py` exit 1 in the clean
tree **and in this working copy**. They are not clean-tree casualties; the clean
run merely surfaced them.

    verify_eval_protocol   : master_results.csv has 11 rows, expected 10
                             counted 22 complete evaluations, expected 20
    verify_efficiency      : rtdetr-l: expected 2 per-session measurements, got 3

All three are the same stale expectation. `master_results.csv` carries 11 rows —
10 `inclusion=benchmark` and 1 `inclusion=diverged` (the `rtdetr_l_pub` run
retained deliberately, per Section 5.3). Tables and figures read it through
`ec61.load_benchmark_rows`, which filters on `inclusion`; these two scripts count
raw rows instead.

**No paper number is affected** — nothing in the paper reads these two scripts'
output. What is affected is the claim that the repository verifies itself: two of
its verifiers have been failing.

### 3. The build needs a fourth LaTeX pass on a cold start

`build_paper.ps1` runs three passes, then one more if references have not
settled. In this working copy three suffice, because stale `.aux` files carry the
cross-references in. In the clean tree the fallback pass fired. The script
handled it and produced the correct document; worth knowing that the 3-pass loop
is only sufficient warm.

### 4. Regenerating any text output makes `git status` show a false modification

The generators write LF (`newline="\n"`, deliberately). `core.autocrlf=true`
materialises CRLF on checkout. After regenerating, the file's raw bytes equal the
committed blob — verified directly against `git show HEAD:<path>` for all six
tables — but `git status` still lists them as modified. A real change would look
identical to this noise. A `.gitattributes` pinning `*.tex`, `*.md` and `*.csv`
to `text eol=lf` would remove the ambiguity.

## What cannot run without the dataset, which is by design

Of 32 scripts run, 9 exit 0, 19 fail for want of `data/ElectroCom-61_v2/` or the
built `data/ElectroCom-61_corrected/`, 1 refuses by design
(`scaffold_config_provenance.py` will not overwrite the hand-filled file), and 3
are the defects above.

The dataset is gitignored on purpose — it is an input, reproduced by download
instruction. So 19 failures are expected. **How they fail is not uniform:**

- **4 exit cleanly with an actionable message** — `figure_near_duplicate.py`,
  `figure_verification_sheet.py`, `consecutive_counter_pairs.py` and
  `v1_provenance.py` name the missing tree and print the command that builds it.
- **15 crash with an unhandled traceback**, including
  `build_corrected_dataset.py` — which is the script the other four *tell the
  user to run next*. Following the advice the repository gives produces a
  `Traceback ... OSError: missing source image directory`.

Three committed figures are produced by two of those scripts and were therefore
never regenerated: `near_duplicate_pair.pdf`, `near_duplicate_pair.png` and
`split_verification_sheet.png`. They match only because nothing rewrote them.
Their reproducibility is untested and stays untested until a checkout has the
dataset beside it.
