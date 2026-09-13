"""Exercise real nginx mTLS with temporary certificates and a local fake upstream."""
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
IMAGE = re.search(r'image: (nginx:\S+)', (ROOT / 'compose.integration.yaml').read_text()).group(1)

def command(*args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT, text=True).strip()

with tempfile.TemporaryDirectory(prefix='misisync-mtls-') as folder:
    p = Path(folder)
    for name in ['server', 'ca', 'outsider']:
        command('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                '-subj', '/CN=localhost', '-keyout', str(p / f'{name}.key'), '-out', str(p / f'{name}.crt'))
    command('openssl', 'req', '-new', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=bot',
            '-keyout', str(p / 'client.key'), '-out', str(p / 'client.csr'))
    command('openssl', 'x509', '-req', '-in', str(p / 'client.csr'), '-CA', str(p / 'ca.crt'),
            '-CAkey', str(p / 'ca.key'), '-CAcreateserial', '-days', '1', '-out', str(p / 'client.crt'))
    config = (ROOT / 'deploy/nginx/integration.conf.template').read_text()
    config = config.replace('${DOMAIN}', 'localhost').replace('${INTEGRATION_PROXY_SECRET}', 'a' * 64)
    config = config.replace('/etc/letsencrypt/live/localhost/fullchain.pem', '/test/server.crt')
    config = config.replace('/etc/letsencrypt/live/localhost/privkey.pem', '/test/server.key')
    config = config.replace('/etc/nginx/client-pki/ca.crt', '/test/ca.crt')
    config = config.replace('http://backend:8000', 'http://127.0.0.1:8081')
    config += '\nserver { listen 127.0.0.1:8081; location / { return 200 "$http_x_integration_key"; } }\n'
    (p / 'default.conf').write_text(config)
    cid = command('docker', 'run', '-d', '--rm', '-p', '127.0.0.1::8443',
                  '-v', f'{p}:/test:ro', '-v', f'{p}/default.conf:/etc/nginx/conf.d/default.conf:ro', IMAGE)
    try:
        port = json.loads(command('docker', 'inspect', cid))[0]['NetworkSettings']['Ports']['8443/tcp'][0]['HostPort']
        url = f'https://127.0.0.1:{port}/api/v1/schedule'
        def fetch(client=None, path=url):
            context = ssl.create_default_context(cafile=str(p / 'server.crt'))
            context.check_hostname = False  # local fixture cert has CN only; production clients verify hostname.
            if client:
                context.load_cert_chain(str(p / f'{client}.crt'), str(p / f'{client}.key'))
            try:
                with urllib.request.urlopen(urllib.request.Request(path, headers={'X-Integration-Key': 'forged'}), context=context, timeout=3) as response:
                    return response.status, response.read().decode()
            except urllib.error.HTTPError as exc:
                return exc.code, ''
            except (urllib.error.URLError, ssl.SSLError):
                return 0, ''
        for _ in range(40):
            status, body = fetch('client')
            if status == 200:
                break
            time.sleep(.1)
        assert status == 200 and body == 'a' * 64, (status, body, command('docker', 'logs', cid))
        assert fetch()[0] != 200, 'Missing certificate accepted'
        assert fetch('outsider')[0] != 200, 'Untrusted certificate accepted'
        assert fetch('client', f'https://127.0.0.1:{port}/api/groups')[0] == 404
        print('mTLS: trusted client accepted; missing/untrusted rejected; proxy secret overwritten; other routes denied')
    finally:
        command('docker', 'stop', cid)
