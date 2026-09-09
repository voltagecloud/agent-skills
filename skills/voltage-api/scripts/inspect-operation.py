#!/usr/bin/env python3
"""Inspect exact operations/schemas/guide sections without loading the full spec."""
import argparse
import json
import re
import sys
from contract import find_operation, load, reference_closure


def inspect(spec, name, part):
    path, method, operation = find_operation(spec, name)
    common = ('operationId', 'summary', 'description', 'tags', 'security')
    fields = common + ({
        'request': ('parameters', 'requestBody'),
        'response': ('responses',),
        'all': ('parameters', 'requestBody', 'responses'),
    }[part])
    selected = {key: operation[key] for key in fields if key in operation}
    selected['security'] = operation.get('security', spec.get('security', []))
    if part != 'response':
        inherited = spec['paths'][path].get('parameters', [])
        overridden = {(p.get('name'), p.get('in')) for p in operation.get('parameters', [])}
        selected['parameters'] = [p for p in inherited if (p.get('name'), p.get('in')) not in overridden] + operation.get('parameters', [])
    auth_names = {key for scheme in selected['security'] for key in scheme}
    return {
        'base_url': 'https://voltageapi.com/v1', 'path': path, 'method': method,
        'operation': selected,
        'security_schemes': {key: spec['components']['securitySchemes'][key] for key in sorted(auth_names)},
        'referenced_definitions': reference_closure(spec, selected),
    }


def guide_section(spec, name, section=None):
    matches = [t for t in spec.get('tags', []) if t['name'] == name]
    if len(matches) != 1:
        raise ValueError('Unknown guide; available names: ' + ', '.join(t['name'] for t in spec.get('tags', [])))
    guide = matches[0].get('description', '')
    if section is None:
        return guide
    headings = list(re.finditer(r'^(#{1,6}) (.+)$', guide, re.M))
    matches = [h for h in headings if h[2] == section]
    if len(matches) != 1:
        raise ValueError('Unknown or ambiguous section; available headings: ' + '; '.join(h[2] for h in headings))
    start = matches[0]
    end = next((h.start() for h in headings if h.start() > start.start() and len(h[1]) <= len(start[1])), len(guide))
    return guide[start.start():end].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', nargs='?')
    parser.add_argument('--part', choices=['request', 'response', 'all'], default='request')
    parser.add_argument('--schema')
    parser.add_argument('--guide')
    parser.add_argument('--section')
    args = parser.parse_args()
    if sum(bool(x) for x in [args.operation, args.schema, args.guide]) != 1 or (args.section and not args.guide):
        parser.error('Choose an operation, --schema, or --guide; --section requires --guide')
    spec = load()
    try:
        if args.guide:
            print(guide_section(spec, args.guide, args.section))
        else:
            if args.schema:
                value = spec['components']['schemas'][args.schema]
                result = {'schema': value, 'referenced_definitions': reference_closure(spec, value)}
            else:
                result = inspect(spec, args.operation, args.part)
            print(json.dumps(result, indent=2))
    except (KeyError, ValueError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
