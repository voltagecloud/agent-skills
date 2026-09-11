import argparse
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills' / 'voltage-api' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('voltage_request', SCRIPTS / 'request.py')
request = importlib.util.module_from_spec(spec)
spec.loader.exec_module(request)

ORG = 'b0684ab8-1130-46af-8f70-71519442f108'
ENV = '123e4567-e89b-12d3-a456-426614174000'
WALLET = '7a68a525-9d11-4c1e-a3dd-1c2bf1378ba2'
KEY = 'synthetic-test-key-not-a-real-credential'
CONFIG = {'VOLTAGE_API_KEY': KEY, 'VOLTAGE_ORGANIZATION_ID': ORG, 'VOLTAGE_ENVIRONMENT_ID': ENV, 'VOLTAGE_WALLET_ID': WALLET}


class ConfigTests(unittest.TestCase):
    def test_literal_parser_and_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            marker = Path(directory) / 'must-not-exist'
            path.write_text(f'# comment\nVOLTAGE_API_KEY="$(touch {marker})"\nVOLTAGE_ENVIRONMENT_ID={ENV}\n')
            path.chmod(0o600)
            values = request.configuration(path, {'VOLTAGE_ENVIRONMENT_ID': ORG})
            self.assertEqual(values['VOLTAGE_ENVIRONMENT_ID'], ORG)
            self.assertTrue(values['VOLTAGE_API_KEY'].startswith('$(touch'))
            self.assertFalse(marker.exists())
            self.assertEqual(request.configuration(path, {'VOLTAGE_API_KEY': ''})['VOLTAGE_API_KEY'], '')
            self.assertIn('$(touch', path.read_text())

    def test_private_regular_config_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('VOLTAGE_API_KEY=test\n')
            path.chmod(0o644)
            with self.assertRaises(ValueError): request.read_config(path)
            path.chmod(0o600)
            link = Path(directory) / 'link'
            link.symlink_to(path)
            with self.assertRaises(OSError): request.read_config(link)
            path.write_text('VOLTAGE_API_KEY=a\nVOLTAGE_API_KEY=b\n')
            with self.assertRaises(ValueError): request.read_config(path)

    def test_api_environment_and_url_are_loaded_with_process_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('VOLTAGE_API_ENV=staging\nVOLTAGE_API_URL=https://saved.example.test/v1/\n')
            path.chmod(0o600)
            values = request.configuration(path, {'VOLTAGE_API_URL': 'https://process.example.test/api'})
            self.assertEqual(values['VOLTAGE_API_ENV'], 'staging')
            self.assertEqual(values['VOLTAGE_API_URL'], 'https://process.example.test/api')


