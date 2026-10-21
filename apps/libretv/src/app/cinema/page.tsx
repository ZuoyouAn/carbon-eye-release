'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Header } from '@/components/header';
import { SiteFooter } from '@/components/site-footer';
import { useAuth } from '@/components/auth';
import { CinemaPlayer } from '@/components/cinema-player';
import { clockOffset, type CinemaSession, type CinemaSnapshot, type CinemaMessage, type CinemaMedia } from '@/lib/cinema-sync';
import { CINEMA_SESSION as STORAGE, CINEMA_PLAYLIST, cinemaRequest as request, CinemaRequestError as ApiFailure, selectionMedia, type CinemaSelection } from '@/lib/cinema-client';
import './cinema.css';

export default function CinemaPage() {
  const { verified, openLogin } = useAuth();
  const [session, setSession] = useState<CinemaSession | null>(null), [snapshot, setSnapshot] = useState<CinemaSnapshot | null>(null);
  const [messages, setMessages] = useState<CinemaMessage[]>([]), [nickname, setNickname] = useState(''), [name, setName] = useState('今晚一起看');
  const [roomCode, setRoomCode] = useState(''), [mediaUrl, setMediaUrl] = useState(''), [title, setTitle] = useState('');
  const [comment, setComment] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false), [offset, setOffset] = useState(0);
  const [playlist, setPlaylist] = useState<CinemaSelection | null>(null);
  const cursor = useRef(0), generation = useRef(0), active = useRef<CinemaSession | null>(null), state = useRef<CinemaSnapshot | null>(null);
  const sequence = useRef(Date.now() * 1000), queue = useRef(Promise.resolve()), rtt = useRef(Infinity);
  function failure(error: unknown) {
    setNotice(error instanceof Error ? error.message : '网络连接失败，请重试');
    if (error instanceof ApiFailure && error.status === 410) { active.current = null; setSession(null); setSnapshot(null); sessionStorage.removeItem(STORAGE); }
    if (error instanceof ApiFailure && error.status === 401) openLogin();
  }
  const accept = useCallback((next: CinemaSnapshot, sent?: number) => {
    if (!active.current || active.current.roomId !== next.roomId) return;
    if (state.current && next.playback.revision < state.current.playback.revision) return;
    state.current = next; setSnapshot(next);
    if (sent !== undefined) {
      const received = Date.now(), duration = received - sent;
      if (duration < rtt.current * 1.5 || !Number.isFinite(rtt.current)) { setOffset(clockOffset(sent, received, next.serverTime)); rtt.current = Math.min(rtt.current, duration); }
    }
    cursor.current = Math.max(cursor.current, next.cursor);
    setMessages(old => [...new Map([...old, ...next.messages].map(item => [item.id, item])).values()].sort((a, b) => a.id - b.id).slice(-80));
  }, []);
  function activate(value: CinemaSession, next: CinemaSnapshot) {
    active.current = value; state.current = null; cursor.current = 0; rtt.current = Infinity; generation.current++;
    setMessages([]); setSession(value); setNotice(''); setOffset(next.serverTime - Date.now()); sessionStorage.setItem(STORAGE, JSON.stringify(value)); accept(next);
  }
  useEffect(() => {
    try {
      const invite = new URLSearchParams(location.search).get('room') || '';
      setRoomCode(invite);
      const saved: CinemaSession | null = JSON.parse(sessionStorage.getItem(STORAGE) || 'null');
      if (saved && typeof saved.roomId === 'string' && typeof saved.memberToken === 'string' && (!invite || invite === saved.roomId)) { active.current = saved; setSession(saved); }
      const selected = JSON.parse(sessionStorage.getItem(CINEMA_PLAYLIST) || 'null');
      if (selected && saved && saved.roomId === selected.roomId && (!invite || invite === saved.roomId) && typeof selected.title === 'string' && Array.isArray(selected.episodes) && selected.episodes.every((url: unknown) => typeof url === 'string')) setPlaylist(selected);
    } catch { setNotice('本机房间记录不可用，可以重新创建或加入'); }
  }, []);
  useEffect(() => {
    if (!session || !verified) return;
    let cancelled = false, timer: ReturnType<typeof setTimeout>;
    const marker = generation.current;
    async function poll() {
      const sent = Date.now();
      try {
        const next = await request<CinemaSnapshot>({ action: 'sync', ...session, after: cursor.current });
        if (!cancelled && marker === generation.current) accept(next, sent);
      } catch (error) { if (!cancelled) failure(error); }
      if (!cancelled) timer = setTimeout(poll, 1500);
    }
    void poll();
    return () => { cancelled = true; clearTimeout(timer); };
    // Auth state restarts polling after the visitor verifies the site password.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, verified, accept]);
  function control(op: string, position = 0, rate?: number, explicit?: CinemaSession, media?: CinemaMedia) {
    const member = explicit || active.current;
    if (!member || (state.current && state.current.role !== 'host')) return;
    const marker = generation.current;
    const body = { action: 'control', ...member, op, position, rate, media: op === 'media' ? media || { url: mediaUrl.trim(), title: title.trim() } : undefined, sequence: ++sequence.current };
    queue.current = queue.current.then(async () => {
      if (marker !== generation.current || !active.current) return;
      await new Promise(resolve => setTimeout(resolve, 150));
      const sent = Date.now(); const next = await request<CinemaSnapshot>(body);
      if (marker === generation.current) accept(next, sent);
    }).catch(error => { if (marker === generation.current) failure(error); });
  }
  async function enter(action: 'create' | 'join') {
    if (!verified) { openLogin(); return; }
    setBusy(true); setNotice('');
    try {
      const result = await request<{ session: CinemaSession; snapshot: CinemaSnapshot }>({ action, name, nickname, roomId: roomCode.trim().toLowerCase(), ...(action === 'create' && mediaUrl.trim() ? { media: { url: mediaUrl.trim(), title: title.trim() } } : {}) });
      activate(result.session, result.snapshot);
      setPlaylist(null); sessionStorage.removeItem(CINEMA_PLAYLIST);
    } catch (error) { failure(error); } finally { setBusy(false); }
  }
  async function leave() {
    if (!active.current) return;
    try { await request({ action: 'leave', ...active.current }); } catch { /* expired rooms can still be cleared locally */ }
    generation.current++; active.current = null; state.current = null; cursor.current = 0;
    setSession(null); setSnapshot(null); setMessages([]); setPlaylist(null); sessionStorage.removeItem(STORAGE); sessionStorage.removeItem(CINEMA_PLAYLIST);
  }
  async function sendComment(event: React.FormEvent) {
    event.preventDefault(); const member = active.current;
    if (!member || !comment.trim()) return;
    setBusy(true);
    try { const next = await request<CinemaSnapshot>({ action: 'chat', ...member, text: comment.trim() }); accept(next); setComment(''); }
    catch (error) { failure(error); } finally { setBusy(false); }
  }
  return <div className="min-h-screen flex flex-col"><Header /><main className="cinema-workspace">
    <div className="cinema-intro"><p>左右视频站</p><h1>放映厅</h1><span>一起看，一起聊。</span></div>
    {!verified && <div className="cinema-alert">请先验证访问密码。<button className="btn-primary" onClick={openLogin}>验证密码</button></div>}
    {notice && <p className="cinema-alert" role="status">{notice}<button onClick={() => setNotice('')}>关闭提示</button></p>}
    {!session ? <section className="cinema-entrance">
      <div className="cinema-card"><h2>选一部影片</h2><p>在搜索结果旁点击「放映厅」，自动选片并创建房间。</p><Link className="btn-primary mt-5" href="/">搜索影片</Link>
        <details className="mt-6"><summary className="cursor-pointer text-sm text-muted">高级：手动播放地址</summary><label>房间名称<input value={name} maxLength={40} onChange={e => setName(e.target.value)} /></label><label>影片名称<input value={title} maxLength={100} placeholder="影片名称" onChange={e => setTitle(e.target.value)} /></label><label>播放地址<input value={mediaUrl} maxLength={2048} placeholder="MP4 / M3U8 直链" onChange={e => setMediaUrl(e.target.value)} /></label><button className="btn-ghost" disabled={busy || !mediaUrl.trim()} onClick={() => void enter('create')}>创建放映厅</button></details>
      </div>
      <div className="cinema-card"><h2>加入放映厅</h2><label>昵称<input value={nickname} maxLength={20} placeholder="你的昵称" onChange={e => setNickname(e.target.value)} /></label><label>房间码<input value={roomCode} maxLength={16} placeholder="16 位房间码" onChange={e => setRoomCode(e.target.value)} /></label><button className="btn-primary" disabled={busy || !roomCode.trim()} onClick={() => void enter('join')}>加入放映厅</button></div>
    </section> : !snapshot ? <p className="cinema-card">正在恢复房间… <button onClick={() => void leave()}>清除本机房间记录</button></p> : <>
      <section className="cinema-room-heading"><div><h2>{snapshot.name}</h2><p>{snapshot.playback.media?.title || '等待选片'} · {snapshot.role === 'host' ? '你是房主' : '你是观众'} · {snapshot.hostOnline ? '房主在线' : '房主已断线，播放暂停'}</p></div><div className="cinema-room-buttons"><code>{snapshot.roomId}</code><button className="btn-ghost" onClick={() => {
        const invite = `${location.origin}/cinema?room=${snapshot.roomId}`;
        void navigator.clipboard.writeText(invite).then(() => setNotice('邀请链接已复制')).catch(() => setNotice('请分享房间码：' + snapshot.roomId));
      }}>复制邀请</button><button className="btn-ghost" onClick={() => void leave()}>{snapshot.role === 'host' ? '结束放映' : '离开放映'}</button></div></section>
      <div className="cinema-room-grid"><section><CinemaPlayer snapshot={snapshot} offset={offset} command={control} />
        <div className="cinema-members">{snapshot.members.map((member, i) => <span key={i}>{member.host ? '♛ ' : '● '}{member.nickname} · {member.online ? '在线' : '暂离'}</span>)}</div>
        {snapshot.role === 'host' && <section className="cinema-card cinema-media-form"><div className="flex items-center justify-between gap-3"><h3>当前影片</h3><Link className="btn-ghost btn-sm" href="/">搜索换片</Link></div><p className="mt-3">{snapshot.playback.media?.title || '未选片'}</p>
          {playlist && playlist.episodes.length > 1 && playlist.episodes.includes(snapshot.playback.media?.url || '') && <label>切换集数<select aria-label="切换集数" className="input w-full" value={playlist.episodes.indexOf(snapshot.playback.media!.url)} onChange={e => {
            const next = { ...playlist, index: Number(e.target.value) }; setPlaylist(next);
            control('media', 0, undefined, undefined, selectionMedia(next));
            sessionStorage.setItem(CINEMA_PLAYLIST, JSON.stringify({ roomId: snapshot.roomId, ...next }));
          }}>{playlist.episodes.map((_url, index) => <option key={index} value={index}>第 {index + 1} 集</option>)}</select></label>}
          <details className="mt-4"><summary className="cursor-pointer text-sm text-muted">手动播放地址</summary><form onSubmit={e => { e.preventDefault(); control('media'); }}><label>影片名称<input value={title} maxLength={100} placeholder="影片名称" onChange={e => setTitle(e.target.value)} /></label><label>播放地址<input value={mediaUrl} maxLength={2048} placeholder="MP4 / M3U8 直链" onChange={e => setMediaUrl(e.target.value)} /></label><button className="btn-ghost" disabled={!mediaUrl.trim()}>载入影片</button></form></details>
        </section>}
      </section><aside className="cinema-card cinema-comments"><h2>评论</h2><div className="cinema-message-list" role="log" aria-live="polite">{!messages.length && <p>暂无评论</p>}{messages.map(message => <article key={message.id}><strong>{message.host ? '房主 · ' : ''}{message.nickname}</strong><time>{new Date(message.at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</time><p>{message.text}</p></article>)}</div><form onSubmit={sendComment}><label className="sr-only" htmlFor="cinema-comment">评论</label><textarea id="cinema-comment" value={comment} maxLength={300} rows={3} placeholder="发表评论，最多 300 字" onChange={e => setComment(e.target.value)} /><button className="btn-primary" disabled={busy || !comment.trim()}>发送评论</button></form></aside></div>
    </>}
    <section className="cinema-rules"><p>最多 8 人 · 房主控制播放 · 断线 20 秒后暂停 · 重启后房间清除</p><details><summary className="cursor-pointer text-sm text-muted">播放与隐私说明</summary><p>仅支持有权使用的 MP4 / HLS 点播。成员可见播放地址、昵称和评论，请勿使用敏感地址。网络缓冲可能产生不同步；房间最长保留 8 小时，评论不永久保存，代理播放消耗服务器带宽。</p></details></section>
  </main><SiteFooter /></div>;
}
