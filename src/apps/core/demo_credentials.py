from __future__ import annotations

from pathlib import Path

from django.conf import settings


def record_local_demo_credential(*, email: str, password: str) -> None:
    """Append a newly created local-only account without replacing user entries."""
    credential_file = Path(settings.PROJECT_ROOT) / "tmp" / "test-accounts.txt"
    credential_file.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = (
        credential_file.read_text(encoding="utf-8").splitlines() if credential_file.exists() else []
    )
    if not any(line.partition(":")[0].strip() == email for line in existing_lines):
        existing_lines.append(f"{email}: {password}")
        credential_file.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")
    credential_file.chmod(0o600)
