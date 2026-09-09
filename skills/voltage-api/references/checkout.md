# Hosted checkout and browser APIs

Sources: [Checkout docs](https://docs.voltageapi.com/checkout-beta), OpenAPI
operations `create_session`, `get_settings`, `update_settings`, `get_session`,
`get_session_allowed_origins`, `create_event_stream_token`, `get_events`, and
their schemas. The human docs describe checkout as beta; verify availability and
current interfaces before production rollout.

## Hosted integration

1. Resolve the receiving wallet/environment and the intended order amount/currency.
2. Configure the environment's origin policy through `get_settings` /
   `update_settings` or the documented dashboard. Prefer the required exact origins
   in an allowlist. An origin includes scheme, host, and optional port, not a path.
3. Your server creates a checkout session using the environment key. Generate and
   persist a session UUID and your order association. Optionally supply a distinct
   `payment_id`; otherwise Voltage generates one. Keep both returned IDs.
4. `create_session` returns `201` with `checkout_url`, `checkout_token`, session ID,
   and payment ID. Open the returned URL unchanged. The hosted checkout can supply
   the browser experience; do not invent an SDK package or initialization signature
   from memory. Read the current human docs if using its JavaScript SDK.
5. Verify payment on your server using the underlying payment ID before fulfilling
   the order. Browser events, redirects, and overlay messages are not authoritative
   evidence of payment. Reconcile as for other payments.

Use this fixed-amount session shape after replacing the IDs and expiry:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "wallet_id": "7a68a525-9d11-4c1e-a3dd-1c2bf1378ba2",
  "payment_id": "22222222-2222-4222-8222-222222222222",
  "payment_kind": "bolt11",
  "amount": {"currency": "btc", "amount": 150000},
  "expires_at": "2030-01-01T00:00:00Z",
  "description": "Order 123",
  "payment_metadata": {"external_id": "order-123"},
  "metadata": {"order_id": "order-123"}
}
```

The expiry above is only a schema fixture. For a real session choose an appropriate
future timestamp (for example now plus 15 minutes, an application choice).
`metadata` is session metadata; use `payment_metadata` for metadata on the underlying
payment/webhooks. Both the server-side environment API key and the returned checkout
token need careful handling, but they have different scopes.

The session ID is an idempotency key: the documented contract allows replay of
the same immutable inputs and returns `409` for conflicting inputs. This endpoint's
replay contract must not be generalized to normal payment POSTs.

## Amounts and methods

Follow `CreateCheckoutSessionRequest`, not a narrower demo's method list. BTC
uses msats, USD uses cents. Fixed Bitcoin receives accept BTC or USD; USD requires
a USD-backed line of credit. Taproot Asset receives require a matching fixed asset
amount. On-chain/BIP21 require their organization feature flags. Only Bolt11/BIP21
support any-amount sessions. An omitted amount defaults currency to BTC unless
explicitly supplied; explicit currency must match a fixed amount. Apply any underlying
payment prerequisites, including effective receive processing fees, and actual enablement.

Do not add a payment `quote_id` to a checkout session: it is not a field of the
current checkout creation schema. Inspect the checkout contract independently from
the direct USD payment workflow.

## Token and origin boundaries

The `checkout_url` fragment contains a bearer credential. Do not strip the fragment,
move it to a query string, log it, send it to analytics, or include it in screenshots.
Return the URL to the intended payer flow without exposing the environment API key.
Do not treat a normal `x-api-key` header as checkout browser authentication.

| Operation | Authentication/behavior |
|---|---|
| `create_session`, settings read/write | Environment API key or user JWT as declared |
| `get_session` | Bearer checkout session token; may return `202` while payment projection is not ready; honor `x-retry-after-ms` or `Retry-After` within a deadline |
| `get_session_allowed_origins` | No security scheme declared; returns browser origin policy for the session |
| `create_event_stream_token` | No header security scheme declared; `CreateEventStreamRequest` carries checkout tokens in its body; not unrestricted anonymous access |
| `get_events` | `stream_token` query credential; returns named server-sent events |

The curl helper intentionally covers API-key operations only. Use exact inspected
browser schemas for session reads and SSE. Preserve the contract's Origin checks,
token expiry, retry hints, and event names in a custom client. Browser tokens must
never be used as environment API keys or vice versa.
