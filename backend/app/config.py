import os
from datetime import date
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    academic_reference_date: date = date(2026, 9, 7)
    academic_reference_kind: str = 'lower'
    integration_proxy_secret: str = ''
    request_timeout_seconds: int = 60
    max_download_bytes: int = 30 * 1024 * 1024
    edu_api_url: str = 'https://edu.misis.ru/schedule'
    edu_filial: str = 'MOSCOW'
    edu_groups: tuple[str, ...] = ()
    edu_request_delay_seconds: float = 0.25
    edu_catalog_ttl_seconds: int = 3600
    edu_schedule_ttl_seconds: int = 900
    edu_schedule_cache_max_entries: int = 256
    edu_stale_if_error_seconds: int = 3600
    edu_retry_backoff_seconds: int = 30
    edu_max_pending_requests: int = 64
    edu_max_concurrent_requests: int = 4

    def __post_init__(self):
        if self.integration_proxy_secret and (len(self.integration_proxy_secret) != 64 or any(c not in '0123456789abcdef' for c in self.integration_proxy_secret)):
            raise ValueError('INTEGRATION_PROXY_SECRET must contain 64 lowercase hexadecimal characters')
        if self.academic_reference_kind not in ('upper', 'lower'):
            raise ValueError('Invalid academic reference kind')
        if self.request_timeout_seconds < 1 or self.max_download_bytes < 1024:
            raise ValueError('Invalid timeout or download limit')
        if self.edu_request_delay_seconds < 0 or self.edu_catalog_ttl_seconds < 0 or self.edu_schedule_ttl_seconds < 0:
            raise ValueError('Invalid edu request delay or cache TTL')
        if self.edu_schedule_cache_max_entries < 1 or self.edu_max_pending_requests < 1 or self.edu_max_concurrent_requests < 1:
            raise ValueError('Invalid cache size or concurrency limit')
        if self.edu_stale_if_error_seconds < 0 or self.edu_retry_backoff_seconds < 1:
            raise ValueError('Invalid stale allowance or retry backoff')
        from urllib.parse import urlsplit
        parts = urlsplit(self.edu_api_url)
        if parts.scheme not in ('https', 'http') or not parts.hostname:
            raise ValueError('EDU_API_URL must be an HTTP(S) URL')

    @classmethod
    def from_env(cls):
        converters = {
            'academic_reference_date': date.fromisoformat,
            'request_timeout_seconds': int,
            'max_download_bytes': int,
            'edu_request_delay_seconds': float,
            'edu_catalog_ttl_seconds': int,
            'edu_schedule_ttl_seconds': int,
            'edu_schedule_cache_max_entries': int,
            'edu_stale_if_error_seconds': int,
            'edu_retry_backoff_seconds': int,
            'edu_max_pending_requests': int,
            'edu_max_concurrent_requests': int,
            'edu_groups': lambda v: tuple(x.strip() for x in v.split(',') if x.strip()),
        }
        return cls(**{key: converters.get(key, str)(os.environ[key.upper()])
                      for key in cls.__dataclass_fields__ if key.upper() in os.environ})
