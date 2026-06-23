from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path

from zeocloud.config.settings import SESSIONS_DIR


@dataclass
class SessionEvent:
    kind: str
    detail: str
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat(timespec="seconds")
    )


@dataclass
class SessionData:
    agent_name: str
    started_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    events: list[SessionEvent] = field(default_factory=list)
    qa_turns: list[dict[str, str]] = field(default_factory=list)
    projects_indexed: list[str] = field(default_factory=list)
    projects_queried: list[str] = field(default_factory=list)

    def log_question(self, project: str, question: str, answer: str) -> None:
        self.qa_turns.append({"project": project, "question": question, "answer": answer})
        if project not in self.projects_queried:
            self.projects_queried.append(project)

    def log_index(self, project: str, file_count: int, chunk_count: int) -> None:
        self.projects_indexed.append(project)
        self.events.append(
            SessionEvent("index", f"Indexed '{project}' — {file_count} files, {chunk_count} chunks")
        )

    def log_event(self, kind: str, detail: str) -> None:
        self.events.append(SessionEvent(kind, detail))


def save_session(session: SessionData) -> Path | None:
    if not session.qa_turns and not session.projects_indexed:
        return None

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    duration_secs = int((now - session.started_at).total_seconds())
    duration_str = _format_duration(duration_secs)
    filename = session.started_at.strftime("%Y-%m-%d_%H-%M-%S") + ".md"
    out: Path = SESSIONS_DIR / filename

    lines: list[str] = [
        f"# Zeocloud Session · {session.started_at.strftime('%Y-%m-%d %H:%M')}\n\n",
        "## Summary\n\n",
        "| Field | Value |\n|---|---|\n",
        f"| Agent | {session.agent_name} |\n",
        f"| Duration | {duration_str} |\n",
        f"| Questions asked | {len(session.qa_turns)} |\n",
        f"| Projects queried | {', '.join(session.projects_queried) or '—'} |\n",
        f"| Projects indexed | {', '.join(session.projects_indexed) or '—'} |\n",
        "\n",
    ]

    if session.events:
        lines.append("## Events\n\n")
        for ev in session.events:
            lines.append(f"- `{ev.timestamp}` **{ev.kind}**: {ev.detail}\n")
        lines.append("\n")

    if session.qa_turns:
        lines.append("## Q&A Log\n\n")
        for i, turn in enumerate(session.qa_turns, start=1):
            lines.append(f"### Question {i} — {turn['project']}\n\n")
            lines.append(f"**Q:** {turn['question']}\n\n")
            lines.append(f"**A:**\n\n{turn['answer']}\n\n")
            lines.append("---\n\n")

    out.write_text("".join(lines), encoding="utf-8")
    return out


def _format_duration(secs: int) -> str:
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    remaining = secs % 60
    if remaining:
        return f"{mins}m {remaining}s"
    return f"{mins}m"
