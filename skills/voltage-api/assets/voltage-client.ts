/** Focused server-side Voltage API example. No automatic write retries. */
import { setTimeout as sleep } from 'node:timers/promises';

type JsonObject = Record<string, unknown>;
type Payment = JsonObject & {
  id: string;
  direction: 'send' | 'receive';
  status: string;
  data: JsonObject;
};
type PollGoal = 'generated' | 'completed' | 'checked';
type PollResult = {
  outcome: 'generated' | 'completed' | 'approved' | 'failed' | 'expired' | 'pending';
  paymentId: string;
  payment?: Payment;
};

function uuid(value: string): string {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error('Expected a UUID');
  }
  return value.toLowerCase();
}

function safeNumbers(value: unknown): void {
  if (typeof value === 'number' && !Number.isSafeInteger(value)) {
    throw new Error('Use safe integer base units or a lossless JSON implementation');
  }
  if (value !== null && typeof value === 'object') {
    for (const child of Object.values(value)) safeNumbers(child);
  }
}

export class VoltageHttpError extends Error {
  status: number;
  retryAfterMs: number;
  errorType?: string;
  errorCode?: string;
  constructor(status: number, body: any, retryAfterMs = 0) {
    super(`Voltage HTTP ${status}; inspect the operation contract and reconcile any submitted ID`);
    this.status = status;
    this.retryAfterMs = retryAfterMs;
    this.errorType = typeof body?.error?.type === 'string' ? body.error.type : undefined;
    this.errorCode = typeof body?.error?.code === 'string' ? body.error.code : undefined;
  }
}

export class SubmissionUnknownError extends Error {
  paymentId: string;
  constructor(paymentId: string) {
    super(`Submission outcome unknown; read payment ${paymentId} before deciding whether to submit again`);
    this.paymentId = paymentId;
  }
}

export class VoltageClient {
  #apiKey: string;
  #scope: string;
  #fetcher: typeof fetch;

  constructor(config: { apiKey: string; organizationId: string; environmentId: string }, fetcher: typeof fetch = fetch) {
    if (!config.apiKey || /[\x00-\x1f\x7f]/.test(config.apiKey)) throw new Error('A valid environment API key is required');
    this.#apiKey = config.apiKey;
    this.#scope = `https://voltageapi.com/v1/organizations/${uuid(config.organizationId)}/environments/${uuid(config.environmentId)}`;
    this.#fetcher = fetcher;
  }

