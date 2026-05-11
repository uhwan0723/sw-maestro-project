# Codex Repository Instructions

## Git Sync Routine

Codex should keep this repository synchronized with `origin` whenever it works here.

At the start of every task, run:

```powershell
.\scripts\codex-git-start.ps1
```

At the end of every task:

- If files were changed by the task, run:

```powershell
.\scripts\codex-git-finish.ps1 -CommitAll -CommitMessage "<short commit message>"
```

- If no files were changed, run:

```powershell
.\scripts\codex-git-finish.ps1
```

Rules:

- Do not force-push.
- If pull, rebase, commit, or push reports a conflict or rejection, stop and explain it to the user.
- Before using `-CommitAll`, check `git status --short` and avoid committing unrelated pre-existing user changes.
- If the user explicitly asks not to commit or push, follow the user's latest instruction.

