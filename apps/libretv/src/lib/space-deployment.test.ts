import { afterEach, describe, expect, it, vi } from 'vitest';
import { sessionFromCookieHeader } from './auth';
import { GET } from '@/app/healthz/route';
import { isPrivateIP, isValidProxyUrl } from './ssrf';

afterEach(() => vi.unstubAllEnvs());

describe('Space deployment', () => {
  it.each(['0.1.2.3', '100.127.0.1', '198.18.0.1', '224.1.2.3', '255.255.255.255', 'febf::1', 'ff02::1', '2001:db8::1'])('rejects reserved target %s', (ip) => {
    expect(isPrivateIP(ip)).toBe(true);
  });
  it('does not accept credentials embedded in a proxy URL', () => {
    expect(isValidProxyUrl('https://user:password@example.com/video.m3u8')).toBe(false);
  });
  it('malformed session cookies fail closed instead of crashing', () => {
    expect(sessionFromCookieHeader('ltv_session=%ZZ')).toBe(false);
  });
  it('reports readiness without probing a video source', async () => {
    vi.stubEnv('PASSWORD', 'test-only-private-value');
    expect(GET().status).toBe(200);
    expect(await GET().json()).toMatchObject({ status: 'ok', app: 'libretv' });
    vi.stubEnv('PASSWORD', '');
    expect(GET().status).toBe(503);
  });
});
