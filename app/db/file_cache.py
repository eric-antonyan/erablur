"""Small atomic JSON cache used for Telegram callback state and AI answers."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, List, Optional

from loguru import logger

from app.config.settings import settings


class FileCache:
    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = Path(cache_dir or settings.cache_dir)
        self.index_file = self.cache_dir / "index.json"
        self._lock = threading.RLock()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index: dict[str, dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        with self._lock:
            try:
                if self.index_file.exists():
                    data = json.loads(self.index_file.read_text(encoding="utf-8"))
                    self.index = data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Cache index was reset: {}", exc)
                self.index = {}

    def _atomic_json_write(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as temp:
            json.dump(payload, temp, ensure_ascii=False, separators=(",", ":"))
            temp.flush()
            os.fsync(temp.fileno())
            temp_name = temp.name
        os.replace(temp_name, path)

    def _save_index_locked(self) -> None:
        self._atomic_json_write(self.index_file, self.index)

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def _expired_locked(self, key: str) -> bool:
        meta = self.index.get(key)
        if not meta:
            return True
        try:
            created = datetime.fromisoformat(str(meta.get("timestamp")))
            ttl = max(1, int(meta.get("ttl") or settings.cache_ttl))
            return datetime.now() - created > timedelta(seconds=ttl)
        except (TypeError, ValueError):
            return True

    def _delete_locked(self, key: str) -> None:
        try:
            self._cache_path(key).unlink(missing_ok=True)
        except OSError:
            pass
        self.index.pop(key, None)

    def _prune_locked(self) -> None:
        for key in list(self.index):
            if self._expired_locked(key) or not self._cache_path(key).exists():
                self._delete_locked(key)
        overflow = len(self.index) - settings.max_cache_items
        if overflow > 0:
            oldest = sorted(self.index, key=lambda item: self.index[item].get("timestamp", ""))[:overflow]
            for key in oldest:
                self._delete_locked(key)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self.index or self._expired_locked(key):
                self._delete_locked(key)
                self._save_index_locked()
                return None
            try:
                payload = json.loads(self._cache_path(key).read_text(encoding="utf-8"))
                return payload.get("value") if isinstance(payload, dict) else None
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Cache read failed for {}: {}", key, exc)
                self._delete_locked(key)
                self._save_index_locked()
                return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            try:
                self._atomic_json_write(self._cache_path(key), {"value": value, "created_at": now})
                self.index[key] = {"timestamp": now, "ttl": int(ttl or settings.cache_ttl)}
                self._prune_locked()
                self._save_index_locked()
            except (OSError, TypeError, ValueError) as exc:
                logger.error("Cache write failed for {}: {}", key, exc)

    def delete(self, key: str) -> None:
        with self._lock:
            self._delete_locked(key)
            self._save_index_locked()

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def clear(self) -> None:
        with self._lock:
            for file in self.cache_dir.glob("*.json"):
                if file != self.index_file:
                    file.unlink(missing_ok=True)
            self.index = {}
            self._save_index_locked()
        logger.info("Cache cleared")

    def lpush(self, key: str, value: str, max_len: int = 10) -> None:
        values = self.get(key)
        values = values if isinstance(values, list) else []
        self.set(key, [value, *values][:max_len])

    def lrange(self, key: str, start: int, end: int) -> List[Any]:
        values = self.get(key)
        if not isinstance(values, list):
            return []
        return values[start:end + 1] if end >= 0 else values[start:]

    def ltrim(self, key: str, start: int, end: int) -> None:
        values = self.get(key)
        if isinstance(values, list):
            self.set(key, values[start:end + 1])

    def incr(self, key: str) -> int:
        current = self.get(key)
        value = int(current) + 1 if isinstance(current, (int, float)) else 1
        self.set(key, value)
        return value

    def sadd(self, key: str, value: str) -> None:
        values = self.get(key)
        values = values if isinstance(values, list) else []
        if value not in values:
            values.append(value)
            self.set(key, values)

    def scard(self, key: str) -> int:
        values = self.get(key)
        return len(values) if isinstance(values, list) else 0

    def hset(self, key: str, mapping: dict) -> None:
        current = self.get(key)
        current = current if isinstance(current, dict) else {}
        current.update(mapping)
        self.set(key, current)

    def hgetall(self, key: str) -> dict:
        value = self.get(key)
        return value if isinstance(value, dict) else {}


cache = FileCache()
