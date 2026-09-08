# Quotes, other rails, fees, treasury, and swaps

Authority: OpenAPI tag `Payments`, `PaymentRequest`, `NewQuoteRequest`, `Quote`,
and the corresponding operations. These rules supplement, not replace, inspecting
the exact request variant. Retrieve full workflows offline as needed:

```sh
python3 <skill-dir>/scripts/inspect-operation.py --guide Payments --section 'Workflow: pay a known BTC invoice from a USD wallet'
python3 <skill-dir>/scripts/inspect-operation.py --guide Payments --section 'Workflow: create a USD-denominated receive'
python3 <skill-dir>/scripts/inspect-operation.py --guide Payments --section 'Swap-backed sends'
```

## USD managed lines of credit: quote before a standard payment

For a USD wallet paying a known BTC invoice:

1. Resolve the wallet's `line_of_credit_id` and network. Persist separate quote and
   payment UUIDs.
2. `request_a_quote`: submit `id`, `line_of_credit_id`, `network`, the exact BTC
   `amount` object, and `to: usd`. This returns empty `202`.
3. Poll `get_a_quote_as_user` until `created_at` and `quote` are non-null,
   `consumed_at`, `failed_at`, and `error` are null, and `expires_at` is future.
   Stop on failure/expiry or your deadline. A quote is single-use.
4. `create_payment`: top-level `currency: usd`, `quote_id`, and exactly the same
   BTC amount in `data.amount`; use the target rail's normal send fields.
5. Poll the payment to completion/failure. Do not run `/payments/check` with the quote.

For a fixed USD-denominated receive, quote the known USD amount to `btc`, wait
for a usable quote, then create the receive with that same top-level USD `amount`
and `quote_id`. Quoted receive expiration is capped by the quote's remaining life.
Poll for the generated request, then payment completion. Never invent an any-amount
USD receive flow.

Read cross-currency results carefully: `data.market_quote` records the market
rate, `exchanges` records actual exchanged amounts, and modern amount/fee fields
can use the market-quote display currency. A quoted receive's `requested_amount`
is the converted BTC rail amount. Rates use `<coefficient>e<scale>` meaning
`coefficient / 10^scale`, **not scientific notation**. Use the currencies and
`exchanges` when reconciling rather than treating legacy numeric rail values as
display-currency values.

## Other rails

| Intent | Required shape and caveat |
|---|---|
| On-chain send | `type: onchain`, `data.address`, BTC `data.amount`; exact satoshis encoded in msats |
| BIP21 send | `type: bip21`, full URI/Bitcoin address in `data.address`; must resolve to a fixed amount |
| On-chain receive | `payment_kind: onchain`, fixed `amount` |
| BIP21 receive | `payment_kind: bip21`, fixed amount, or supported BTC any-amount flow |
| Taproot Asset receive | `payment_kind: taprootasset`, fixed matching asset-currency amount, and actual enablement |
| Taproot Asset send | Published schema exists, but the embedded guide states schema and processor do not agree on a canonical amount shape. Confirm with Voltage before generating executable integration code. |

On-chain and BIP21 operations can require organization feature flags. BIP21 URI
parameters take precedence over duplicate explicit fields: `amount`, `lightning`,
and `label`/`message` supply amount, invoice, and description. Do not validate only
the duplicated JSON while ignoring what the URI requests.

## Fees

Submitted amounts are principal. For sends the wallet pays principal plus network
and processing fees. For fee-bearing fixed receives the server adds the processing
fee to the payer-facing request while the wallet receives principal.

`data.max_fee` limits network/provider fees; processing fees are additional.
The documented defaults are the greater of 1% or 1 sat for Lightning, 1% or
263 sats for on-chain, and the Lightning-style default for BIP21. Set a deliberate
ceiling where the intended BIP21 on-chain path requires more. Do not represent
`max_fee` as a cap on the total debit. Check current contract terms before executing.

Top-level `processing_fee` records immutable approved/generated terms. The
`payment_breakdown` fields provide aggregate settled principal, network fee, and
processing fee when present; final processing fees can differ from the original
terms if the settled principal changes. Use server-calculated fees and the actual
breakdown, not local floating-point approximations. `data.fees` can include both
network and processing fees. Fee-free and historical responses can omit fields.

## Treasury movements: explicitly enabled, own funds only

`create_treasury_movement` accepts the same send/receive shapes but requires
Voltage to approve and enable the feature. It is for the wallet owner's own funds.
Ordinary payments use `create_payment`.

The selected endpoint records `payment_category: treasury` and does not assess a
processing fee; network/provider fees remain. Do not set category or fee-waiver
fields in the request, use treasury to evade standard payment fees, or assume all
billing effects disappear. It affects balances, settlement, and interest. It
returns empty `202`; use the normal payment read. An already-visible ID produces
`409`; an approved check cannot be promoted here.

## Node-backed swap sends: explicit provisioning

Most integrations should omit `flow_preference`. Only use swaps for an eligible
node-backed wallet with Voltage-enabled fulfillment infrastructure. They require
a private customer/swap-node channel, appropriate liquidity/funds, available nodes
on the same network, and a Bolt11 or Bitcoin on-chain **send**. The API does not
provision that channel. Credit-backed wallets without customer node infrastructure,
BIP21, asset sends, and receives do not use this flow.

`flow_preference: swap` selects the opposite funding rail. In the object form
`{"type":"swap","rail":"lightning"}`, `rail` denotes funding, not destination.
Read the full embedded swap guide before building this flow; it explains prerequisites,
fees, outflow stages, and failure handling. A failed swap does not fall back to a
direct payment. An internal match can result in a short-circuit outflow despite
top-level `route: swap`.

Non-custodial swap contracts do not imply an automated customer refund API. The
guide says the current API does not construct/sign/broadcast refund transactions;
recovery after funds lock can require Voltage support. Do not invent recovery routes.
