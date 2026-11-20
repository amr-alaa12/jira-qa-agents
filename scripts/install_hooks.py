#!/usr/bin/env python3
"""
Install local Git Pre-Push Guardrail for Jira QA Agents.
Configures Git to intercept 'git push' and run verification tests automatically.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def install():
    repo_root = Path(__file__).resolve().parent.parent
    githooks_dir = repo_root / ".githooks"
    git_dir = repo_root / ".git"

    if not git_dir.exists():
        print("❌ Error: Not a git repository! Run this inside the repo root.", file=sys.stderr)
        sys.exit(1)

    print("==================================================")
    print(" Installing Pre-Push Hook for Jira QA Agents...   ")
    print("==================================================")

    # 1. Configure git core.hooksPath to .githooks
    try:
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo_root, check=True)
        print("  ✓ Configured git core.hooksPath -> .githooks")
    except Exception as e:
        print(f"  ⚠ Could not set core.hooksPath: {e}")

    # 2. Also copy to .git/hooks/pre-push as universal fallback
    target_hook = git_dir / "hooks" / "pre-push"
    source_hook = githooks_dir / "pre-push"

    if source_hook.exists():
        target_hook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_hook, target_hook)
        try:
            # Make executable if on Unix/Linux/macOS
            os.chmod(target_hook, 0o755)
            os.chmod(source_hook, 0o755)
        except Exception:
            pass
        print(f"  ✓ Copied pre-push hook to {target_hook}")

    print("\n🎉 SUCCESS! Git pre-push hook is active.")
    print("Every time you run 'git push origin main', Git will automatically:")
    print("  1. Verify zero forbidden ready-made AI APIs are imported.")
    print("  2. Check all Python files for syntax errors.")
    print("  3. Run the 134-test pytest suite.")
    print("\nIf any error is found, Git will prevent the push to protect your team!")

if __name__ == "__main__":
    install()
