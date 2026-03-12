"""
Local workspace storage — saved targets, notes, search history.
All data is persisted to ~/.config/shodan-tui/ as JSON files.
Nothing here is ever sent to Shodan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shodan_tui.config import Config

MAX_HISTORY = 100


@dataclass
class SavedTarget:
    ip: str
    label: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    investigation: str = "Default"
    saved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def from_dict(cls, data: dict) -> "SavedTarget":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HistoryEntry:
    query: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    result_count: int = 0


class WorkspaceStorage:
    """Persists saved targets, notes, and search history locally."""

    def __init__(self, config: "Config") -> None:
        self._workspace_file = config.workspace_file
        self._history_file = config.history_file
        self._targets: list[SavedTarget] = []
        self._history: list[HistoryEntry] = []
        self._load()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._workspace_file.exists():
            try:
                raw = json.loads(self._workspace_file.read_text(encoding="utf-8"))
                self._targets = [SavedTarget.from_dict(t) for t in raw.get("targets", [])]
            except Exception:
                self._targets = []

        if self._history_file.exists():
            try:
                raw = json.loads(self._history_file.read_text(encoding="utf-8"))
                self._history = [HistoryEntry(**h) for h in raw]
            except Exception:
                self._history = []

    def _save_workspace(self) -> None:
        self._workspace_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"targets": [asdict(t) for t in self._targets]}
        self._workspace_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _save_history(self) -> None:
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        self._history_file.write_text(
            json.dumps([asdict(h) for h in self._history], indent=2),
            encoding="utf-8",
        )

    # ── Targets ───────────────────────────────────────────────────────────────

    @property
    def targets(self) -> list[SavedTarget]:
        return list(self._targets)

    def save_target(
        self,
        ip: str,
        label: str | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
        investigation: str | None = None,
    ) -> SavedTarget:
        """Save or update an IP target in the workspace.

        Only fields that are explicitly passed (not None) are written.
        Pass an empty string to intentionally clear a field.
        """
        for t in self._targets:
            if t.ip == ip:
                if label is not None:
                    t.label = label
                if notes is not None:
                    t.notes = notes
                if tags is not None:
                    t.tags = tags
                if investigation is not None:
                    t.investigation = investigation
                self._save_workspace()
                return t
        # New target — use sensible defaults for any fields not supplied
        target = SavedTarget(
            ip=ip,
            label=label or "",
            notes=notes or "",
            tags=tags or [],
            investigation=investigation or "Default",
        )
        self._targets.append(target)
        self._save_workspace()
        return target

    def remove_target(self, ip: str) -> bool:
        """Remove a saved target. Returns True if it was found and removed."""
        before = len(self._targets)
        self._targets = [t for t in self._targets if t.ip != ip]
        if len(self._targets) < before:
            self._save_workspace()
            return True
        return False

    def get_target(self, ip: str) -> SavedTarget | None:
        return next((t for t in self._targets if t.ip == ip), None)

    def get_investigations(self) -> list[str]:
        """Return all unique investigation names."""
        names = {t.investigation for t in self._targets}
        return sorted(names) or ["Default"]

    def is_saved(self, ip: str) -> bool:
        return any(t.ip == ip for t in self._targets)

    # ── History ───────────────────────────────────────────────────────────────

    @property
    def history(self) -> list[HistoryEntry]:
        return list(self._history)

    def add_history(self, query: str, result_count: int = 0) -> None:
        """Add a query to history, deduplicating and capping at MAX_HISTORY."""
        self._history = [h for h in self._history if h.query != query]
        self._history.insert(0, HistoryEntry(query=query, result_count=result_count))
        self._history = self._history[:MAX_HISTORY]
        self._save_history()

    def clear_history(self) -> None:
        self._history = []
        self._save_history()
