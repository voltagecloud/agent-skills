# Voltage API operation index

Generated from [openapi.json](openapi.json); do not edit by hand.

Base URL: `https://voltageapi.com/v1`. Every path below is relative to it.
47 operations across 38 paths.

Inspect the exact operation by ID with `scripts/inspect-operation.py`.
Use `--part request`, `--part response`, or `--part all`. The output includes
referenced definitions, parameters, response codes, and security schemes.
An absent security declaration does not imply that a body contains no credentials.

Embedded workflow guides can be read with `--guide Payments` or `--guide Webhooks`;
use `--section` with an exact heading to narrow the output. Guide names and
operation IDs retain upstream terminology.

## Assets

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_all_organization_supported_assets` | `GET /organizations/{organization_id}/assets` | api_key OR bearer_token | 200, 400, 401, 403, 500 |

## Wallets

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_all_organizations_wallets_as_user` | `GET /organizations/{organization_id}/wallets` | api_key OR bearer_token | 200, 400, 401, 403, 500 |
| `create_wallet` | `POST /organizations/{organization_id}/wallets` | api_key OR bearer_token | 202, 400, 401, 403, 413, 415, 422, 500 |
| `get_wallet` | `GET /organizations/{organization_id}/wallets/{wallet_id}` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `delete_wallet` | `DELETE /organizations/{organization_id}/wallets/{wallet_id}` | api_key OR bearer_token | 202, 400, 401, 403, 404, 500 |
| `update_wallet` | `PATCH /organizations/{organization_id}/wallets/{wallet_id}` | api_key OR bearer_token | 202, 400, 401, 403, 404, 413, 415, 422, 500 |
| `get_wallet_ledger_as_user` | `GET /organizations/{organization_id}/wallets/{wallet_id}/ledger` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |

## Wallet Policies

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_wallet_policies` | `GET /organizations/{organization_id}/wallets/{wallet_id}/policies` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `update_wallet_policies` | `PATCH /organizations/{organization_id}/wallets/{wallet_id}/policies` | api_key OR bearer_token | 202, 400, 401, 403, 404, 413, 415, 422, 500 |

## Payments

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_payments` | `GET /organizations/{organization_id}/environments/{environment_id}/payments` | api_key OR bearer_token | 200, 400, 401, 403, 500, 503 |
| `create_payment` | `POST /organizations/{organization_id}/environments/{environment_id}/payments` | api_key OR bearer_token | 202, 400, 401, 403, 409, 413, 415, 422, 500 |
| `create_treasury_movement` | `POST /organizations/{organization_id}/environments/{environment_id}/treasury_movements` | api_key OR bearer_token | 202, 400, 401, 403, 404, 409, 413, 415, 422, 500 |
| `check_payment` | `POST /organizations/{organization_id}/environments/{environment_id}/payments/check` | api_key OR bearer_token | 202, 400, 401, 403, 409, 413, 415, 422, 500 |
| `get_payment_summary` | `GET /organizations/{organization_id}/environments/{environment_id}/payments/summary` | api_key OR bearer_token | 200, 400, 401, 403, 500, 503 |
| `get_wallet_payment_summary` | `GET /organizations/{organization_id}/wallets/{wallet_id}/payments/summary` | api_key OR bearer_token | 200, 400, 401, 403, 500, 503 |
| `get_payment` | `GET /organizations/{organization_id}/environments/{environment_id}/payments/{payment_id}` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500, 503 |
| `get_payment_history` | `GET /organizations/{organization_id}/environments/{environment_id}/payments/{payment_id}/history` | api_key OR bearer_token | 200, 400, 401, 403, 500, 503 |

## Lines of Credit

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `update_sandbox_line_of_credit` | `PATCH /organizations/{organization_id}/environments/{environment_id}/lines_of_credit/{line_id}/sandbox` | api_key OR bearer_token | 202, 400, 401, 403, 404, 413, 415, 422, 500 |
| `get_line_of_credit_summary_as_user` | `GET /organizations/{organization_id}/lines_of_credit/{line_id}/summary` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `get_lines_of_credit_summaries_as_user` | `GET /organizations/{organization_id}/lines_of_credit/summaries` | api_key OR bearer_token | 200, 400, 401, 403, 500 |

