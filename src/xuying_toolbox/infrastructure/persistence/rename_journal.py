"""时间重命名 JSON 撤回记录。"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from xuying_toolbox.domain.models.photo import RenamePlan
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths


class JsonRenameJournal:
    def __init__(self, paths: SupportPaths) -> None:
        self.paths = paths

    def create(self, plan: RenamePlan) -> Path:
        self.paths.ensure_directories()
        manifest = self.paths.rename_backups / (
            datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8] + ".json"
        )
        payload = {
            "created_at": datetime.now().astimezone().isoformat(),
            "state": "executing",
            "operations": [asdict(operation) for operation in plan.operations],
        }
        self._write_atomic(manifest, payload)
        return manifest

    def latest(self) -> Path | None:
        manifests = (
            sorted(self.paths.rename_backups.glob("*.json"), reverse=True)
            if self.paths.rename_backups.exists()
            else []
        )
        for manifest in manifests:
            try:
                state = self.load(manifest).get("state")
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if state in {None, "completed"}:
                return manifest
        return None

    def load(self, manifest: Path) -> dict[str, Any]:
        return json.loads(manifest.read_text(encoding="utf-8"))

    def mark_completed(self, manifest: Path) -> None:
        payload = self.load(manifest)
        payload["state"] = "completed"
        payload["completed_at"] = datetime.now().astimezone().isoformat()
        self._write_atomic(manifest, payload)

    def mark_failed(self, manifest: Path, detail: str) -> None:
        payload = self.load(manifest)
        payload["state"] = "failed"
        payload["failed_at"] = datetime.now().astimezone().isoformat()
        payload["failure"] = detail
        self._write_atomic(manifest, payload)

    def delete(self, manifest: Path) -> None:
        manifest.unlink(missing_ok=True)

    def _write_atomic(self, manifest: Path, payload: dict[str, Any]) -> None:
        temporary = manifest.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(manifest)
