# Source discrepancies and contract limitations

Reviewed 2026-09-08. This file records actionable differences, not a claim that
every example on both sites has been audited. Recheck when updating the snapshot.

| Topic | Conflicting or incomplete source | Follow this rule |
|---|---|---|
| Reconciliation windows | The [human webhook guide](https://docs.voltageapi.com/webhooks) describes `start_date` / `end_date` plus `sort_key=updated_at` as an updated-time window | The contract's `get_payments` parameters filter **creation** time and its Webhooks guide prescribes repeated complete, unfiltered cursor sweeps ordered by `created_at`. Sorting is not a change feed. |
| Receive `succeeded` | The human webhook guide's partial on-chain example shows payment `status: succeeded` | `ReceiveStatus` contains `generating`, `receiving`, `expired`, `failed`, `completed`. `succeeded` can be a receive **event**, not that payment status. |
| Webhook create body | Human examples add organization/environment fields | Current `NewWebhookRequest` declares `id`, `url`, `name`, `events`; organization and environment go in the route. Do not generate undeclared body fields from an old example. |
| Taproot Asset sends | A send variant exists in `PaymentRequest` / `SendPaymentRequest` | The contract's embedded Payments guide explicitly states the schema and asynchronous processor lack a single canonical amount shape. Expose the gap and confirm with Voltage before implementing that send. |
| Asset `Amount` example | The generic `Amount` schema has an illustrative asset string shorter than its own required 66 hex characters | Honor the schema pattern `^asset:[a-fA-F0-9]{66}$`. Generate valid dummy group keys for schema fixtures; use a real supported asset for live calls. |
| Product naming | Original sources still say “Voltage Payments” / “Payments API” | New authored guidance uses Voltage / Voltage API per the product owner's direction. Preserve original source bytes, operation IDs, API fields, and necessary UI labels. |

Schema-valid does not mean runtime-supported. Respect descriptions covering
permissions, currency, feature gates, funding, fee policies, and provisioning.
Where the contract has an internal limitation, avoid presenting a guess as working
code. Never silently repair source bytes; fix derived guidance and record the issue.
