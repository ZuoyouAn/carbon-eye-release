'use client';

import { Header } from '@/components/header';
import { SiteFooter } from '@/components/site-footer';
import { AnalyticsPreference } from '@/components/traffic-tracker';

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-2xl w-full mx-auto px-4 py-10 space-y-8">
        <section>
          <h1 className="text-xl font-bold text-content mb-3">关于左右视频站</h1>
          <p className="text-sm text-muted leading-relaxed">
            基于 LibreTV，提供影视搜索、播放、直播和同步放映厅。
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-content mb-2.5">单人播放快捷键</h2>
          <ul className="text-sm text-muted space-y-1.5 list-disc list-inside">
            <li><code className="text-accent">空格</code> 播放 / 暂停</li>
            <li><code className="text-accent">←</code> / <code className="text-accent">→</code> 快退 / 快进 5 秒</li>
            <li><code className="text-accent">↑</code> / <code className="text-accent">↓</code> 音量调节</li>
            <li><code className="text-accent">F</code> 切换全屏</li>
            <li><code className="text-accent">Alt + ←/→</code> 上一集 / 下一集</li>
            <li>移动端长按视频可 3 倍速播放</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-content mb-2.5">隐私与数据</h2>
          <p className="text-sm text-muted leading-relaxed">
            历史与单人观看进度保存在本机浏览器。搜索和代理请求会发送到服务器及数据源。
            放映厅的播放地址、昵称和评论会提供给房间成员，重启或休眠后清除。请勿填写敏感地址或公开发布私密源配置。
          </p>
        </section>

        <AnalyticsPreference />
        <section>
          <h2 className="text-base font-semibold text-content mb-2.5">免责声明</h2>
          <p className="text-sm text-faint leading-relaxed">
            本项目不存储、不制作任何视频内容，仅提供第三方公开接口的聚合与播放能力。
            请仅使用有权访问的内容；第三方源不保证始终可用。
          </p>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
