param(
    [string]$Remote = "origin",
    [string]$CommitMessage = "chore: update project files",
    [switch]$CommitAll,
    [switch]$AllowNoBaseline,
    [switch]$IgnoreBaseline
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Get-GitOutput {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $output = & git @Arguments 2>$null
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($exitCode -ne 0) {
        return $null
    }
    return $output
}

function Get-StatusPath {
    param([Parameter(Mandatory = $true)][string]$Line)

    if ($Line.Length -lt 4) {
        return $null
    }

    $path = $Line.Substring(3)
    if ($path -like "* -> *") {
        $parts = $path -split " -> ", 2
        return $parts[1]
    }

    return $path
}

function Get-DirtyPaths {
    param([string[]]$StatusLines)

    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($line in $StatusLines) {
        $path = Get-StatusPath $line
        if ($path) {
            $paths.Add($path)
        }
    }
    return $paths
}

function Get-BaselinePaths {
    if ($IgnoreBaseline) {
        return @()
    }

    $baselinePath = Join-Path (Join-Path (Get-Location) ".codex") "git-sync-baseline.txt"
    if (-not (Test-Path -LiteralPath $baselinePath)) {
        if ($AllowNoBaseline) {
            return @()
        }
        throw "No Git baseline found at $baselinePath. Run .\scripts\codex-git-start.ps1 first, or pass -AllowNoBaseline."
    }

    $baselineLines = Get-Content -Path $baselinePath -Encoding UTF8
    return Get-DirtyPaths $baselineLines
}

$repoRoot = Get-GitOutput @("rev-parse", "--show-toplevel")
if (-not $repoRoot) {
    throw "This directory is not inside a Git repository."
}

Set-Location $repoRoot

$branch = Get-GitOutput @("branch", "--show-current")
if (-not $branch) {
    throw "Detached HEAD detected. Refusing to push automatically."
}

$remoteUrl = Get-GitOutput @("remote", "get-url", $Remote)
if (-not $remoteUrl) {
    Write-Host "Remote '$Remote' is not configured. Skipping automatic push."
    exit 0
}

if ($CommitAll) {
    $currentStatus = & git status --porcelain=v1
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read git status."
    }

    $currentPaths = Get-DirtyPaths $currentStatus
    $baselinePaths = Get-BaselinePaths
    $baselineSet = New-Object "System.Collections.Generic.HashSet[string]"
    foreach ($path in $baselinePaths) {
        [void]$baselineSet.Add($path)
    }
    $pathsToCommit = @($currentPaths | Where-Object { -not $baselineSet.Contains($_) } | Sort-Object -Unique)

    if ($pathsToCommit.Count -eq 0) {
        Write-Host "No new task changes to commit."
    }
    else {
        foreach ($path in $pathsToCommit) {
            Invoke-Git @("add", "--", $path)
        }

        $staged = & git diff --cached --name-only
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to inspect staged changes."
        }

        if ($staged) {
            Invoke-Git @("commit", "-m", $CommitMessage)
        }
        else {
            Write-Host "No staged changes to commit."
        }
    }
}

$head = Get-GitOutput @("rev-parse", "--verify", "HEAD")
if (-not $head) {
    Write-Host "No local commits yet. Nothing to push."
    exit 0
}

Invoke-Git @("fetch", $Remote, "--prune")

$upstream = Get-GitOutput @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
if ($upstream) {
    Invoke-Git @("pull", "--rebase", "--autostash")
    Invoke-Git @("push")
}
else {
    Invoke-Git @("push", "-u", $Remote, $branch)
}

Write-Host "Git finish sync complete."
