import asyncio
import json


class EduGateway:
    def __init__(self, settings):
        self.settings = settings

    async def rpc(self, transport, method, params):
        await asyncio.sleep(self.settings.edu_request_delay_seconds)
        body = {'jsonrpc': '2.0', 'method': f'ScheduleService.{method}', 'params': params, 'id': 1}
        document = await transport.request('POST', self.settings.edu_api_url, body=json.dumps(body).encode(),
                                           headers={'Content-Type': 'text/plain;charset=UTF-8'})
        envelope = json.loads(document.content)
        if not isinstance(envelope, dict) or envelope.get('jsonrpc') != '2.0' or envelope.get('id') != 1:
            raise ValueError('Invalid JSON-RPC envelope')
        if 'error' in envelope or 'result' not in envelope:
            raise ValueError('JSON-RPC source returned an error or missing result')
        return envelope['result']
