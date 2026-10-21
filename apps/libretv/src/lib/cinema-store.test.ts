import { describe, expect, it } from 'vitest';
import { CinemaStore, validateMedia } from './cinema-store';
import { clockOffset, desiredPosition } from './cinema-sync';

function fixture() {
  let now = 1000;
  const store = new CinemaStore(() => now);
  const host = store.create('测试放映厅', '房主昵称').session;
  const guest = store.join(host.roomId, '观众昵称').session;
  let sequence = 0;
  const control = (op: string, position = 0, extra: Record<string, unknown> = {}) => {
    now += 200;
    return store.control(host.roomId, host.memberToken, { op, position, sequence: ++sequence, ...extra });
  };
  return { store, host, guest, control, advance: (ms: number) => { now += ms; } };
}
const media = { url: 'https://example.com/demo.mp4', title: '合法测试视频' };

describe('cinema server authority', () => {
  it('issues independent opaque credentials and roles; invitation code is not a token', () => {
    const f = fixture();
    expect(f.host.role).toBe('host'); expect(f.guest.role).toBe('guest');
    expect(f.host.memberToken).not.toBe(f.guest.memberToken);
    expect(f.host.roomId).toMatch(/^[a-f0-9]{16}$/);
    const snap = f.store.sync(f.host.roomId, f.guest.memberToken);
    expect(JSON.stringify(snap)).not.toContain(f.host.memberToken);
    expect(JSON.stringify(snap)).not.toContain(f.guest.memberToken);
  });
  it.each(['media', 'play', 'pause', 'seek', 'rate'])('rejects guest %s even with a forged host role', op => {
    const f = fixture(); f.control('media', 0, { media });
    expect(() => f.store.control(f.host.roomId, f.guest.memberToken, { op, position: 500, media, rate: 2, role: 'host', sequence: 999 })).toThrow('只有房主');
    expect(f.store.sync(f.host.roomId, f.host.memberToken).playback.position).toBe(0);
  });
  it('computes a shared playing timeline and pauses at the host position', () => {
    const f = fixture(); f.control('media', 0, { media }); f.control('play', 12);
    f.advance(3500);
    expect(f.store.sync(f.host.roomId, f.guest.memberToken).playback.position).toBe(15.5);
    f.control('seek', 70); f.control('pause', 71); f.advance(2000);
    expect(f.store.sync(f.host.roomId, f.guest.memberToken).playback).toMatchObject({ playing: false, position: 71 });
  });
  it('applies rate changes to the server timeline', () => {
    const f = fixture(); f.control('media', 0, { media }); f.control('rate', 0, { rate: 2 }); f.control('play', 0); f.advance(1000);
    expect(f.store.sync(f.host.roomId, f.guest.memberToken).playback.position).toBe(2);
  });
  it('freezes when the host disappears; a guest heartbeat does not keep host authority alive', () => {
    const f = fixture(); f.control('media', 0, { media }); f.control('play', 10); f.advance(21_000);
    const guest = f.store.sync(f.host.roomId, f.guest.memberToken);
    expect(guest.hostOnline).toBe(false); expect(guest.playback.playing).toBe(false); expect(guest.playback.position).toBe(30);
    const reconnected = f.store.sync(f.host.roomId, f.host.memberToken);
    expect(reconnected.hostOnline).toBe(true); expect(reconnected.playback.playing).toBe(false);
  });
  it('refuses replayed commands and invalid positions without changing the timeline', () => {
    const f = fixture(); f.control('media', 0, { media });
    f.advance(200);
    expect(() => f.store.control(f.host.roomId, f.host.memberToken, { op: 'seek', position: 99, sequence: 1 })).toThrow('过期');
    expect(() => f.control('seek', NaN)).toThrow('播放位置');
    expect(() => f.control('seek', -3)).toThrow('播放位置');
    expect(() => f.control('rate', 3, { rate: 100 })).toThrow('播放速度');
  });
  it('keeps comments as text and uses server membership for author identity', () => {
    const f = fixture();
    const snap = f.store.chat(f.host.roomId, f.guest.memberToken, '<img src=x onerror=alert(1)>');
    expect(snap.messages[0]).toMatchObject({ nickname: '观众昵称', host: false, text: '<img src=x onerror=alert(1)>' });
    expect(f.store.sync(f.host.roomId, f.host.memberToken, snap.cursor).messages).toEqual([]);
    const reply = f.store.chat(f.host.roomId, f.host.memberToken, '收到');
    expect(reply.messages.map(message => message.text)).toEqual(['<img src=x onerror=alert(1)>', '收到']);
  });
  it('limits comments, member slots and expired guest credentials', () => {
    const f = fixture();
    for (let i = 0; i < 6; i++) f.store.chat(f.host.roomId, f.guest.memberToken, 'hello');
    expect(() => f.store.chat(f.host.roomId, f.guest.memberToken, 'spam')).toThrow('评论太快');
    for (let i = 0; i < 6; i++) f.store.join(f.host.roomId, '成员');
    expect(() => f.store.join(f.host.roomId, '第九人')).toThrow('最多 8 人');
    f.advance(91_000); expect(f.store.join(f.host.roomId, '新成员').session.role).toBe('guest');
    expect(() => f.store.sync(f.host.roomId, f.guest.memberToken)).toThrow('不是这个房间');
  });
  it('guest exit cannot close the host room; host exit closes it for everyone', () => {
    const f = fixture(); expect(f.store.leave(f.host.roomId, f.guest.memberToken).closed).toBe(false);
    expect(f.store.sync(f.host.roomId, f.host.memberToken).members).toHaveLength(1);
    expect(f.store.leave(f.host.roomId, f.host.memberToken).closed).toBe(true);
    expect(() => f.store.sync(f.host.roomId, f.host.memberToken)).toThrow('已结束');
  });
  it('rejects unknown/cross-room credentials and enforces room expiry', () => {
    const f = fixture(); const other = f.store.create('另一个房间', '另一个房主').session;
    expect(() => f.store.sync(f.host.roomId, other.memberToken)).toThrow('不是这个房间');
    expect(() => f.store.sync(f.host.roomId, 'x')).toThrow('凭证');
    f.advance(8 * 3600_000 + 1);
    expect(() => f.store.sync(f.host.roomId, f.host.memberToken)).toThrow('过期');
  });
  it('bounds active rooms', () => {
    const store = new CinemaStore();
    for (let i = 0; i < 20; i++) store.create('厅', '我');
    expect(() => store.create('满了', '我')).toThrow('已满');
  });
});
describe('cinema media and clock', () => {
  it.each(['javascript:alert(1)', 'file:///secret', 'https://name:password@example.com/video'])('rejects unsafe media %s', url => {
    expect(() => validateMedia({ url })).toThrow();
  });
  it('allows only bounded titles and preserves valid signed CDN URLs inside the private room', () => {
    const result = validateMedia({ url: 'https://example.com/demo.m3u8?expires=123', title: 'x'.repeat(200) });
    expect(result.title).toHaveLength(100); expect(result.url).toContain('expires=123');
  });
  it('accounts for different wall clocks and estimates elapsed playback', () => {
    const f = fixture(); f.control('media', 0, { media }); f.control('play', 10);
    const snap = f.store.sync(f.host.roomId, f.guest.memberToken);
    const offset = clockOffset(1_000_000, 1_000_200, snap.serverTime);
    expect(desiredPosition(snap, offset, 1_001_100)).toBeCloseTo(11, 3);
  });
});
