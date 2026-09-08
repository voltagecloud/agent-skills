# Payment lifecycle and reads

Authority: OpenAPI tag `Payments`, operations `create_payment`, `get_payment`,
`get_payments`, `check_payment`, `get_wallet`, and their referenced schemas.
Use the inspector for exact payloads and complete response/error definitions.

## Receive a Lightning invoice

1. Resolve the intended wallet and verify its scope, network, active state, and
   currency. Read [specialized flows](specialized-flows.md) for USD or feature-gated rails.
2. Generate a UUIDv4 and store it with the application's order/reference before any
   write. Generate a new ID for a new logical payment, not for a transport retry.
3. Submit a fixed BTC receive using this shape (IDs are examples; replace them):

```json
{
  "id": "11ca843c-bdaa-44b6-965a-39ac550fcef7",
  "wallet_id": "7a68a525-9d11-4c1e-a3dd-1c2bf1378ba2",
  "payment_kind": "bolt11",
  "amount": {"currency": "btc", "amount": 150000},
  "description": "Order 123",
  "expiration": 3600,
  "metadata": {"external_id": "order-123"}
}
```

This requests 150 sats of principal. Any applicable receive processing fee is
added by the server to the payer-facing request; do not compute and add it again.

```sh
python3 <skill-dir>/scripts/request.py create_payment --body /path/receive.json
python3 <skill-dir>/scripts/request.py get_payment --param "payment_id=$PAYMENT_ID"
```

4. `POST` returns an empty `202`. Poll by the submitted UUID. A brief read `404`
   after acceptance is eventual consistency, not grounds for a new payment.
5. Wait for `receiving` and the generated `data.payment_request` before sharing a
   Lightning invoice. For other rails inspect `data` and the top-level `bip21_uri`
   according to the response schema. A fast completion can precede your first read.
6. Continue tracking until `completed`, `failed`, or `expired`. Creating or sharing
   an invoice is not evidence of payment. Use verified webhooks plus reconciliation
   for a deployed integration.

For any-amount BTC Bolt11/BIP21 receives, omit every amount field and provide
top-level `currency: btc`. They require zero/no effective receive processing fee.
Nonzero fees cause asynchronous failure before invoice/URI generation. USD,
on-chain, and Taproot Asset receives require fixed amounts.

## Send a Lightning payment

Resolve the user's destination invoice, source wallet, amount, and fee allowance.
A fixed invoice can supply the BTC amount; an amountless invoice requires an
explicit positive amount. For a BTC wallet, the send shape is:

```json
{
  "id": "68d00852-8dd8-4c71-94d2-91c84695da78",
  "wallet_id": "7a68a525-9d11-4c1e-a3dd-1c2bf1378ba2",
  "currency": "btc",
  "type": "bolt11",
  "data": {
    "payment_request": "REPLACE_WITH_RECIPIENT_INVOICE",
    "amount": {"currency": "btc", "amount": 150000},
    "max_fee": {"currency": "btc", "amount": 1000}
  },
  "metadata": {"external_id": "order-123"}
}
```

The illustrative invoice is not executable. Do not send until a real intended
recipient invoice is supplied and its network/amount fit the chosen wallet and
authorization. This example allows 1 sat in network/provider fees; processing fees
are additional. For USD wallets, top-level `currency` is `usd` while the rail amount
remains BTC, with the appropriate quote. See [specialized flows](specialized-flows.md).

Submit once through `create_payment`, then poll `get_payment`. For normal sends,
`sending` and `approved` are intermediate; `completed` and `failed` are terminal.

## Policy check is a different workflow

`check_payment` is an asynchronous, policy-check-only send using the send request
schema. It is not a synchronous fee quote. Poll to `approved` or `failed`, both
terminal **for a check**. Do not attach a quote: the check consumes it. Do not use
this as a quote-to-payment step or as a preview for explicit swap routing. A check
being approved is not proof that funds were sent. Do not assume the treasury
endpoint can promote a checked payment; it returns conflict for an already-visible ID.

## Amounts and response interpretation

| Value | Convention |
|---|---|
| BTC | Integer millisatoshis; 1 sat = 1,000 msats |
| USD | Integer cents; $1 = 100 |
| Asset currency | `asset:<66-character-hex-group-key>`, integer asset base units |
| On-chain BTC amount object | Still msats; use multiples of 1,000 for exact satoshis |
| Request `unit` | Optional and ignored; omit and let `currency` determine units |
| Legacy numeric amount/fee aliases | Compatibility only; use modern amount objects in new code |

Branch on `direction`, then `type`. Sends expose `data.outflows`; receives expose
`data.receipts`. Arrays may be empty during processing or contain several entries.
Read actual currency/unit fields instead of assuming every BTC-rail response is
expressed in BTC, especially for cross-currency display amounts.

The `get_wallet` response contains `balances`, `holds`, and `pending_settlements`.
Report each relevant balance's `available` and `total` in its actual currency and
unit, respecting the signed-amount representation. Do not describe a credit limit
as cash on hand, aggregate unlike currencies, or invent a `/balance` endpoint.
Use `get_wallet_ledger_as_user` for ledger history and the published payment/credit
summary operations when those answer the user's question more directly.

## Bounded polling and recovery

Choose an application deadline and bounded backoff (for example, 0.5 seconds
growing to 5 seconds with jitter); these timings are local client policy, not a
Voltage SLA. Bound each network request too. Stop polling on the desired state,
an explicit terminal failure/expiry, a non-retryable HTTP error, or the deadline.
On deadline, report pending/unknown with the existing payment ID; do not submit again.

Read retries after transient transport/5xx errors are distinct from write retries.
Respect a server retry hint if present within the deadline. A persistent `404`
requires scope/ID investigation; never retry indefinitely. For `401`/`403`, inspect
credentials/scope/permissions rather than rotating secrets or trying alternate
production environments without direction.

For non-2xx HTTP results inspect the endpoint's `error.type`, `error.code` when
present, and structured context. Do not parse `detail` text for branching. Accepted
payments can subsequently fail with a resource-level `error`. For a timeout or
uncertain POST result, query the persisted ID before deciding what to do next.
Do not assume a client-supplied UUID provides general POST replay guarantees.

The [TypeScript client example](../assets/voltage-client.ts) implements single
submission and bounded polling. Persist IDs in the application's own durable store;
the example deliberately does not create a database or retry a write.

## Listing and reconciliation

For normal browsing, use documented filters and pagination. Cursor results have
`has_more`/`next_cursor` and omit `total`. Preserve filters and ordering between
pages. Payment array filters use `statuses[]=completed`; metadata uses
`metadata[external_id]=order-123`. Inspect other operations rather than assuming
every list has the same encoding or envelope.

For complete reconciliation, follow the unfiltered, repeated cursor sweeps in
[webhooks.md](webhooks.md). `start_date` and `end_date` filter creation time;
sorting by `updated_at` does not create an “updated since” query.
