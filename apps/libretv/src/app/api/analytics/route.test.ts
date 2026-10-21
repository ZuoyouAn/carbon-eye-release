import { afterEach, describe, expect, it, vi } from 'vitest';
import { POST } from './route';
function req(body: unknown, headers: Record<string, string> = {}) {
  return new Request('https://video.example/api/analytics', { method: 'POST', headers: { origin: 'https://video.example', 'content-type': 'application/json', ...headers }, body: typeof body === 'string' ? body : JSON.stringify(body) });
}
afterEach(() => vi.unstubAllGlobals());
describe('video page analytics relay', () => {
  it('uses one fixed destination and does not forward credentials or client addresses', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 })); vi.stubGlobal('fetch', fetcher);
    const body = { site: 'video', path: '/cinema', visitor_id: 'test-anonymous', event_id: 'test-event' };
    const response = await POST(req(body, { cookie: 'private-cookie', authorization: 'Bearer private', 'x-forwarded-for': 'private-address', 'user-agent': 'Browser', dnt: '1' }));
    expect(response.status).toBe(204);
    const [url, options] = fetcher.mock.calls[0];
    expect(url).toBe('https://personal-website-carbon-eye-api.onrender.com/api/analytics/collect');
    expect(options.headers).toEqual({ 'Content-Type': 'application/json', Origin: 'https://zuoyou-space-libretv.onrender.com', 'User-Agent': 'Browser', DNT: '1', 'Sec-GPC': '0' });
    expect(options.body).toBe(JSON.stringify(body));
    expect(response.headers.get('cache-control')).toBe('no-store');
  });
  it('rejects cross-site and malformed origins before sending any request', async () => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
    expect((await POST(req({ site: 'video' }, { origin: 'https://other.example' }))).status).toBe(403);
    expect((await POST(req({ site: 'video' }, { 'sec-fetch-site': 'cross-site' }))).status).toBe(403);
    expect((await POST(req({ site: 'video' }, { origin: 'invalid-origin' }))).status).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('bounds incoming data and cannot be turned into a general-purpose proxy', async () => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
    expect((await POST(req('x'.repeat(4097)))).status).toBe(413);
    expect((await POST(req({ site: 'space', url: 'http://127.0.0.1' }))).status).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('returns a generic retryable failure without exposing upstream errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private diagnostic')));
    const response = await POST(req({ site: 'video' }));
    expect(response.status).toBe(503); expect(await response.text()).toBe('');
  });
});
