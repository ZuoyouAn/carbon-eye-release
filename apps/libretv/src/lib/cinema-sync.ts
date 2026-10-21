export interface CinemaMedia { url: string; title: string }
export interface CinemaPlayback { media: CinemaMedia | null; position: number; playing: boolean; rate: number; revision: number }
export interface CinemaMessage { id: number; nickname: string; text: string; at: number; host: boolean }
export interface CinemaSnapshot {
  roomId: string; name: string; role: 'host' | 'guest'; serverTime: number; hostOnline: boolean;
  playback: CinemaPlayback; members: { nickname: string; host: boolean; online: boolean }[];
  messages: CinemaMessage[]; cursor: number;
}
export interface CinemaSession { roomId: string; memberToken: string; role: 'host' | 'guest' }

/** Midpoint estimate avoids requiring the two computers' wall clocks to agree. */
export function clockOffset(sent: number, received: number, serverTime: number): number {
  return serverTime - (sent + received) / 2;
}
export function desiredPosition(snapshot: CinemaSnapshot, offset: number, now = Date.now()): number {
  const elapsed = snapshot.playback.playing ? Math.max(0, (now + offset - snapshot.serverTime) / 1000) : 0;
  return Math.max(0, snapshot.playback.position + elapsed * snapshot.playback.rate);
}
