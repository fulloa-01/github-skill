# Git Operations Reference

Full command reference for the GitHub Git Manager skill. Loaded on demand for less-common operations.

> Destructive commands are marked **⚠️ DESTRUCTIVE**. Always run the confirmation block from `SKILL.md` before executing them.

---

## Repositories

```bash
# Discover repos (use the helper)
python3 scripts/git_manager.py find

# Status of a specific repo
git -C <path> status --short --branch

# Clone (SSH preferred)
git clone git@github.com:USER/REPO.git ~/projects/REPO
git clone -b BRANCH git@github.com:USER/REPO.git ~/projects/REPO

# Initialize
cd ~/projects/new-project && git init
git remote add origin git@github.com:USER/REPO.git
```

---

## Branches

```bash
# View
git branch                  # local
git branch -a               # local + remote
git branch --show-current
git branch -v               # last commit per branch

# Switch (modern syntax)
git switch BRANCH
git switch -c BRANCH        # create + switch

# Rename
git branch -m new-name              # current branch
git branch -m old-name new-name     # specific branch

# Delete
git branch -d BRANCH        # safe — only if merged
git branch -D BRANCH        # ⚠️ DESTRUCTIVE — force delete
git push origin --delete BRANCH    # delete on remote
```

---

## Staging & Commits

```bash
# Inspect
git status --short --branch
git diff                    # unstaged
git diff --cached           # staged
git diff --stat             # summary only

# Stage
git add -A                  # everything
git add PATH                # specific
git add -p                  # interactive, hunk by hunk
git restore --staged PATH   # unstage

# Commit
git commit -m "feat(auth): add JWT validation"
git commit --amend --no-edit            # only if NOT pushed yet
git commit --amend -m "new message"     # only if NOT pushed yet
```

**Conventional commit format (suggest by default):**
```
type(scope): summary

types: feat | fix | docs | style | refactor | test | chore | perf
```

---

## Remote Sync

```bash
# Fetch + preview before pulling
git fetch origin
git log HEAD..origin/BRANCH --oneline       # what's incoming

# Pull
git pull --ff-only          # safer default — refuses to merge if not fast-forward
git pull --rebase           # cleaner linear history

# Push
git push origin HEAD                        # current branch
git push --set-upstream origin BRANCH       # first push of new branch
git push --force-with-lease origin BRANCH   # ⚠️ DESTRUCTIVE — never plain --force
```

```bash
# Manage remotes
git remote -v
git remote add origin git@github.com:USER/REPO.git
git remote set-url origin git@github.com:USER/NEW-REPO.git
git remote remove origin
```

---

## History & Inspection

```bash
git log --oneline -20
git log --oneline --graph --all -20
git log --oneline -- PATH                   # for one file
git log -S "function_name" --oneline        # commits that added/removed text
git log --grep="login" --oneline            # search messages

git diff main..feature/branch
git blame PATH
git show COMMIT
```

---

## Stash

```bash
git stash push -m "wip: login form"
git stash list
git stash pop                 # apply most recent + remove
git stash apply stash@{2}     # apply without removing
git stash drop  stash@{0}     # ⚠️ DESTRUCTIVE
git stash clear               # ⚠️ DESTRUCTIVE — drops ALL stashes
```

---

## Undo & Reset

```bash
# Safe — creates a new commit that undoes another
git revert COMMIT
git revert HEAD

# Restore working-tree files (⚠️ DESTRUCTIVE — loses uncommitted edits)
git restore PATH                 # one file
git restore .                    # everything

# Reset (⚠️ varies)
git reset --soft HEAD~1          # safe — moves HEAD, keeps changes staged
git reset --mixed HEAD~1         # safe — moves HEAD, unstages changes
git reset --hard HEAD~1          # ⚠️ DESTRUCTIVE — discards changes + commits
git reset --hard COMMIT          # ⚠️ DESTRUCTIVE

# Clean untracked (⚠️ DESTRUCTIVE)
git clean -nfd                   # dry run — preview only (safe)
git clean -fd                    # delete untracked files + dirs
git clean -fdx                   # also delete .gitignored files
```

---

## Tags

```bash
git tag                              # list
git tag -a v1.0.0 -m "Release 1.0.0" # annotated
git push origin --tags
git tag -d v1.0.0                    # delete local
git push origin --delete v1.0.0      # delete remote
```

---

## Merge & Rebase

```bash
# Merge
git merge BRANCH
git merge --no-ff BRANCH             # always create a merge commit
git merge --abort                    # bail out if it goes wrong

# Rebase
git rebase main
git rebase -i HEAD~5                 # interactive — edit last 5 commits
git rebase --continue                # after resolving conflicts
git rebase --abort                   # bail out
```

> Rebasing rewrites history. Don't rebase commits already pushed and shared.

---

## Config

```bash
git config --global --list
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.editor "code --wait"

# Useful aliases
git config --global alias.st  "status --short --branch"
git config --global alias.lg  "log --oneline --graph --all -20"
git config --global alias.unstage "restore --staged"
```

> The helper script (`git_manager.py run`) will refuse `git config --global` and `--system` to protect user-wide state. Run those manually if you intend to.