## Billing

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_bill_as_user` | `GET /organizations/{organization_id}/bills/{bill_id}` | bearer_token OR api_key | 200, 400, 401, 403, 404, 500 |
| `get_bills_as_user` | `GET /organizations/{organization_id}/bills` | api_key OR bearer_token | 200, 400, 401, 403, 500 |
| `get_bill_summary_as_user` | `GET /organizations/{organization_id}/bills/summary` | api_key OR bearer_token | 200, 400, 401, 403, 500 |

## Webhooks

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_webhooks_as_user` | `GET /organizations/{organization_id}/webhooks` | api_key OR bearer_token | 200, 400, 401, 403, 500 |
| `create_webhook` | `POST /organizations/{organization_id}/environments/{environment_id}/webhooks` | api_key OR bearer_token | 202, 400, 401, 403, 409, 413, 415, 422, 500 |
| `get_webhook` | `GET /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `delete_webhook` | `DELETE /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}` | api_key OR bearer_token | 202, 400, 401, 403, 404, 500 |
| `update_webhook` | `PATCH /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}` | api_key OR bearer_token | 202, 400, 401, 403, 404, 413, 415, 422, 500 |
| `generate_webhook_key` | `POST /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/keys` | api_key OR bearer_token | 202, 400, 401, 403, 404, 500 |
| `test_webhook` | `POST /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/test` | api_key OR bearer_token | 202, 400, 401, 403, 404, 413, 415, 422, 500 |
| `start_webhook_as_user` | `POST /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/start` | api_key OR bearer_token | 202, 400, 401, 403, 404, 500 |
| `stop_webhook_as_user` | `POST /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/stop` | api_key OR bearer_token | 202, 400, 401, 403, 404, 500 |
| `get_webhook_deliveries_as_user` | `GET /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/deliveries` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `get_webhook_delivery_summary_as_user` | `GET /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/deliveries/summary` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `get_webhook_delivery` | `GET /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/deliveries/{delivery_id}` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `abandon_webhook_delivery` | `POST /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/deliveries/{delivery_id}/abandon` | api_key OR bearer_token | 202, 400, 401, 403, 404, 500 |
| `retry_webhook_delivery` | `POST /organizations/{organization_id}/environments/{environment_id}/webhooks/{webhook_id}/deliveries/{delivery_id}/retry` | api_key OR bearer_token | 202, 400, 401, 403, 404, 500 |

## Quoting (USD managed line of credit only)

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_quotes_as_user` | `GET /organizations/{organization_id}/environments/{environment_id}/quotes` | api_key OR bearer_token | 200, 400, 401, 403, 500 |
| `request_a_quote` | `POST /organizations/{organization_id}/environments/{environment_id}/quotes` | api_key OR bearer_token | 202, 400, 401, 403, 409, 413, 415, 422, 500 |
| `get_a_quote_as_user` | `GET /organizations/{organization_id}/environments/{environment_id}/quotes/{quote_id}` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |

## Checkout Event Streams

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_events` | `GET /checkout/events` | checkout_stream_token | 200, 400, 401, 403, 500 |
| `create_event_stream_token` | `POST /checkout/streams` | No scheme declared; inspect body/parameters | 201, 400, 401, 403, 413, 415, 422, 500 |

## Checkout Settings

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `get_settings` | `GET /organizations/{organization_id}/environments/{environment_id}/checkout/settings` | api_key OR bearer_token | 200, 400, 401, 403, 404, 500 |
| `update_settings` | `PUT /organizations/{organization_id}/environments/{environment_id}/checkout/settings` | api_key OR bearer_token | 200, 400, 401, 403, 413, 415, 422, 500 |

## Checkout Sessions

| Operation ID | Method and path | Authentication | Responses |
|---|---|---|---|
| `create_session` | `POST /organizations/{organization_id}/environments/{environment_id}/checkout/sessions` | api_key OR bearer_token | 201, 400, 401, 403, 409, 413, 415, 422, 500 |
| `get_session` | `GET /checkout/sessions/{session_id}` | checkout_session_token | 200, 202, 400, 401, 403, 404, 409, 500 |
| `get_session_allowed_origins` | `GET /checkout/sessions/{session_id}/allowed-origins` | No scheme declared; inspect body/parameters | 200, 400, 404, 500 |
