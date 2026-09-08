from dataclasses import dataclass
from typing import Optional, Protocol
from .domain import Catalog, Schedule, Snapshot, SourceInfo, Status, Window


@dataclass(frozen=True)
class Document:
    url: str
    content: bytes


class DocumentTransport(Protocol):
    async def request(self, method: str, url: str, *, body: Optional[bytes] = None, headers: Optional[dict] = None) -> Document: ...


class ScheduleSource(Protocol):
    info: SourceInfo

    async def fetch(self, transport: DocumentTransport, window: Window) -> Snapshot: ...


class ScheduleRepository(Protocol):
    def initialize(self) -> None: ...
    def replace(self, snapshot: Snapshot, timestamp: str) -> None: ...
    def failure(self, timestamp: str, message: str) -> None: ...
    def status(self) -> Status: ...
    def catalog(self) -> Catalog: ...
    def schedule(self, group_id: str, window: Window) -> Schedule: ...
