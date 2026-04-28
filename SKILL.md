---
name: github-git-manager
version: 2.1.0
description: Manage Git repositories and GitHub operations through natural language. Use whenever the user mentions git, github, commits, branches, push, pull, clone, merge, diff, stash, or any version-control workflow — even casually ("commit my changes", "what branch am I on?"). Works in English and Spanish. Read-only operations run immediately; destructive operations require explicit YES / SÍ confirmation.
---

# GitHub & Git Manager

Manage Git repositories through natural conversation. Claude executes Git operations on the user's behalf, handles errors clearly, and **never executes a destructive operation without explicit confirmation**.

## Core Principles

1. **Safety first** — destructive operations require literal `YES` (or `SÍ`). No synonyms.
2. **Transparency** — always show the exact command run and its raw output.
3. **Helpful errors** — when something fails, explain the cause and offer concrete fixes.
4. **Minimal footprint** — only touch the repos and files the user named.
5. **Never leak secrets** — never display tokens, SSH private keys, or credentials embedded in URLs.

---

## When to load the reference files

This skill ships with two reference files. Do not load them by default — load on demand:

- **`references/operations.md`** — load when the user asks about a Git command you're unsure about, or when handling tags, rebase, interactive workflows, or anything beyond status/add/commit/push/pull/branch/merge.
- **`references/errors.md`** — load when an operation fails with an error message, or when the user reports a Git error.

For everyday operations (status, log, diff, commit, branch, push, pull) the rules in this file are sufficient.

---

## Repository Discovery

When the user refers to "my project" / "my repo" / "mi proyecto" without a path, search in this order:

```
~/projects/   ~/repos/   ~/code/   ~/Documents/GitHub/
```

`~/Desktop/` is **not** searched by default (too noisy). The user can opt in: *"buscá también en ~/Desktop"*.

Use `scripts/git_manager.py find` for discovery. If multiple matches exist, list them and ask which one. If none are found, suggest cloning or initializing — never guess a path.

---

## Operation Tiers

### Safe — execute immediately
| User says | Command |
|-----------|---------|
| "show my repos" / "lista mis repos" | `git_manager.py find` |
| "what branch am I on?" / "¿en qué rama estoy?" | `git branch --show-current` |
| "show changes" / "qué cambió" | `git status --short --branch` + `git diff --stat` |
| "show history" / "historial" | `git log --oneline -20` |
| "fetch" / "buscar actualizaciones" | `git fetch` |

### Moderate — warn if working tree is dirty, then proceed
| User says | Command | Pre-check |
|-----------|---------|-----------|
| "switch to [branch]" | `git switch <branch>` | If dirty: offer to stash |
| "pull" | `git fetch` then preview, then `git pull` | If dirty: offer to stash |
| "create branch [name]" | `git switch -c <branch>` | None (safe) |

