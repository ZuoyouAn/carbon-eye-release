<template>
  <main class="content-page cinema-page">
    <section class="cinema-hero panel">
      <RouterLink class="back-button" to="/projects">返回项目</RouterLink>
      <p class="eyebrow">左右大人服务 · SPACE CINEMA</p>
      <h1>给自己一点<br />好好观看的时间。</h1>
      <p class="cinema-lead">电影、AI短剧，还有与你一起观看的人。收进左右大人服务，异地也能一起看、一起聊。</p>
      <div class="cinema-actions">
        <a v-if="deploymentReady" class="cinema-primary" :href="serviceUrl" target="_blank" rel="noopener noreferrer">打开左右大人服务 <span aria-hidden="true">↗</span></a>
        <button v-else class="cinema-primary" type="button" disabled>等待服务部署</button>
        <a v-if="deploymentReady" class="text-button" :href="`${serviceUrl}/live`" target="_blank" rel="noopener noreferrer">进入直播 / IPTV ↗</a>
        <a v-if="deploymentReady" class="text-button" :href="`${serviceUrl}/cinema`" target="_blank" rel="noopener noreferrer">一起看 · 放映厅 ↗</a>
        <a v-if="deploymentReady" class="text-button" :href="`${serviceUrl}/ai-drama`" target="_blank" rel="noopener noreferrer">发现 AI短剧 ↗</a>
      </div>
      <p v-if="!deploymentReady" class="cinema-note" role="status">独立影音服务正在维护，暂时不能在线搜索或播放。请稍后重试。</p>
      <p class="cinema-note">将在新标签页打开独立服务，需要影音访问密码；与本站账号登录分开。免费实例休眠后，首次打开可能需要等待约一分钟。</p>
      <div class="cinema-art" aria-hidden="true"><div class="cinema-screen"><span>SPACE</span><i>▶</i><small>YOUR LITTLE CINEMA</small></div><div class="cinema-glow"></div></div>
    </section>
    <section class="cinema-features" aria-label="影音功能">
      <article v-for="item in features" :key="item.title" class="panel"><span class="cinema-number">{{ item.number }}</span><h2>{{ item.title }}</h2><p>{{ item.text }}</p></article>
    </section>
    <section class="panel cinema-guide">
      <div><p class="eyebrow">QUICK START</p><h2>第一次使用</h2></div>
      <ol><li>打开左右大人服务，用管理员提供的独立访问密码验证。</li><li>已预置非凡、暴风、魔都、量子 4 个普通影视源，首次加载会自动勾选；可以直接输入片名搜索。</li><li>播放页点击「一起看」创建放映厅，分享邀请链接。朋友验证网站密码后加入，只有房主能播放、暂停和拖动；所有成员可以评论。</li><li>AI短剧页面提供站内关键词与官方平台搜索入口，不承诺第三方内容一定可播。如需补充有权使用的接口，进入设置 → 源管理。</li></ol>
      <p>只同步普通影视源地址，不迁移本机密码或私密配置。请只观看有权访问的内容；接口探活正常不保证所有影片可播，数据源失效、区域限制和编码不支持也会影响播放。</p>
    </section>
    <section class="panel cinema-guide"><h2>数据与开源</h2><p>历史、收藏与观看进度存于影音服务域名下的本机浏览器，不与本站账号云同步。搜索和部分播放请求经过服务端代理，直连播放或封面仍可能访问第三方服务；不要在源地址中填写敏感凭据，也不要公开发布含私密地址的源列表。</p><p>放映厅最多 8 人，评论和房间只保存在服务器内存中；服务重启或休眠会丢失，房主断线超过 20 秒自动暂停，房间最长保留 8 小时。它同步各设备的播放进度，不是屏幕直播，也不提供影片授权。</p><p>本服务基于 LibreTV，遵循 AGPL-3.0-or-later。保留上游署名并公开本部署完整源码，不托管影视内容，也不保证所有第三方源可用。</p><div class="cinema-links"><a :href="sourceUrl" target="_blank" rel="noopener noreferrer">本部署完整源码 ↗</a><a href="https://github.com/LibreSpark/LibreTV" target="_blank" rel="noopener noreferrer">上游 LibreTV ↗</a></div></section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'
