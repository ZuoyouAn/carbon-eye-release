import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CINEMA_PLAYLIST, CINEMA_SESSION, CinemaRequestError, launchCinema, resolveCinemaSelection, selectionMedia } from './cinema-client';
import type { SearchResultItem, SourceConfig } from './types';

const source: SourceConfig = { key: 'test', name: '测试源', url: 'https://example.com/cms' };
const items: SearchResultItem[] = [1, 2].map(id => ({ sourceKey: 'test', sourceName: '测试源', vodId: String(id), name: '同一影片' }));
const selection = { title: '影片', episodes: ['https://example.com/one.mp4', 'https://example.com/two.mp4'], index: 0 };
const session = { roomId: '1234567890abcdef', memberToken: 'test-only-member-token-not-a-secret', role: 'host' };
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
const result = { session, snapshot: { roomId: session.roomId, role: 'host' } };
let storage: Map<string, string>;
beforeEach(() => {
  storage = new Map();
  vi.stubGlobal('sessionStorage', { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value), removeItem: (key: string) => storage.delete(key) });
});
afterEach(() => vi.unstubAllGlobals());

describe('search-to-cinema selection', () => {
  it('selects the first episode without copying a link', async () => {
    const detail = vi.fn().mockResolvedValue({ episodes: selection.episodes });
    expect(await resolveCinemaSelection(items, () => source, detail)).toEqual({ ...selection, title: '同一影片' });
    expect(detail).toHaveBeenCalledTimes(1);
    expect(selectionMedia(selection).title).toBe('影片 · 第1集');
    expect(selectionMedia({ ...selection, index: 1 }).url).toContain('two.mp4');
  });
  it('falls back within the same film when a source has no playable detail', async () => {
    const detail = vi.fn().mockResolvedValueOnce({ episodes: [] }).mockResolvedValueOnce({ episodes: selection.episodes });
    await resolveCinemaSelection(items, () => source, detail);
    expect(detail).toHaveBeenCalledTimes(2);
    expect(detail.mock.calls.map(call => call[0])).toEqual(['1', '2']);
  });
  it('does not treat an unavailable or unsafe source as playable', async () => {
    await expect(resolveCinemaSelection(items, () => undefined, vi.fn())).rejects.toThrow('未找到可播放');
    await expect(resolveCinemaSelection(items, () => source, vi.fn().mockResolvedValue({ episodes: ['javascript:alert(1)'] }))).rejects.toThrow('未找到可播放');
  });
  it('stops on authentication failure instead of silently trying more sources', async () => {
    const detail = vi.fn().mockRejectedValue(new CinemaRequestError(401, '需要登录'));
    await expect(resolveCinemaSelection(items, () => source, detail)).rejects.toMatchObject({ status: 401 });
    expect(detail).toHaveBeenCalledTimes(1);
  });
  it('cancels before allocating any room', async () => {
    const controller = new AbortController(); controller.abort();
    const detail = vi.fn();
    await expect(resolveCinemaSelection(items, () => source, detail, controller.signal)).rejects.toThrow();
    expect(detail).not.toHaveBeenCalled();
  });
});
describe('direct room launch', () => {
  it('creates a room with media in one request and persists its playlist', async () => {
    const fetcher = vi.fn().mockResolvedValue(json(result)); vi.stubGlobal('fetch', fetcher);
    await launchCinema(selection);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ action: 'create', media: selectionMedia(selection) });
    expect(JSON.parse(storage.get(CINEMA_SESSION)!)).toEqual(session);
    expect(JSON.parse(storage.get(CINEMA_PLAYLIST)!)).toMatchObject({ roomId: session.roomId, episodes: selection.episodes });
  });
  it('reuses the existing host room using the server role, not the stored role', async () => {
    storage.set(CINEMA_SESSION, JSON.stringify({ ...session, role: 'guest' }));
    const fetcher = vi.fn().mockResolvedValueOnce(json({ role: 'host' })).mockResolvedValueOnce(json(result.snapshot)); vi.stubGlobal('fetch', fetcher);
    await launchCinema(selection);
    const bodies = fetcher.mock.calls.map(call => JSON.parse(call[1].body));
    expect(bodies.map(body => body.action)).toEqual(['sync', 'control']);
    expect(bodies[1]).toMatchObject({ roomId: session.roomId, op: 'media', media: selectionMedia(selection) });
    expect(JSON.parse(storage.get(CINEMA_SESSION)!).role).toBe('host');
  });
  it('does not change another host room when the visitor was a guest', async () => {
    storage.set(CINEMA_SESSION, JSON.stringify({ ...session, role: 'host' }));
    const fetcher = vi.fn().mockResolvedValueOnce(json({ role: 'guest' })).mockResolvedValueOnce(json(result)).mockResolvedValue(json({ closed: false })); vi.stubGlobal('fetch', fetcher);
    await launchCinema(selection);
    expect(fetcher.mock.calls.map(call => JSON.parse(call[1].body).action)).toEqual(['sync', 'create', 'leave']);
  });
  it('recovers an expired room with a new media-loaded room', async () => {
    storage.set(CINEMA_SESSION, JSON.stringify(session));
    const fetcher = vi.fn().mockResolvedValueOnce(json({ error: '已过期' }, 410)).mockResolvedValueOnce(json(result)); vi.stubGlobal('fetch', fetcher);
    await launchCinema(selection);
    expect(JSON.parse(fetcher.mock.calls[1][1].body).action).toBe('create');
  });
  it('does not duplicate rooms on ambiguous network failures', async () => {
    storage.set(CINEMA_SESSION, JSON.stringify(session));
    const fetcher = vi.fn().mockRejectedValue(new TypeError('network unavailable')); vi.stubGlobal('fetch', fetcher);
    await expect(launchCinema(selection)).rejects.toThrow('network unavailable');
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('does not persist a room when the server rejects its media', async () => {
    const fetcher = vi.fn().mockResolvedValue(json({ error: '私网地址被拒绝' }, 400)); vi.stubGlobal('fetch', fetcher);
    await expect(launchCinema(selection)).rejects.toMatchObject({ status: 400 });
    expect(storage.size).toBe(0);
  });
});
