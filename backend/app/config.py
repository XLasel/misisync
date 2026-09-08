import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_path: str = 'data/misisync.sqlite3'
    source_url: str = 'https://misis.ru/students/'
    source_link_pattern: str = ''
    update_interval_seconds: int = 14400
    request_timeout_seconds: int = 60
    max_download_bytes: int = 30 * 1024 * 1024
    enable_scheduler: bool = True
    # MISIS two-row grids: top row = numerator, bottom row = denominator.
    upper_row_week: str = 'odd'

    @classmethod
    def from_env(cls):
        result = cls(
            database_path=os.getenv('DATABASE_PATH', cls.database_path),
            source_url=os.getenv('SOURCE_URL', cls.source_url),
            source_link_pattern=os.getenv('SOURCE_LINK_PATTERN', ''),
            update_interval_seconds=int(os.getenv('UPDATE_INTERVAL_SECONDS', '14400')),
            request_timeout_seconds=int(os.getenv('REQUEST_TIMEOUT_SECONDS', '60')),
            max_download_bytes=int(os.getenv('MAX_DOWNLOAD_BYTES', str(cls.max_download_bytes))),
            enable_scheduler=os.getenv('ENABLE_SCHEDULER', 'true').lower() == 'true',
            upper_row_week=os.getenv('UPPER_ROW_WEEK', 'odd'),
        )
        if result.update_interval_seconds < 60 or result.request_timeout_seconds < 1 or result.max_download_bytes < 1024:
            raise ValueError('Invalid update interval, timeout or download limit')
        if result.upper_row_week not in ('odd', 'even'):
            raise ValueError('UPPER_ROW_WEEK must be odd or even')
        return result
