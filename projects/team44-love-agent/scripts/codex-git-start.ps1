param(
    [string]$Remote = "origin",
    [switch]$SkipPull
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

function Save-Baseline {
    $stateDir = Join-Path (Get-Location) ".codex"
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

    $baselinePath = Join-Path $stateDir "git-sync-baseline.txt"
    $status = & git status --porcelain=v1
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read git status."
    }

    $status | Set-Content -Path $baselinePath -Encoding UTF8
    Write-Host "Saved Git baseline to $baselinePath"
}

$repoRoot = Get-GitOutput @("rev-parse", "--show-toplevel")
if (-not $repoRoot) {
    throw "This directory is not inside a Git repository."
}

Set-Location $repoRoot
Save-Baseline

$branch = Get-GitOutput @("branch", "--show-current")
if (-not $branch) {
    Write-Host "Detached HEAD detected. Skipping automatic pull."
    exit 0
}

$remoteUrl = Get-GitOutput @("remote", "get-url", $Remote)
if (-not $remoteUrl) {
    Write-Host "Remote '$Remote' is not configured. Skipping automatic pull."
    exit 0
}

$head = Get-GitOutput @("rev-parse", "--verify", "HEAD")
if (-not $head) {
    Write-Host "No local commits yet. Skipping automatic pull."
    exit 0
}

Invoke-Git @("fetch", $Remote, "--prune")

$upstream = Get-GitOutput @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
if (-not $upstream) {
    $remoteBranch = Get-GitOutput @("rev-parse", "--verify", "--quiet", "refs/remotes/$Remote/$branch")
    if ($remoteBranch) {
        Invoke-Git @("branch", "--set-upstream-to=$Remote/$branch", $branch)
    }
    else {
        Write-Host "No upstream branch found for '$branch'. Skipping automatic pull."
        exit 0
    }
}

if ($SkipPull) {
    Write-Host "Pull skipped by request."
    exit 0
}

Invoke-Git @("pull", "--rebase", "--autostash")
Write-Host "Repository is up to date with upstream."
