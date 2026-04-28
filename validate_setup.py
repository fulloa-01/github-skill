#!/usr/bin/env python3
"""
Validate the environment for the GitHub & Git Manager skill.

Wraps `git_manager.py validate` and prints a friendly report.
Returns exit code 0 on full pass, 1 on any failure.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GIT_MANAGER = SCRIPT_DIR / "git_manager.py"
TIMEOUT = 60  # seconds — generous for repo discovery


def main() -> int:
    print("\n🔍 Validating environment for GitHub & Git Manager skill...\n")

    if not GIT_MANAGER.exists():
        print(f"❌ Cannot find git_manager.py at {GIT_MANAGER}")
        return 1

    try:
        result = subprocess.run(
            [sys.executable, str(GIT_MANAGER), "--json", "validate"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"❌ Validation timed out after {TIMEOUT}s.")
        return 1

    if not result.stdout.strip():
        print(f"❌ git_manager.py produced no output.\nStderr:\n{result.stderr}")
        return 1

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ Could not parse JSON output: {e}")
        print(f"Raw output:\n{result.stdout[:500]}")
        return 1

    all_ok = True
    for key, val in data.items():
        if key == "overall" or not isinstance(val, dict) or "ok" not in val:
            continue

        icon = "✅" if val["ok"] else "❌"
        label = key.replace("_", " ").title()
        print(f"{icon} {label}")

        for k, v in val.items():
            if k in ("ok", "fix"):
                continue
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v) if v else "(none)"
            print(f"   {k}: {v}")

        if not val["ok"]:
            all_ok = False
            if val.get("fix"):
                print("\n   ↳ How to fix:")
                for line in val["fix"].splitlines():
                    print(f"     {line}")
        print()

    print("─" * 50)
    if all_ok:
        print('\n✅ Everything looks good. Try: "Show me my repositories"\n')
        return 0
    else:
        print("\n⚠️  Some issues need attention. After fixing, re-run this script.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
