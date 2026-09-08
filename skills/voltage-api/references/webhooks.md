# Webhooks and reconciliation

Authority: OpenAPI tag `Webhooks`; `NewWebhookRequest`, `WebhookPlainSecret`,
`EventTypes`, `Payload`, `ReceiveEventTypes`, `SendEventTypes`, `DeliveryStatus`,
and the webhook operations. Inspect the exact contract before extending examples.

## Register and retain identity

Generate a webhook UUID and call `create_webhook` in the organization's environment:

```json
{
  "id": "b0fc9829-f139-4035-bb14-4a4b6cd58f0e",
  "url": "https://merchant.example/voltage/webhook",
  "name": "Order payment events",
  "events": [
    {"receive": "generated"},
    {"receive": "completed"},
    {"receive": "failed"},
    {"send": "succeeded"},
    {"send": "failed"}
  ]
}
```

Replace the callback with an HTTPS endpoint the user controls and intends to use.
Organization/environment IDs are in the path; they are not fields of the current
`NewWebhookRequest` schema. Events are individual tagged objects, not strings such
as `receive.completed`.

The `202` response includes `id` and `shared_secret`. Save them together, privately;
the plaintext secret is returned only on creation or key rotation. Arrange storage
before sending the request. `request.py` requires `--output` for these operations.
For secret rotation, retain old/new candidates for the same registration during
the handoff, then retire the old secret according to your operational process.

| Identity | Where and why |
|---|---|
| Webhook ID | Registration ID; management paths and `x-voltage-webhook-id` |
| Payment ID | Verified callback `detail.data.id`; normal payment reads and order association |
| Delivery ID | Delivery inspection/retry/abandon resource; do not assume an undocumented callback header carries it |
| Shared secret | Signing credential, stored by registration ID; not a payment or delivery ID |

## Verify exact bytes before applying events

The contract defines the signed message as:

```text
<raw_request_body>.<x-voltage-timestamp>
```

Use the literal UTF-8 shared secret as the HMAC-SHA256 key and Base64-encode the
digest. Read the raw body before a framework parses/re-serializes it. Verify with
a constant-time comparison, reject malformed signatures and missing/unknown webhook
IDs, and reject timestamps outside an application-defined tolerance. A five-minute
tolerance in the example is a local policy, not a promised Voltage delivery deadline.

`x-voltage-webhook-id` selects candidate secrets. `x-voltage-event` is a routing hint.
Neither header is part of the signature, so treat them as untrusted and route on
the **verified** body's `type` and `detail.event`. A valid signature authenticates
the body/timestamp, not other headers. Use separate secrets per registration.

Adapt [verify-webhook.ts](../assets/verify-webhook.ts); it verifies a `Uint8Array`
of raw bytes, checks timestamp tolerance, and only parses after verification.
Configure your framework to preserve the raw body and enforce an application body
size limit. Do not put signing secrets in frontend code.

## Apply payment events idempotently

Send/receive callbacks contain `{type, detail: {event, data}}`, with the payment in
`detail.data`. Branch on verified `type`, then `detail.event`, and inspect payment
status. For Bolt11, receive `completed` with payment `status: completed` is the
success signal. `generated` / `receiving` only means the invoice is ready. Send
event `succeeded` is different from receive event `succeeded`, which can indicate
partial on-chain receipt. Do not invent a receive status `succeeded`; it is absent
from `ReceiveStatus`.

Persist incoming work durably before acknowledging with 2xx, then process the
business effect idempotently. Use the payment ID and a durable order/fulfillment
constraint to prevent duplicate fulfillment even when deliveries repeat or more
than one webhook matches a payment. Use delivery IDs for delivery management where
available, but do not invent their location in a callback. Fetch current payment
state when an old or conflicting notification would regress stored business state.

HTTP delivery status `succeeded` means the receiver returned 2xx; it does not mean
the embedded payment is complete. `attempting`, `failed`, and `abandoned` are also
delivery states, separate from payment states.

## Manage and test

Use `get_webhooks_as_user`, `get_webhook`, `update_webhook`, `delete_webhook`,
`start_webhook_as_user`, `stop_webhook_as_user`, and `generate_webhook_key` according
to the task. Inspect `TestWebhookRequest` before `test_webhook`: it accepts
`delivery_id` and `payload`. A test callback verifies webhook handling, not actual
movement of funds.

Inspect delivery lists/summaries/details to diagnose failures. Use
`retry_webhook_delivery` or `abandon_webhook_delivery` only when the user intends
that action; a retry can trigger downstream business logic again. Check callback
configuration and HTTP outcomes rather than treating payment state as delivery state.

## Reconcile against the API

Webhooks are the low-latency path; the payment API is the source of current state.
The embedded contract guide prescribes repeated complete environment sweeps:

1. Request `get_payments` with `pagination=cursor`, `limit=100`,
   `sort_key=created_at`, `sort_order=DESC`, and **no payment filters**.
2. Upsert each payment by ID, applying idempotent business effects.
3. Follow `next_cursor` with unchanged parameters until `has_more` is false.
4. Repeat complete sweeps on an application-appropriate schedule. Protect against
   overlapping workers or stale updates regressing newer stored state.

Cursor pages are not a snapshot; a resource can change during a sweep. A repeated
complete sweep catches subsequent changes. Do not substitute a finite recent window
for this correctness guarantee. `start_date` / `end_date` filter creation time,
and `updated_at` ordering is not a monotonic reconciliation watermark. Status
filters can hide a resource after its state changes. Large deployments needing a
different strategy should confirm supported recovery semantics with Voltage.
