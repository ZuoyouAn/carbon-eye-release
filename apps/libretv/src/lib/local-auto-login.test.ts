import { afterEach, describe, expect, it, vi } from 'vitest';
import { isLocalAutoLoginAllowed, requestHasSession, SESSION_COOKIE, signSession } from './auth';
import { guardRequest } from './api-guard';
import { GET as getStatus } from '@/app/api/status/route';

afterEach(() => vi.unstubAllEnvs());

function enableLocalLauncher() {
  vi.stubEnv('NODE_ENV', 'development');
  vi.stubEnv('LIBRETV_LOCAL_AUTO_LOGIN', '1');
  vi.stubEnv('PASSWORD', 'local-test-password');
}

function localRequest(headers: Record<string, string> = {}) {
  return new Request('http://localhost:8080/api/status', { headers: { host: 'localhost:8080', ...headers } });
}

describe('local launcher authentication', () => {
  it('fresh local browser can use protected APIs and receives verified status without cookies', async () => {
    enableLocalLauncher();
    const req = localRequest();
    expect(guardRequest(req)).toBeNull();
    const status = await (await getStatus(req)).json();
    expect(status).toMatchObject({ passwordRequired: true, verified: true, localAutoLogin: true });
  });

  it('ordinary starts and production deployments still require a session', () => {
    enableLocalLauncher();
    vi.stubEnv('LIBRETV_LOCAL_AUTO_LOGIN', '0');
    expect(guardRequest(localRequest())?.status).toBe(401);
    vi.stubEnv('LIBRETV_LOCAL_AUTO_LOGIN', '1');
    vi.stubEnv('NODE_ENV', 'production');
    expect(guardRequest(localRequest())?.status).toBe(401);
  });

  it('does not allow nonlocal hosts, host lookalikes, or cross-origin requests to log in automatically', () => {
    enableLocalLauncher();
    const deniedHeaders: Record<string, string>[] = [
      { host: '192.168.1.5:8080' },
      { host: 'localhost.example.com:8080' },
      { origin: 'https://example.com' },
      { origin: 'null' },
      { 'sec-fetch-site': 'cross-site' },
    ];
    for (const headers of deniedHeaders) {
      expect(isLocalAutoLoginAllowed(localRequest(headers))).toBe(false);
      expect(guardRequest(localRequest(headers))?.status).toBe(401);
    }
  });

  it('accepts same-origin requests and explicit loopback IP hosts', () => {
    enableLocalLauncher();
    expect(isLocalAutoLoginAllowed(localRequest({ origin: 'http://localhost:8080' }))).toBe(true);
    expect(isLocalAutoLoginAllowed(localRequest({ host: '127.0.0.1:8080' }))).toBe(true);
    expect(isLocalAutoLoginAllowed(localRequest({ host: '[::1]:8080' }))).toBe(true);
  });

  it('keeps existing password sessions valid when local mode is disabled', () => {
    enableLocalLauncher();
    vi.stubEnv('LIBRETV_LOCAL_AUTO_LOGIN', '0');
    const { token } = signSession();
    expect(requestHasSession(localRequest({ cookie: `${SESSION_COOKIE}=${token}` }))).toBe(true);
    expect(requestHasSession(localRequest())).toBe(false);
  });
});
