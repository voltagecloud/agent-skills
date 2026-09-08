import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'voltage-api'
sys.path.insert(0, str(SKILL / 'scripts'))
import contract


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


inspector = module('inspector', SKILL / 'scripts' / 'inspect-operation.py')
refresh = module('refresh', ROOT / 'tools' / 'refresh-reference.py')


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = contract.load()
        resource = Resource.from_contents({'$schema': 'https://json-schema.org/draft/2020-12/schema', **cls.spec})
        cls.registry = Registry().with_resource('urn:voltage:contract', resource)

    def validator(self, schema):
        # Use a base URI for local #/components/... references in the OpenAPI document.
        ref = {'$ref': 'urn:voltage:contract#/components/schemas/' + schema}
        return Draft202012Validator(ref, registry=self.registry, format_checker=FormatChecker())

    def test_snapshot_and_index_integrity(self):
        data = (SKILL / 'references' / 'openapi.json').read_bytes()
        manifest = json.loads((SKILL / 'references' / 'sources.json').read_text())
        self.assertEqual(hashlib.sha256(data).hexdigest(), manifest['contract']['sha256'])
        self.assertEqual(refresh.index(self.spec), (SKILL / 'references' / 'api-index.md').read_text())
        refresh.validate(data)

    def test_portable_skill_frontmatter(self):
        text = (SKILL / 'SKILL.md').read_text()
        frontmatter = yaml.safe_load(text.split('---', 2)[1])
        self.assertEqual(frontmatter['name'], 'voltage-api')
        self.assertTrue(0 < len(frontmatter['description']) <= 1024)
        self.assertNotIn('allowed-tools', frontmatter)

    def test_every_operation_can_be_inspected_with_resolvable_references(self):
        for path, method, operation in contract.operations(self.spec):
            with self.subTest(operation=operation['operationId']):
                result = inspector.inspect(self.spec, operation['operationId'], 'all')
                self.assertEqual(result['path'], path)
                self.assertEqual(result['method'], method)
                self.assertEqual(result['operation']['responses'], operation['responses'])
                for ref, definition in result['referenced_definitions'].items():
                    self.assertEqual(contract.pointer(self.spec, ref), definition)
                self.assertIn('`' + operation['operationId'] + '`', refresh.index(self.spec))

    def test_auth_is_operation_specific(self):
        self.assertEqual(inspector.inspect(self.spec, 'get_events', 'request')['operation']['security'], [{'checkout_stream_token': []}])
        stream = inspector.inspect(self.spec, 'create_event_stream_token', 'request')
        self.assertEqual(stream['operation']['security'], [])
        self.assertIn('requestBody', stream['operation'])
        self.assertIn('api_key', inspector.inspect(self.spec, 'create_payment', 'request')['security_schemes'])

    def test_focused_guide_extraction(self):
        guide = inspector.guide_section(self.spec, 'Payments', 'Workflow: pay a known BTC invoice from a USD wallet')
        self.assertIn('### 4. Poll the payment', guide)
        self.assertNotIn('## Workflow: create a USD-denominated receive', guide)
        with self.assertRaises(ValueError):
            inspector.guide_section(self.spec, 'Payments', 'nonexistent')

    def test_authored_json_examples_match_contract(self):
        mappings = {'payment-lifecycle.md': 'PaymentRequest', 'webhooks.md': 'NewWebhookRequest', 'checkout.md': 'CreateCheckoutSessionRequest'}
        for filename, schema in mappings.items():
            examples = re.findall(r'```json\n(.*?)\n```', (SKILL / 'references' / filename).read_text(), re.S)
            self.assertTrue(examples)
            for example in examples:
                with self.subTest(file=filename, example=example[:60]):
                    self.validator(schema).validate(json.loads(example))

    def test_units_and_request_variants_reject_invalid_shapes(self):
        for value in [{'currency': 'btc', 'amount': 1.5}, {'currency': 'usd', 'amount': 100, 'unit': 'msats'}, {'currency': 'asset:123', 'amount': 1}]:
            self.assertFalse(self.validator('Amount').is_valid(value))
        self.validator('Amount').validate({'currency': 'asset:' + 'a' * 66, 'amount': 25})
        self.assertFalse(self.validator('PaymentRequest').is_valid({'id': 'not-a-uuid', 'wallet_id': 'not-a-uuid', 'payment_kind': 'bolt11', 'amount': {'currency': 'btc', 'amount': 1000}}))

    def test_all_local_markdown_links_exist(self):
        for path in [ROOT / 'README.md', ROOT / 'CONTRIBUTING.md', *SKILL.rglob('*.md')]:
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                target = target.split('#', 1)[0]
                with self.subTest(file=str(path), target=target):
                    self.assertTrue((path.parent / target).exists())


if __name__ == '__main__':
    unittest.main()
