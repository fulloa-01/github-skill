# Common Git Errors & Fixes

Reference for diagnosing Git errors. For each: show the exact error, the likely cause, and ranked solutions.

> **Loaded on demand** — only when a git operation fails or the user reports an error.

---

## Authentication

### `Permission denied (publickey)`
**Cause:** SSH key not configured, not loaded in the agent, or not added to GitHub.
```bash
# Diagnose
ssh -T git@github.com

# Fix 1 — add existing key to the agent
ssh-add ~/.ssh/id_ed25519

# Fix 2 — generate a new key
ssh-keygen -t ed25519 -C "you@example.com"
cat ~/.ssh/id_ed25519.pub   # add the OUTPUT to GitHub → Settings → SSH Keys
# Never display, copy, or share the file WITHOUT .pub — that's the private key.

# Fix 3 — switch this repo to HTTPS
git remote set-url origin https://github.com/USER/REPO.git
```

### `Authentication failed` (HTTPS)
**Cause:** GitHub no longer accepts passwords. Use a Personal Access Token (PAT).
```bash
# Generate at: github.com → Settings → Developer Settings → Personal Access Tokens
# Use the token as the password when prompted.
```
> ⚠️ **Credential storage warning:**
> - `git config --global credential.helper store` saves tokens **in plaintext** at `~/.git-credentials`. Anyone with read access to your home directory sees them. Avoid on shared machines.
> - `credential.helper cache` keeps them in memory only (default 15 min). Safer.
> - Best: use a system keychain — `osxkeychain` (macOS), `manager-core` (Windows), or `libsecret` (Linux).

### `remote: Repository not found`
**Cause:** Wrong URL, private repo without access, or repo deleted/renamed.
```bash
git remote -v                                         # check current URL
git remote set-url origin git@github.com:USER/REPO.git  # fix it
ssh -T git@github.com                                 # verify SSH access
```

---

## Merge & Conflicts

### `CONFLICT (content): Merge conflict in <file>`
**Cause:** The same lines were changed in both branches.
```bash
git status --short | grep "^UU"   # list conflicted files

# Open each file and look for:
#   <<<<<<< HEAD          ← your side
#   =======
#   >>>>>>> other-branch  ← their side

# After resolving each file:
git add <file>
git commit               # if merging
git rebase --continue    # if rebasing
```

### `Your local changes would be overwritten by merge`
**Cause:** Uncommitted local changes conflict with the incoming merge.
```bash
# Option 1 — stash, pull, restore
git stash push -m "before pull"
git pull
git stash pop

# Option 2 — commit first
git add -A && git commit -m "wip: save before pull"
git pull

# Option 3 — DESTRUCTIVE: discard local changes (confirm with user)
git restore .
git pull
```

### `fatal: refusing to merge unrelated histories`
**Cause:** The two branches have no common ancestor.
```bash
# Only if you're sure both histories should merge:
git pull origin main --allow-unrelated-histories
```

---

## Branch

### `error: pathspec 'NAME' did not match any file(s) known to git`
**Cause:** Branch doesn't exist locally yet.
```bash
git fetch origin
git branch -a               # list all branches
git switch NAME             # auto-tracks the remote if it exists
```

### `error: Cannot delete branch 'main' checked out`
**Cause:** Can't delete the branch you're currently on.
```bash
git switch develop
git branch -d main
```

### `The branch 'feature/x' is not fully merged`
**Cause:** The branch has commits not present in the current branch.
```bash
git log main..feature/x --oneline   # see what would be lost

# Safe: merge first
git merge feature/x
git branch -d feature/x

# DESTRUCTIVE: force delete (confirm with user)
git branch -D feature/x
```

---

## Push

### `[rejected] main -> main (non-fast-forward)`
**Cause:** Remote has commits you don't have locally.
```bash
git pull --rebase origin main
git push origin main
```

### `error: failed to push some refs`
**Cause:** Either no upstream set, or non-fast-forward.
```bash
# If no upstream:
git push --set-upstream origin <branch>

# If non-fast-forward:
git pull --rebase && git push
```

### `! [remote rejected] ... (protected branch hook declined)`
**Cause:** Branch is protected on GitHub. Direct pushes are disabled.
```bash
# Push to a feature branch and open a PR instead:
git push origin HEAD:refs/heads/feature/your-name
```

---

## Repository State

### `fatal: not a git repository`
**Cause:** Current directory is not inside a git repo.
```bash
pwd
ls -la            # look for .git
git init          # initialize, if that's what you want
# or: cd to the correct directory
```

### `fatal: detected dubious ownership in repository`
**Cause:** Repo owned by a different user (Docker, WSL, shared mounts).
```bash
# Recommended — trust this specific repo only:
git config --global --add safe.directory /full/path/to/repo
```
> ⚠️ **Avoid `safe.directory '*'`** — it disables the ownership check for *every* repo on the system, including any malicious repo someone could plant. Add paths one by one.

### `error: Your local changes would be overwritten by checkout`
**Cause:** Uncommitted changes prevent the branch switch.
```bash
git stash && git switch other-branch && git stash pop   # safe
git add -A && git commit -m "wip"; git switch other-branch  # alt

# DESTRUCTIVE: force switch, loses changes (confirm)
git switch -f other-branch
```

### `HEAD detached at <commit>`
**Cause:** You checked out a commit directly, not a branch.
```bash
git switch main                          # go back
git switch -c new-branch-from-here       # or save current state as a branch
```

---

## Config

### `Please tell me who you are`
**Cause:** Git identity not set.
```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

### `warning: LF will be replaced by CRLF` (Windows)
**Cause:** Line-ending mismatch.
```bash
# Windows
git config --global core.autocrlf true
# macOS / Linux
git config --global core.autocrlf input
```

### `gpg: signing failed: No secret key`
**Cause:** Commit signing is on but no GPG key is configured.
```bash
# Quick fix — turn signing off
git config --global commit.gpgsign false

# Or configure a key
gpg --list-secret-keys --keyid-format LONG
git config --global user.signingkey <KEY-ID>
```

---

## Large Files

### `error: File too large` / GitHub's 100 MB limit
```bash
git rm --cached BIGFILE
echo "BIGFILE" >> .gitignore
git add .gitignore
git commit --amend --no-edit
# For genuinely large files, recommend Git LFS: https://git-lfs.com
# If already pushed, rewriting history requires git-filter-repo — guide carefully.
```

---

## Diagnosis Commands

```bash
git status -v                       # everything
git fsck                            # repo integrity
git reflog --oneline -20            # find "lost" commits — your safety net
git remote -v
git remote show origin
git config --list --show-origin     # who set each setting and where
```