  private async request(method: string, suffix: string, body?: JsonObject, timeoutMs = 30_000): Promise<{ status: number; body: any }> {
    if (body) safeNumbers(body);
    const response = await this.#fetcher(this.#scope + suffix, {
      method,
      headers: { 'x-api-key': this.#apiKey, accept: 'application/json', ...(body ? { 'content-type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      redirect: 'error',
      signal: AbortSignal.timeout(Math.max(1, Math.ceil(timeoutMs))),
    });
    const raw = await response.text();
    let content: any = null;
    if (raw) {
      try { content = JSON.parse(raw); }
      catch { /* Do not log arbitrary error bodies or assume an empty 202 contains JSON. */ }
    }
    if (!response.ok) {
      const header = response.headers.get('retry-after');
      const delay = header === null ? 0 : /^\d+(\.\d+)?$/.test(header)
        ? Number(header) * 1000 : Math.max(0, Date.parse(header) - Date.now());
      throw new VoltageHttpError(response.status, content, Number.isFinite(delay) ? delay : 0);
    }
    return { status: response.status, body: content };
  }

  /** Persist payload.id in your application before calling this method. */
  async createPayment(payload: JsonObject, options: { checkOnly?: boolean } = {}): Promise<{ paymentId: string; httpStatus: 202 }> {
    const id = uuid(String(payload.id));
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id)) {
      throw new Error('Generate and persist a UUIDv4 for a new payment');
    }
    safeNumbers(payload);
    if (options.checkOnly && payload.quote_id) throw new Error('Do not attach a single-use quote to a policy check');
    // Inspect PaymentRequest (or SendPaymentRequest for a check) before constructing payload.
    try {
      const response = await this.request('POST', '/payments' + (options.checkOnly ? '/check' : ''), payload);
      if (response.status !== 202) throw new SubmissionUnknownError(id);
      return { paymentId: id, httpStatus: 202 };
    } catch (error) {
      if (error instanceof VoltageHttpError || error instanceof SubmissionUnknownError) throw error;
      throw new SubmissionUnknownError(id);
    }
  }

  async getPayment(id: string, timeoutMs = 30_000): Promise<Payment> {
    const response = await this.request('GET', '/payments/' + uuid(id), undefined, timeoutMs);
    if (response.status !== 200 || typeof response.body?.id !== 'string' || response.body.id.toLowerCase() !== uuid(id)) {
      throw new Error('Unexpected payment response; do not infer a business outcome');
    }
    safeNumbers(response.body);
    return response.body as Payment;
  }

  /** Poll an existing, known submitted ID. Timings are client policy, not a service SLA. */
  async waitPayment(id: string, options: { goal?: PollGoal; timeoutMs?: number; initialDelayMs?: number; maxDelayMs?: number } = {}): Promise<PollResult> {
    id = uuid(id);
    const goal = options.goal ?? 'completed';
    const timeout = options.timeoutMs ?? 60_000;
    const maximum = options.maxDelayMs ?? 5000;
    let delay = options.initialDelayMs ?? 500;
    if (![timeout, maximum, delay].every(n => Number.isFinite(n) && n > 0)) throw new Error('Polling timings must be positive and finite');
    const deadline = performance.now() + timeout;
    let payment: Payment | undefined;
    while (performance.now() < deadline) {
      let retryHint = 0;
      try {
        payment = await this.getPayment(id, Math.min(30_000, deadline - performance.now()));
        const valid = payment.direction === 'receive'
          ? ['generating', 'receiving', 'expired', 'failed', 'completed']
          : payment.direction === 'send' ? ['sending', 'approved', 'failed', 'completed'] : [];
        if (!valid.includes(payment.status)) throw new Error('Unknown payment direction/status; inspect the current contract');
        if (goal === 'checked' && payment.direction !== 'send') throw new Error('A policy check must be a send');
        if (goal === 'generated' && payment.direction !== 'receive') throw new Error('Request generation applies to receives');
        if (['failed', 'expired', 'completed'].includes(payment.status)) {
          return { outcome: payment.status as 'failed' | 'expired' | 'completed', paymentId: id, payment };
        }
        if (goal === 'checked' && payment.status === 'approved') return { outcome: 'approved', paymentId: id, payment };
        if (goal === 'generated' && payment.status === 'receiving' &&
            (payment.data?.payment_request || payment.data?.address || payment.bip21_uri)) {
          return { outcome: 'generated', paymentId: id, payment };
        }
      } catch (error) {
        if (error instanceof VoltageHttpError) {
          if (![404, 429, 500, 502, 503, 504].includes(error.status)) throw error;
          retryHint = error.retryAfterMs;
        } else if (!(error instanceof TypeError) && !(error instanceof DOMException && ['TimeoutError', 'AbortError'].includes(error.name))) {
          throw error;
        }
        // GET retries only. Never create a replacement payment from this loop.
      }
      const remaining = deadline - performance.now();
      if (remaining <= 0) break;
      const backoff = Math.min(delay, maximum) * (0.8 + Math.random() * 0.2);
      const wait = Math.max(backoff, retryHint);
      // If the next permitted attempt is past our deadline, return pending now.
      // Sleeping only until the deadline can wake early and violate Retry-After.
      if (wait >= remaining) break;
      await sleep(Math.ceil(wait));
      delay = Math.min(maximum, delay * 2);
    }
    return { outcome: 'pending', paymentId: id, payment };
  }
}
