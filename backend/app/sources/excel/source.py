import asyncio
from ...domain import SourceInfo, Window, Snapshot
from .loader import ExcelLoader
from .mapper import ExcelMapper


class ExcelSource:
    def __init__(self, settings):
        self.info = SourceInfo(id='excel', label='Таблицы МИСИС', url=settings.excel_source_url, basis='weekly_template')
        self.loader = ExcelLoader(settings)
        self.mapper = ExcelMapper(settings, self.info)

    async def fetch(self, transport, window: Window) -> Snapshot:
        documents = await self.loader.load(transport)
        return await asyncio.to_thread(self.mapper.map, documents, window)
