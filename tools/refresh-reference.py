#!/usr/bin/env python3
"""Fetch a candidate or explicitly adopt a reviewed Voltage OpenAPI snapshot."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'voltage-api'
sys.path.insert(0, str(SKILL / 'scripts'))
from contract import operations, reference_closure

URL = 'https://voltageapi.com/v1/openapi/docs.json'
REF = SKILL / 'references'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(data):
    spec = json.loads(data)
    if not spec.get('openapi', '').startswith('3.1.') or spec.get('servers') != [{'url': '/v1'}]:
        raise ValueError('Unexpected OpenAPI version/server; review before extending the updater')
    ids = [o.get('operationId') for _, _, o in operations(spec)]
    if not ids or None in ids or len(ids) != len(set(ids)):
        raise ValueError('Missing or duplicate operation IDs')
    reference_closure(spec, spec)
    return spec


def index(spec):
    lines = ['# Voltage API operation index', '',
             'Generated from [openapi.json](openapi.json); do not edit by hand.', '',
             'Base URL: `https://voltageapi.com/v1`. Every path below is relative to it.',
             f'{sum(1 for _ in operations(spec))} operations across {len(spec["paths"])} paths.', '',
             'Inspect the exact operation by ID with `scripts/inspect-operation.py`.',
             'Use `--part request`, `--part response`, or `--part all`. The output includes',
             'referenced definitions, parameters, response codes, and security schemes.',
             'An absent security declaration does not imply that a body contains no credentials.', '',
             'Embedded workflow guides can be read with `--guide Payments` or `--guide Webhooks`;',
             'use `--section` with an exact heading to narrow the output. Guide names and',
             'operation IDs retain upstream terminology.', '']
    groups = {}
    for path, method, operation in operations(spec):
        groups.setdefault((operation.get('tags') or ['Other'])[0], []).append((path, method, operation))
    for group, items in groups.items():
        lines += ['## ' + group, '', '| Operation ID | Method and path | Authentication | Responses |', '|---|---|---|---|']
        for path, method, operation in items:
            auth = operation.get('security', spec.get('security', []))
            display = ' OR '.join(' + '.join(s) or 'none' for s in auth) if auth else 'No scheme declared; inspect body/parameters'
            lines.append(f'| `{operation["operationId"]}` | `{method} {path}` | {display} | {", ".join(operation["responses"])} |')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--fetch', type=Path, help='Fetch to a new candidate file and write provenance sidecar')
    mode.add_argument('--adopt', type=Path, help='Adopt an already reviewed local candidate')
    mode.add_argument('--check', action='store_true', help='Offline check of snapshot hash and generated index')
    parser.add_argument('--retrieved-at', help='ISO timestamp for manually fetched candidate without sidecar')
    args = parser.parse_args()
    if args.fetch:
        with urlopen(URL, timeout=30) as response:
            data = response.read()
        validate(data)
        metadata = {'url': URL, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'sha256': digest(data)}
        with args.fetch.open('xb') as output:
            output.write(data)
        args.fetch.with_suffix(args.fetch.suffix + '.source.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print('Candidate fetched; review the diff before --adopt')
        return
    manifest_path = REF / 'sources.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'product_sources': []}
    if args.adopt:
        data = args.adopt.read_bytes()
        spec = validate(data)
        sidecar = args.adopt.with_suffix(args.adopt.suffix + '.source.json')
        if sidecar.exists():
            source = json.loads(sidecar.read_text())
            if source.get('url') != URL or source.get('sha256') != digest(data):
                raise ValueError('Candidate provenance does not match its bytes/source')
        elif args.retrieved_at:
            datetime.fromisoformat(args.retrieved_at.replace('Z', '+00:00'))
            source = {'url': URL, 'retrieved_at': args.retrieved_at, 'sha256': digest(data)}
        else:
            raise ValueError('Manual candidates need --retrieved-at; fetched candidates carry a sidecar')
        source.update({'reference_page': 'https://voltageapi.com/v1/docs', 'file': 'openapi.json',
                       'openapi': spec['openapi'], 'info_version': spec['info']['version'],
                       'operation_count': sum(1 for _ in operations(spec))})
        manifest['contract'] = source
        (REF / 'openapi.json').write_bytes(data)
        (REF / 'api-index.md').write_text(index(spec))
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        print('Snapshot/index/provenance updated. Review handwritten guidance and run tests before release.')
    else:
        data = (REF / 'openapi.json').read_bytes()
        spec = validate(data)
        if manifest['contract']['sha256'] != digest(data):
            raise ValueError('Snapshot hash mismatch')
        if (REF / 'api-index.md').read_text() != index(spec):
            raise ValueError('Operation index is stale')
        print('Snapshot hash, references, operation IDs, and generated index verified')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        sys.exit(str(error))
