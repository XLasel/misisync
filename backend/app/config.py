import os
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class Settings:
    request_timeout_seconds: int = 60
    max_download_bytes: int = 30 * 1024 * 1024
    edu_api_url: str = 'https://edu.misis.ru/schedule'
    edu_filial: str = 'MOSCOW'
    edu_groups: tuple[str, ...] = ()
    edu_request_delay_seconds: float = 0.25
    edu_catalog_ttl_seconds: int = 3600
    edu_schedule_ttl_seconds: int = 900
    edu_schedule_cache_max_entries: int = 256
    schedule_rate_limit_per_minute: int = 60

    def __post_init__(self):
        if self.request_timeout_seconds < 1 or self.max_download_bytes < 1024:
            raise ValueError('Invalid timeout or download limit')
        if self.edu_request_delay_seconds < 0 or self.edu_catalog_ttl_seconds < 0 or self.edu_schedule_ttl_seconds < 0:
            raise ValueError('Invalid edu request delay or cache TTL')
        if self.edu_schedule_cache_max_entries < 1 or self.schedule_rate_limit_per_minute < 1:
            raise ValueError('Invalid cache size or rate limit')
        from urllib.parse import urlsplit
        parts = urlsplit(self.edu_api_url)
        if parts.scheme not in ('https', 'http') or not parts.hostname:
            raise ValueError('EDU_API_URL must be an HTTP(S) URL')

    @classmethod
    def from_env(cls):
        converters = {
            'request_timeout_seconds': int,
            'max_download_bytes': int,
            'edu_request_delay_seconds': float,
            'edu_catalog_ttl_seconds': int,
            'edu_schedule_ttl_seconds': int,
            'edu_schedule_cache_max_entries': int,
            'schedule_rate_limit_per_minute': int,
            'edu_groups': lambda v: tuple(x.strip() for x in v.split(',') if x.strip()),
        }
        return cls(**{key: converters.get(key, str)(os.environ[key.upper()])
                      for key in cls.__dataclass_fields__ if key.upper() in os.environ})


class SlidingWindowRateLimiter:
    """In-memory fixed-window limiter for a single process."""

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = monotonic()
        bucket = self._hits[key]
        while bucket and bucket[0] <= now - self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True
