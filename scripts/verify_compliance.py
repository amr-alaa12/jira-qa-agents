#!/usr/bin/env python3
"""
Pre-push & CI Verification Script for Jira QA Agents.
Ensures 100% self-made model policy and structural code integrity.
Pure standard-library Python (zero external dependencies).
"""
import os
import sys
import re
import compileall

# Ensure UTF-8 output handling without crashing on Windows cp1252
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FORBIDDEN_PACKAGES = [
    r"\bopenai\b",
    r"\banthropic\b",
    r"\bgoogle\.generativeai\b",
    r"\bgoogle_genai\b",
    r"\btransformers\b",
    r"\blangchain\b",
    r"\bcrewai\b",
]

IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".idea", ".vscode"}

def check_syntax(root_dir: str = ".") -> bool:
    print("[1/2] Verifying Python syntax across all source files...")
    success = compileall.compile_dir(root_dir, rx=re.compile(r"[/\\](\.venv|venv|\.git)[/\\]"), quiet=1)
    if not success:
        print("  [FAIL] Syntax errors detected in Python files!", file=sys.stderr)
        return False
    print("  [OK] All Python files compiled with 0 syntax errors.")
    return True

def check_model_compliance(root_dir: str = ".") -> bool:
    print("[2/2] Verifying 100% Self-Made Models Academic Compliance...")
    violations = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            stripped = line.strip()
                            if stripped.startswith("import ") or stripped.startswith("from "):
                                for pattern in FORBIDDEN_PACKAGES:
                                    if re.search(pattern, stripped):
                                        violations.append(f"  [FORBIDDEN] {filepath}:{line_num} -> {stripped}")
                except Exception as e:
                    violations.append(f"  [ERROR] Could not read {filepath}: {e}")

    if violations:
        print("\n".join(violations), file=sys.stderr)
        print("\n[CRITICAL FAILURE] Academic compliance check failed! External ready-made AI models/APIs are forbidden.", file=sys.stderr)
        return False

    print("  [OK] Academic compliance verified: Zero forbidden ready-made AI APIs detected (100% Self-Made).")
    return True

def main():
    print("==================================================")
    print(" Jira QA Agents: Automated Bug & Compliance Gate  ")
    print("==================================================")
    syntax_ok = check_syntax()
    compliance_ok = check_model_compliance()

    if syntax_ok and compliance_ok:
        print("\n[OK] ALL INTEGRITY CHECKS PASSED.")
        sys.exit(0)
    else:
        print("\n[FAIL] INTEGRITY CHECKS FAILED. Please resolve errors.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
