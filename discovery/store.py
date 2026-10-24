from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


EMPTY_STORE = {"run": {"status": "idle"}, "candidates": [], "source_errors": []}


class DiscoveryStore:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return dict(EMPTY_STORE)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise ValueError(f"discovery store is invalid: {error}") from error
        if not isinstance(data, dict) or not isinstance(data.get("candidates", []), list):
            raise ValueError("discovery store has an invalid schema")
        return data

    def write(self, payload):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
