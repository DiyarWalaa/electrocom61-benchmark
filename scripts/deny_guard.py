"""
deny_guard.py -- block destructive and network-installing commands outright

WHY THIS EXISTS

Permission rules in .claude/settings.json match a command by PREFIX. That is
enough for "git rebase" (the flag is the second word) but not for "git push
--force in any flag position": `git push --force origin main` matches the
prefix `git push --force`, and `git push origin main --force` does not. It is
also blind to compound lines -- `git status; rm -rf x` starts with `git status`
and matches no rm rule at all.

This runs as a PreToolUse hook, sees the whole command string, and decides on
the SEGMENTS of it. Anything the prefix rules miss, this catches.

HOW IT DECIDES

The command is split on shell separators (; && || | newline) and each segment
is tested with its pattern ANCHORED AT THE START. Anchoring is what keeps
`git commit -m "remove the rm call"` from being read as an `rm`: the segment
begins with `git commit`, and the word `rm` inside the message never sits in
command position.

The one place that trade is wrong is a separator inside a quoted string --
`git commit -m "a; rm -rf b"` splits at the `;` and the second half looks like
a deletion. That fails toward blocking, which is the safe direction, and is
rare enough to live with.

FAIL-OPEN ON ERROR

If stdin is not the JSON this expects, the guard exits without a decision and
the normal permission rules apply. A guard that crashed closed would block
every command in the session, including the ones needed to fix it. The deny
list in settings.json is the second layer for exactly that case.
"""

import json
import re
import sys

# Shell separators. `|` is last so `||` is consumed by the alternation before
# the single-pipe branch can split it in the middle.
SEPARATORS = re.compile(r"&&|\|\||[;\n|]")

# Each entry is (compiled pattern, human-readable reason). Patterns are matched
# against a stripped segment, case-insensitively, because PowerShell cmdlets
# are case-insensitive and `RM` is as destructive as `rm`.
RULES = [
    (r"^(rm|rmdir|rd|del|erase|mv)\b",
     "file deletion or move"),
    (r"^(remove-item|move-item|rename-item|clear-content|ri|ren)\b",
     "file deletion, move or truncation"),
    (r"^git\s+(rm|clean)\b",
     "git deletion"),
    (r"^git\s+(rebase|filter-branch)\b",
     "history rewrite"),
    (r"^git\s+checkout\b",
     "git checkout (detaches or discards working-tree state)"),
    (r"^git\s+switch\b.*--detach\b",
     "detached checkout"),
    (r"^git\s+reset\b.*--hard\b",
     "hard reset"),
    (r"^git\s+commit\b.*--amend\b",
     "commit amend (rewrites a commit)"),
    # Force push, flag position independent: the segment must BE a git push,
    # then any force spelling anywhere in it -- including a `+refspec`.
    (r"^git\s+push\b.*(--force|--force-with-lease|\s-f\b|\s\+\S)",
     "force push"),
    (r"^git\s+clone\b",
     "network clone"),
    (r"^(pip|pip3|conda|npm|npx|winget|choco|mpm|miktex)\b",
     "package installation"),
    (r"^python\s+-m\s+pip\b",
     "package installation"),
    (r"^(install-module|install-package)\b",
     "package installation"),
    (r"^(curl|wget|invoke-webrequest|invoke-restmethod|iwr|irm|start-bitstransfer)\b",
     "network download"),
    # Not anchored: the script is reached through `powershell -File ...`, so the
    # flag is what matters, wherever the invocation starts.
    (r"build_paper\.ps1.*-allowinstall",
     "build_paper.ps1 -AllowInstall (downloads MiKTeX packages)"),
]

COMPILED = [(re.compile(p, re.IGNORECASE), why) for p, why in RULES]


def verdict(command):
    """Return a reason string if the command must be denied, else None."""
    for segment in SEPARATORS.split(command):
        segment = segment.strip()
        if not segment:
            continue
        for pattern, why in COMPILED:
            if pattern.search(segment):
                return "%s -- blocked by scripts/deny_guard.py (segment: %r)" % (
                    why, segment[:120])
    return None


def main():
    try:
        payload = json.load(sys.stdin)
        command = payload.get("tool_input", {}).get("command", "")
    except Exception:
        return 0  # fail open; see module docstring
    if not isinstance(command, str) or not command:
        return 0

    reason = verdict(command)
    if reason is None:
        return 0

    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
