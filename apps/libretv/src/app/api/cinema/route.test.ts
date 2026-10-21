import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { POST } from './route';
import { SESSION_COOKIE, signSession } from '@/lib/auth';
import type { CinemaSession, CinemaSnapshot } from '@/lib/cinema-sync';

vi.mock('@/lib/ssrf', () => ({ checkUpstreamAllowed: vi.fn(async (url: string) => ({ ok: !url.includes('127.0.0.1'), reason: '私网地址被拒绝' })) }));
beforeEach(() => { vi.stubEnv('PASSWORD', 'test-cinema-password'); vi.stubEnv('LIBRETV_LOCAL_AUTO_LOGIN', '0'); });
afterEach(() => vi.unstubAllEnvs());
function req(body: unknown, headers: Record<string, string> = {}, authenticated = true) {
  return new Request('https://cinema.test/api/cinema', { method: 'POST', headers: { 'content-type': 'application/json', ...(authenticated ? { cookie: `${SESSION_COOKIE}=${signSession().token}` } : {}), ...headers }, body: JSON.stringify(body) });
}
async function create() {
  const res = await POST(req({ action: 'create', name: '房间', nickname: 'host' }));
  expect(res.status).toBe(200);
  return (await res.json()) as { session: CinemaSession; snapshot: CinemaSnapshot };
}
describe('cinema route guard', () => {
  it('atomically creates a media-loaded room from a search selection', async () => {
    const response = await POST(req({ action: 'create', name: '影片', media: { url: 'https://example.com/a.mp4', title: '第一集' } }));
    expect(response.status).toBe(200);
    const result = await response.json();
    expect(result.snapshot.playback).toMatchObject({ playing: false, position: 0, media: { title: '第一集' } });
  });
  it('applies the same private-address restriction to initial media', async () => {
    expect((await POST(req({ action: 'create', media: { url: 'http://127.0.0.1/a.mp4' } }))).status).toBe(400);
  });
  it('requires the site password session', async () => { expect((await POST(req({ action: 'create' }, {}, false))).status).toBe(401); });
  it('rejects cross-origin browser requests', async () => {
    expect((await POST(req({ action: 'create' }, { origin: 'https://evil.test' }))).status).toBe(403);
    expect((await POST(req({ action: 'create' }, { 'sec-fetch-site': 'cross-site' }))).status).toBe(403);
  });
  it('rejects oversized, malformed and non-JSON requests', async () => {
    expect((await POST(req({ action: 'create', name: 'x'.repeat(17_000) }))).status).toBe(413);
    expect((await POST(req([], {}))).status).toBe(400);
    expect((await POST(req({ action: 'create' }, { 'content-type': 'text/plain' }))).status).toBe(415);
  });
  it('checks guest authority on the server rather than accepting a forged role', async () => {
    const { session: host } = await create();
    const join = await POST(req({ action: 'join', roomId: host.roomId, nickname: 'guest', role: 'host' }));
    const guest = (await join.json()).session as CinemaSession;
    const result = await POST(req({ action: 'control', ...guest, role: 'host', op: 'media', media: { url: 'https://example.com/a.mp4' }, sequence: 1 }));
    expect(result.status).toBe(403);
    expect((await (await POST(req({ action: 'sync', ...guest }))).json()).playback.media).toBeNull();
  });
  it('validates media targets and can share ordinary controls and comments', async () => {
    const { session: host } = await create();
    expect((await POST(req({ action: 'control', ...host, op: 'media', media: { url: 'http://127.0.0.1/a.mp4' }, sequence: 1 }))).status).toBe(400);
    const update = await POST(req({ action: 'control', ...host, op: 'media', media: { url: 'https://example.com/a.mp4', title: '电影' }, sequence: 2 }));
    expect(update.status).toBe(200);
    expect((await update.json()).playback.media.title).toBe('电影');
    const chat = await POST(req({ action: 'chat', ...host, text: '一起看' }));
    expect((await chat.json()).messages[0]).toMatchObject({ host: true, text: '一起看' });
    expect((await POST(req({ action: 'sync', roomId: host.roomId, memberToken: 'wrong-token-but-long-enough' }))).status).toBe(403);
    expect((await POST(req({ action: 'leave', ...host }))).status).toBe(200);
  });
});
