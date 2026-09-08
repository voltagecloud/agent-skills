/** Server-side signature verification. Pass exact raw HTTP request bytes. */
import { createHmac, timingSafeEqual } from 'node:crypto';

export function verifyWebhook(
  rawBody: Uint8Array,
  headers: Headers,
  secretsByWebhookId: ReadonlyMap<string, readonly string[]>,
  options: { nowSeconds?: number; toleranceSeconds?: number } = {},
): { webhookId: string; payload: unknown } {
  const id = headers.get('x-voltage-webhook-id');
  const timestamp = headers.get('x-voltage-timestamp');
  const signature = headers.get('x-voltage-signature');
  const secrets = id ? secretsByWebhookId.get(id) : undefined;
  const now = options.nowSeconds ?? Math.floor(Date.now() / 1000);
  const tolerance = options.toleranceSeconds ?? 300; // Application policy; choose for your receiver.
  if (!Number.isFinite(now) || !Number.isFinite(tolerance) || tolerance < 0) throw new Error('Invalid verification time policy');
  if (!id || !secrets?.length || !timestamp || !/^\d+$/.test(timestamp) ||
      !Number.isSafeInteger(Number(timestamp)) || Math.abs(now - Number(timestamp)) > tolerance ||
      !signature || !/^[A-Za-z0-9+/]{43}=$/.test(signature)) {
    throw new Error('Invalid webhook authentication');
  }
  const actual = Buffer.from(signature, 'base64');
  if (actual.length !== 32 || actual.toString('base64') !== signature) throw new Error('Invalid webhook signature');
  let verified = false;
  for (const secret of secrets) {
    if (!secret) continue;
    const expected = createHmac('sha256', secret).update(rawBody).update('.' + timestamp).digest();
    verified = timingSafeEqual(expected, actual) || verified;
  }
  if (!verified) throw new Error('Invalid webhook signature');
  // Only body + timestamp are signed. Route on this payload, not x-voltage-event.
  const payload: unknown = JSON.parse(Buffer.from(rawBody).toString('utf8'));
  return { webhookId: id, payload };
}
