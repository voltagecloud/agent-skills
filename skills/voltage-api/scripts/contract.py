"""Shared, offline access to the contract installed with this skill."""
import json
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[1] / 'references' / 'openapi.json'
METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'}


def load():
    return json.loads(REFERENCE.read_text())


def operations(spec):
    for path, item in spec['paths'].items():
        for method, operation in item.items():
            if method in METHODS:
                yield path, method.upper(), operation


def find_operation(spec, name):
    matches = [(p, m, o) for p, m, o in operations(spec) if o.get('operationId') == name]
    if len(matches) != 1:
        raise ValueError('Unknown or ambiguous operation ID; consult references/api-index.md')
    return matches[0]


def pointer(spec, ref):
    if not ref.startswith('#/'):
        raise ValueError('Only local contract references are supported')
    value = spec
    for part in ref[2:].split('/'):
        value = value[part.replace('~1', '/').replace('~0', '~')]
    return value


def reference_closure(spec, value):
    """Return definitions by original JSON pointer; keep cycles as references."""
    found = {}

    def visit(node):
        if isinstance(node, dict):
            ref = node.get('$ref')
            if ref and ref not in found:
                found[ref] = pointer(spec, ref)
                visit(found[ref])
            for item in node.values():
                visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(value)
    return found
