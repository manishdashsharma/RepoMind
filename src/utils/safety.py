from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_BLOCKED_TREES: frozenset[Path] = frozenset(
    {
        Path("/etc"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/lib"),
        Path("/boot"),
        Path("/sys"),
        Path("/proc"),
        Path("/dev"),
        Path("/var"),
        Path.home() / ".ssh",
        Path.home() / ".aws",
        Path.home() / ".gnupg",
        Path.home() / ".zeocloud",
    }
)

_BLOCKED_EXACT: frozenset[Path] = frozenset({Path("/"), Path.home()})

_SENSITIVE_NAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.staging",
        ".env.development",
        "secrets.yml",
        "secrets.yaml",
        "secrets.json",
        "credentials",
        "credentials.json",
        "service-account.json",
        "serviceaccount.json",
        "private.key",
        "id_rsa",
        "id_ed25519",
        ".npmrc",
        ".pypirc",
        "netrc",
        ".netrc",
    }
)

_SENSITIVE_EXTS: frozenset[str] = frozenset({".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"})

MAX_QUESTION_LEN = 2000


@dataclass
class PathReport:
    is_safe: bool = True
    block_reason: str = ""
    sensitive_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_repo_path(repo_path: Path) -> PathReport:
    report = PathReport()
    resolved = repo_path.resolve()

    for blocked in _BLOCKED_EXACT:
        if resolved == blocked.resolve():
            report.is_safe = False
            report.block_reason = (
                f"Indexing '{resolved}' is not allowed. Index a specific project folder instead."
            )
            return report

    for blocked in _BLOCKED_TREES:
        try:
            resolved.relative_to(blocked.resolve())
            report.is_safe = False
            report.block_reason = (
                f"Indexing '{resolved}' is not allowed. "
                "System and sensitive directories are protected."
            )
            return report
        except ValueError:
            continue

    if not resolved.is_dir():
        report.is_safe = False
        report.block_reason = f"'{resolved}' is not a directory."
        return report

    if not os.access(resolved, os.R_OK):
        report.is_safe = False
        report.block_reason = f"No read permission for '{resolved}'."
        return report

    _find_sensitive_files(resolved, report)
    return report


def validate_question(question: str) -> tuple[bool, str]:
    stripped = question.strip()
    if len(stripped) < 3:
        return False, "Question is too short — please be more specific."
    if len(stripped) > MAX_QUESTION_LEN:
        return False, f"Question exceeds {MAX_QUESTION_LEN} characters."
    return True, ""


def _find_sensitive_files(repo_path: Path, report: PathReport) -> None:
    for item in repo_path.rglob("*"):
        if not item.is_file():
            continue
        if item.name.lower() in _SENSITIVE_NAMES or item.suffix.lower() in _SENSITIVE_EXTS:
            report.sensitive_files.append(str(item.relative_to(repo_path)))

    if report.sensitive_files:
        count = len(report.sensitive_files)
        report.warnings.append(
            f"Found {count} potentially sensitive file(s) (.env, private keys, etc.).\n"
            "  Add them to .gitignore to exclude from the index."
        )
