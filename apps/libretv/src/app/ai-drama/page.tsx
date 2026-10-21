'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Header } from '@/components/header';
import { SiteFooter } from '@/components/site-footer';

export default function AiDramaPage() {
  const [query, setQuery] = useState('AI漫剧');
  const keyword = query.trim().slice(0, 100) || 'AI漫剧';
  return <div className="min-h-screen flex flex-col"><Header /><main className="max-w-5xl w-full mx-auto px-5 py-12 flex-1">
    <p className="text-xs tracking-widest text-muted mb-4">左右大人服务 · AI STORY DISCOVERY</p><h1 className="text-3xl sm:text-4xl font-semibold mb-5">去发现，下一部 AI 短剧。</h1>
    <p className="text-muted leading-8 max-w-3xl mb-7">这里提供关键词检索与官方平台搜索入口，不把未经核实的接口包装成免费片库，也不会解析付费或受保护的视频网页。是否可在放映厅播放，取决于你是否拥有可用的授权点播地址。</p>
    <label className="block text-sm mb-2" htmlFor="drama-keyword">搜索关键词</label><input id="drama-keyword" className="input w-full max-w-xl" value={query} maxLength={100} onChange={e => setQuery(e.target.value)} />
    <div className="flex gap-2 flex-wrap mt-4 mb-8">{['AI短剧', 'AI漫剧', 'AIGC短剧', '漫剧'].map(word => <button key={word} className="btn-ghost btn-sm" onClick={() => setQuery(word)}>{word}</button>)}</div>
    <div className="grid sm:grid-cols-3 gap-5">
      <article className="border border-line rounded-2xl bg-surface p-6"><h2 className="font-semibold text-xl mb-3">搜索已配置的源</h2><p className="text-sm text-muted leading-7 mb-5">沿用你勾选的普通影视源。关键词没有结果不代表平台接口故障，不保证源站收录 AI 短剧。</p><Link href={`/?s=${encodeURIComponent(keyword)}`} className="btn-primary">站内搜索</Link></article>
      <article className="border border-line rounded-2xl bg-surface p-6"><h2 className="font-semibold text-xl mb-3">哔哩哔哩搜索</h2><p className="text-sm text-muted leading-7 mb-5">在平台页面查看创作者发布内容。可能需要登录，内容和访问权限以平台为准。</p><a className="btn-primary" href={`https://search.bilibili.com/all?keyword=${encodeURIComponent(keyword)}`} target="_blank" rel="noopener noreferrer">去平台搜索 ↗</a></article>
      <article className="border border-line rounded-2xl bg-surface p-6"><h2 className="font-semibold text-xl mb-3">抖音搜索</h2><p className="text-sm text-muted leading-7 mb-5">使用官方站内搜索查找短剧、漫剧或创作者；只跳转搜索，不搬运视频或获取登录信息。</p><a className="btn-primary" href={`https://www.douyin.com/search/${encodeURIComponent(keyword)}`} target="_blank" rel="noopener noreferrer">去平台搜索 ↗</a></article>
    </div>
    <section className="border border-line rounded-2xl p-6 mt-6"><h2 className="text-xl font-semibold mb-3">已核对的官方线索</h2><p className="text-sm text-muted leading-8">快手官方曾介绍可灵参与 AIGC 短剧创作；其开放平台也提供短剧行业接入方案。但这些信息不等于面向任意网站开放免费播放 API，更不代表获得了内容转播授权。</p><div className="flex flex-wrap gap-5 text-sm text-accent mt-4"><a href="https://ir.kuaishou.com/zh-hans/news-releases/news-release-details/kling-ai-advances-20-era-empowering-everyone-tell-great-stories" target="_blank" rel="noopener noreferrer">可灵官方内容说明 ↗</a><a href="https://open.kuaishou.com/docs/new_industry_solution/vertical_industry_solution/shortplay_solution.html" target="_blank" rel="noopener noreferrer">快手短剧接入文档 ↗</a><Link href="/cinema">进入放映厅 →</Link></div></section>
  </main><SiteFooter /></div>;
}
