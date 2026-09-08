import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

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


async def discover(transport, settings):
    if is_workbook(settings.excel_source_url):
        return [(settings.excel_source_url, '')]
    queue, visited, found = [(settings.excel_source_url, 0)], set(), {}
    host = urlparse(settings.excel_source_url).netloc
    while queue:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if len(visited) > 15:
            raise ValueError('Too many schedule pages')
        document = await transport.request('GET', url)
        data, effective_url = document.content, document.url
        parser = Links()
        parser.feed(data.decode('utf-8-sig'))
        for href, label in parser.links:
            target = urljoin(effective_url, href)
            if urlparse(target).scheme not in ('http', 'https') or urlparse(target).netloc != host:
                continue
            if is_workbook(target):
                if not settings.excel_link_pattern or re.search(settings.excel_link_pattern, target + ' ' + label, re.I):
                    if target not in found:
                        found[target] = label
            elif depth < 2 and ('расписание учебных' in label.lower() or urlparse(target).path.rstrip('/') == '/students/schedule'):
                queue.append((target, depth + 1))
    if not found:
        raise ValueError('No matching XLS/XLSX schedule links found')
    return sorted(found.items())


class ExcelLoader:
    def __init__(self, settings):
        self.settings = settings

    async def load(self, transport):
        documents = []
        for url, label in await discover(transport, self.settings):
            document = await transport.request('GET', url)
            documents.append((document, label))
        return documents
