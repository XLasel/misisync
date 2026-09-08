"""Offline adapter verification. Only captured JSON-RPC responses are read; no network or JS execution."""
import argparse
import asyncio
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl

from app.config import Settings
from app.domain import Window
from app.ports import Document
from app.sources.edu.source import EduApiSource


def key(body):
    method, params = body['method'], body['params']
    if method == 'ScheduleService.getSchedule':
        params = sorted(parse_qsl(params[0]))
    return method, json.dumps(params, sort_keys=True, ensure_ascii=False)


class HarTransport:
    def __init__(self, path, endpoint):
        self.responses = {}
        self.captured_at = []
        for entry in json.loads(Path(path).read_text())['log']['entries']:
            request = entry['request']
            if request['method'] != 'POST' or request['url'] != endpoint or entry['response']['status'] != 200:
                continue
            try:
                body = json.loads(request['postData']['text'])
            except (KeyError, ValueError):
                continue
            if body.get('method') not in ('ScheduleService.getFillialInfo', 'ScheduleService.getSchedule'):
                continue
            self.responses[key(body)] = entry['response']['content']['text'].encode()
            self.captured_at.append(entry['startedDateTime'])

    async def request(self, method, url, *, body=None, headers=None):
        if method != 'POST':
            raise ValueError('Only recorded RPC requests can be replayed')
        request_key = key(json.loads(body))
        if request_key not in self.responses:
            raise ValueError(f'Request not present in HAR: {request_key[0]}; no live fallback')
        return Document(url, self.responses[request_key])


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('har')
    parser.add_argument('--group', action='append', required=True)
    parser.add_argument('--start', type=date.fromisoformat, required=True)
    parser.add_argument('--weeks', type=int, default=4)
    args = parser.parse_args()
    settings = Settings(edu_groups=tuple(args.group), edu_request_delay_seconds=0)
    if args.start.weekday() != 0:
        parser.error('--start must be a Monday')
    window = Window(start=args.start, end=args.start + timedelta(weeks=args.weeks) - timedelta(days=1))
    transport = HarTransport(args.har, settings.edu_api_url)
    snapshot = await EduApiSource(settings).fetch(transport, window)
    print(json.dumps({'groups': len(snapshot.groups), 'lessons': len(snapshot.lessons),
                      'start': window.start.isoformat(), 'end': window.end.isoformat()}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
