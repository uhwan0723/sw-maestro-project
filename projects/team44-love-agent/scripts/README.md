# Scripts

Git synchronization helpers for Codex sessions.

## Start Sync

Run this at the beginning of a Codex task:

```powershell
.\scripts\codex-git-start.ps1
```

It records the current dirty working tree state in `.codex/` and then tries to fetch and pull the current branch with `--rebase --autostash`.

## Finish Sync

Run this at the end of a Codex task:

```powershell
.\scripts\codex-git-finish.ps1
```

This pushes already committed local work.

To also commit task changes before pushing:

```powershell
.\scripts\codex-git-finish.ps1 -CommitAll -CommitMessage "docs: update project plan"
```

The finish script uses the baseline saved by the start script to avoid automatically staging files that were already dirty before the task started.

For a one-time initial repository commit, use:

```powershell
.\scripts\codex-git-finish.ps1 -CommitAll -IgnoreBaseline -CommitMessage "chore: initial project setup"
```
