"""
Thread-safe in-memory TTL cache with LRU eviction for hirist_mcp.
Caches static lookups, job details, taxonomies, and profile data to prevent redundant network calls.
"""
import time
import threading
from typing import Any, Optional, Dict, Tuple


class TTLCache:
    """Thread-safe bounded in-memory cache with Time-To-Live (TTL) support."""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value if present and not expired; otherwise return None."""
        with self._lock:
            if key not in self._store:
                return None
            val, expires_at = self._store[key]
            if time.time() > expires_at:
                del self._store[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store key-value pair with expiration time. Evicts expired or oldest entries if full."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl

        with self._lock:
            if len(self._store) >= self.max_size:
                now = time.time()
                # Purge expired keys first
                expired_keys = [k for k, (_, exp) in self._store.items() if exp <= now]
                for k in expired_keys:
                    del self._store[k]

                # If still at capacity, evict oldest 20%
                if len(self._store) >= self.max_size:
                    keys_to_remove = list(self._store.keys())[:int(self.max_size * 0.2) + 1]
                    for k in keys_to_remove:
                        del self._store[k]

            self._store[key] = (value, expires_at)

    def invalidate(self, prefix: str = "") -> int:
        """Invalidate keys matching prefix (or all keys if prefix is empty). Returns count removed."""
        with self._lock:
            if not prefix:
                count = len(self._store)
                self._store.clear()
                return count
            matching = [k for k in self._store if k.startswith(prefix)]
            for k in matching:
                del self._store[k]
            return len(matching)

    def size(self) -> int:
        """Current count of items in cache."""
        with self._lock:
            return len(self._store)


# Global singleton cache instance for hirist_mcp
CACHE = TTLCache(default_ttl=300, max_size=1000)
