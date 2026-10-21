import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
const API = 'https://personal-website-carbon-eye-api.onrender.com/api/analytics/collect';
const SITE_ORIGIN = 'https://zuoyou-space-libretv.onrender.com';
export async function POST(req: Request) {
  if (req.headers.get('sec-fetch-site') === 'cross-site') return new NextResponse(null, { status: 403 });
  const origin = req.headers.get('origin');
  try {
    if (origin && new URL(origin).host !== req.headers.get('host') && new URL(origin).host !== new URL(req.url).host) return new NextResponse(null, { status: 403 });
  } catch { return new NextResponse(null, { status: 400 }); }
  const reader = req.body?.getReader();
  if (!reader) return new NextResponse(null, { status: 400 });
  let size = 0; const chunks: Uint8Array[] = [];
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    size += value.byteLength;
    if (size > 4096) { await reader.cancel(); return new NextResponse(null, { status: 413 }); }
    chunks.push(value);
  }
  try {
    const payload = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (!payload || payload.site !== 'video') return new NextResponse(null, { status: 400 });
    // Fixed destination only. Never forward cookies, bearer tokens, IPs or URLs.
    const response = await fetch(API, { method: 'POST', headers: {
      'Content-Type': 'application/json', Origin: SITE_ORIGIN,
      'User-Agent': req.headers.get('user-agent') || 'unknown',
      DNT: req.headers.get('dnt') || '0', 'Sec-GPC': req.headers.get('sec-gpc') || '0',
    }, body: JSON.stringify(payload), cache: 'no-store', signal: AbortSignal.timeout(60_000) });
    return new NextResponse(null, { status: response.status === 204 ? 204 : response.status >= 500 ? 503 : response.status, headers: { 'Cache-Control': 'no-store' } });
  } catch { return new NextResponse(null, { status: 503, headers: { 'Cache-Control': 'no-store' } }); }
}
