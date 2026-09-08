import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { VoltageClient, SubmissionUnknownError, VoltageHttpError } from '../skills/voltage-api/assets/voltage-client.ts';
import { verifyWebhook } from '../skills/voltage-api/assets/verify-webhook.ts';

const id = '11ca843c-bdaa-44b6-965a-39ac550fcef7';
const wallet = '7a68a525-9d11-4c1e-a3dd-1c2bf1378ba2';
const config = { apiKey: 'synthetic-key', organizationId: 'b0684ab8-1130-46af-8f70-71519442f108', environmentId: '123e4567-e89b-12d3-a456-426614174000' };
const receive = { id, wallet_id: wallet, payment_kind: 'bolt11', amount: { currency: 'btc', amount: 150000 } };
const payment = (status, direction = 'receive', data = {}) => ({ id, direction, status, data });
const json = (body, status = 200, headers) => new Response(JSON.stringify(body), { status, headers });
const fast = { timeoutMs: 200, initialDelayMs: 1, maxDelayMs: 2 };

function sequence(responses) {
  const calls = [];
  const transport = async (url, options) => {
    calls.push({ url, ...options });
    const response = responses.shift();
    if (response instanceof Error) throw response;
    if (!response) throw new Error('Unexpected extra request');
    return response;
  };
  return { client: new VoltageClient(config, transport), calls };
}

test('empty 202, eventual read 404, generation, and completion without duplicate POST', async () => {
  const { client, calls } = sequence([
    new Response(null, { status: 202 }), json({ error: { type: 'not_found' } }, 404),
    json(payment('generating')), json(payment('receiving', 'receive', { payment_request: 'synthetic-invoice' })),
    json(payment('completed')),
  ]);
  assert.deepEqual(await client.createPayment(receive), { paymentId: id, httpStatus: 202 });
  const generated = await client.waitPayment(id, { ...fast, goal: 'generated' });
  assert.equal(generated.outcome, 'generated');
  assert.equal(generated.payment.data.payment_request, 'synthetic-invoice');
  assert.equal((await client.waitPayment(id, fast)).outcome, 'completed');
  assert.equal(calls.filter(c => c.method === 'POST').length, 1);
  assert.equal(calls[0].headers['x-api-key'], config.apiKey);
  assert.equal(calls[0].redirect, 'error');
  assert.deepEqual(JSON.parse(calls[0].body), receive);
});

test('approved remains intermediate on sends but is terminal on checks', async () => {
  let setup = sequence([json(payment('approved', 'send')), json(payment('completed', 'send'))]);
  assert.equal((await setup.client.waitPayment(id, fast)).outcome, 'completed');
  assert.equal(setup.calls.length, 2);
  setup = sequence([json(payment('approved', 'send'))]);
  assert.equal((await setup.client.waitPayment(id, { ...fast, goal: 'checked' })).outcome, 'approved');
  assert.equal(setup.calls.length, 1);
});

test('a network-ambiguous write exposes the original ID and is not retried', async () => {
  const { client, calls } = sequence([new TypeError('connection lost')]);
  await assert.rejects(client.createPayment(receive), error => error instanceof SubmissionUnknownError && error.paymentId === id);
  assert.equal(calls.length, 1);
});

test('does not consume a quote on check or serialize unsafe amount integers', async () => {
  const { client, calls } = sequence([]);
  await assert.rejects(client.createPayment({ ...receive, quote_id: id }, { checkOnly: true }), /single-use quote/);
  await assert.rejects(client.createPayment({ ...receive, amount: { currency: 'btc', amount: Number.MAX_SAFE_INTEGER + 1 } }), /safe integer/);
  assert.equal(calls.length, 0);
});

test('client objects do not expose credentials and unsafe response integers are rejected', async () => {
  const { client } = sequence([json({ ...payment('completed'), requested_amount: { currency: 'btc', amount: Number.MAX_SAFE_INTEGER + 1 } })]);
  assert.equal(JSON.stringify(client), '{}');
  await assert.rejects(client.getPayment(id), /safe integer/);
});

