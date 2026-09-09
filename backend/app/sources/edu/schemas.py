from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class Upstream(BaseModel):
    model_config = ConfigDict(extra='ignore')


class Subgroup(Upstream):
    id: str
    number: int = Field(ge=1)


class EduGroup(Upstream):
    id: str
    name: str = Field(min_length=1)
    subgroups: list[Subgroup]


class Membership(Upstream):
    group_id: str
    group_name: str
    subgroup_id: Optional[str]
    subgroup_number: Optional[int] = Field(ge=1)


class Teacher(Upstream):
    teacher_name: Optional[str]


class Room(Upstream):
    room_name: Optional[str]


class EduLesson(Upstream):
    lesson_index: str
    subject_id: Optional[str]
    subject_name: Optional[str]
    lesson_type: str
    lesson_start: Optional[str]
    lesson_end: Optional[str]
    rooms: list[Room]
    teachers: list[Teacher]
    ed_groups: list[Membership]


class Cell(Upstream):
    bell_id: str
    bell_subset_id: str
    bell_number: int = Field(ge=1)
    bell_start: Optional[str]
    bell_end: Optional[str]
    lessons: list[EduLesson]

    @property
    def key(self):
        return self.bell_subset_id, self.bell_id, self.bell_number


class Row(Upstream):
    lesson_date: date
    day_number: int = Field(ge=1, le=7)
    cells: list[Cell]


class Week(Upstream):
    week_number: int
    rows: list[Row]


class CalendarResult(Upstream):
    lists: list[Week]