class RequestTests(unittest.TestCase):
    def test_base_url_defaults_and_shortcuts(self):
        spec = request.load()
        for environment, expected in [
            (None, 'https://voltageapi.com/v1'),
            ('production', 'https://voltageapi.com/v1'),
            ('staging', 'https://staging.voltageapi.com/v1'),
            ('local', 'https://localhost:3210'),
        ]:
            config = dict(CONFIG)
            if environment:
                config['VOLTAGE_API_ENV'] = environment
            _, url, _ = request.prepare(spec, 'get_payments', config)
            self.assertTrue(url.startswith(expected + '/organizations/'))

    def test_custom_base_url_wins_and_is_validated(self):
        custom = {**CONFIG, 'VOLTAGE_API_ENV': 'invalid-but-ignored', 'VOLTAGE_API_URL': 'https://api.example.test/custom/'}
        _, url, _ = request.prepare(request.load(), 'get_payments', custom)
        self.assertTrue(url.startswith('https://api.example.test/custom/organizations/'))
        for value in ['', 'http://api.example.test/v1', 'https://user:pass@api.example.test/v1',
                      'https://api.example.test/v1?key=value', 'https://api.example.test:bad/v1']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    request.prepare(request.load(), 'get_payments', {**CONFIG, 'VOLTAGE_API_URL': value})
        with self.assertRaisesRegex(ValueError, 'VOLTAGE_API_ENV'):
            request.prepare(request.load(), 'get_payments', {**CONFIG, 'VOLTAGE_API_ENV': 'preview'})

    def test_explicit_overrides_encoding_and_original_configuration(self):
        config = dict(CONFIG)
        method, url, key = request.prepare(request.load(), 'get_payments', config, [('environment_id', ORG)], [('statuses[]', 'completed'), ('metadata[external_id]', 'a&b?c')])
        self.assertEqual(method, 'GET')
        self.assertIn('/environments/' + ORG + '/payments', url)
        self.assertIn('metadata%5Bexternal_id%5D=a%26b%3Fc', url)
        self.assertEqual(config, CONFIG)
        self.assertNotIn(key, url)

    def test_rejects_wrong_auth_paths_queries_and_header_injection(self):
        for op, config, params, query in [
            ('get_session', CONFIG, [], []),
            ('get_wallet', CONFIG, [('wallet_id', '../../elsewhere')], []),
            ('get_wallet', CONFIG, [('unexpected', WALLET)], []),
            ('get_wallet', CONFIG, [], [('unknown', 'x')]),
            ('get_wallet', {**CONFIG, 'VOLTAGE_API_KEY': 'x\nheader=bad'}, [], []),
        ]:
            with self.subTest(op=op, params=params):
                with self.assertRaises(ValueError): request.prepare(request.load(), op, config, params, query)
        with self.assertRaises(ValueError): request.prepare(request.load(), 'create_payment', CONFIG)

    def test_redacts_known_secrets_and_exact_key_echo(self):
        self.assertEqual(request.redact({'shared_secret': 'secret', 'data': {'echo': KEY}, 'checkout_url': 'https://example.test/#token'}, KEY),
                         {'shared_secret': '[REDACTED]', 'data': {'echo': '[REDACTED]'}, 'checkout_url': '[REDACTED]'})

    def test_secret_output_reserved_before_transport_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / 'request.json'
            body.write_text(json.dumps({'id': WALLET, 'url': 'https://example.test/webhook', 'name': 'test', 'events': [{'receive': 'completed'}]}))
            output = Path(directory) / 'secret.json'
            args = argparse.Namespace(config=None, operation='create_webhook', body=str(body), param=[], query=[], timeout=30, output=None)
            with patch.object(request, 'configuration', return_value=CONFIG), patch.object(request, 'curl_request') as transport:
                with self.assertRaises(ValueError): request.execute(args)
                transport.assert_not_called()
                args.output = str(output)
                def respond(*unused):
                    self.assertTrue(output.exists())
                    self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
                    return {'http_status': 202, 'body': {'id': WALLET, 'shared_secret': 'one-time-test-secret'}}
                transport.side_effect = respond
                console = io.StringIO()
                with contextlib.redirect_stdout(console): self.assertEqual(request.execute(args), 0)
                self.assertNotIn('one-time-test-secret', console.getvalue())
                self.assertEqual(json.loads(output.read_text())['body']['shared_secret'], 'one-time-test-secret')
                with self.assertRaises(FileExistsError): request.execute(args)
                self.assertEqual(transport.call_count, 1)

    def test_http_failure_exit_is_not_success(self):
        args = argparse.Namespace(config=None, operation='get_wallet', body=None, param=[], query=[], timeout=30, output=None)
        with patch.object(request, 'configuration', return_value=CONFIG), patch.object(request, 'curl_request', return_value={'http_status': 403, 'body': {'error': {'type': 'forbidden'}}}):
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(request.execute(args), 1)


class CurlTransportTests(unittest.TestCase):
    def test_real_curl_against_loopback_without_production_auth(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                captured.append((self.path, self.headers.get('x-api-key'), json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(202)
                self.end_headers()
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        real_run = subprocess.run
        def local_run(command, **kwargs):
            # Test-only interception: production code cannot choose an arbitrary origin
            # or allow HTTP. Exercise actual curl/config/body handling on loopback.
            self.assertEqual(command[:2], ['curl', '--disable'])
            self.assertNotIn(KEY, ' '.join(command))
            self.assertNotIn('--retry', command)
            self.assertNotIn('--location', command)
            self.assertEqual(kwargs['input'], f'header = "x-api-key: {KEY}"\n')
            self.assertEqual(command[command.index('--proto') + 1], '=https')
            command = list(command)
            command[command.index('--proto') + 1] = '=http'
            command[command.index('--url') + 1] = f'http://127.0.0.1:{server.server_port}/payments'
            return real_run(command, **kwargs)
        try:
            with patch.object(request.subprocess, 'run', side_effect=local_run):
                result = request.curl_request('POST', 'https://voltageapi.com/v1/test', KEY, {'memo': 'quote " and newline\n'}, 2)
            self.assertEqual(result, {'http_status': 202, 'body': None, 'non_json_body': False})
            self.assertEqual(captured, [('/payments', KEY, {'memo': 'quote " and newline\n'})])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_transport_failure_is_not_retried(self):
        with patch.object(request.subprocess, 'run', return_value=subprocess.CompletedProcess([], 28, '', 'timeout')) as run:
            with self.assertRaisesRegex(ValueError, 'outcome may be unknown'):
                request.curl_request('POST', 'https://voltageapi.com/v1/test', KEY, {'id': WALLET}, 1)
            self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
