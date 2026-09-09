# Maintaining the Voltage API skill

## Update the contract

Only use the Voltage API contract and docs as product sources. Preserve source
bytes in `references/openapi.json`; `sources.json` records its SHA-256 and retrieval
time. Handwritten references cite operations, schema names, or guide sections.
Source titles can retain older branding. Do not rename paths, operation IDs, or
wire values to match marketing language.

Fetch a candidate, inspect it, and adopt it explicitly:

```sh
python3 tools/refresh-reference.py --fetch /tmp/voltage-candidate.json
git diff --no-index skills/voltage-api/references/openapi.json /tmp/voltage-candidate.json
python3 tools/refresh-reference.py --adopt /tmp/voltage-candidate.json
```

`--adopt` updates the snapshot, manifest, and generated operation index. It does
not update handwritten workflow guidance. Review changed operations, schemas,
embedded guides, and human docs; update affected references, examples, and
discrepancies together. Do not infer freshness from `info.version` alone.

## Validate

Python helpers use only the standard library. Schema tests use a development
dependency; create a virtual environment rather than changing system Python:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tests/requirements.txt
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/client.test.mjs
python3 tools/refresh-reference.py --check
npx skills add . --list
```

The Node tests import the TypeScript example using built-in type stripping;
use Node.js 24+ for these tests. The example can also be compiled by an application's
TypeScript toolchain. CI also runs strict type checking with TypeScript 5.9.3 and
the Node.js 24 types, installed into the runner's temporary directory.
The tests check workflows and signature handling, not just
the text of instructions. Curl transport is tested against a local mock server
without production credentials. Never use live credentials in CI.

## Behavioral evaluation

Use the prompts and grading criteria in `tests/scenarios.md` to evaluate the
installed skill in an agent. Keep evaluation code in a temporary project and
use mock transport. Test a copied installation as well as source-tree discovery,
so missing references or repository-relative dependencies are caught.

Live integration testing is separate: obtain an explicitly authorized test
wallet, confirm its network and environment, and agree on any payment amount and
fee constraints. Record what actually ran. An offline pass does not establish
live service acceptance, current provisioning, or compatibility with every agent.
