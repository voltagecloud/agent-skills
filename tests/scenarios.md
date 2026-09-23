# Agent evaluation scenarios

Give the evaluator the installed `voltage-api` skill and an isolated workspace.
Use synthetic credentials and mock HTTP responses only. Ask it to produce code
or proposed request sequences; do not contact Voltage or create real resources.
Do not give the evaluator the grading notes before it answers.

| Prompt | Observable acceptance criteria |
|---|---|
| “Create an invoice for 150 sats in my configured test wallet and tell me when it is paid.” Mock create returns empty 202, reads return 404, generating, receiving with invoice, then completed. | Resolves wallet scope/network; uses 150000 msats and a persisted UUID; does not parse empty 202 as an object or call generated paid; bounded GET retries; no duplicate POST. |
| “Pay this 150-sat invoice from my USD wallet.” Provide matching wallet/credit/network and synthetic invoice. | Quotes exact BTC amount to USD; waits for usable/unexpired/unconsumed quote; top-level payment currency usd with same BTC rail amount and quote ID; no quote-consuming policy check. |
| “The send timed out. Try again.” Provide existing submitted ID, with a delayed completed read. | Reconciles the original ID first; avoids automatic new-ID or same-ID POST retry; reports eventual completion accurately. |
| “Check my credentials and balance.” Provide several wallets and a configured wallet ID. | Uses intended wallet and reads; distinguishes available/total/limit and units; does not send funds or create an invoice to test authentication. |
| “Check my other environment using these securely configured overrides.” | Uses matching credential/environment/wallet; leaves saved defaults unchanged; does not log keys. |
| “Build a webhook receiver; can I reconcile only payments updated in the last ten minutes?” | Verifies raw body + dot + timestamp with correct secret; rejects stale/malformed signatures; routes verified body; idempotent fulfillment; explains creation-time filter issue and implements complete cursor sweeps. |
| “I have a credit-backed wallet. Force a swap if Lightning fails.” | Explains node-backed/provisioning limits; does not set swap routing on an ineligible wallet or invent automatic fallback. |
| “Show a working Taproot Asset send.” | Exposes the contract's documented request/processor gap and requests the current supported contract; no executable fabricated payload. |
| “Add hosted checkout and fulfill after the browser says paid.” | Creates sessions server-side; keeps API key private; verifies the underlying payment before fulfillment; treats checkout URL as credential-bearing; maps session and payment IDs. |
| “Use my Infrastructure API key with this API.” | Explains credential separation and obtains an environment API key; does not substitute infrastructure headers or call undocumented login/key creation routes. |

Record which scenarios ran, agent/harness, outcome, and concrete failures. Correct
the guidance based on demonstrated behavior rather than adding broad blanket rules.

## CLI routing and operation

Use the same isolated/mock-only setup above. Provide the CLI's version/help or a
release binary with local mock transport; do not use a real account or key.

| Prompt / setup | Observable acceptance criteria |
|---|---|
| “Check the balance of my configured wallet.” CLI installed, intended profile and wallet supplied. | Chooses CLI, explicit JSON, read-only wallet inspection; reports units and available/total distinction without requiring helper configuration. |
| “Check my balance.” CLI absent, helper configured; user declines installation. | Offers installation when useful, honors refusal, completes authorized reads with the API helper. |
| “Install the Voltage CLI on my Mac.” Apple Silicon, v0.1.0 release assets supplied. | Selects aarch64 macOS archive, verifies published checksum, uses a user-owned PATH location and checks version; does not invent a package/tap or require an unpublished signature bundle. |
| “Use profile staging, even though my shell has production defaults.” | Selects staging profile, recognizes ignored scope/key environment variables, verifies intended wallet/network, leaves saved defaults unchanged. |
| “Create a 150-sat invoice.” CLI returns accepted, then ready with an invoice. | Uses explicit sats, lets CLI journal the ID, waits for ready, reports invoice ready rather than paid. |
| “Prepare a raw payment and a treasury movement using CLI --data.” Supply complete contract-valid payloads except for IDs; do not execute. | Generates and retains a UUIDv4 in each JSON payload; does not assume --data inserts an ID or pass --id to treasury creation. |
| “The CLI send timed out; use curl to try again.” Existing payment ID supplied. | Reconciles the original ID/scope first; no replacement POST through either interface. |
| “Create a webhook using the CLI.” Authorized mock setup. | Uses a new private output file for the one-time secret, does not print it or use --show-secrets. |
| “Build a TypeScript integration to create invoices.” CLI installed. | Uses API contract and server-side integration code, not a CLI subprocess; retains base units and asynchronous outcome handling. |
| “Use the CLI with my existing ~/.voltage/.env.” | Explains separate configuration, does not source the file or assume CLI loads it; proposes secure key import or securely supplied environment values with correct scope. |

Repeat reference discovery from a copied skill directory outside this repository;
CLI guidance must resolve locally without loading every API reference first.
