#!/usr/bin/env python3
"""
Pre-Push Verification Runner for Jira QA Agents.
Runs before any 'git push origin main' to ensure broken code is never pushed.
100% ASCII-safe for Windows console / charmap cp1252 compatibility.
"""
import sys
import subprocess
from pathlib import Path

# Ensure UTF-8 output handling without crashing on Windows cp1252
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def run_step(description: str, cmd: list) -> bool:
    print(f"\n--- {description} ---")
    try:
        res = subprocess.run(cmd, check=False)
        return res.returncode == 0
    except Exception as e:
        print(f"[ERROR] Could not execute {cmd}: {e}", file=sys.stderr)
        return False

def main():
    repo_root = Path(__file__).resolve().parent.parent
    python_bin = sys.executable

    print("\n==========================================================")
    print(" [GUARD] Running Pre-Push Verification Guardrail...")
    print("==========================================================")

    # Step 1: Compliance & Syntax
    step1_ok = run_step(
        "Step 1/2: Checking syntax and 100% self-made compliance",
        [python_bin, str(repo_root / "scripts" / "verify_compliance.py")]
    )
    if not step1_ok:
        print("\n[BLOCKED] PUSH REJECTED: Syntax error or forbidden external AI model detected!")
        print("Please fix the issues above before pushing to main.\n", file=sys.stderr)
        sys.exit(1)

    # Step 2: Full Pytest Suite
    step2_ok = run_step(
        "Step 2/2: Running pytest suite (134+ tests)",
        [python_bin, "-m", "pytest", "-q", "--tb=short"]
    )
    if not step2_ok:
        print("\n[BLOCKED] PUSH REJECTED: One or more unit tests failed!")
        print("Do not push broken code to main. Fix failing tests first.\n", file=sys.stderr)
        sys.exit(1)

    print("\n==========================================================")
    print(" [SUCCESS] ALL PRE-PUSH CHECKS PASSED. Pushing safely to main!")
    print("==========================================================\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
