# Voltage agent skills

Skills for building with and operating the **Voltage API**. The first skill,
`voltage-api`, covers the product model, the published API contract, payment
lifecycles, webhooks, checkout, and authenticated curl requests.

## Install

Install all skills globally across the agents supported by Vercel's
[skills installer](https://github.com/vercel-labs/skills):

```sh
npx skills add voltagecloud/agent-skills --global --all
```

For interactive agent selection, omit `--all`. For installation into the current
project, omit `--global`. To install only this skill:

```sh
npx skills add voltagecloud/agent-skills --global --skill voltage-api
```

These repository commands work once this skill is merged into the default branch. To
inspect or install a local checkout:

```sh
npx skills add . --list
npx skills add . --skill voltage-api
```

No Voltage CLI, MCP server, or npm package is required. The optional helpers
require Python 3.9+ and curl; the TypeScript examples target server-side Node.js.

## Try it

- “Use Voltage to create a Lightning invoice and wait for payment.”
- “Build a Voltage webhook receiver that verifies signatures and reconciles payments.”
- “Check the available balance of my staging wallet.”
- “Explain which parts of this integration apply to a node-backed wallet.”
- “Add hosted Voltage checkout to this application.”

## Local credentials

The skill uses `~/.voltage/.env` as a local configuration convention. Installing
the skill does not create this file or connect to your account. Create it locally
and populate it using your environment's API credentials; do not paste secrets
into agent conversations.

```sh
mkdir -p ~/.voltage
chmod 700 ~/.voltage
(umask 077; touch ~/.voltage/.env)
chmod 600 ~/.voltage/.env
```

File contents:

```dotenv
VOLTAGE_API_KEY=your-environment-api-key
VOLTAGE_ORGANIZATION_ID=your-organization-uuid
VOLTAGE_ENVIRONMENT_ID=your-environment-uuid
# Optional default:
VOLTAGE_WALLET_ID=your-wallet-uuid
```

Process environment values override the file. Explicit resource parameters
override defaults for a single request. See the skill's
[configuration guide](skills/voltage-api/references/configuration.md).

## Source policy and maintenance

The [OpenAPI contract](https://voltageapi.com/v1/openapi/docs.json), exposed by
the [API reference](https://voltageapi.com/v1/docs), is authoritative, including
its embedded workflow guides. [Voltage docs](https://docs.voltageapi.com/)
provide product and setup context. Conflicts resolve in favor of the contract;
unsupported behavior is left explicit. Original source terminology is retained
in the unmodified contract; authored guidance calls the product Voltage and its
developer interface the Voltage API.

See [maintenance and validation](CONTRIBUTING.md) before refreshing references.
This skill does not claim that schema-valid requests bypass permissions,
provisioning, feature gates, or asynchronous validation.
