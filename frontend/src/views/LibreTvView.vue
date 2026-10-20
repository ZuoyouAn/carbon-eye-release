<template>
  <main class="content-page cinema-page">
    <section class="cinema-hero panel">
      <RouterLink class="back-button" to="/projects">返回项目</RouterLink>
      <p class="eyebrow">SPACE CINEMA · POWERED BY LIBRETV</p>
      <h1>给自己一点<br />好好观看的时间。</h1>
      <p class="cinema-lead">影视搜索、直播与续播记录，收进一个独立的影音空间。保留 LibreTV 的完整播放器，不挤在小窗里。</p>
      <div class="cinema-actions">
        <a class="cinema-primary" :href="serviceUrl" target="_blank" rel="noopener noreferrer">打开 LibreTV <span aria-hidden="true">↗</span></a>
        <a class="text-button" :href="`${serviceUrl}/live`" target="_blank" rel="noopener noreferrer">进入直播 / IPTV ↗</a>
      </div>
      <p class="cinema-note">将在新标签页打开独立服务，需要影音访问密码；与本站账号登录分开。免费实例休眠后，首次打开可能需要等待约一分钟。</p>
      <div class="cinema-art" aria-hidden="true"><div class="cinema-screen"><span>SPACE</span><i>▶</i><small>YOUR LITTLE CINEMA</small></div><div class="cinema-glow"></div></div>
    </section>
    <section class="cinema-features" aria-label="影音功能">
      <article v-for="item in features" :key="item.title" class="panel"><span class="cinema-number">{{ item.number }}</span><h2>{{ item.title }}</h2><p>{{ item.text }}</p></article>
    </section>
    <section class="panel cinema-guide">
      <div><p class="eyebrow">QUICK START</p><h2>第一次使用</h2></div>
      <ol><li>打开 LibreTV，用管理员提供的独立访问密码验证。</li><li>进入设置 → 源管理，添加你有权使用的点播接口或 M3U 直播订阅。</li><li>勾选点播源后搜索；或进入直播页选择频道。可调整主题、倍速、字幕及连播设置。</li></ol>
      <p>不会迁移本机私密配置或预置未经授权的影视源。无数据源时搜索为空属于正常现象；数据源失效、区域限制和编码不支持也会影响播放。</p>
    </section>
    <section class="panel cinema-guide"><h2>数据与开源</h2><p>历史、收藏与观看进度存于影音服务域名下的本机浏览器，不与本站账号云同步。搜索和部分播放请求经过服务端代理，直连播放或封面仍可能访问第三方服务；不要在源地址中填写敏感凭据，也不要公开发布含私密地址的源列表。</p><p>LibreTV 使用 AGPL-3.0-or-later。本站提供的是独立应用入口，不托管影视内容，也不保证所有第三方源可用。</p><div class="cinema-links"><a :href="sourceUrl" target="_blank" rel="noopener noreferrer">本部署完整源码 ↗</a><a href="https://github.com/LibreSpark/LibreTV" target="_blank" rel="noopener noreferrer">上游 LibreTV ↗</a></div></section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'
const serviceUrl = 'https://zuoyou-space-libretv.onrender.com'
const sourceUrl = 'https://github.com/ZuoyouAn/carbon-eye-release/tree/main/apps/libretv'
const features = [
  { number: '01', title: '聚合搜索', text: '多源并行搜索，同名影片合并展示；失败的源不会阻断其他结果。' },
  { number: '02', title: '完整播放器', text: 'HLS 播放、倍速、快捷键、自动连播、换源测速与进度续播。' },
  { number: '03', title: '直播与订阅', text: 'M3U 频道分组、收藏与 XMLTV 节目单；保留源管理、探活及配置导入导出。' },
]
</script>

<style scoped>
.cinema-page{max-width:1160px;margin:auto}.cinema-hero{position:relative;overflow:hidden;min-height:480px;padding:40px;background:linear-gradient(120deg,#f8faff,#eef1fb);isolation:isolate}.cinema-hero .eyebrow{margin-top:36px;color:#536b9b}.cinema-hero h1{font-size:clamp(36px,5vw,58px);letter-spacing:-.055em;line-height:1.15;max-width:600px;margin:16px 0 24px}.cinema-lead{font-size:18px;line-height:1.85;max-width:520px;color:#526075}.cinema-actions{display:flex;align-items:center;gap:24px;flex-wrap:wrap;margin:30px 0 18px}.cinema-primary{display:inline-flex;gap:24px;padding:14px 23px;border-radius:100px;background:#315bba;color:white;font-weight:600;text-decoration:none}.cinema-primary:hover{background:#254b9e}.cinema-primary:focus-visible{outline:3px solid #859cdf;outline-offset:4px}.cinema-note{font-size:14px;line-height:1.8;color:#637186;max-width:480px}.cinema-art{position:absolute;width:320px;height:300px;right:35px;top:130px;z-index:-1;transform:rotate(-7deg)}.cinema-screen{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;height:230px;background:linear-gradient(145deg,#8098ce,#c5d1f1);border:9px solid #e6eaf4;border-radius:25px;box-shadow:0 30px 70px #5876b52b;color:white;letter-spacing:.3em}.cinema-screen span{font-size:32px;font-weight:600}.cinema-screen i{font-size:38px;font-style:normal}.cinema-screen small{font-size:10px}.cinema-glow{height:20px;width:70%;margin:22px auto;background:#8a9fc0;filter:blur(20px);opacity:.3}.cinema-features{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:22px 0}.cinema-features .panel{padding:26px}.cinema-number{font-size:14px;letter-spacing:.15em;color:#5772aa}.cinema-features h2,.cinema-guide h2{font-size:23px;margin:16px 0}.cinema-features p,.cinema-guide p,.cinema-guide li{font-size:16px;line-height:1.85;color:#586376}.cinema-guide{padding:30px;margin-bottom:20px}.cinema-guide li{padding:6px 0}.cinema-links{display:flex;gap:24px;flex-wrap:wrap}.cinema-links a{color:#315bba}@media(max-width:1050px){.cinema-art{opacity:.3;right:-100px}.cinema-lead,.cinema-note{max-width:600px}}@media(max-width:700px){.cinema-hero{padding:25px;min-height:auto}.cinema-art{display:none}.cinema-features{grid-template-columns:1fr}.cinema-guide{padding:24px}.cinema-actions{gap:18px}.cinema-hero h1{font-size:39px}}
</style>
<style scoped>
.cinema-hero > .eyebrow { display: block; margin-top: 28px; }
</style>
