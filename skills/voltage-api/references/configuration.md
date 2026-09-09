# Configuration and direct execution

Contract authority: `components.securitySchemes`, each operation's `security` and
parameters, `NewWalletRequest`, `NewWebhookRequest`. Setup context:
[wallet setup](https://docs.voltageapi.com/wallet-setup-guide) and
[access model](https://docs.voltageapi.com/access-model).

## Local convention

`~/.voltage/` is reserved here for local Voltage configuration. This is a skill-pack
convention, not an API requirement or a claim about a future CLI/MCP format.

Use a regular file `~/.voltage/.env`, owned by the current user, mode `600` (or
`400` if read-only), with a directory mode of `700`. Create it only when the user
needs local configuration; installation itself does not connect an account.
Preserve existing contents when helping edit it.

```dotenv
VOLTAGE_API_KEY=your-environment-key
VOLTAGE_ORGANIZATION_ID=your-organization-uuid
VOLTAGE_ENVIRONMENT_ID=your-environment-uuid
VOLTAGE_WALLET_ID=optional-default-wallet-uuid
```

The optional wallet line should be omitted if there is no default. Only these
four keys are currently supported by the helper. Values are literal single-line
strings, optionally surrounded by matching single/double quotes. Blank lines and
full-line comments are supported. No shell expansion, `export`, escapes, or inline
comments are interpreted. Do not `source` the file or use `eval` to load it.

Precedence: explicit `--param` resource values > process environment > configuration
file. `--config` selects a different file for that invocation; process variables
still win, including explicitly empty variables. An empty key fails rather than
silently falling back to a saved key. Config file values are never rewritten by
requests. Body fields are always explicit: the helper does not insert wallet IDs,
amounts, or generated IDs into JSON.

To switch environments, use a matching set of key/environment/wallet values. For
example, if a separate key is already securely supplied in the process environment:

```sh
VOLTAGE_API_KEY="$OTHER_VOLTAGE_API_KEY" \
  python3 <skill-dir>/scripts/request.py get_payments \
  --param environment_id="$OTHER_VOLTAGE_ENVIRONMENT_ID" \
  --query pagination=cursor --query limit=10
```

Do not paste literal keys in command text or enable shell tracing. To select an
alternate private file without inherited defaults taking precedence:

```sh
env -u VOLTAGE_API_KEY -u VOLTAGE_ORGANIZATION_ID \
  -u VOLTAGE_ENVIRONMENT_ID -u VOLTAGE_WALLET_ID \
  python3 <skill-dir>/scripts/request.py get_payments \
  --config ~/.voltage/test.env --query pagination=cursor --query limit=10
```

## IDs and authentication

| Value | How to obtain/use it |
|---|---|
| API key | Obtain from the selected environment's dashboard; `x-api-key` header; permissions must allow the action |
| Organization/environment UUIDs | Existing dashboard/application configuration; use where the operation specifies path, query, or body |
| Wallet UUID | Configured default or wallet list/read; verify scope/network before use |
| Line-of-credit UUID | Selected wallet's `line_of_credit_id` or permitted credit-summary results; needed for wallet creation and quoting |
| New payment UUID | Generate UUIDv4 and persist before submission; reuse to query an uncertain result |
| New quote/webhook/wallet/session UUID | Client-generated according to its create request; keep resource identities distinct |
| Existing bill/delivery/etc. UUID | Obtain from the corresponding list or known resource; do not generate a replacement for a read |
| Checkout tokens | Issued by checkout operations; browser session and stream credentials are not environment API keys |

An environment-scoped key cannot be made organization-wide just by changing a
path. Organization-level routes still enforce the authenticated key's scope and
permissions. API keys, user JWTs, checkout tokens, and webhook secrets are not interchangeable.

## Discover and issue a request

Find the operation in [api-index.md](api-index.md), then inspect it:

```sh
python3 <skill-dir>/scripts/inspect-operation.py get_all_organizations_wallets_as_user --part all
python3 <skill-dir>/scripts/request.py get_all_organizations_wallets_as_user \
  --query "environment_id=$VOLTAGE_ENVIRONMENT_ID"
python3 <skill-dir>/scripts/request.py get_wallet --param "wallet_id=$WALLET_ID"
```

Shell variables in examples must already exist in your shell or be set to non-secret
values you resolved. The helper's internal `.env` loader does not export shell variables.

The helper runs curl against the fixed `https://voltageapi.com/v1` origin. It
supports operations that explicitly allow `api_key`, passes that header through
stdin rather than process arguments, disables curlrc loading, does not follow
redirects, and performs no automatic retries. It does not implement checkout browser
auth, arbitrary hosts/headers, SSE, automatic pagination, or application-level polling.

Use `--body /path/request.json` or `--body -` for a JSON object on stdin. Construct
dynamic JSON with a JSON serializer, not shell string concatenation. Serialize
query pairs with repeated `--query`; curl receives the URL with safe URL encoding:

```sh
python3 <skill-dir>/scripts/request.py get_payments \
  --query pagination=cursor --query sort_key=created_at --query sort_order=DESC \
  --query 'statuses[]=completed' --query 'metadata[external_id]=order-123'
```

It checks operation identity, path UUIDs, query names, required body presence, and
credential handling. It is **not** a full schema/runtime validator. Inspect the
request schema and workflow constraints before executing.

## Responses and secrets

Normal output is a JSON envelope with `http_status`, parsed `body` (null for an
empty response), and `non_json_body`. Non-JSON server text is suppressed. Inspect
both HTTP status and business status. Exit 0 means HTTP 2xx, **not payment success**;
exit 1 means non-2xx; exit 2 means local or transport failure, which may leave a write
outcome unknown. A transport failure does not establish that the server rejected a write.

`create_webhook`, `generate_webhook_key`, and `create_session` require `--output`
before execution. This reserves a **new** file with mode `600` and stores the full
response envelope. It refuses to overwrite an existing file. Console output shows
only the HTTP status and that a response was saved. Other calls also support this
option. If execution fails, the reserved file may be empty; inspect it securely and
reconcile the operation before deciding whether to use a new filename or retry.

```sh
python3 <skill-dir>/scripts/request.py create_webhook \
  --body /private/path/webhook-request.json \
  --output ~/.voltage/webhook-created.json
```

Provision a writable private destination before a one-time-secret operation. Move
the returned `body.shared_secret` into the application's secret storage associated
with `body.id`. Do not print the file to the conversation. For rotation, preserve the
old secret during the documented overlap. Checkout URLs also contain a credential;
do not log them or move their fragments into query parameters.

Normal console responses redact known secret fields and any exact echo of the API
key, but they may still contain customer data, invoices, and arbitrary metadata.
Use private output and selective reporting for sensitive responses. File output
is intentionally unredacted, and is not a general-purpose secret manager.

## Writing curl directly

The helper is optional. Generated backend examples may use curl directly with
`x-api-key`, JSON serialization, bounded `--max-time`, and explicit HTTP status
handling. For agent-executed requests prefer the helper's private header handling;
avoid putting an expanded key in curl argv, verbose traces, or shell history.
Do not send environment keys to checkout browser endpoints or follow redirects
with credentials. Do not supply `--retry` to a payment POST.
