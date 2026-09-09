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
