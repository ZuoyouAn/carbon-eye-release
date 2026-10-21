import { createHash } from 'node:crypto';
import { NextResponse } from 'next/server';
import { guardRequest } from '@/lib/api-guard';
import { CinemaError, cinemaStore, validateMedia } from '@/lib/cinema-store';
import { checkUpstreamAllowed } from '@/lib/ssrf';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const processGlobal = globalThis as typeof globalThis & { cinemaJoins?: Map<string, number[]> };
const joins = processGlobal.cinemaJoins ??= new Map<string, number[]>();
function rateJoin(req: Request) {
  const key = createHash('sha256').update(req.headers.get('cookie') || '').digest('hex');
  const now = Date.now();
  for (const [k, dates] of joins) if (!dates.length || now - dates[dates.length - 1] > 60_000) joins.delete(k);
  const recent = (joins.get(key) || []).filter(at => now - at < 60_000);
  if (recent.length >= 10 || (!joins.has(key) && joins.size >= 2000)) throw new CinemaError(429, '创建或加入过快，请一分钟后再试');
  joins.set(key, [...recent, now]);
}
async function readBody(req: Request): Promise<Record<string, unknown>> {
  if (!req.headers.get('content-type')?.startsWith('application/json')) throw new CinemaError(415, '请使用 JSON 请求');
  const reader = req.body?.getReader();
  if (!reader) throw new CinemaError(400, '请求内容为空');
  const chunks: Uint8Array[] = []; let length = 0;
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    length += value.byteLength;
    if (length > 16_384) { await reader.cancel(); throw new CinemaError(413, '请求内容过大'); }
    chunks.push(value);
  }
  try {
    const body: unknown = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error();
    return body as Record<string, unknown>;
  } catch { throw new CinemaError(400, '请求格式错误'); }
}
export async function POST(req: Request) {
  const guarded = guardRequest(req); if (guarded) return guarded;
  try {
    if (req.headers.get('sec-fetch-site') === 'cross-site') throw new CinemaError(403, '不允许跨站操作');
    const origin = req.headers.get('origin');
    if (origin && new URL(origin).host !== req.headers.get('host') && new URL(origin).host !== new URL(req.url).host) throw new CinemaError(403, '不允许跨站操作');
    const body = await readBody(req);
    const action = body.action;
    let result: unknown;
    if (action === 'create') { rateJoin(req); result = cinemaStore.create(body.name, body.nickname); }
    else {
      if (typeof body.roomId !== 'string' || !/^[a-f0-9]{16}$/.test(body.roomId)) throw new CinemaError(400, '房间码为 16 位字母数字');
      if (action === 'join') { rateJoin(req); result = cinemaStore.join(body.roomId, body.nickname); }
      else {
        if (typeof body.memberToken !== 'string') throw new CinemaError(403, '缺少房间凭证');
        if (action === 'control') {
          // Verify membership/host role before doing DNS or any network work.
          if (cinemaStore.sync(body.roomId, body.memberToken).role !== 'host') throw new CinemaError(403, '只有房主可以改变播放状态');
          if (body.op === 'media') {
            const media = validateMedia(body.media);
            const allowed = await checkUpstreamAllowed(media.url);
            if (!allowed.ok) throw new CinemaError(400, allowed.reason);
          }
          result = cinemaStore.control(body.roomId, body.memberToken, body);
        } else if (action === 'sync') {
          const after = typeof body.after === 'number' && Number.isSafeInteger(body.after) ? Math.max(0, body.after) : 0;
          result = cinemaStore.sync(body.roomId, body.memberToken, after);
        } else if (action === 'chat') result = cinemaStore.chat(body.roomId, body.memberToken, body.text);
        else if (action === 'leave') result = cinemaStore.leave(body.roomId, body.memberToken);
        else throw new CinemaError(400, '操作无效');
      }
    }
    return NextResponse.json(result, { headers: { 'Cache-Control': 'no-store' } });
  } catch (err) {
    const status = err instanceof CinemaError ? err.status : 400;
    return NextResponse.json({ error: err instanceof CinemaError ? err.message : '房间请求失败' }, { status, headers: { 'Cache-Control': 'no-store' } });
  }
}
