"""Export the external gateway contract, without the private proxy credential."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.main import create_app

schema = create_app().openapi()
schema['info'] = {'title': 'Misisync integration API', 'version': '1.0.0',
                  'description': 'Client certificate required. Times are Europe/Moscow. Week parity is an estimate.'}
schema['servers'] = [{'url': 'https://schedule.sovngarde.ru:8443'}]
schema['paths'] = {k: v for k, v in schema['paths'].items() if k.startswith('/api/v1/')}
schema['components']['securitySchemes'] = {'ClientCertificate': {'type': 'mutualTLS'}}
for path in schema['paths'].values():
    for operation in path.values():
        operation['security'] = [{'ClientCertificate': []}]
Path('docs/api/openapi.json').write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\n')
