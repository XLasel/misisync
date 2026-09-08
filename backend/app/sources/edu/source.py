from datetime import timedelta
from urllib.parse import urlencode

from ...domain import Coverage, Group, Snapshot, SourceInfo, Window, merge_duplicates
from ..classification import education_level
from .gateway import EduGateway
from .mapper import EduMapper
from .schemas import CalendarResult, EduGroup


class EduApiSource:
    """JSON-RPC access to edu.misis.ru. Batch fetch() remains for HAR/offline tools; HTTP serves via EduLiveService."""

    def __init__(self, settings):
        self.settings = settings
        self.info = SourceInfo(id='edu_api', label='Электронное расписание МИСИС', url=settings.edu_api_url, basis='dated')
        self.gateway = EduGateway(settings)
        self.mapper = EduMapper(settings.edu_filial, settings.edu_api_url)

    async def load_catalog(self, transport) -> list[EduGroup]:
        catalog = await self.gateway.rpc(transport, 'getFillialInfo', [self.settings.edu_filial])
        upstream = [EduGroup.model_validate(g) for g in catalog['groups']]
        if not upstream or len({g.id for g in upstream}) != len(upstream) or len({g.name for g in upstream}) != len(upstream):
            raise ValueError('Empty or ambiguous group catalog')
        if self.settings.edu_groups:
            selected = set(self.settings.edu_groups)
            if selected - {g.name for g in upstream}:
                raise ValueError('Configured EDU_GROUPS missing from source catalog')
            upstream = [g for g in upstream if g.name in selected]
        return upstream

    def domain_group(self, edu_group: EduGroup, lessons=()) -> Group:
        return Group(id=edu_group.name, name=edu_group.name, education_level=education_level(edu_group.name),
                     subgroups=sorted({s.number for s in edu_group.subgroups} |
                                      {s for lesson in lessons for s in lesson.subgroup_ids}))

    async def fetch_week(self, transport, edu_group: EduGroup, monday, window: Window):
        saturday = monday + timedelta(days=5)
        params = urlencode({'begin_date': monday.isoformat(), 'end_date': saturday.isoformat(),
                            'ed_group_id': edu_group.id, 'show_ceiltail': 'true', 'show_sunday': 'false'})
        result = CalendarResult.model_validate(await self.gateway.rpc(transport, 'getSchedule', [params]))
        return self.mapper.normalize(result, edu_group, monday, window)

    @staticmethod
    def week_mondays(window: Window):
        monday = window.start - timedelta(days=window.start.weekday())
        while monday <= window.end:
            yield monday
            monday += timedelta(days=7)

    async def fetch(self, transport, window: Window) -> Snapshot:
        upstream = await self.load_catalog(transport)
        groups, lessons = [], []
        for group in upstream:
            group_lessons = []
            for monday in self.week_mondays(window):
                group_lessons.extend(await self.fetch_week(transport, group, monday, window))
            groups.append(self.domain_group(group, group_lessons))
            lessons.extend(group_lessons)
        return Snapshot(source=self.info, coverage=Coverage(**window.model_dump(), weekdays=list(range(6))),
                        groups=groups, lessons=merge_duplicates(lessons),
                        warnings=['Источник предоставляет данные с понедельника по субботу. Воскресенье не загружено.'])
