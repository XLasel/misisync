import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .domain import Window


@dataclass(frozen=True)
class Settings:
    database_path: str = 'data/schedule.sqlite3'
    schedule_source: str = 'excel'
    update_interval_seconds: int = 14400
    request_timeout_seconds: int = 60
    max_download_bytes: int = 30 * 1024 * 1024
    enable_scheduler: bool = True
    sync_weeks: int = 4
    excel_source_url: str = 'https://misis.ru/students/'
    excel_link_pattern: str = ''
    excel_upper_row_week: str = 'odd'
    excel_term_start: date = date(2026, 9, 1)
    excel_term_end: date = date(2027, 1, 31)
    edu_api_url: str = 'https://edu.misis.ru/schedule'
    edu_filial: str = 'MOSCOW'
    edu_groups: tuple[str, ...] = ()
    edu_request_delay_seconds: float = 0.25

    def __post_init__(self):
        if self.schedule_source not in ('excel', 'edu_api'):
            raise ValueError('SCHEDULE_SOURCE must be excel or edu_api')
        if self.update_interval_seconds < 60 or self.request_timeout_seconds < 1 or self.max_download_bytes < 1024:
            raise ValueError('Invalid update interval, timeout or download limit')
        if not 1 <= self.sync_weeks <= 12 or self.edu_request_delay_seconds < 0:
            raise ValueError('Invalid sync horizon or request delay')
        if self.excel_upper_row_week not in ('odd', 'even') or self.excel_term_end < self.excel_term_start:
            raise ValueError('Invalid Excel term or row parity')
        from urllib.parse import urlsplit
        for url in (self.excel_source_url, self.edu_api_url):
            if urlsplit(url).scheme not in ('https', 'http') or not urlsplit(url).hostname:
                raise ValueError('Sources must be HTTP(S) URLs')

    def window(self, today=None):
        today = today or datetime.now(ZoneInfo('Europe/Moscow')).date()
        start = today - timedelta(days=today.weekday())
        return Window(start=start, end=start + timedelta(weeks=self.sync_weeks) - timedelta(days=1))

    @classmethod
    def from_env(cls):
        converters = {'update_interval_seconds': int, 'request_timeout_seconds': int,
                      'max_download_bytes': int, 'sync_weeks': int, 'edu_request_delay_seconds': float,
                      'excel_term_start': date.fromisoformat, 'excel_term_end': date.fromisoformat,
                      'edu_groups': lambda v: tuple(x.strip() for x in v.split(',') if x.strip())}
        def boolean(value):
            if value.lower() not in ('true', 'false'):
                raise ValueError('ENABLE_SCHEDULER must be true or false')
            return value.lower() == 'true'
        converters['enable_scheduler'] = boolean
        return cls(**{key: converters.get(key, str)(os.environ[key.upper()])
                      for key in cls.__dataclass_fields__ if key.upper() in os.environ})
