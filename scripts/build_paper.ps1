<#
.SYNOPSIS
    Compile paper/main.tex and report problems in readable form.

.DESCRIPTION
    Runs the standard four-pass sequence from paper/:

        pdflatex -> bibtex -> pdflatex -> pdflatex

    Three pdflatex passes are needed because the first writes the .aux, bibtex
    resolves the bibliography from it, and the last two settle cross-references
    and citations. Fewer passes leave ?? wherever a \ref or \cite should be.

    Rather than dumping the LaTeX log, this parses it and reports errors,
    missing files, undefined references, undefined citations and duplicate
    labels as a short list.

    THE INSTALLER IS DISABLED BY DEFAULT.

    MiKTeX's on-the-fly package installer opens a GUI dialog. In a
    non-interactive shell that dialog is invisible and pdflatex simply blocks
    until something kills it -- which is what happened the first time this was
    run here. With the installer off, a missing package fails immediately with
    a message naming the file, which is actionable. Pass -AllowInstall to turn
    it back on when running interactively.

.PARAMETER AllowInstall
    Permit MiKTeX to download missing packages. Only use this from an
    interactive terminal: it can open a dialog and block otherwise.

.PARAMETER Clean
    Delete the auxiliary files before building.

.EXAMPLE
    powershell -File scripts\build_paper.ps1
    powershell -File scripts\build_paper.ps1 -AllowInstall -Clean
#>
[CmdletBinding()]
param(
    [switch]$AllowInstall,
    [switch]$Clean
)

$ErrorActionPreference = 'Continue'

$repoRoot  = Split-Path -Parent $PSScriptRoot
$paperDir  = Join-Path $repoRoot 'paper'
$jobName   = 'main'
$logPath   = Join-Path $paperDir "$jobName.log"
$blgPath   = Join-Path $paperDir "$jobName.blg"
$pdfPath   = Join-Path $paperDir "$jobName.pdf"

function Find-Tool {
    param([string]$Name)
    # Prefer the bare name. Returning $cmd.Source here would work, but it makes
    # every pass invoke a different absolute path, which reads as a new and
    # unrecognised binary to anything auditing commands. If it is on PATH, call
    # it the way a person would.
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $cmd) { return $Name }
    # Fallback only. MiKTeX installs per-user by default, so its PATH entry does
    # not reach a shell that was already open when it was installed -- a fresh
    # shell sees it, this one may not. Look in the usual places before giving up.
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\MiKTeX\miktex\bin\x64\$Name.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\MiKTeX\miktex\bin\$Name.exe"),
        (Join-Path $env:ProgramFiles "MiKTeX\miktex\bin\x64\$Name.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "MiKTeX\miktex\bin\$Name.exe")
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    return $null
}

Write-Host ''
Write-Host '=== toolchain ===' -ForegroundColor Cyan
$pdflatex = Find-Tool 'pdflatex'
$bibtex   = Find-Tool 'bibtex'
if ($null -eq $pdflatex -or $null -eq $bibtex) {
    Write-Host 'pdflatex or bibtex could not be found.' -ForegroundColor Red
    Write-Host 'Install MiKTeX or TeX Live, or add its bin directory to PATH.'
    exit 2
}
Write-Host "  pdflatex : $pdflatex"
Write-Host "  bibtex   : $bibtex"