// Switch only after the independent service is live and public login is verified.
const deploymentReady = true
const serviceUrl = 'https://zuoyou-space-libretv.onrender.com'
const sourceUrl = 'https://github.com/ZuoyouAn/carbon-eye-release/tree/main/apps/libretv'
const features = [
  { number: '01', title: '聚合搜索', text: '多源并行搜索，同名影片合并展示；失败的源不会阻断其他结果。' },
  { number: '02', title: '异地放映厅', text: '邀请朋友同步观看和评论。仅房主能拖动、暂停、调速和换片，成员保留音量与全屏。' },
  { number: '03', title: '发现 AI短剧', text: 'AI漫剧、AIGC短剧关键词与官方平台搜索入口；保留 HLS 点播与直播订阅。' },
]
</script>

<style scoped>
.cinema-page{max-width:1160px;margin:auto}.cinema-hero{position:relative;overflow:hidden;min-height:480px;padding:40px;background:linear-gradient(120deg,#f8faff,#eef1fb);isolation:isolate}.cinema-hero .eyebrow{margin-top:36px;color:#536b9b}.cinema-hero h1{font-size:clamp(36px,5vw,58px);letter-spacing:-.055em;line-height:1.15;max-width:600px;margin:16px 0 24px}.cinema-lead{font-size:18px;line-height:1.85;max-width:520px;color:#526075}.cinema-actions{display:flex;align-items:center;gap:24px;flex-wrap:wrap;margin:30px 0 18px}.cinema-primary{display:inline-flex;gap:24px;padding:14px 23px;border-radius:100px;background:#315bba;color:white;font-weight:600;text-decoration:none}.cinema-primary:hover{background:#254b9e}.cinema-primary:focus-visible{outline:3px solid #859cdf;outline-offset:4px}.cinema-note{font-size:14px;line-height:1.8;color:#637186;max-width:480px}.cinema-art{position:absolute;width:320px;height:300px;right:35px;top:130px;z-index:-1;transform:rotate(-7deg)}.cinema-screen{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;height:230px;background:linear-gradient(145deg,#8098ce,#c5d1f1);border:9px solid #e6eaf4;border-radius:25px;box-shadow:0 30px 70px #5876b52b;color:white;letter-spacing:.3em}.cinema-screen span{font-size:32px;font-weight:600}.cinema-screen i{font-size:38px;font-style:normal}.cinema-screen small{font-size:10px}.cinema-glow{height:20px;width:70%;margin:22px auto;background:#8a9fc0;filter:blur(20px);opacity:.3}.cinema-features{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:22px 0}.cinema-features .panel{padding:26px}.cinema-number{font-size:14px;letter-spacing:.15em;color:#5772aa}.cinema-features h2,.cinema-guide h2{font-size:23px;margin:16px 0}.cinema-features p,.cinema-guide p,.cinema-guide li{font-size:16px;line-height:1.85;color:#586376}.cinema-guide{padding:30px;margin-bottom:20px}.cinema-guide li{padding:6px 0}.cinema-links{display:flex;gap:24px;flex-wrap:wrap}.cinema-links a{color:#315bba}@media(max-width:1050px){.cinema-art{opacity:.3;right:-100px}.cinema-lead,.cinema-note{max-width:600px}}@media(max-width:700px){.cinema-hero{padding:25px;min-height:auto}.cinema-art{display:none}.cinema-features{grid-template-columns:1fr}.cinema-guide{padding:24px}.cinema-actions{gap:18px}.cinema-hero h1{font-size:39px}}
</style>
<style scoped>
.cinema-hero > .eyebrow { display: block; margin-top: 28px; }
.cinema-primary:disabled { opacity: .6; cursor: not-allowed; border: 0; font: inherit; }
</style>