### Destructive — REQUIRE explicit confirmation
| User says | Command | What can be lost |
|-----------|---------|------------------|
| "discard changes" / "descartar cambios" | `git restore <file>` | Uncommitted edits |
| "reset hard" / "reset all" | `git reset --hard` | Uncommitted + recent commits |
| "force delete branch" | `git branch -D <name>` | Unmerged commits |
| "force push" | `git push --force-with-lease` | Remote history (others' work) |
| "clean untracked" | `git clean -fd` | Untracked files (often unrecoverable) |
| "remove file" | `git rm <file>` | The file |

**Push to `main` / `master` is also gated** — even though it's not destructive locally, it can be destructive for collaborators. Always confirm.

---

## Confirmation Format (mandatory for destructive ops)

Output **exactly** this block before executing any destructive command:

```
⚠️  DESTRUCTIVE OPERATION
    Command: git <exact command>
    Effect:  <plain English: what changes, what is lost>
    Affects: <files / commits / branches at risk>
    Repo:    <absolute path>

    Type YES (or SÍ) to confirm. Anything else cancels.
```

Then **wait** for the next user turn.

**Confirmation rules — strict:**
- Accept only: `YES`, `SI`, `SÍ` (case-insensitive but the word must appear alone or as the clear answer).
- Do **not** accept: "ok", "sure", "dale", "claro", "go ahead", "procede", "yes please" (these are too easy to type by accident).
- Anything else → cancel and confirm cancellation to the user.
- A confirmation applies to **one** operation only. The next destructive op needs a fresh YES.

---

## Commit Workflow

When the user says "commit [message]" / "guarda mis cambios":

1. Run `git status --short --branch` — show what would be staged.
2. If working tree is clean → tell the user, stop.
3. Run `git diff --cached --stat` (and `git diff --stat` if nothing is staged yet) so the user sees the scope.
4. Stage: `git add -A` (or specific paths if the user named them).
5. If no message was provided, propose one in conventional-commit style based on the diff and **wait for approval**:
   ```
   feat(scope): <summary>     # for new functionality
   fix(scope): <summary>      # for bug fixes
   docs / refactor / chore / test / style
   ```
6. Execute: `git commit -m "<message>"`.
7. Show the resulting hash (`git log -1 --oneline`).

Never auto-commit without showing what will be committed. Never use `git commit -a` blindly.

---

## Push & Pull

**Pull (always preview first):**
```bash
git fetch origin
git log HEAD..origin/<branch> --oneline   # show incoming
# If dirty working tree: offer `git stash push -m "before pull"` first
git pull --ff-only                         # safer default
# Fall back to `git pull --rebase` only if user wants linear history
```

**Push:**
```bash
git push origin HEAD                       # current branch
git push --set-upstream origin <branch>    # first push of a new branch
```
- Never `--force`. If force is genuinely needed, use `--force-with-lease` AND require destructive confirmation.
- Pushing to `main`/`master` always requires confirmation.

---

## Conflict Handling

When `git status` shows conflicts:

1. Run `git status` to list conflicted paths.
2. For each conflicted file, show the conflict markers (`<<<<<<< HEAD`, `=======`, `>>>>>>> branch`) and explain what each side represents.
3. Ask the user how to resolve: theirs, ours, or manual edit.
4. After edits: `git add <file>` then either `git commit` (merge) or `git rebase --continue` (rebase).
5. Provide an escape hatch: `git merge --abort` / `git rebase --abort`.

**Never auto-resolve conflicts.**

---

## Error Handling

Standard pattern for any failed git command:

1. Show the exact stderr output.
2. State the likely cause in one sentence.
3. Offer 1–3 ranked, concrete fixes — each with the exact command.
4. Ask which fix to try (or wait for the user's call).

Never silently retry. Never invent error messages.

For common errors and their fixes, load `references/errors.md`.

---

## Output Format

**Success:**
```
✅ <Operation>
   Repo:    <path>
   Branch:  <name>
   <relevant detail, e.g. commit hash>

<raw command output if useful>
```

**Failure:**
```
❌ <Operation> failed
   Error: <exact stderr>
   Cause: <one-line diagnosis>

   Options:
   1. <fix A> →  git <command>
   2. <fix B> →  git <command>
```

---

## Security Rules — non-negotiable

- **Never** display the contents of SSH private keys, `.git-credentials`, or any token.
- **Never** suggest `git config --global credential.helper store` without warning the user it stores tokens in plaintext at `~/.git-credentials`. Prefer `cache` or a system keychain helper.
- **Never** suggest `git config --global --add safe.directory '*'` without warning that it disables the ownership check globally. Prefer the specific path.
- **Never** run `git config --global` or `git config --system` via `git_manager.py run` — these are blocked by the script's allowlist.
- When echoing remote URLs, use the script's sanitized output (credentials are stripped).

---

## Helper Scripts

- **`scripts/git_manager.py`** — main helper. CLI: `find`, `status`, `run`, `validate`. Run subcommand allowlist + destructive-op guard built in. For destructive ops, pass `--confirmed` only after the user has typed `YES`/`SÍ`.
- **`scripts/validate_setup.py`** — environment checker. Run once after install or whenever something seems off.

For single, simple operations on a known repo, calling `git` directly via `bash` is fine and faster. Use the script when:
- Discovering repos across multiple directories
- Running a destructive op (the script enforces the allowlist + confirmation flag)
- Producing JSON output for downstream parsing

---

## Language

Reply in the user's language. English and Spanish are first-class. Mixed messages are normal — match the dominant language of the latest user message.
