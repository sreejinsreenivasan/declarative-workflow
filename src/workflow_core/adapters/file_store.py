"""File-backed ExecutionStore: one JSON file per execution.

For single-process tools, CLIs and local agents that need suspended runs to survive a
restart without Redis. Writes are atomic (temp file + rename), so a crash mid-save never
leaves a half-written execution. Not for concurrent writers across processes.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path

from workflow_core.context import Context

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _check_id(execution_id: str) -> str:
    if not _SAFE_ID.match(execution_id) or ".." in execution_id:
        raise ValueError(
            f"unsafe execution id {execution_id!r}: use letters, digits, '.', '_' or '-'"
        )
    return execution_id


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class FileStore:
    def __init__(self, directory: str | os.PathLike[str]) -> None:
        self._dir = Path(directory)

    def _path(self, execution_id: str) -> Path:
        return self._dir / f"{_check_id(execution_id)}.json"

    async def save(self, execution_id: str, context: Context) -> None:
        path = self._path(execution_id)
        await asyncio.to_thread(_write_atomic, path, context.model_dump_json(indent=1))

    async def load(self, execution_id: str) -> Context | None:
        path = self._path(execution_id)
        if not path.exists():
            return None
        text = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return Context.model_validate_json(text)
