"""Validate both production templates in an isolated nginx container, without live services."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
image = re.search(r'image: (nginx:\S+)', (ROOT / 'compose.prod.yaml').read_text()).group(1)
with tempfile.TemporaryDirectory(prefix='misisync-nginx-') as directory:
    temp = Path(directory)
    cert = temp / 'certs/live/schedule.example.test'
    cert.mkdir(parents=True)
    templates = temp / 'templates'
    templates.mkdir()
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                    '-subj', '/CN=schedule.example.test', '-keyout', str(cert / 'privkey.pem'),
                    '-out', str(cert / 'fullchain.pem')], check=True, capture_output=True)
    for filename in ['http.conf.template', 'ssl.conf.tls']:
        config = (ROOT / 'deploy/nginx' / filename).read_text()
        assert 'proxy_set_header X-Forwarded-For $remote_addr;' in config
        assert '$proxy_add_x_forwarded_for' not in config
        (templates / 'default.conf.template').write_text(config)
        subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--add-host', 'frontend:127.0.0.1',
                        '-e', 'DOMAIN=schedule.example.test', '-e', 'NGINX_ENVSUBST_FILTER=^DOMAIN$',
                        '-v', f'{templates}:/etc/nginx/templates:ro',
                        '-v', f'{temp / "certs"}:/etc/letsencrypt:ro', image, 'nginx', '-t'], check=True)
        print(f'{filename}: valid', flush=True)
    env = temp / '.env'
    env.write_text('DOMAIN=schedule.example.test\n')
    subprocess.run(['docker', 'compose', '--env-file', str(env), '-f', str(ROOT / 'compose.yaml'),
                    '-f', str(ROOT / 'compose.prod.yaml'), 'config', '--quiet'], check=True)