test('terminal receive failure/expiry is not reported as paid', async () => {
  for (const status of ['failed', 'expired']) {
    const { client, calls } = sequence([json(payment(status))]);
    assert.equal((await client.waitPayment(id, { ...fast, goal: 'generated' })).outcome, status);
    assert.equal(calls.length, 1);
  }
});

test('persistent pending reads stop on deadline and never submit', async () => {
  const calls = [];
  const client = new VoltageClient(config, async (url, options) => {
    calls.push(options);
    return json(payment('generating'));
  });
  const result = await client.waitPayment(id, { ...fast, timeoutMs: 15 });
  assert.equal(result.outcome, 'pending');
  assert.equal(result.paymentId, id);
  assert.ok(calls.length > 0);
  assert.ok(calls.every(c => c.method === 'GET'));
});

test('non-retryable authorization failure stops promptly', async () => {
  const { client, calls } = sequence([json({ error: { type: 'forbidden', code: 'test_code' } }, 403)]);
  await assert.rejects(client.waitPayment(id, fast), error => error instanceof VoltageHttpError && error.status === 403 && error.errorType === 'forbidden');
  assert.equal(calls.length, 1);
});

test('Retry-After longer than deadline returns pending without another request', async () => {
  const { client, calls } = sequence([json({ error: { type: 'busy' } }, 503, { 'retry-after': '60' })]);
  assert.equal((await client.waitPayment(id, { ...fast, timeoutMs: 15 })).outcome, 'pending');
  assert.equal(calls.length, 1);
});

test('unknown status and mismatched resource ID do not imply success', async () => {
  const { client } = sequence([json(payment('succeeded'))]);
  await assert.rejects(client.waitPayment(id, fast), /Unknown payment/);
  const other = sequence([json({ ...payment('completed'), id: wallet })]);
  await assert.rejects(other.client.waitPayment(id, fast), /Unexpected payment/);
});

const timestamp = '1800000000';
const webhookId = 'b0fc9829-f139-4035-bb14-4a4b6cd58f0e';
const raw = Buffer.from('{ "type": "receive", "detail": {"event":"completed", "data":{"id":"' + id + '"}} }');
const secret = 'synthetic-webhook-secret';
function headersFor(body = raw, key = secret, time = timestamp) {
  return new Headers({
    'x-voltage-webhook-id': webhookId,
    'x-voltage-timestamp': time,
    'x-voltage-signature': createHmac('sha256', key).update(body).update('.' + time).digest('base64'),
    'x-voltage-event': 'untrusted-hint',
  });
}
const keys = new Map([[webhookId, [secret]]]);
const clock = { nowSeconds: Number(timestamp), toleranceSeconds: 300 };

test('webhook uses raw bytes, literal secret, dot separator, and verified body routing', () => {
  const result = verifyWebhook(raw, headersFor(), keys, clock);
  assert.equal(result.payload.detail.event, 'completed');
  assert.equal(result.webhookId, webhookId);
  const reserialized = Buffer.from(JSON.stringify(JSON.parse(raw.toString())));
  assert.throws(() => verifyWebhook(reserialized, headersFor(), keys, clock), /signature/);
});

test('webhook supports registration-specific rotation candidates', () => {
  const rotating = new Map([[webhookId, ['old-test-secret', secret]]]);
  assert.equal(verifyWebhook(raw, headersFor(), rotating, clock).webhookId, webhookId);
  assert.throws(() => verifyWebhook(raw, headersFor(), new Map([[webhookId, ['wrong-test-secret']]]), clock), /signature/);
});

test('rejects missing/unknown IDs, stale/future/malformed timestamps, and malformed signatures', () => {
  for (const [field, value] of [
    ['x-voltage-webhook-id', null], ['x-voltage-webhook-id', 'unknown'],
    ['x-voltage-timestamp', 'yesterday'], ['x-voltage-timestamp', String(Number(timestamp) - 301)],
    ['x-voltage-timestamp', String(Number(timestamp) + 301)],
    ['x-voltage-signature', 'short'], ['x-voltage-signature', '!'.repeat(44)],
  ]) {
    const headers = headersFor();
    value === null ? headers.delete(field) : headers.set(field, value);
    assert.throws(() => verifyWebhook(raw, headers, keys, clock));
  }
});
