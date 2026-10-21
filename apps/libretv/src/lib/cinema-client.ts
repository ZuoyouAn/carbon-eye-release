import type { CinemaMedia, CinemaSession, CinemaSnapshot } from './cinema-sync';
import type { SearchResultItem, SourceConfig, VideoDetail } from './types';

export const CINEMA_SESSION = 'space-cinema-session-v1';
export const CINEMA_PLAYLIST = 'space-cinema-playlist-v1';
export interface CinemaSelection { title: string; episodes: string[]; index: number }
export class CinemaRequestError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function cinemaRequest<T>(body: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  const response = await fetch('/api/cinema', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    cache: 'no-store', signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15_000)]) : AbortSignal.timeout(15_000),
  });
  const data = await response.json();
  if (!response.ok) throw new CinemaRequestError(response.status, data.error || '房间请求失败');
  return data as T;
}
export function selectionMedia(selection: CinemaSelection): CinemaMedia {
  const index = Math.max(0, Math.min(selection.index, selection.episodes.length - 1));
  const url = selection.episodes[index];
  if (!url || !/^https?:\/\//i.test(url)) throw new Error('未找到可用播放地址，请尝试其他来源');
  return { url, title: selection.title + (selection.episodes.length > 1 ? ` · 第${index + 1}集` : '') };
}

/** Try the group's sources in display order; never substitute a different film. */
export async function resolveCinemaSelection(
  items: SearchResultItem[],
  sourceFor: (item: SearchResultItem) => SourceConfig | undefined,
  detailFor: (id: string, source: SourceConfig, signal?: AbortSignal) => Promise<VideoDetail>,
  signal?: AbortSignal,
): Promise<CinemaSelection> {
  for (const item of items.slice(0, 4)) {
    signal?.throwIfAborted();
    const source = sourceFor(item);
    if (!source) continue;
    try {
      const detail = await detailFor(item.vodId, source, signal);
      const selection = { title: item.name, episodes: detail.episodes, index: 0 };
      selectionMedia(selection);
      return selection;
    } catch (error) {
      signal?.throwIfAborted();
      if (error && typeof error === 'object' && 'status' in error && [401, 503].includes(Number(error.status))) throw error;
    }
  }
  throw new Error('未找到可播放的来源，请换一个来源或稍后再试');
}

/** Create with media atomically, or switch the existing host's room without losing guests. */
export async function launchCinema(selection: CinemaSelection, signal?: AbortSignal) {
  const media = selectionMedia(selection);
  let saved: CinemaSession | null = null;
  try {
    const value = JSON.parse(sessionStorage.getItem(CINEMA_SESSION) || 'null');
    if (value && /^[a-f0-9]{16}$/.test(value.roomId) && typeof value.memberToken === 'string') saved = value;
  } catch { /* ignore obsolete local records, not network failures */ }
  let previous: CinemaSnapshot | null = null;
  if (saved) {
    try { previous = await cinemaRequest<CinemaSnapshot>({ action: 'sync', ...saved }, signal); }
    catch (error) {
      if (!(error instanceof CinemaRequestError) || ![403, 410].includes(error.status)) throw error;
      saved = null;
    }
  }
  let result: { session: CinemaSession; snapshot: CinemaSnapshot };
  if (saved && previous?.role === 'host') {
    const snapshot = await cinemaRequest<CinemaSnapshot>({ action: 'control', ...saved, op: 'media', media, sequence: Date.now() * 1000 }, signal);
    result = { session: { ...saved, role: 'host' }, snapshot };
  } else {
    result = await cinemaRequest<typeof result>({ action: 'create', name: selection.title.slice(0, 40), nickname: '房主', media }, signal);
    if (saved && previous?.role === 'guest') {
      // Failure to remove a stale guest must not lose the newly created room.
      void cinemaRequest({ action: 'leave', ...saved }).catch(() => {});
    }
  }
  sessionStorage.setItem(CINEMA_SESSION, JSON.stringify(result.session));
  sessionStorage.setItem(CINEMA_PLAYLIST, JSON.stringify({ roomId: result.session.roomId, ...selection }));
  return result;
}
