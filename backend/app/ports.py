from dataclasses import dataclass
from typing import Optional, Protocol

from .domain import Catalog, Schedule, Snapshot, SourceInfo, Status, Window


class SourceBusy(Exception):
    """The provider cannot accept more work right now."""


@dataclass(frozen=True)
class Document:
    url: str
    content: bytes


class DocumentTransport(Protocol):
    async def request(self, method: str, url: str, *, body: Optional[bytes] = None, headers: Optional[dict] = None) -> Document: ...


class ScheduleProvider(Protocol):
    """Live serving adapter used by HTTP routes. Swap implementations in composition."""

    info: SourceInfo

    async def catalog(self) -> Catalog: ...
    async def schedule(self, group_id: str, window: Window) -> Schedule: ...
    async def status(self) -> Status: ...


class ScheduleSource(Protocol):
    """Optional batch importer (HAR/offline tools). Not required for the live HTTP path."""

    info: SourceInfo

    async def fetch(self, transport: DocumentTransport, window: Window) -> Snapshot: ...
