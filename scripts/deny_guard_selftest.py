"""
deny_guard_selftest.py -- cases scripts/deny_guard.py must and must not block

WHY THIS EXISTS

The guard is the only thing standing between an agent and an irreversible
command, and it is regex over shell text, which is a category of code that fails
quietly in both directions. A rule that stops matching lets a deletion through;
a rule that matches too eagerly blocks ordinary work, which is worse than it
sounds because the block arrives mid-task and the obvious response is to work
around the guard rather than fix it.

Both directions are checked here. The ALLOW list is not decoration: every entry
under "regression" is a command that this guard actually blocked during normal
work, and each one cost a round trip before the rule was corrected.

Run with no arguments; exits non-zero on any failure:

    python scripts/deny_guard_selftest.py
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "deny_guard.py")

MUST_BLOCK = [
    # deletion and movement
    "rm -rf data",
    "rmdir runs",
    "del results.csv",
    "mv a b",
    "Remove-Item -Recurse -Force runs",
    "Clear-Content notes.md",
    # compound lines: the case no prefix rule catches
    "git status; rm -rf x",
    "cd C:/research/electrocom61 && Remove-Item foo",
    # history rewrites, flag position independent
    "git push --force",
    "git push origin main --force",
    "git push -f origin main",
    "git push origin +main",
    "git reset --hard HEAD~1",
    "git rebase -i main",
    "git commit --amend -m x",
    "git filter-branch --tree-filter true HEAD",
    # checkout: commit-ish and path forms only
    "git checkout 0f7e707",
    "git checkout HEAD~1",
    "git checkout main^",
    "git checkout HEAD@{2}",
    "git checkout --detach main",
    "git checkout -- README.md",
    "git switch --detach 0f7e707",
    # installs and network
    "pip install torch",
    "python -m pip install x",
    "conda install y",
    "npm i",
    "winget install z",
    "curl https://example.com/x",
    "wget https://example.com/x",
    "Invoke-WebRequest -Uri x",
    "git clone https://example.com/r.git",
    r"powershell -File scripts\build_paper.ps1 -AllowInstall -Clean",
]

MUST_ALLOW = [
    # --- regression: commands this guard wrongly blocked during real work -----
    # `rd=` matched the rmdir alias, because \b matches before "=".
    "python - <<'PY'\nrd=open('README.md').read()\nPY",
    "python -c \"rd=open('x').read()\"",
    "python -c \"ri=1; ren=2\"",
    "python -c \"mv=3\"",
    # --- ordinary work -------------------------------------------------------
    "git status --short",
    "git add -A",
    "git commit -F msg.txt",
    "git push",
    "git log --oneline -5",
    "git diff -- tables/",
    "git ls-files data/",
    "git show HEAD:README.md",
    # branch navigation stays allowed; only commit-ish checkout is denied
    "git checkout main",
    "git checkout -b feature-x",
    "git checkout -B rebuild",
    "git checkout -b bead123",          # valid hex, but a branch name
    "git switch main",
    "git switch -c feature-y",
    # the build, without the installer flag
    r"powershell -File scripts\build_paper.ps1",
    r"powershell -File scripts\build_paper.ps1 -Clean",
    "python scripts/make_tables.py",
    "python scripts/split_adjacency_check.py",
    "pdflatex main.tex",
    "Get-Content README.md",
    "Select-String -Pattern rm README.md",
    # a quoted word in command position elsewhere is not a command
    'git commit -m "remove the rm call from the docs"',
]


def verdict(command):
    """Run the guard exactly as the hook does and return its reason, or ''."""
    proc = subprocess.run(
        [sys.executable, GUARD],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": command}}),
        capture_output=True, text=True)
    out = proc.stdout.strip()
    if not out:
        return ""
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]


def main():
    failures = []
    for cmd in MUST_BLOCK:
        if not verdict(cmd):
            failures.append(("NOT BLOCKED", cmd, ""))
    for cmd in MUST_ALLOW:
        why = verdict(cmd)
        if why:
            failures.append(("FALSE POSITIVE", cmd, why))

    for kind, cmd, why in failures:
        print("%-15s %r%s" % (kind, cmd[:70], ("  -> " + why[:60]) if why else ""))

    print("\n%d must-block, %d must-allow, %d failure(s)"
          % (len(MUST_BLOCK), len(MUST_ALLOW), len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
