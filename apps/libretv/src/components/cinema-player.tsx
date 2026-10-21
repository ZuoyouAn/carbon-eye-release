'use client';
import { useEffect, useRef, useState } from 'react';
import type HlsType from 'hls.js';
import { desiredPosition, type CinemaSnapshot } from '@/lib/cinema-sync';

interface Props {
  snapshot: CinemaSnapshot; offset: number;
  command: (op: string, position: number, rate?: number) => void;
}
export function CinemaPlayer({ snapshot, offset, command }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const latest = useRef({ snapshot, offset, command }); latest.current = { snapshot, offset, command };
  const suppress = useRef(0), lastHostRevision = useRef(-1), playPending = useRef(false), blocked = useRef(false);
  const [gesture, setGesture] = useState(false), [error, setError] = useState(''), [proxy, setProxy] = useState(false);
  const url = snapshot.playback.media?.url;
  const host = snapshot.role === 'host';
  useEffect(() => { setProxy(false); }, [url]);
  useEffect(() => {
    const video = videoRef.current; if (!video || !url) return;
    let cancelled = false, hls: HlsType | null = null;
    setError(''); suppress.current = Date.now() + 1200; lastHostRevision.current = -1;
    const source = proxy ? '/api/proxy?url=' + encodeURIComponent(url) : url;
    const failed = () => {
      if (cancelled) return;
      if (!proxy) setProxy(true);
      else setError('媒体加载失败。请核对播放地址、源站权限与浏览器编码支持；普通网页链接不能直接播放。');
    };
    video.addEventListener('error', failed);
    if (/\.m3u8(?:[?#]|$)/i.test(url) && !video.canPlayType('application/vnd.apple.mpegurl')) {
      void import('hls.js').then(({ default: Hls }) => {
        if (cancelled) return;
        if (!Hls.isSupported()) { setError('浏览器不支持此 HLS 视频，请换用新版浏览器'); return; }
        hls = new Hls({ maxBufferLength: 20, maxMaxBufferLength: 40, backBufferLength: 15 });
        hls.on(Hls.Events.ERROR, (_event, data) => { if (data.fatal) failed(); });
        hls.loadSource(source); hls.attachMedia(video);
      }).catch(failed);
    } else { video.src = source; video.load(); }
    return () => { cancelled = true; video.removeEventListener('error', failed); hls?.destroy(); video.pause(); video.removeAttribute('src'); video.load(); };
  }, [url, proxy]);

  useEffect(() => {
    const timer = setInterval(() => {
      const video = videoRef.current, state = latest.current;
      if (!video || !state.snapshot.playback.media || video.readyState < 1) return;
      const isHost = state.snapshot.role === 'host';
      if (isHost && lastHostRevision.current === state.snapshot.playback.revision) return;
      if (isHost) lastHostRevision.current = state.snapshot.playback.revision;
      if (!Number.isFinite(video.duration)) return;
      const target = Math.min(Math.max(0, video.duration - .05), desiredPosition(state.snapshot, state.offset));
      const drift = target - video.currentTime;
      const baseRate = state.snapshot.playback.rate;
      suppress.current = Date.now() + 600;
      if (Math.abs(drift) > (state.snapshot.playback.playing ? .8 : .15)) video.currentTime = target;
      const rate = !isHost && state.snapshot.playback.playing && Math.abs(drift) > .15 && Math.abs(drift) <= .8 ? baseRate + Math.sign(drift) * .03 : baseRate;
      if (Math.abs(video.playbackRate - rate) > .005) video.playbackRate = Math.max(.25, Math.min(2, rate));
      if (!state.snapshot.playback.playing) { if (!video.paused) video.pause(); }
      else if (video.paused && !blocked.current && !playPending.current) {
        playPending.current = true;
        void video.play().catch(() => { blocked.current = true; setGesture(true); }).finally(() => { playPending.current = false; });
      }
    }, 250);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const timer = setInterval(() => {
      const video = videoRef.current, state = latest.current;
      if (state.snapshot.role === 'host' && video && video.readyState >= 2 && Date.now() > suppress.current) state.command('seek', video.currentTime);
    }, 5000);
    return () => clearInterval(timer);
  }, []);
  function event(op: string) {
    const video = videoRef.current;
    if (!video || !host) return;
    const current = latest.current;
    if (op === 'play' && current.snapshot.playback.playing) return;
    if (op === 'pause' && !current.snapshot.playback.playing) return;
    if (op === 'rate' && Math.abs(video.playbackRate - current.snapshot.playback.rate) < .01) return;
    if (op === 'seek' && Date.now() < suppress.current && Math.abs(video.currentTime - desiredPosition(current.snapshot, current.offset)) < .8) return;
    command(op, video.currentTime, video.playbackRate);
  }
  return <div ref={rootRef} className="cinema-video-shell">
    <video ref={videoRef} controls={host} playsInline preload="metadata" controlsList="nodownload noremoteplayback" disablePictureInPicture
      aria-label={host ? '房主播放器' : '成员同步播放器，进度由房主控制'}
      onPlay={() => event('play')} onPause={() => event('pause')} onSeeked={() => event('seek')} onRateChange={() => event('rate')} onEnded={() => event('pause')} />
    {!url && <p className="cinema-video-empty">等待房主选择影片</p>}
    {gesture && <button type="button" className="cinema-activate" onClick={() => {
      const video = videoRef.current; if (!video) return;
      suppress.current = Date.now() + 800; blocked.current = false;
      void video.play().then(() => { setGesture(false); if (!latest.current.snapshot.playback.playing) video.pause(); }).catch(() => setError('浏览器仍阻止播放，请再次点击或检查媒体加载状态'));
    }}>点击启用同步播放</button>}
    {error && <p role="alert" className="cinema-player-error">{error}</p>}
    <div className="cinema-local-controls">
      <span>{host ? '你是房主：使用播放器控制进度' : '进度锁定 · 仅房主可控制'}</span>
      <label>音量 <input aria-label="本机音量" type="range" min="0" max="1" step=".05" defaultValue="1" onChange={e => { if (videoRef.current) videoRef.current.volume = Number(e.target.value); }} /></label>
      <button type="button" onClick={() => { const v = videoRef.current; if (v) v.muted = !v.muted; }}>静音切换</button>
      <button type="button" onClick={() => { if (rootRef.current?.requestFullscreen) void rootRef.current.requestFullscreen().catch(() => setError('当前设备不支持此全屏方式')); }}>全屏</button>
    </div>
    {proxy && <p className="cinema-proxy-note">直连失败，已切换原有代理通道。代理播放会消耗服务器带宽，受免费额度限制。</p>}
  </div>;
}
