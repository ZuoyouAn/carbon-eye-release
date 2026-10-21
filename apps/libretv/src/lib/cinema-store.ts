import { createHash, randomBytes } from 'node:crypto';
import type { CinemaMedia, CinemaMessage, CinemaSession, CinemaSnapshot } from './cinema-sync';

const HOST_GRACE = 20_000;
const MAX_MEMBERS = 8;
interface Member { nickname: string; host: boolean; seen: number; lastCommand: number; messages: number[] }
interface Room {
  id: string; name: string; created: number; touched: number; members: Map<string, Member>;
  media: CinemaMedia | null; position: number; playing: boolean; rate: number; anchor: number;
  revision: number; sequence: number; lastSequence: number; messages: CinemaMessage[];
}
export class CinemaError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
function digest(token: string) { return createHash('sha256').update(token).digest('hex'); }
function label(value: unknown, fallback: string, max: number) {
  if (typeof value !== 'string') return fallback;
  return value.replace(/[\u0000-\u001f\u007f]/g, '').trim().slice(0, max) || fallback;
}
export function validateMedia(input: unknown): CinemaMedia {
  if (!input || typeof input !== 'object') throw new CinemaError(400, '请输入播放地址');
  const media = input as Record<string, unknown>;
  if (typeof media.url !== 'string' || media.url.length > 2048) throw new CinemaError(400, '播放地址无效');
  let url: URL;
  try { url = new URL(media.url); } catch { throw new CinemaError(400, '播放地址无效'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new CinemaError(400, '仅支持不含账号密码的公网 HTTP(S) 地址');
  return { url: url.href, title: label(media.title, '一起看的影片', 100) };
}
export class CinemaStore {
  private rooms = new Map<string, Room>();
  constructor(private now = () => Date.now()) {}
  private sweep() {
    const now = this.now();
    for (const [id, room] of this.rooms) {
      if (now - room.created > 8 * 3600_000 || now - room.touched > 2 * 3600_000) this.rooms.delete(id);
    }
  }
  private locate(id: string) {
    this.sweep();
    const room = this.rooms.get(id);
    if (!room) throw new CinemaError(410, '房间已结束或过期，请重新创建');
    const host = [...room.members.values()].find(m => m.host);
    if (room.playing && host && this.now() - host.seen > HOST_GRACE) {
      room.position = this.position(room, host.seen + HOST_GRACE);
      room.anchor = this.now(); room.playing = false; room.revision++;
    }
    return room;
  }
  private access(id: string, token: string) {
    if (typeof token !== 'string' || token.length < 20 || token.length > 128) throw new CinemaError(403, '房间凭证无效');
    const room = this.locate(id);
    const member = room.members.get(digest(token));
    if (!member) throw new CinemaError(403, '你不是这个房间的成员');
    member.seen = this.now(); room.touched = this.now();
    return { room, member };
  }
  private position(room: Room, at = this.now()) {
    return Math.max(0, room.position + (room.playing ? Math.max(0, at - room.anchor) / 1000 * room.rate : 0));
  }
  private addMember(room: Room, nickname: unknown, host: boolean): CinemaSession {
    if (room.members.size >= MAX_MEMBERS) throw new CinemaError(409, '房间最多 8 人');
    const token = randomBytes(24).toString('base64url');
    room.members.set(digest(token), { nickname: label(nickname, host ? '房主' : '观众', 20), host, seen: this.now(), lastCommand: -Infinity, messages: [] });
    return { roomId: room.id, memberToken: token, role: host ? 'host' : 'guest' };
  }
  create(name: unknown, nickname: unknown) {
    this.sweep();
    if (this.rooms.size >= 20) throw new CinemaError(429, '当前放映厅已满，请稍后再试');
    const id = randomBytes(8).toString('hex');
    const room: Room = { id, name: label(name, '一起看一部电影', 40), created: this.now(), touched: this.now(), members: new Map(), media: null, position: 0, playing: false, rate: 1, anchor: this.now(), revision: 0, sequence: 0, lastSequence: -1, messages: [] };
    const session = this.addMember(room, nickname, true); this.rooms.set(id, room);
    return { session, snapshot: this.sync(id, session.memberToken) };
  }
  join(id: string, nickname: unknown) {
    const room = this.locate(id);
    // Abandoned guests do not permanently consume a slot; the host is never replaced.
    for (const [key, member] of room.members) if (!member.host && this.now() - member.seen > 90_000) room.members.delete(key);
    const session = this.addMember(room, nickname, false);
    return { session, snapshot: this.sync(id, session.memberToken) };
  }
  sync(id: string, token: string, after = 0): CinemaSnapshot {
    const { room, member } = this.access(id, token);
    const host = [...room.members.values()].find(m => m.host)!;
    return {
      roomId: room.id, name: room.name, role: member.host ? 'host' : 'guest', serverTime: this.now(), hostOnline: this.now() - host.seen <= HOST_GRACE,
      playback: { media: room.media, position: this.position(room), playing: room.playing, rate: room.rate, revision: room.revision },
      members: [...room.members.values()].map(m => ({ nickname: m.nickname, host: m.host, online: this.now() - m.seen <= HOST_GRACE })),
      messages: room.messages.filter(m => m.id > after).slice(-40), cursor: room.sequence,
    };
  }
  control(id: string, token: string, input: Record<string, unknown>) {
    const { room, member } = this.access(id, token);
    if (!member.host) throw new CinemaError(403, '只有房主可以改变播放状态');
    const sequence = input.sequence;
    if (typeof sequence !== 'number' || !Number.isSafeInteger(sequence) || sequence < 0) throw new CinemaError(400, '控制序号无效');
    if (sequence <= room.lastSequence) throw new CinemaError(409, '过期的播放指令已拒绝');
    if (this.now() - member.lastCommand < 100) throw new CinemaError(429, '操作过快，请稍后重试');
    const op = input.op;
    if (!['media', 'play', 'pause', 'seek', 'rate'].includes(String(op))) throw new CinemaError(400, '播放指令无效');
    if (op === 'media') {
      room.media = validateMedia(input.media); room.position = 0; room.playing = false; room.rate = 1;
    } else {
      if (!room.media) throw new CinemaError(400, '请先选择影片');
      const position = input.position;
      if (typeof position !== 'number' || !Number.isFinite(position) || position < 0 || position > 7 * 86400) throw new CinemaError(400, '播放位置无效');
      if (op === 'rate' && (typeof input.rate !== 'number' || !Number.isFinite(input.rate) || input.rate < .25 || input.rate > 2)) throw new CinemaError(400, '播放速度范围为 0.25–2 倍');
      room.position = position;
      if (op === 'play') room.playing = true;
      if (op === 'pause') room.playing = false;
      if (op === 'rate') room.rate = Number(input.rate);
    }
    room.anchor = this.now(); room.lastSequence = sequence; member.lastCommand = this.now(); room.revision++;
    return this.sync(id, token);
  }
  chat(id: string, token: string, text: unknown) {
    const { room, member } = this.access(id, token);
    if (typeof text !== 'string' || !text.trim() || text.length > 300) throw new CinemaError(400, '评论需要 1–300 个字符');
    member.messages = member.messages.filter(at => this.now() - at < 10_000);
    if (member.messages.length >= 6) throw new CinemaError(429, '评论太快，请稍后再发');
    member.messages.push(this.now());
    room.messages.push({ id: ++room.sequence, nickname: member.nickname, host: member.host, text: text.trim(), at: this.now() });
    room.messages = room.messages.slice(-80);
    // Include recent peer messages too: an acknowledgement must not advance the
    // client's cursor beyond messages it has not received yet.
    return this.sync(id, token);
  }
  leave(id: string, token: string) {
    const { room, member } = this.access(id, token);
    if (member.host) this.rooms.delete(id); else room.members.delete(digest(token));
    return { closed: member.host };
  }
}
const processGlobal = globalThis as typeof globalThis & { spaceCinema?: CinemaStore };
export const cinemaStore = processGlobal.spaceCinema ??= new CinemaStore();
