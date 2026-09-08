# Voltage product model

Sources: [Voltage docs](https://docs.voltageapi.com/),
[setup](https://docs.voltageapi.com/setup),
[wallet setup](https://docs.voltageapi.com/wallet-setup-guide),
[access model](https://docs.voltageapi.com/access-model), and the pinned
OpenAPI schemas `Wallet`, `NewWalletRequest`, `SummaryLineOfCredit`, and `SupportedNetwork`.
Product naming follows the repository owner's direction: Voltage / Voltage API.

## Orientation

Voltage is an API-centered platform for building payment integrations. Developers
usually complete initial organization/environment, wallet, and credential setup
in the dashboard, then automate the supported workflows through the API. The
dashboard also provides wallet, credit, billing, and webhook management.

Some UI labels still distinguish “Infrastructure” and “Payments”. Mention the
exact label if it helps a user navigate, but do not present “Voltage Payments”
as the primary product name in new integration docs or generated application copy.

The public contract bundled here does **not** publish operations to create
organizations, environments, environment API keys, or the underlying credit facility.
Use documented dashboard setup for those prerequisites. Do not invent their API routes.

## Resource map

| Concept | Meaning and implementation consequence |
|---|---|
| Organization | Owning account scope; most API paths start with `organization_id`. The dashboard may call the human team boundary a team. |
| Environment | Separates wallet activity, keys, and webhooks. A key belongs to one environment and its permissions. Some organization-level routes take environment query filters instead of a path component. |
| Wallet | Holds balances and payment activity; belongs to an organization/environment and has a network and backing relationship. Read its actual state before choosing it for an operation. |
| Line of credit | Referenced by wallets and quoting/billing APIs. The API uses this resource relationship even where customer-controlled node infrastructure is involved. Do not infer a missing `line_of_credit_id` from “node-backed”. |
| Network | The current `SupportedNetwork` request enum is `mainnet`, `testnet3`, `mutinynet`. Verify what the specific operation accepts and what the selected wallet uses. |
| Currency | Wallet/account denomination and rail amount can differ, especially for USD wallets moving funds over Bitcoin/Lightning. |
| Payment | Client-identified asynchronous send or receive. One accepted request can produce later state changes, receipts, outflows, and errors. |
| Quote | Single-use, expiring conversion resource for supported USD managed lines of credit. The client supplies its UUID and polls readiness. |
| Webhook | Environment-scoped callback registration with its own ID and signing secret. Delivery success means HTTP delivery succeeded, not that money moved. |
| Checkout session | Connects a hosted browser payment experience to an underlying payment; session and payment IDs are separate. |

## Wallet backing

| Guidance | Credit-backed | Node-backed |
|---|---|---|
| Backing | Voltage-provided line of credit; the customer does not operate the underlying Lightning node | Customer-controlled Lightning node and reserve beneath the API |
| Routine integration | Use the Voltage API | Use the Voltage API |
| Additional customer responsibilities | Credit/funding arrangement and account setup | Node credentials, custody, backups, liquidity, monitoring, and treasury/infrastructure operations |
| Swap routing | Wallets without customer node infrastructure cannot request this flow | Requires explicit swap provisioning and additional rail/channel/liquidity prerequisites |

Explain applicability, follow the user's selected model, and refer provisioning
or funding-model decisions to the customer's Voltage contact when needed. The
product owner's guidance is that credit-backed is the easiest/recommended starting
point for most customers; it is not a rule to migrate an existing node-backed customer.

Wallet currency and backing model are separate axes. Do not equate USD with every
credit-backed wallet or BTC with only node-backed wallets. Inspect the relevant
wallet and credit summary before deriving a quote or balance interpretation.

## Setup and testing

The wallet setup docs describe creating an environment, opening it, adding a
Development wallet, and then generating an environment key. They distinguish
Mutinynet Bitcoin for Bitcoin-backed tests (both models) and Mutinynet USD for
USD line-of-credit tests. These UI flows are contextual guidance, not extra API
endpoints. Check current docs before giving exact UI steps.

The same docs describe Voltage Cash as experimental and not live for production;
do not turn schema visibility of asset types into a promise of customer availability.

Before testing, read the wallet's organization, environment, `active` state, and
network, and inspect its available balance/credit as relevant. Verify the intended
test configuration rather than trusting a name such as “Staging”. A mainnet wallet
can involve real funds even when a developer is merely testing application code.

## Credential boundaries

Use environment API keys for this API. A user JWT is an alternative only where
the operation declares it and the user already has a legitimate token. This
contract does not define a JWT login/refresh flow.

Infrastructure API keys and direct LND macaroons are separate credentials. Do not
send them as an environment API key, substitute their authentication headers, or
try to operate an LND node using this skill's request helper. The concepts are
relevant to understanding node-backed wallets; direct node administration is outside
this skill's API scope.