Push-Location $paperDir
try {
    $auxExt = @('.aux', '.log', '.bbl', '.blg', '.out', '.toc')
    if ($Clean) {
        foreach ($e in $auxExt) {
            $f = "$jobName$e"
            if (Test-Path $f) { Remove-Item $f -Force }
        }
        Write-Host '  cleaned auxiliary files'
    }

    $texArgs = @('-interaction=nonstopmode', '-file-line-error')
    if (-not $AllowInstall) { $texArgs += '--disable-installer' }

    $passes = @(
        @{ Name = 'pdflatex (1/3)'; Exe = $pdflatex; Args = ($texArgs + "$jobName.tex") },
        @{ Name = 'bibtex';         Exe = $bibtex;   Args = @($jobName) },
        @{ Name = 'pdflatex (2/3)'; Exe = $pdflatex; Args = ($texArgs + "$jobName.tex") },
        @{ Name = 'pdflatex (3/3)'; Exe = $pdflatex; Args = ($texArgs + "$jobName.tex") }
    )

    Write-Host ''
    Write-Host '=== passes ===' -ForegroundColor Cyan
    $fatal = $false
    foreach ($p in $passes) {
        $null = & $p.Exe $p.Args
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            Write-Host ("  {0,-16} ok" -f $p.Name)
        } else {
            Write-Host ("  {0,-16} exit {1}" -f $p.Name, $code) -ForegroundColor Yellow
            # bibtex returns non-zero for warnings alone; only pdflatex failing
            # is worth abandoning the sequence for.
            if ($p.Name -like 'pdflatex*') { $fatal = $true; break }
        }
    }

    # --- settle cross-references --------------------------------------------
    # Three passes are the usual recipe, but they are not always enough. bibtex
    # consumes one of them, and adding a labelled sectioning command shifts page
    # breaks, so the labels can still be moving when pass 3 ends. LaTeX says so
    # in the log -- "Rerun to get cross-references right" -- and a build that
    # ignores it emits a PDF with stale \ref values and exits 0.
    #
    # So: keep running pdflatex while the log still asks. Capped, because a
    # request that never clears is a real defect (commonly a \label inside a
    # moving box) and looping forever would hide it.
    $maxExtra = 2
    $extra = 0
    while (-not $fatal -and $extra -lt $maxExtra -and (Test-Path $logPath) -and
           (Select-String -Path $logPath -Pattern 'Rerun to get' -Quiet)) {
        $extra++
        $null = & $pdflatex ($texArgs + "$jobName.tex")
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            Write-Host ("  {0,-16} ok  (cross-references had not settled)" -f
                        "pdflatex (+$extra)")
        } else {
            Write-Host ("  {0,-16} exit {1}" -f "pdflatex (+$extra)", $code) `
                       -ForegroundColor Yellow
            $fatal = $true
        }
    }

    if (-not (Test-Path $logPath)) {
        Write-Host ''
        Write-Host 'No log file was produced; nothing to report.' -ForegroundColor Red
        exit 1
    }
    $log = Get-Content $logPath

    # --- parse ---------------------------------------------------------------
    $errors      = $log | Select-String -Pattern '^(.+?):(\d+): (.+)$' | ForEach-Object { $_.Line }
    $bangs       = $log | Select-String -Pattern '^! ' | ForEach-Object { $_.Line }
    $missing     = $log | Select-String -Pattern "File ``(.+?)' not found" |
                   ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
    $undefRef    = $log | Select-String -Pattern "Reference ``(.+?)' on page" |
                   ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
    $undefCite   = $log | Select-String -Pattern "Citation ``(.+?)' on page" |
                   ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
    $multiLabel  = $log | Select-String -Pattern "Label ``(.+?)' multiply defined" |
                   ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
    $overfull    = ($log | Select-String -Pattern '^Overfull \\[hv]box' | Measure-Object).Count
    $underfull   = ($log | Select-String -Pattern '^Underfull \\[hv]box' | Measure-Object).Count
    $rerun       = ($log | Select-String -Pattern 'Rerun to get' | Measure-Object).Count

    Write-Host ''
    Write-Host '=== result ===' -ForegroundColor Cyan
    # An unsatisfied rerun request after the extra passes is a FAILURE, not a
    # statistic. The PDF exists and looks fine, but its \ref values are stale --
    # precisely the kind of silently-wrong output this project refuses to ship.
    $unsettled = ($rerun -gt 0)

    $built = Test-Path $pdfPath
    if ($built -and -not $fatal -and -not $unsettled) {
        $size = [math]::Round((Get-Item $pdfPath).Length / 1KB, 1)
        $pages = ($log | Select-String -Pattern 'Output written on .+ \((\d+) page')
        $pageCount = ''
        if ($null -ne $pages) { $pageCount = ", $($pages.Matches[0].Groups[1].Value) pages" }
        Write-Host "  COMPILED  main.pdf ($size KB$pageCount)" -ForegroundColor Green
    } elseif ($unsettled) {
        # Interpolation, not -f: in ('a{0}' + 'b' -f $x) the format operator
        # binds to the second string only, leaving {0} in the first unexpanded.
        Write-Host "  FAILED    cross-references still unsettled after $maxExtra extra pass(es)" -ForegroundColor Red
        Write-Host '            The PDF exists but its \ref values may be stale.'
        Write-Host '            A \label inside a float or moving box can request'
        Write-Host '            a rerun that never clears; check recent \label use.'
    } else {
        Write-Host '  FAILED    no usable PDF produced' -ForegroundColor Red
    }

    if ($missing.Count -gt 0) {
        Write-Host ''
        Write-Host 'Missing files (LaTeX packages that are not installed):' -ForegroundColor Red
        foreach ($m in $missing) { Write-Host "  - $m" }
        Write-Host ''
        Write-Host '  MiKTeX has these but has not downloaded them. Either:' -ForegroundColor Yellow
        Write-Host '    open MiKTeX Console -> Updates -> check, then Packages -> install; or'
        Write-Host '    re-run this script with -AllowInstall from an interactive terminal.'
    }

    if ($bangs.Count -gt 0) {
        Write-Host ''
        Write-Host 'Errors:' -ForegroundColor Red
        foreach ($e in ($bangs | Select-Object -First 20)) { Write-Host "  $e" }
    } elseif ($errors.Count -gt 0) {
        Write-Host ''
        Write-Host 'Errors:' -ForegroundColor Red
        foreach ($e in ($errors | Select-Object -First 20)) { Write-Host "  $e" }
    }

    if ($undefRef.Count -gt 0) {
        Write-Host ''
        Write-Host "Undefined references ($($undefRef.Count)):" -ForegroundColor Yellow
        foreach ($r in $undefRef) { Write-Host "  - $r" }
    }
    if ($undefCite.Count -gt 0) {
        Write-Host ''
        Write-Host "Undefined citations ($($undefCite.Count)):" -ForegroundColor Yellow
        foreach ($c in $undefCite) { Write-Host "  - $c" }
    }
    if ($multiLabel.Count -gt 0) {
        Write-Host ''
        Write-Host "Labels defined more than once ($($multiLabel.Count)):" -ForegroundColor Yellow
        foreach ($l in $multiLabel) { Write-Host "  - $l" }
    }

    if (Test-Path $blgPath) {
        # -CaseSensitive matters: BibTeX ends every log with a statistics block
        # listing its built-in functions, one of which is literally `warning$`.
        # A case-insensitive '^Warning' matches that counter and reports
        # "warning$ -- 0" as though it were a warning. Match the real prefixes.
        $blg = Get-Content $blgPath |
               Select-String -CaseSensitive -Pattern '^(Warning--|I couldn''t|I found no|Repeated entry)'
        if ($null -ne $blg) {
            Write-Host ''
            Write-Host 'BibTeX:' -ForegroundColor Yellow
            foreach ($b in $blg) { Write-Host "  $($b.Line)" }
        }
    }

    Write-Host ''
    Write-Host "Boxes: $overfull overfull, $underfull underfull.  Rerun requests: $rerun."

    # --- internal markers must not reach the printed bibliography ------------
    # BibTeX PRINTS the `note` field. Editorial markers parked there -- VERIFY,
    # PLACEHOLDER, TODO, UNSOURCED -- are typeset into the References section
    # and shipped to the reader. That happened: the References section carried
    # "VERIFY: author list ... are UNSOURCED" and a sentence explaining that a
    # corporate author was a placeholder for BibTeX's sorting.
    #
    # The fix was to move every such note into a % comment, which BibTeX
    # ignores. This check is what stops it coming back, because the failure is
    # invisible in references.bib -- the markers look like annotations there,
    # and only main.bbl shows they were typeset.
    #
    # main.bbl is checked rather than references.bib: comments are legitimate
    # and expected in the source, so scanning the source would fail on its own
    # documentation. main.bbl is BibTeX's OUTPUT and contains only what prints.
    $leakTokens = @('VERIFY', 'PLACEHOLDER', 'TODO', 'UNSOURCED')
    $leaked = @()
    if (Test-Path $blgPath -PathType Leaf) { }   # no-op; keeps $blgPath in scope
    $bblPath = Join-Path $paperDir "$jobName.bbl"
    if (Test-Path $bblPath) {
        $bblLines = Get-Content $bblPath
        foreach ($tok in $leakTokens) {
            $hits = $bblLines | Select-String -SimpleMatch -CaseSensitive $tok
            foreach ($h in $hits) {
                $leaked += ("{0}  (line {1}): {2}" -f $tok, $h.LineNumber, $h.Line.Trim())
            }
        }
    }

    if ($leaked.Count -gt 0) {
        Write-Host ''
        Write-Host "INTERNAL MARKERS IN THE PRINTED BIBLIOGRAPHY ($($leaked.Count)):" -ForegroundColor Red
        foreach ($l in $leaked) { Write-Host "  - $l" }
        Write-Host ''
        Write-Host '  These are typeset into the References section and shipped to' -ForegroundColor Yellow
        Write-Host '  the reader. BibTeX prints the `note` field; move the text into a'
        Write-Host '  % comment in references.bib, which BibTeX ignores, then rebuild.'
    }

    if ($fatal -or -not $built -or $unsettled -or $leaked.Count -gt 0) { exit 1 }
    exit 0
}
finally {
    Pop-Location
}
