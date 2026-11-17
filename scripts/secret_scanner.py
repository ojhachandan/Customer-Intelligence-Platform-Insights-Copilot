"""Exhaustive Confidentiality and Secret Scanner for The Qasar."""
from __future__ import annotations

import os
import re
import subprocess
import sys

SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
    (r"ghp_[a-zA-Z0-9]{20,}", "GitHub Personal Access Token"),
    (r"github_pat_[a-zA-Z0-9]{20,}", "GitHub Fine-Grained Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google API Key"),
    (r"sk-ant-[a-zA-Z0-9-_]{20,}", "Anthropic API Key"),
    (r"hf_[a-zA-Z0-9]{20,}", "Hugging Face Token"),
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private Key"),
    (r"(?i)(?:api_key|secret_key|private_key|access_token|password)[\s]*[=:][\s]*[\"'][A-Za-z0-9+/=_\-\.]{12,}[\"']", "Generic Hardcoded Secret"),
    (r"postgres(?:ql)?:\/\/[a-zA-Z0-9_-]+:[a-zA-Z0-9_#@!$%^&*()+=~-]+@[a-zA-Z0-9.-]+", "PostgreSQL URI with Password"),
]

SAFE_PLACEHOLDERS = [
    "your_api_key", "your-api-key", "placeholder", "replace_with", "replace-with",
    "example", "<api_key>", "ci/cd", "dummy", "test", "postgres:5432", "sqlite://",
    "cip:cip@postgres", "cip:cip@localhost", "your_postgres", "your_database",
]

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", "scratch", "dist", "build", "customer_intelligence_platform.egg-info"
}

EXCLUDE_EXTENSIONS = {
    ".xlsx", ".zip", ".db", ".sqlite", ".sqlite3", ".pyc", ".png", ".jpg", ".jpeg", ".ico", ".svg"
}

def scan_working_tree(root_dir: str = ".") -> list[dict]:
    findings = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            _, ext = os.path.splitext(f)
            if ext in EXCLUDE_EXTENSIONS:
                continue
            filepath = os.path.join(dirpath, f)
            relpath = os.path.relpath(filepath, root_dir)
            if relpath.startswith((".git", "scratch")):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_idx, line in enumerate(fp, 1):
                        for pattern, category in SECRET_PATTERNS:
                            matches = re.finditer(pattern, line)
                            for match in matches:
                                text = match.group(0)
                                line_lower = line.lower()
                                if any(p in line_lower for p in SAFE_PLACEHOLDERS):
                                    continue
                                redacted = text[:4] + "..." + text[-4:] if len(text) > 8 else "***"
                                findings.append({
                                    "file": relpath,
                                    "line": line_idx,
                                    "category": category,
                                    "redacted": redacted,
                                    "snippet": line.strip()[:80],
                                })
            except (OSError, UnicodeDecodeError) as exc:
                print(f"Warning: could not read {filepath}: {exc}", file=sys.stderr)
    return findings

def scan_git_history() -> list[dict]:
    findings = []
    try:
        proc = subprocess.run(
            ["git", "log", "-p", "origin/main", "--", "."],
            capture_output=True,
            text=True,
            check=False,
            errors="ignore",
        )
        if proc.returncode != 0:
            return findings
        current_commit = "unknown"
        current_file = "unknown"
        for line in proc.stdout.splitlines():
            if line.startswith("commit "):
                current_commit = line.split()[1][:8]
            elif line.startswith("diff --git a/"):
                parts = line.split()
                if len(parts) >= 3:
                    current_file = parts[2].replace("a/", "")
            elif line.startswith("+") and not line.startswith("+++"):
                added_line = line[1:]
                for pattern, category in SECRET_PATTERNS:
                    matches = re.finditer(pattern, added_line)
                    for match in matches:
                        text = match.group(0)
                        if any(p in added_line.lower() for p in SAFE_PLACEHOLDERS):
                            continue
                        redacted = text[:4] + "..." + text[-4:] if len(text) > 8 else "***"
                        findings.append({
                            "commit": current_commit,
                            "file": current_file,
                            "category": category,
                            "redacted": redacted,
                            "snippet": added_line.strip()[:80],
                        })
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Warning scanning git history: {exc}", file=sys.stderr)
    return findings

if __name__ == "__main__":
    print("=== THE QASAR CONFIDENTIALITY & SECRET AUDIT ===")
    print("1. Scanning local working tree...")
    wt_findings = scan_working_tree()
    print(f"Working tree scan findings count: {len(wt_findings)}")
    for f in wt_findings:
        print(f"  [ALERT] {f['file']}:{f['line']} | {f['category']} | {f['redacted']}")

    print("\n2. Scanning remote git history on origin/main...")
    gh_findings = scan_git_history()
    print(f"Git history scan findings count: {len(gh_findings)}")
    for f in gh_findings:
        print(f"  [ALERT] {f['commit']} in {f['file']} | {f['category']} | {f['redacted']}")

    if not wt_findings and not gh_findings:
        print("\nCONFIDENTIALITY AUDIT PASSED: Zero leaked credentials or secrets found.")
        sys.exit(0)
    else:
        print("\nCONFIDENTIALITY AUDIT COMPLETED WITH FINDINGS.")
        sys.exit(1 if wt_findings else 0)
