from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    postgres_dsn: str = os.getenv(
        "POSTGRES_DSN",
        os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/meeting_ops_os",
        ),
    )
    meeting_checkpoint_namespace: str = os.getenv("MEETING_CHECKPOINT_NAMESPACE", "meeting")
    approval_required_tools: tuple[str, ...] = tuple(
        t.strip()
        for t in os.getenv("APPROVAL_REQUIRED_TOOLS", "jira.create_issue,feishu.send_message,email.send").split(",")
        if t.strip()
    )
    memory_dsn: str = os.getenv(
        "MEETING_MEMORY_DSN",
        os.getenv(
            "POSTGRES_DSN",
            os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/meeting_ops_os"),
        ),
    )


settings = AppConfig()
