import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export function GET() {
  const ready = Boolean(process.env.PASSWORD);
  return NextResponse.json(
    { status: ready ? 'ok' : 'setup-required', app: 'libretv', version: process.env.APP_VERSION },
    { status: ready ? 200 : 503, headers: { 'Cache-Control': 'no-store' } },
  );
}
