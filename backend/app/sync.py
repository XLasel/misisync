import asyncio
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from .parser import ParseError, parse_workbook
from .catalog import institute_name

logger = logging.getLogger(__name__)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), '']

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(tuple(self.current))
            self.current = None


def is_workbook(url):
    return bool(re.search(r'\.xlsx?$', urlparse(url).path, re.I))


async def download(client, url, max_bytes):
    async with client.stream('GET', url) as response:
        response.raise_for_status()
        parts, total = [], 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise ValueError('Source exceeds MAX_DOWNLOAD_BYTES')
            parts.append(chunk)
        return b''.join(parts), str(response.url)


async def discover(client, settings, with_labels=False):
    if is_workbook(settings.source_url):
        return [(settings.source_url, '')] if with_labels else [settings.source_url]
    queue, visited, found = [(settings.source_url, 0)], set(), {}
    host = urlparse(settings.source_url).netloc
    while queue:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if len(visited) > 15:
            raise ValueError('Too many schedule pages')
        data, effective_url = await download(client, url, settings.max_download_bytes)
        parser = Links()
        parser.feed(data.decode('utf-8-sig'))
        for href, label in parser.links:
            target = urljoin(effective_url, href)
            if urlparse(target).scheme not in ('http', 'https') or urlparse(target).netloc != host:
                continue
            if is_workbook(target):
                if not settings.source_link_pattern or re.search(settings.source_link_pattern, target + ' ' + label, re.I):
                    if target not in found:
                        found[target] = label
            elif depth < 2 and ('расписание учебных' in label.lower() or urlparse(target).path.rstrip('/') == '/students/schedule'):
                queue.append((target, depth + 1))
    if not found:
        raise ValueError('No matching XLS/XLSX schedule links found')
    return sorted(found.items()) if with_labels else sorted(found)


class Synchronizer:
    def __init__(self, db, settings):
        self.db, self.settings = db, settings
        self._lock = None

    @property
    def updating(self):
        return self._lock is not None and self._lock.locked()

    async def run_once(self, client=None):
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                if client is None:
                    async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=True, headers={'User-Agent': 'Misisync/1.0 schedule-reader'}) as owned:
                        lessons, groups, warnings = await self.fetch(owned)
                else:
                    lessons, groups, warnings = await self.fetch(client)
                await asyncio.to_thread(self.db.replace, lessons, groups, datetime.now(timezone.utc).isoformat(), self.settings.source_url, warnings)
                logger.info('Imported %d lessons for %d groups', len(lessons), len(groups))
                return True
            except Exception as error:
                logger.exception('Schedule update failed; previous snapshot retained')
                await asyncio.to_thread(self.db.failure, timestamp, f'{type(error).__name__}: {error}'[:1000])
                return False

    async def fetch(self, client):
        lessons, groups, warnings = [], {}, []
        for url, label in await discover(client, self.settings, with_labels=True):
            data, final_url = await download(client, url, self.settings.max_download_bytes)
            parsed, names, notes = await asyncio.to_thread(parse_workbook, data, final_url, self.settings.upper_row_week)
            lessons.extend(parsed)
            institute = institute_name(final_url, label)
            for name in names:
                groups.setdefault(name, set())
                if institute:
                    groups[name].add(institute)
            warnings.extend(notes)
        if not lessons:
            raise ParseError('No lessons found in selected sources')
        return lessons, groups, sorted(set(warnings))

    async def loop(self):
        while True:
            await self.run_once()
            await asyncio.sleep(self.settings.update_interval_seconds)
