#!/usr/bin/env python3
"""
GitHub & Git Manager - Helper Script
Provides CLI interface for common Git operations with safety checks.

Usage:
    python3 git_manager.py find [--base-dir DIR ...]
    python3 git_manager.py status <repo-path>
    python3 git_manager.py run <repo-path> [--confirmed] -- <git-args...>
    python3 git_manager.py validate

Security model:
    - Subcommand allowlist (refuses unknown / global-config commands)
    - Destructive operations require --confirmed flag
    - Repo paths must be inside an existing git repo (not bare paths)
    - All subprocess calls have timeouts
    - Credentials in remote URLs are stripped before display
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────────────

VERSION = "2.1.0"

DEFAULT_SEARCH_DIRS = [
    "~/projects",
    "~/repos",
    "~/code",
    "~/Documents/GitHub",
]
# Note: ~/Desktop intentionally excluded from defaults — too noisy on most systems.
# Pass --base-dir ~/Desktop explicitly if needed.

MAX_SEARCH_DEPTH = 3  # depth relative to each base dir; lower = faster

# Per-command timeouts (seconds). Kept tight — git ops should be local.
TIMEOUT_FAST = 10   # status, branch, log, diff
TIMEOUT_SLOW = 60   # fetch, pull, push, clone

# Allowlist of git subcommands the `run` action will execute.
# Anything not in this set is rejected. This blocks `config --global`,
# `filter-branch`, `update-ref`, etc., that could harm user state.
ALLOWED_SUBCOMMANDS = {
    # read-only
    "status", "log", "diff", "show", "branch", "tag",
    "remote", "ls-files", "ls-remote", "rev-parse", "blame",
    "shortlog", "describe", "reflog",
    # workspace mutation (non-destructive by default)
    "add", "commit", "stash", "fetch", "pull", "push",
    "merge", "rebase", "cherry-pick", "revert",
    "checkout", "switch", "restore",
    # destructive — require --confirmed
    "reset", "clean", "rm",
}

# Subcommand+args combinations that count as destructive.
# Function signature: (args: list[str]) -> bool
def _is_destructive(args: list[str]) -> bool:
    if not args:
        return False
    sub = args[0]
    rest = args[1:]

    # Always destructive
    if sub == "clean":
        # `git clean -n` is a dry run (safe). Anything else with -f deletes.
        return any(a.startswith("-f") or a == "--force" for a in rest)
    if sub == "rm":
        return True  # removes from working tree

    # reset is destructive only with --hard or --merge
    if sub == "reset":
        return any(a in ("--hard", "--merge", "--keep") for a in rest)

    # checkout/switch/restore lose changes only with -f / --force
    if sub in ("checkout", "switch", "restore"):
        return any(a in ("-f", "--force", "--theirs", "--ours") for a in rest)

    # branch -D is force-delete
    if sub == "branch":
        return "-D" in rest or "--delete" in rest and "--force" in rest

    # push --force / --mirror / --delete
    if sub == "push":
        return any(a in ("--force", "-f", "--mirror") for a in rest) or \
               "--delete" in rest

    # stash drop / clear
    if sub == "stash":
        return len(rest) > 0 and rest[0] in ("clear", "drop")

    # rebase/merge with --abort is safe; --continue is safe.
    # Interactive rebase is interactive — refuse via allowlist if needed.
    return False


# Subcommand+args that are explicitly REFUSED even with --confirmed,
# because they alter user-global state outside the target repo.
def _is_forbidden(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, ""
    sub = args[0]

    # Refuse `git config --global` / `--system`
    if sub == "config" and any(a in ("--global", "--system") for a in args[1:]):
        return True, "Refusing to modify global/system git config."

    # Refuse `git clean -fdx` on an unconfirmed call (handled separately),
    # but explicitly refuse `git clean` outside repo paths is handled by repo check.

    # Refuse credential-helper changes via `run`
    if sub == "credential":
        return True, "Refusing to manipulate credential helpers via this script."

    return False, ""


# Regex to strip credentials from URLs (https://user:token@host, git://user@host, ssh://user@host)
_CRED_RE = re.compile(r"(?P<scheme>https?://|git://|ssh://)[^/@\s]+@")


def _sanitize_url(url: str) -> str:
    """Remove embedded credentials from a remote URL for display."""
    return _CRED_RE.sub(r"\g<scheme>", url)


# ── Helpers ──────────────────────────────────────────────────────────────────

def is_git_repo(path: Path) -> bool:
    """True if path is the root of a Git repository (worktree or submodule)."""
    git_marker = path / ".git"
    return git_marker.is_dir() or git_marker.is_file()


def run_git(args: list[str], cwd: Path, timeout: int = TIMEOUT_FAST) -> dict:
    """Run a git command and return a structured result. Never raises."""
    if not shutil.which("git"):
        return {
            "success": False,
            "stdout": "",
            "stderr": "Git is not installed or not in PATH.",
            "returncode": 127,
            "command": f"git {' '.join(args)}",
        }

    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.rstrip("\n"),
            "stderr": result.stderr.rstrip("\n"),
            "returncode": result.returncode,
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s.",
            "returncode": -1,
            "command": " ".join(cmd),
        }
    except OSError as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"OS error: {e}",
            "returncode": -1,
            "command": " ".join(cmd),
        }


def get_repo_info(repo_path: Path) -> dict:
    """Gather summary info about a single repository."""
    info: dict = {"path": str(repo_path), "name": repo_path.name}

    branch = run_git(["branch", "--show-current"], repo_path)
    info["branch"] = branch["stdout"] or "(detached)" if branch["success"] else "unknown"

    status = run_git(["status", "--short", "--branch"], repo_path)
    if status["success"]:
        lines = status["stdout"].splitlines()
        info["status_header"] = lines[0] if lines else ""
        info["changed_files"] = sum(1 for l in lines[1:] if l.strip())
    else:
        info["status_header"] = ""
        info["changed_files"] = 0

    last = run_git(["log", "-1", "--format=%h %s (%cr)"], repo_path)
    info["last_commit"] = last["stdout"] if last["success"] else "no commits yet"

    remote = run_git(["remote", "get-url", "origin"], repo_path)
    info["remote"] = _sanitize_url(remote["stdout"]) if remote["success"] and remote["stdout"] else None

    return info


def _validate_repo_path(repo_path: str) -> tuple[Optional[Path], Optional[str]]:
    """Resolve and validate a repo path. Returns (path, error)."""
    try:
        path = Path(repo_path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as e:
        return None, f"Invalid path: {e}"

    if not path.exists():
        return None, f"Path does not exist: {path}"
    if not path.is_dir():
        return None, f"Path is not a directory: {path}"
    if not is_git_repo(path):
        return None, f"Not a git repository: {path}"
    return path, None


# ── Commands ─────────────────────────────────────────────────────────────────

_SKIP_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__", "vendor",
    "target", "dist", "build", ".next", ".cache",
}


def cmd_find(base_dirs: Optional[list[str]] = None) -> list[dict]:
    """Find git repositories under the given base directories."""
    search_dirs = base_dirs or DEFAULT_SEARCH_DIRS
    repos: list[dict] = []
    seen: set[str] = set()

    for dir_pattern in search_dirs:
        base = Path(dir_pattern).expanduser()
        if not base.exists() or not base.is_dir():
            continue

        for dirpath, dirnames, _ in os.walk(base, followlinks=False):
            current = Path(dirpath)
            try:
                depth = len(current.relative_to(base).parts)
            except ValueError:
                continue

            # Stop descending past max depth
            if depth >= MAX_SEARCH_DEPTH:
                dirnames.clear()
                continue

            # Prune hidden + build/cache dirs in-place (mutates os.walk)
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d not in _SKIP_DIRS
            ]

            if is_git_repo(current):
                key = str(current.resolve())
                if key not in seen:
                    seen.add(key)
                    repos.append(get_repo_info(current))
                dirnames.clear()  # don't recurse into a repo

    repos.sort(key=lambda r: r["name"].lower())
    return repos


def cmd_status(repo_path: str) -> dict:
    """Detailed status of a single repository."""
    path, err = _validate_repo_path(repo_path)
    if err:
        return {"error": err}

    info = get_repo_info(path)

    diff_stat = run_git(["diff", "--stat"], path)
    info["diff_stat"] = diff_stat["stdout"]

    staged_stat = run_git(["diff", "--cached", "--stat"], path)
    info["staged_stat"] = staged_stat["stdout"]

    stash = run_git(["stash", "list"], path)
    info["stash_count"] = len(stash["stdout"].splitlines()) if stash["success"] else 0

    return info


def cmd_run(repo_path: str, git_args: list[str], confirmed: bool = False) -> dict:
    """
    Run a git command in the given repo with safety checks:
    - Subcommand must be in ALLOWED_SUBCOMMANDS
    - Forbidden combos (e.g., config --global) are blocked unconditionally
    - Destructive combos require confirmed=True
    """
    path, err = _validate_repo_path(repo_path)
    if err:
        return {"error": err}

    if not git_args:
        return {"error": "No git command provided."}

    sub = git_args[0]
    if sub not in ALLOWED_SUBCOMMANDS:
        return {
            "error": (
                f"Subcommand '{sub}' is not in the allowlist. "
                f"Allowed: {', '.join(sorted(ALLOWED_SUBCOMMANDS))}"
            )
        }

    forbidden, reason = _is_forbidden(git_args)
    if forbidden:
        return {"error": reason}

    is_dest = _is_destructive(git_args)
    if is_dest and not confirmed:
        return {
            "requires_confirmation": True,
            "command": f"git {' '.join(git_args)}",
            "repo": str(path),
            "destructive": True,
            "message": (
                "Destructive operation. Re-run with --confirmed after the user "
                "has explicitly typed YES (or SÍ in Spanish)."
            ),
        }

    timeout = TIMEOUT_SLOW if sub in ("fetch", "pull", "push", "clone") else TIMEOUT_FAST
    result = run_git(git_args, path, timeout=timeout)
    result["repo"] = str(path)
    result["destructive"] = is_dest
    return result


def cmd_validate() -> dict:
    """Check that the environment is ready to use this skill."""
    checks: dict = {}

    # Git
    git_path = shutil.which("git")
    if git_path:
        ver = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, timeout=5, check=False,
        )
        checks["git"] = {"ok": True, "detail": ver.stdout.strip(), "path": git_path}
    else:
        checks["git"] = {
            "ok": False,
            "detail": "Git not found in PATH.",
            "fix": "Install Git from https://git-scm.com/downloads",
        }

    # Python
    checks["python"] = {
        "ok": sys.version_info >= (3, 7),
        "detail": sys.version.split()[0],
    }

    # Identity
    try:
        name = subprocess.run(
            ["git", "config", "--global", "user.name"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
        email = subprocess.run(
            ["git", "config", "--global", "user.email"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        name = email = ""

    checks["git_identity"] = {
        "ok": bool(name and email),
        "name": name or "(not set)",
        "email": email or "(not set)",
        "fix": (
            'git config --global user.name "Your Name"\n'
            'git config --global user.email "you@example.com"'
        ) if not (name and email) else None,
    }

    # SSH keys (presence only — we never read or transmit the private key)
    ssh_dir = Path("~/.ssh").expanduser()
    public_keys: list[str] = []
    if ssh_dir.is_dir():
        public_keys = [p.name for p in ssh_dir.glob("id_*.pub")]
    checks["ssh_keys"] = {
        "ok": len(public_keys) > 0,
        "keys_found": public_keys,
        "detail": f"{len(public_keys)} public key(s) found",
        "fix": (
            "Generate a key:  ssh-keygen -t ed25519 -C you@example.com\n"
            "Then add the .pub file to GitHub → Settings → SSH and GPG keys."
        ) if not public_keys else None,
    }

    # Repos
    repos = cmd_find()
    checks["repositories"] = {
        "ok": len(repos) > 0,
        "count": len(repos),
        "repos": [{"name": r["name"], "path": r["path"]} for r in repos],
        "fix": (
            "Clone a repo, e.g.:  git clone git@github.com:user/repo.git ~/projects/repo"
        ) if not repos else None,
    }

    overall_ok = all(
        c["ok"] for c in checks.values()
        if isinstance(c, dict) and "ok" in c
    )
    checks["overall"] = "✅ All checks passed" if overall_ok else "⚠️  Some checks need attention"
    return checks


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="GitHub & Git Manager helper script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    sub = parser.add_subparsers(dest="command", required=True)

    find_p = sub.add_parser("find", help="Find git repositories")
    find_p.add_argument("--base-dir", nargs="+", help="Directories to search")

    status_p = sub.add_parser("status", help="Show repo status")
    status_p.add_argument("repo", help="Path to repository")

    run_p = sub.add_parser("run", help="Run a git command in a repo")
    run_p.add_argument("repo", help="Path to repository")
    run_p.add_argument(
        "--confirmed", action="store_true",
        help="User has confirmed a destructive operation (typed YES / SÍ).",
    )
    run_p.add_argument("git_args", nargs=argparse.REMAINDER, help="Git arguments after --")

    sub.add_parser("validate", help="Check environment setup")

    args = parser.parse_args()

    if args.command == "find":
        result = cmd_find(args.base_dir)
    elif args.command == "status":
        result = cmd_status(args.repo)
    elif args.command == "run":
        git_args = args.git_args or []
        if git_args and git_args[0] == "--":
            git_args = git_args[1:]
        result = cmd_run(args.repo, git_args, confirmed=args.confirmed)
    elif args.command == "validate":
        result = cmd_validate()
    else:
        parser.print_help()
        return 1

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, indent=2, default=str))
    else:
        _pretty_print(args.command, result)

    # Exit code reflects success
    if isinstance(result, dict):
        if result.get("error") or result.get("requires_confirmation"):
            return 2
        if result.get("success") is False:
            return 1
    return 0


def _pretty_print(command: str, result) -> None:
    if isinstance(result, list):
        if not result:
            print("\nNo repositories found.")
            print(f"Searched: {', '.join(DEFAULT_SEARCH_DIRS)}")
            print("Tip: clone a repo into ~/projects/ or pass --base-dir.\n")
            return
        print(f"\n{'─' * 60}")
        print(f"  Found {len(result)} repositor{'y' if len(result) == 1 else 'ies'}")
        print(f"{'─' * 60}")
        for r in result:
            changed = f"  ({r['changed_files']} changed)" if r.get("changed_files") else ""
            print(f"\n  📁 {r['name']}")
            print(f"     Path:   {r['path']}")
            print(f"     Branch: {r.get('branch')}{changed}")
            print(f"     Commit: {r.get('last_commit')}")
            if r.get("remote"):
                print(f"     Remote: {r['remote']}")
        print()
        return

    if not isinstance(result, dict):
        print(result)
        return

    if "error" in result:
        print(f"\n❌ Error: {result['error']}\n")
        return

    if result.get("requires_confirmation"):
        print(f"\n⚠️  Confirmation required")
        print(f"   Command: {result['command']}")
        print(f"   Repo:    {result['repo']}")
        print(f"\n   Re-run with --confirmed once the user types YES / SÍ.\n")
        return

    if command == "validate":
        print(f"\n{'─' * 60}")
        print("  Environment Validation")
        print(f"{'─' * 60}")
        for key, val in result.items():
            if key == "overall":
                print(f"\n  {val}\n")
                continue
            if not isinstance(val, dict):
                continue
            icon = "✅" if val.get("ok") else "❌"
            print(f"\n  {icon} {key.replace('_', ' ').title()}")
            for k, v in val.items():
                if k in ("ok", "fix"):
                    continue
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v) if v else "(none)"
                print(f"     {k}: {v}")
            if not val.get("ok") and val.get("fix"):
                print(f"     → Fix:\n       {val['fix']}")
        return

    # Generic command output
    if result.get("success") is False:
        print(f"\n❌ {result.get('stderr', 'Unknown error')}")
        if result.get("command"):
            print(f"   Command: {result['command']}")
    else:
        if result.get("stdout"):
            print(result["stdout"])
        if result.get("stderr"):
            print(result["stderr"], file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
