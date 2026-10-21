'use client';
import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { createPageTracker, optedOut, setOptOut } from '../../../../shared/traffic-tracker.mjs';

export function TrafficTracker() {
  const path = usePathname();
  const tracker = useRef<ReturnType<typeof createPageTracker> | null>(null);
  useEffect(() => {
    tracker.current = createPageTracker({ site: 'video', endpoint: '/api/analytics', enabled: process.env.NODE_ENV === 'production' });
    return () => { tracker.current?.stop(); tracker.current = null; };
  }, []);
  useEffect(() => { if (path) tracker.current?.track(path); }, [path]);
  return null;
}

export function AnalyticsPreference() {
  const [disabled, setDisabled] = useState(false);
  useEffect(() => { setDisabled(optedOut()); }, []);
  return <section><h2 className="text-base font-semibold mb-3">匿名访问统计</h2><p className="text-sm text-muted leading-7 mb-3">记录页面浏览与匿名浏览器数，不保存 IP、账号、搜索词、房间码或播放链接。标识 30 天轮换，统计展示近 90 天；过期明细在下次统计请求时清理，仅管理员查看汇总。尊重浏览器 DNT / GPC 设置。</p><button className="btn-ghost btn-sm" onClick={() => { setOptOut(!disabled); setDisabled(!disabled); }}>{disabled ? '已关闭统计 · 点击允许' : '关闭本机访问统计'}</button></section>;
}
