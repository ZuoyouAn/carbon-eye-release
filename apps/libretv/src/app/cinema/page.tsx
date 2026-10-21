'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Header } from '@/components/header';
import { SiteFooter } from '@/components/site-footer';
import { useAuth } from '@/components/auth';
import { CinemaPlayer } from '@/components/cinema-player';
import { clockOffset, type CinemaSession, type CinemaSnapshot, type CinemaMessage } from '@/lib/cinema-sync';
import './cinema.css';

const STORAGE = 'space-cinema-session-v1';
class ApiFailure extends Error { constructor(public status: number, text: string) { super(text); } }
async function request<T>(body: Record<string, unknown>): Promise<T> {
  const response = await fetch('/api/cinema', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), cache: 'no-store', signal: AbortSignal.timeout(10_000) });
  const data = await response.json();
  if (!response.ok) throw new ApiFailure(response.status, data.error || '房间请求失败');
  return data as T;
}
export default function CinemaPage() {
  const { verified, openLogin } = useAuth();
  const [session, setSession] = useState<CinemaSession | null>(null), [snapshot, setSnapshot] = useState<CinemaSnapshot | null>(null);
  const [messages, setMessages] = useState<CinemaMessage[]>([]), [nickname, setNickname] = useState(''), [name, setName] = useState('今晚一起看');
  const [roomCode, setRoomCode] = useState(''), [mediaUrl, setMediaUrl] = useState(''), [title, setTitle] = useState('');
  const [comment, setComment] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false), [offset, setOffset] = useState(0);
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
      const picked = JSON.parse(sessionStorage.getItem('space-cinema-pick') || 'null');
      if (picked && typeof picked.url === 'string') { setMediaUrl(picked.url); setTitle(typeof picked.title === 'string' ? picked.title : ''); sessionStorage.removeItem('space-cinema-pick'); }
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
  function control(op: string, position = 0, rate?: number, explicit?: CinemaSession) {
    const member = explicit || active.current;
    if (!member || (state.current && state.current.role !== 'host')) return;
    const marker = generation.current;
    const body = { action: 'control', ...member, op, position, rate, media: op === 'media' ? { url: mediaUrl.trim(), title: title.trim() } : undefined, sequence: ++sequence.current };
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
      const result = await request<{ session: CinemaSession; snapshot: CinemaSnapshot }>({ action, name, nickname, roomId: roomCode.trim().toLowerCase() });
      activate(result.session, result.snapshot);
      if (action === 'create' && mediaUrl.trim()) control('media', 0, undefined, result.session);
    } catch (error) { failure(error); } finally { setBusy(false); }
  }
  async function leave() {
    if (!active.current) return;
    try { await request({ action: 'leave', ...active.current }); } catch { /* expired rooms can still be cleared locally */ }
    generation.current++; active.current = null; state.current = null; cursor.current = 0;
    setSession(null); setSnapshot(null); setMessages([]); sessionStorage.removeItem(STORAGE);
  }
  async function sendComment(event: React.FormEvent) {
    event.preventDefault(); const member = active.current;
    if (!member || !comment.trim()) return;
    setBusy(true);
    try { const next = await request<CinemaSnapshot>({ action: 'chat', ...member, text: comment.trim() }); accept(next); setComment(''); }
    catch (error) { failure(error); } finally { setBusy(false); }
  }
  return <div className="min-h-screen flex flex-col"><Header /><main className="cinema-workspace">
    <div className="cinema-intro"><p>左右大人服务 · PRIVATE SCREENING</p><h1>隔着距离，一起入戏。</h1><span>同步播放与评论 · 仅房主掌握进度</span></div>
    {!verified && <div className="cinema-alert">创建、加入与观看前都需验证本站访问密码。<button className="btn-primary" onClick={openLogin}>验证访问密码</button></div>}
    {notice && <p className="cinema-alert" role="status">{notice}<button onClick={() => setNotice('')}>关闭提示</button></p>}
    {!session ? <section className="cinema-entrance">
      <div className="cinema-card"><h2>创建你的放映厅</h2><label>你的昵称<input value={nickname} maxLength={20} placeholder="朋友们怎么称呼你" onChange={e => setNickname(e.target.value)} /></label><label>放映厅名称<input value={name} maxLength={40} onChange={e => setName(e.target.value)} /></label><button className="btn-primary" disabled={busy} onClick={() => void enter('create')}>创建放映厅</button></div>
      <div className="cinema-card"><h2>赴一场电影之约</h2><label>房间码<input value={roomCode} maxLength={16} placeholder="输入朋友发来的 16 位房间码" onChange={e => setRoomCode(e.target.value)} /></label><p>加入时沿用左侧填写的昵称。邀请链接不包含房主控制凭证。</p><button className="btn-primary" disabled={busy || !roomCode.trim()} onClick={() => void enter('join')}>加入放映厅</button></div>
    </section> : !snapshot ? <p className="cinema-card">正在恢复房间… <button onClick={() => void leave()}>清除本机房间记录</button></p> : <>
      <section className="cinema-room-heading"><div><h2>{snapshot.name}</h2><p>{snapshot.playback.media?.title || '等待选片'} · {snapshot.role === 'host' ? '你是房主' : '你是观众'} · {snapshot.hostOnline ? '房主在线' : '房主已断线，播放暂停'}</p></div><div className="cinema-room-buttons"><code>{snapshot.roomId}</code><button className="btn-ghost" onClick={() => {
        const invite = `${location.origin}/cinema?room=${snapshot.roomId}`;
        void navigator.clipboard.writeText(invite).then(() => setNotice('邀请链接已复制，朋友仍需验证网站密码')).catch(() => setNotice('无法复制，请手动分享房间码：' + snapshot.roomId));
      }}>复制邀请</button><button className="btn-ghost" onClick={() => void leave()}>{snapshot.role === 'host' ? '结束放映' : '离开放映'}</button></div></section>
      <div className="cinema-room-grid"><section><CinemaPlayer snapshot={snapshot} offset={offset} command={control} />
        <div className="cinema-members">{snapshot.members.map((member, i) => <span key={i}>{member.host ? '♛ ' : '● '}{member.nickname} · {member.online ? '在线' : '暂离'}</span>)}</div>
        {snapshot.role === 'host' && <form className="cinema-card cinema-media-form" onSubmit={e => { e.preventDefault(); control('media'); }}><h3>房主选片</h3><label>影片名称<input value={title} maxLength={100} placeholder="今晚一起看的影片" onChange={e => setTitle(e.target.value)} /></label><label>点播地址<input value={mediaUrl} maxLength={2048} placeholder="你有权使用的 MP4 / M3U8 直链，不是视频网页地址" onChange={e => setMediaUrl(e.target.value)} /></label><button className="btn-primary" disabled={!mediaUrl.trim()}>载入影片并暂停等待</button><p>也可以先搜索影片，在原播放页点击「一起看」，将当前集带入这里。换片从 0 秒暂停开始。</p></form>}
      </section><aside className="cinema-card cinema-comments"><h2>边看边聊</h2><div className="cinema-message-list" role="log" aria-live="polite">{!messages.length && <p>第一句评论，就从你开始。</p>}{messages.map(message => <article key={message.id}><strong>{message.host ? '房主 · ' : ''}{message.nickname}</strong><time>{new Date(message.at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</time><p>{message.text}</p></article>)}</div><form onSubmit={sendComment}><label className="sr-only" htmlFor="cinema-comment">评论</label><textarea id="cinema-comment" value={comment} maxLength={300} rows={3} placeholder="说点什么，最多 300 字" onChange={e => setComment(e.target.value)} /><button className="btn-primary" disabled={busy || !comment.trim()}>发送评论</button></form></aside></div>
    </>}
    <section className="cinema-rules"><h2>入场须知</h2><p>最多 8 人；房主可播放、暂停、拖动、调速与换片。成员只能调整本机音量和全屏，伪造控制请求也会被服务端拒绝。网络同步存在延迟，不是逐帧直播；缓冲慢时请房主暂停等待。</p><p>支持有固定时长的 MP4 / HLS 点播，不支持 DRM、付费平台网页解析或直播时间轴。各设备独立拉取媒体，保留原有直连/代理策略；代理模式会产生服务器带宽消耗。</p><p>邀请加入者可见播放地址、昵称和本房间评论，请勿使用敏感地址。房主暂离超过 20 秒会暂停；关闭后台标签可能影响心跳。房主结束即关闭，房间最多保留 8 小时；服务重启或免费实例休眠会丢失房间，评论不永久保存。</p></section>
  </main><SiteFooter /></div>;
}
