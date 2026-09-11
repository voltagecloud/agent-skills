#!/usr/bin/env python3
"""Make one Voltage API-key request with curl, without exposing the key in argv."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlencode, urlsplit
from uuid import UUID
from contract import find_operation, load

BASE_URLS = {
    'production': 'https://voltageapi.com/v1',
    'staging': 'https://staging.voltageapi.com/v1',
    'local': 'https://localhost:3210',
}
CONFIG_KEYS = {
    'VOLTAGE_API_KEY', 'VOLTAGE_ORGANIZATION_ID', 'VOLTAGE_ENVIRONMENT_ID',
    'VOLTAGE_WALLET_ID', 'VOLTAGE_API_ENV', 'VOLTAGE_API_URL',
}
SECRET_OPERATIONS = {'create_webhook', 'generate_webhook_key', 'create_session'}
SECRET_FIELDS = {'shared_secret', 'checkout_token', 'checkout_url', 'stream_token', 'api_key', 'preimage'}


def read_config(path, required=False):
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except FileNotFoundError:
        if required:
            raise ValueError('Explicit configuration file does not exist')
        return {}
    with os.fdopen(fd) as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Configuration must be a regular file')
        if os.name == 'posix' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('Configuration must be owned by you with mode 600 (or 400)')
        values = {}
        for number, line in enumerate(file, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, separator, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if not separator or key not in CONFIG_KEYS or key in values:
                raise ValueError(f'Invalid or duplicate configuration key on line {number}')
            if value[:1] in ('"', "'"):
                if len(value) < 2 or value[-1] != value[0]:
                    raise ValueError(f'Unclosed configuration quote on line {number}')
                value = value[1:-1]
            values[key] = value  # Literal data: no expansion, shell execution, or escapes.
        return values


def configuration(path=None, environ=None):
    values = read_config(Path(path).expanduser() if path else Path.home() / '.voltage' / '.env', required=path is not None)
    env = os.environ if environ is None else environ
    values.update({key: env[key] for key in CONFIG_KEYS if key in env})
    return values


def base_url(config):
    if 'VOLTAGE_API_URL' not in config:
        environment = config.get('VOLTAGE_API_ENV', 'production')
        if environment not in BASE_URLS:
            choices = ', '.join(BASE_URLS)
            raise ValueError(f'VOLTAGE_API_ENV must be one of: {choices}')
        return BASE_URLS[environment]

    value = config['VOLTAGE_API_URL']
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError('VOLTAGE_API_URL must be a nonempty HTTPS URL without control characters')
    parsed = urlsplit(value)
    try:
        parsed.port  # Validate a supplied port before the URL reaches curl.
    except ValueError:
        raise ValueError('VOLTAGE_API_URL has an invalid port') from None
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError('VOLTAGE_API_URL must be an HTTPS base URL without credentials, query, or fragment')
    return value.rstrip('/')


def pairs(items, unique=False):
    result = []
    for item in items:
        key, sep, value = item.partition('=')
        if not sep or not key or (unique and key in dict(result)):
            raise ValueError('Parameters must use name=value; path parameters must be unique')
        result.append((key, value))
    return result


def prepare(spec, operation_id, config, params=(), query=(), body=None):
    path, method, operation = find_operation(spec, operation_id)
    auth = operation.get('security', spec.get('security', []))
    if {'api_key': []} not in auth:
        raise ValueError('This helper only supports environment API-key operations; inspect the checkout browser contract instead')
    key = config.get('VOLTAGE_API_KEY', '')
    if not key or any(ord(char) < 32 or ord(char) == 127 for char in key):
        raise ValueError('A nonempty API key without control characters is required')
    parameters = operation.get('parameters', []) + spec['paths'][path].get('parameters', [])
    path_params = {p['name']: p for p in parameters if p.get('in') == 'path'}
    supplied = dict(params)
    if set(supplied) - set(path_params):
        raise ValueError('Unknown path parameter for this operation')
    for name, parameter in path_params.items():
        value = supplied.get(name, config.get('VOLTAGE_' + name.upper()))
        if not value:
            raise ValueError('Missing path parameter: ' + name)
        # Every path parameter in the current contract is a UUID. Fail closed on change.
        if parameter.get('schema', {}).get('format') != 'uuid':
            raise ValueError('Unsupported path parameter format; inspect the updated contract')
        try:
            value = str(UUID(value))
        except ValueError:
            raise ValueError('Path parameter must be a UUID: ' + name) from None
        path = path.replace('{' + name + '}', value)
    allowed_query = {p['name'] for p in parameters if p.get('in') == 'query'}
    if any(re.split(r'\[', key, 1)[0] not in allowed_query for key, value in query):
        raise ValueError('Unknown query parameter for this operation')
    if body is None and operation.get('requestBody', {}).get('required'):
        raise ValueError('This operation requires --body with a JSON file (or - for stdin)')
    if body is not None:
        if 'requestBody' not in operation:
            raise ValueError('This operation does not accept a request body')
        if not isinstance(body, dict):
            raise ValueError('The request JSON must be an object')
    return method, base_url(config) + path + ('?' + urlencode(query) if query else ''), key


def redact(value, key):
    if isinstance(value, dict):
        return {name: '[REDACTED]' if name.lower() in SECRET_FIELDS else redact(item, key) for name, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, str):
        return value.replace(key, '[REDACTED]')
    return value


def curl_request(method, url, key, body, timeout):
    """No shell, redirects, curlrc, trace, or retries. Header travels over stdin."""
    escaped = key.replace('\\', '\\\\').replace('"', '\\"')
    curl_config = f'header = "x-api-key: {escaped}"\n'
    with tempfile.TemporaryDirectory(prefix='voltage-request-') as directory:
        response = Path(directory) / 'response'
        command = ['curl', '--disable', '--silent', '--show-error', '--proto', '=https',
                   '--max-time', str(timeout), '--connect-timeout', str(min(timeout, 10)),
                   '--request', method, '--config', '-', '--header', 'accept: application/json',
                   '--output', str(response), '--write-out', '%{http_code}', '--url', url]
        if body is not None:
            payload = Path(directory) / 'payload.json'
            payload.write_text(json.dumps(body, allow_nan=False))
            payload.chmod(0o600)
            command.extend(['--header', 'content-type: application/json', '--data-binary', '@' + str(payload)])
        environment = {k: v for k, v in os.environ.items() if k not in CONFIG_KEYS}
        try:
            result = subprocess.run(command, input=curl_config, text=True, capture_output=True,
                                    timeout=timeout + 5, env=environment, check=False)
        except (subprocess.TimeoutExpired, OSError):
            raise ValueError('Transport did not complete; submission outcome may be unknown. Reconcile existing resource IDs before retrying.') from None
        if result.returncode:
            raise ValueError(f'curl failed (exit {result.returncode}); submission outcome may be unknown. Reconcile existing resource IDs before retrying.')
        try:
            status = int(result.stdout)
        except ValueError:
            raise ValueError('curl returned an unreadable HTTP status; reconcile before retrying') from None
        raw = response.read_text() if response.exists() else ''
        try:
            content = json.loads(raw) if raw else None
        except ValueError:
            # Do not print arbitrary server HTML/text which might echo credentials.
            content = None
        return {'http_status': status, 'body': content, 'non_json_body': bool(raw and content is None)}


def execute(args):
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 300:
        raise ValueError('--timeout must be greater than 0 and at most 300 seconds')
    config = configuration(args.config)
    body = None
    if args.body:
        try:
            body = json.loads(sys.stdin.read() if args.body == '-' else Path(args.body).read_text(),
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
        except (OSError, ValueError):
            raise ValueError('Unable to read a valid JSON request object') from None
    method, url, key = prepare(load(), args.operation, config,
                               pairs(args.param, unique=True), pairs(args.query), body)
    if args.operation in SECRET_OPERATIONS and not args.output:
        raise ValueError('This operation returns a secret; supply --output with a NEW private file before executing')
    output = None
    try:
        if args.output:
            fd = os.open(Path(args.output).expanduser(), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            output = os.fdopen(fd, 'w')  # Reserve before sending so a one-time secret can be saved.
        result = curl_request(method, url, key, body, args.timeout)
        if output:
            json.dump(result, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
            print(json.dumps({'http_status': result['http_status'], 'response_saved': True}))
        else:
            print(json.dumps(redact(result, key), indent=2))
        return 0 if 200 <= result['http_status'] < 300 else 1
    finally:
        if output:
            output.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', help='Exact operationId from the installed OpenAPI contract')
    parser.add_argument('--config', help='Explicit .env file; process variables still override it')
    parser.add_argument('--param', action='append', default=[], help='Path parameter name=value')
    parser.add_argument('--query', action='append', default=[], help='Query name=value; repeat for arrays using the documented key syntax')
    parser.add_argument('--body', help='JSON file, or - for stdin; body fields are never filled implicitly')
    parser.add_argument('--output', help='NEW file receiving the unredacted response envelope, mode 600')
    parser.add_argument('--timeout', type=float, default=30, help='Per-request seconds, default 30')
    args = parser.parse_args()
    try:
        return execute(args)
    except (ValueError, OSError) as error:
        # OSError filenames may originate from user input; do not expose file contents.
        print(str(error) if isinstance(error, ValueError) else 'File or process operation failed; check paths and permissions. If submission started, reconcile its ID before retrying.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
