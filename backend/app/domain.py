"""Source-independent calendar contract. No HTTP, SQLite or spreadsheet knowledge."""
import hashlib
import json
from datetime import date, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


def identity(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Window(Model):
    start: date
    end: date

    @model_validator(mode='after')
    def ordered(self):
        if self.end < self.start:
            raise ValueError('End must not precede start')
        return self

    def dates(self):
        for offset in range((self.end - self.start).days + 1):
            yield self.start + timedelta(days=offset)


class Coverage(Window):
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)))

    @model_validator(mode='after')
    def valid_days(self):
        if not self.weekdays or any(d not in range(7) for d in self.weekdays):
            raise ValueError('Invalid coverage weekdays')
        return self

    def includes(self, day: date) -> bool:
        return self.start <= day <= self.end and day.weekday() in self.weekdays


class SourceInfo(Model):
    id: str
    label: str
    url: str
    basis: Literal['dated', 'weekly_template']


class Group(Model):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    institutes: list[str] = Field(default_factory=list)
    education_level: str = ''
    subgroups: list[int] = Field(default_factory=list)


class Evidence(Model):
    url: str
    label: str
    raw_text: str
    external_id: Optional[str] = None


class Lesson(Model):
    id: str = Field(min_length=1)
    group_id: str
    date: date
    start_time: Optional[str] = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    end_time: Optional[str] = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    subject: str = Field(min_length=1)
    lesson_type: str = ''
    teachers: list[str] = Field(default_factory=list)
    rooms: list[str] = Field(default_factory=list)
    subgroup_ids: list[int] = Field(default_factory=list)
    subgroup_label: str = ''
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(min_length=1)

    @model_validator(mode='after')
    def valid_time(self):
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError('Time interval must be complete or unknown')
        if self.start_time and self.end_time <= self.start_time:
            raise ValueError('Invalid time interval')
        if any(i < 1 for i in self.subgroup_ids):
            raise ValueError('Invalid subgroup number')
        return self


def merge_duplicates(lessons: list[Lesson]) -> list[Lesson]:
    """Keep one calendar entry and every distinct source reference."""
    merged = {}
    for lesson in lessons:
        previous = merged.get(lesson.id)
        if previous is None:
            merged[lesson.id] = lesson
            continue
        if previous.model_dump(exclude={'evidence'}) != lesson.model_dump(exclude={'evidence'}):
            raise ValueError('Conflicting lesson IDs')
        evidence = {e.model_dump_json(): e for e in previous.evidence + lesson.evidence}
        merged[lesson.id] = previous.model_copy(update={'evidence': list(evidence.values())})
    return list(merged.values())


class Snapshot(Model):
    source: SourceInfo
    coverage: Coverage
    groups: list[Group] = Field(min_length=1)
    lessons: list[Lesson]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def consistent(self):
        groups = {g.id for g in self.groups}
        if len(groups) != len(self.groups):
            raise ValueError('Duplicate group IDs')
        seen = {}
        for lesson in self.lessons:
            if lesson.group_id not in groups or not self.coverage.includes(lesson.date):
                raise ValueError('Lesson outside snapshot groups or coverage')
            if lesson.id in seen and lesson != seen[lesson.id]:
                raise ValueError('Conflicting lesson IDs')
            seen[lesson.id] = lesson
        return self


class Status(Model):
    source: Optional[SourceInfo] = None
    coverage: Optional[Coverage] = None
    revision: Optional[str] = None
    last_success: Optional[str] = None
    last_attempt: Optional[str] = None
    last_error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    group_count: int = 0
    lesson_count: int = 0
    configured_source: str = ''
    updating: bool = False


class Catalog(Model):
    revision: Optional[str]
    groups: list[Group]


class Schedule(Model):
    revision: Optional[str]
    group: Optional[Group]
    source: Optional[SourceInfo]
    coverage: Optional[Coverage]
    window: Window
    available_dates: list[date]
    lessons: list[Lesson]
    warnings: list[str]
