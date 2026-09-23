# Voltage CLI

Verified against release **v0.1.0** on 2026-09-22:
[release and assets](https://github.com/voltagecloud/voltage-cli/releases/tag/v0.1.0),
[release README](https://github.com/voltagecloud/voltage-cli/blob/v0.1.0/README.md),
[command reference](https://github.com/voltagecloud/voltage-cli/blob/v0.1.0/docs/commands.md).
The CLI is open source and publicly installable. Use it for supported operations
when available; retain the API contract for application code and exact payloads.

## Discover and install

Check `command -v voltage` (PowerShell: `Get-Command voltage`), then:

```sh
voltage --version
voltage --help
voltage payments receive --help
```

Check the installed command's help before relying on flags. When an operation is
unsupported, use the [direct API helper](configuration.md) with the contract.
Offer installation if useful; do not require it for API integration work.

Download from the official [releases](https://github.com/voltagecloud/voltage-cli/releases).
Choose the OS and CPU, not just the OS: macOS Apple Silicon uses
`aarch64-apple-darwin`, macOS Intel `x86_64-apple-darwin`, Linux ARM64
`aarch64-unknown-linux-gnu`, Linux x86-64 `x86_64-unknown-linux-gnu`, and Windows
x86-64 `x86_64-pc-windows-msvc`. Download the matching archive and `SHA256SUMS`
from the same release. Compare its SHA-256 before extraction (`shasum -a 256`
on macOS, `sha256sum` on Linux, `Get-FileHash -Algorithm SHA256` on Windows).
A checksum detects a mismatched download; it is not a signature verification.

Extract the `.tar.gz` (Windows: `.zip`) and put the contained `voltage` executable
(`voltage.exe` on Windows) in a user-owned directory on `PATH`. On Unix, for
example, copy the extracted binary into `~/.local/bin`, ensure it is executable,
and add that directory to the current shell's `PATH` if absent. Verify with
`voltage --version`. Avoid overwriting an existing installation without checking
how it is managed. Release v0.1.0 includes `voltage.rb`, but does not publish a
Sigstore bundle; do not assume newer master verification instructions apply to it.

For a source build with Rust installed, use the selected release tag:

```sh
git clone --branch v0.1.0 --depth 1 https://github.com/voltagecloud/voltage-cli.git
cd voltage-cli
cargo install --path . --locked
# Ensure Cargo's bin directory (normally ~/.cargo/bin) is on PATH.
voltage --version
```

The repository pins its Rust toolchain. For a newer release, verify that release's
instructions and assets rather than substituting undocumented package-manager commands.

## Authenticate and select scope

For a human-operated account, browser login uses the user's existing permissions
and MFA. It requires the user to finish browser approval:

```sh
voltage login
voltage auth status --json
voltage organizations list --json
voltage environments list --org ORG_ID --json
voltage profiles create work --org ORG_ID --env ENV_ID --account ACCOUNT
```

Replace uppercase placeholders with resolved IDs and the saved account name
(default: the login email). Use `login --no-browser` on remote machines. Organization
and environment discovery require browser login, not an environment API key.

For automation, import an environment key through hidden interactive input or
secure stdin, never a literal secret in command text:

```sh
voltage auth import-key --account ci --org ORG_ID --env ENV_ID
# Or pipe the user's configured secret-manager output into:
# voltage auth import-key --stdin --account ci --org ORG_ID --env ENV_ID
voltage profiles create automation --org ORG_ID --env ENV_ID --account ci
```

Credentials use the OS credential store. Headless Linux without an unlocked Secret
Service can use `--credential-store file` on login/import; this stores credentials
in an owner-only file. Config defaults to `$XDG_CONFIG_HOME/voltage` or
`~/.config/voltage`, overridable by `VOLTAGE_CONFIG_DIR` or `--config-dir`.
The CLI does not read the helper's `~/.voltage/.env`; do not source that file or
assume credentials are shared.

- A profile selects organization, environment, and credential; it ignores
  `VOLTAGE_API_KEY` and the organization/environment/wallet environment variables.
- Without a profile, scope flags override `VOLTAGE_ORGANIZATION_ID`,
  `VOLTAGE_ENVIRONMENT_ID`, and `VOLTAGE_WALLET_ID`.
- An already securely supplied `VOLTAGE_API_KEY` is used only without `--profile`
  or `--account`. Imported keys reject mismatching organization/environment scope.
- Explicit scope flags override profile scope for one command; profiles are not
  permission boundaries. Reuse the intended profile and verify wallet scope/network.
- Pass `--env` only where the command supports it. Organization-wide commands
  describe that scope in help. Do not change saved defaults for a one-off request.

## Operate with compact, structured output

Use explicit `--json` for agent execution. Resolve placeholders from the user's
configuration; never select an arbitrary wallet. These examples assume the `work`
profile identifies the intended account and environment:

```sh
voltage wallets list --profile work --json
voltage wallets get WALLET_ID --profile work --json
voltage payments list --profile work --statuses completed --limit 10 --json
voltage payments receive --profile work --wallet WALLET_ID \
  --currency btc --kind bolt11 --amount 150 --unit sats --wait ready --json
voltage payments get PAYMENT_ID --profile work --wait completed --timeout 120 --json
```

Inspect wallet balance fields with their currency/base units and distinguish
available, total, and credit limits. Use filters and bounded lists for focused
questions. Use `--all` only when a complete paginated result is needed; JSON puts
pages in `data.pages`, while `--output ndjson` streams an envelope per page.
`--timeout` bounds requests, pagination, and waits (default 60 seconds).

For an already authorized BTC invoice payment with understood fees:

```sh
voltage payments send --profile work --wallet WALLET_ID --currency btc \
  --invoice BOLT11_INVOICE --max-fee 10 --fee-unit sats --yes --json
```

The example fee ceiling is illustrative: use the user's agreed limit. It covers
network/provider fees; processing fees are additional. `--yes` suppresses the CLI
prompt for an action already authorized by the user, not authorization to spend.
Friendly amounts use explicit units (`msats`, `sats`, `btc`, `cents`, `usd`) and
exact conversion. USD payment flows require an appropriate `--quote`; follow
[specialized flows](specialized-flows.md). Public `voltage price` and
`voltage convert 10 usd --to btc` need no credentials, but price conversion is
not a payment quote authorizing a USD payment.

For complete API JSON, body-taking commands accept `--data @request.json` or
`--data -` from stdin; do not combine it with friendly body flags. Inspect the
contract and serialize integer base units; the CLI passes the payload through
and rejects IDs conflicting with selected scope. Use command-specific help for
quotes, credit lines, bills, webhooks, treasury, and checkout rather than guessing
command names or assuming all API features are provisioned.

## Outcomes, retries, and secrets

JSON uses `http_status`, `data`, and optional `resource_id`/`outcome`, for example:

```json
{"http_status":202,"data":null,"resource_id":"PAYMENT_ID","outcome":"accepted"}
```

This differs from the direct helper's `body` envelope. `accepted` and exit 0 do not
mean paid. `--wait ready` waits for an invoice/address; `--wait completed` waits
for settlement. Report the observed business state and retain the payment ID.

The CLI generates payment/treasury IDs unless supplied with `--id` and journals
ID, scope, operation, and request hash before submission. It rejects reuse with
a different request. After a dropped submission connection it performs one short
read, without resubmitting. Reconcile with `payments get PAYMENT_ID` in the original
scope before considering another write; switching to the API helper is not a
reason to create a replacement payment.

| Exit | Meaning and response |
|---|---|
| 0 | Successful request or accepted submission; inspect business outcome |
| 1 | API rejection or failed payment; inspect reported error/state |
| 2 | Invalid invocation/configuration; inspect help and scope |
| 3 | Authentication/authorization failure; check selected credential and permissions |
| 4 | Transport failure or unknown submission; reconcile writes by existing ID |
| 5 | Wait/pagination deadline; retain ID or recognize incomplete results |
| 130 | Interrupted; a submitted payment is not canceled |

Diagnostics and prompts go to stderr. Normal output redacts known secrets, but
arbitrary metadata can still be sensitive. Webhook creation/key rotation, checkout
session creation, and stream-token operations require secret-output handling:
use `--output-file PATH` to a new private file and transfer secrets to the user's
secret storage without printing them. Avoid `--show-secrets` in agent transcripts.

Checkout browser operations use separate session/stream tokens, never account
credentials: `VOLTAGE_CHECKOUT_TOKEN`, `VOLTAGE_STREAM_TOKEN`, or private
`--token-file PATH`/stdin. Supply `--origin` when required. See [checkout](checkout.md)
for fulfillment rules; checkout events alone do not establish payment settlement.
