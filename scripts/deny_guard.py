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
    # A command token must be followed by WHITESPACE or the end of the segment,
    # not merely a word boundary. \b also matches before "=" and "(", so a
    # Python snippet containing `rd=open(...)` was read as the rmdir alias and
    # blocked. Short aliases -- rd, ri, mv, del -- are the ones that collide
    # with ordinary identifiers, so the constraint matters most for this rule.
    (r"^(rm|rmdir|rd|del|erase|mv)(?=\s|$)",
     "file deletion or move"),
    (r"^(remove-item|move-item|rename-item|clear-content|ri|ren)(?=\s|$)",
     "file deletion, move or truncation"),
    (r"^git\s+(rm|clean)\b",
     "git deletion"),
    (r"^git\s+(rebase|filter-branch)\b",
     "history rewrite"),
    # `git checkout` is handled by checkout_verdict(), not here: switching to and
    # creating branches are allowed, so a blanket pattern is too coarse.
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
    # `git clone` is handled by clone_verdict(), not here. A blanket pattern
    # blocked a local clone during the clean-checkout verification on
    # 2026-08-15 and reported it as a "network clone", which it was not.
    (r"^(pip|pip3|conda|npm|npx|winget|choco|mpm|miktex)(?=\s|$)",
     "package installation"),
    (r"^python\s+-m\s+pip(?=\s|$)",
     "package installation"),
    (r"^(install-module|install-package)(?=\s|$)",
     "package installation"),
    (r"^(curl|wget|invoke-webrequest|invoke-restmethod|iwr|irm|start-bitstransfer)(?=\s|$)",
     "network download"),
    # Not anchored: the script is reached through `powershell -File ...`, so the
    # flag is what matters, wherever the invocation starts.
    (r"build_paper\.ps1.*-allowinstall",
     "build_paper.ps1 -AllowInstall (downloads MiKTeX packages)"),
]

COMPILED = [(re.compile(p, re.IGNORECASE), why) for p, why in RULES]

IS_CLONE = re.compile(r"^git\s+clone(?=\s|$)", re.IGNORECASE)

# What makes a clone a NETWORK clone. Anything else -- a relative path, an
# absolute POSIX path, a Windows drive path, a file:// URL -- is local, costs
# nothing and is how this repository gets verified against a clean checkout.
REMOTE_FORMS = (
    # An explicit remote scheme. file:// is deliberately NOT here.
    (re.compile(r"^(https?|ssh|git|ftps?)://", re.IGNORECASE), "remote URL"),
    # scp-like with an explicit user: git@github.com:owner/repo.
    (re.compile(r"^[^/\\@]+@[^/\\:]+:"), "scp-style remote"),
    # scp-like without a user: host.tld:path. The negative lookahead keeps a
    # Windows drive path (C:\..., D:/...) out, since it has the same shape.
    (re.compile(r"^(?![A-Za-z]:[\\/])[A-Za-z0-9._-]+\.[A-Za-z]{2,}:"),
     "scp-style remote"),
)


def clone_verdict(segment):
    """None if this is not a clone or is a local one; a reason if it is remote.

    Erring toward ALLOW here is deliberate and narrow: the rule exists to stop
    a clone from reaching the network, and every remote spelling git accepts is
    covered above. A path that matches none of them cannot reach a network.
    """
    if not IS_CLONE.match(segment):
        return None
    for token in segment.split()[2:]:
        if token.startswith("-"):
            continue                      # a flag, not a source or destination
        for pattern, why in REMOTE_FORMS:
            if pattern.match(token):
                return "network clone (%s: %s)" % (why, token)
    return None


IS_CHECKOUT = re.compile(r"^git\s+checkout\b", re.IGNORECASE)
CREATES_BRANCH = re.compile(r"\s-[bB]\b")
# A commit-ish rather than a branch name: a bare hex object name, or any
# revision expression -- HEAD~2, main^, HEAD@{1}, a tag with an offset.
COMMIT_ISH = re.compile(r"(^|\s)(?:[0-9a-f]{7,40}|\S*(?:@\{|[~^])\S*)(\s|$)",
                        re.IGNORECASE)


def checkout_verdict(segment):
    """Deny `git checkout` only where it detaches HEAD or discards files.

    Switching branches (`git checkout main`) and creating them (`git checkout
    -b feature`) are ordinary navigation and stay allowed. What is denied is
    checking out a commit-ish, which detaches HEAD, and `git checkout --
    <path>`, which discards working-tree changes with no undo.

    `-b` short-circuits the commit-ish test: the branch NAME is what follows it,
    and a name like `bead123` is valid hex without being an object.
    """
    if not IS_CHECKOUT.search(segment):
        return None
    if re.search(r"--detach\b", segment, re.IGNORECASE):
        return "detached checkout"
    if re.search(r"\s--(\s|$)", segment):
        return "git checkout -- <path> (discards working-tree changes)"
    if CREATES_BRANCH.search(segment):
        return None
    # Test only the arguments, so the words `git` and `checkout` cannot match.
    args = segment.split(None, 2)[2] if len(segment.split()) > 2 else ""
    if COMMIT_ISH.search(" " + args + " "):
        return "checkout of a commit (detaches HEAD)"
    return None


def verdict(command):
    """Return a reason string if the command must be denied, else None."""
    for segment in SEPARATORS.split(command):
        segment = segment.strip()
        if not segment:
            continue
        for special in (checkout_verdict, clone_verdict):
            why = special(segment)
            if why:
                return "%s -- blocked by scripts/deny_guard.py (segment: %r)" % (
                    why, segment[:120])
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
