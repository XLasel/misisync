from datetime import timedelta
from urllib.parse import urlencode
from ...domain import Coverage, Group, Snapshot, SourceInfo, Window, merge_duplicates
from ..classification import education_level
from .schemas import EduGroup, CalendarResult
from .gateway import EduGateway
from .mapper import EduMapper


class EduApiSource:
    def __init__(self, settings):
        self.settings = settings
        self.info = SourceInfo(id='edu_api', label='Электронное расписание МИСИС', url=settings.edu_api_url, basis='dated')
        self.gateway = EduGateway(settings)
        self.mapper = EduMapper(settings.edu_filial, settings.edu_api_url)

    async def fetch(self, transport, window: Window) -> Snapshot:
        catalog = await self.gateway.rpc(transport, 'getFillialInfo', [self.settings.edu_filial])
        upstream = [EduGroup.model_validate(g) for g in catalog['groups']]
        if not upstream or len({g.id for g in upstream}) != len(upstream) or len({g.name for g in upstream}) != len(upstream):
            raise ValueError('Empty or ambiguous group catalog')
        if self.settings.edu_groups:
            selected = set(self.settings.edu_groups)
            if selected - {g.name for g in upstream}:
                raise ValueError('Configured EDU_GROUPS missing from source catalog')
            upstream = [g for g in upstream if g.name in selected]
        groups, lessons = [], []
        for group in upstream:
            group_lessons = []
            monday = window.start - timedelta(days=window.start.weekday())
            while monday <= window.end:
                saturday = monday + timedelta(days=5)
                params = urlencode({'begin_date': monday.isoformat(), 'end_date': saturday.isoformat(),
                                    'ed_group_id': group.id, 'show_ceiltail': 'true', 'show_sunday': 'false'})
                result = CalendarResult.model_validate(await self.gateway.rpc(transport, 'getSchedule', [params]))
                group_lessons.extend(self.mapper.normalize(result, group, monday, window))
                monday += timedelta(days=7)
            groups.append(Group(id=group.name, name=group.name, education_level=education_level(group.name),
                                subgroups=sorted({s.number for s in group.subgroups} |
                                                 {s for l in group_lessons for s in l.subgroup_ids})))
            lessons.extend(group_lessons)
        return Snapshot(source=self.info, coverage=Coverage(**window.model_dump(), weekdays=list(range(6))),
                        groups=groups, lessons=merge_duplicates(lessons),
                        warnings=['Источник предоставляет данные с понедельника по субботу. Воскресенье не загружено.'])
