<template>
  <main class="content-page cinema-page">
    <section class="cinema-hero panel">
      <RouterLink class="back-button" to="/projects">返回项目</RouterLink>
      <p class="eyebrow">SPACE VIDEO</p>
      <h1>左右视频站</h1>
      <p class="cinema-lead">搜索影片，或邀请朋友一起看。</p>
      <div class="cinema-actions">
        <a v-if="deploymentReady" class="cinema-primary" :href="serviceUrl" target="_blank" rel="noopener noreferrer">搜索影片 <span aria-hidden="true">↗</span></a>
        <button v-else class="cinema-primary" type="button" disabled>等待服务部署</button>
        <a v-if="deploymentReady" class="text-button" :href="`${serviceUrl}/live`" target="_blank" rel="noopener noreferrer">进入直播 / IPTV ↗</a>
        <a v-if="deploymentReady" class="text-button" :href="`${serviceUrl}/cinema`" target="_blank" rel="noopener noreferrer">一起看 · 放映厅 ↗</a>
      </div>
      <p v-if="!deploymentReady" class="cinema-note" role="status">独立影音服务正在维护，暂时不能在线搜索或播放。请稍后重试。</p>
      <p class="cinema-note">需要影音访问密码。免费服务休眠后，首次打开可能较慢。</p>
      <div class="cinema-art" aria-hidden="true"><div class="cinema-screen"><span>SPACE</span><i>▶</i><small>YOUR LITTLE CINEMA</small></div><div class="cinema-glow"></div></div>
    </section>
    <section class="cinema-features" aria-label="影音功能">
      <article v-for="item in features" :key="item.title" class="panel"><span class="cinema-number">{{ item.number }}</span><h2>{{ item.title }}</h2><p>{{ item.text }}</p></article>
    </section>
    <section class="panel cinema-guide">
      <h2>一起看，只需三步</h2>
      <ol><li>搜索影片，点击结果旁的「放映厅」。</li><li>影片自动载入，分享邀请链接给朋友。</li><li>房主控制进度，所有成员都能评论。</li></ol>
    </section>
    <details class="panel cinema-guide"><summary>使用说明与开源许可</summary><p>放映厅最多 8 人，重启或休眠后清除；房主断线 20 秒后暂停，房间最多保留 8 小时。历史收藏存于本机，房间成员可见媒体地址和评论。请只使用有权访问的内容，不填写敏感地址；第三方源可能失效。</p><p>基于 LibreTV，遵循 AGPL-3.0-or-later。</p><div class="cinema-links"><a :href="sourceUrl" target="_blank" rel="noopener noreferrer">部署源码 ↗</a><a href="https://github.com/LibreSpark/LibreTV" target="_blank" rel="noopener noreferrer">上游 LibreTV ↗</a></div></details>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'
// Switch only after the independent service is live and public login is verified.
const deploymentReady = true
const serviceUrl = 'https://zuoyou-space-libretv.onrender.com'
const sourceUrl = 'https://github.com/ZuoyouAn/carbon-eye-release/tree/main/apps/libretv'
const features = [
  { number: '01', title: '影视搜索', text: '多源搜索，选集播放，保存本机观看进度。' },
  { number: '02', title: '同步放映厅', text: '影片旁一键开房，邀请朋友同步观看和评论。' },
  { number: '03', title: '直播', text: '频道订阅、分组、收藏与节目单。' },
]
</script>

<style scoped>
.cinema-page{max-width:1160px;margin:auto}.cinema-hero{position:relative;overflow:hidden;min-height:480px;padding:40px;background:linear-gradient(120deg,#f8faff,#eef1fb);isolation:isolate}.cinema-hero .eyebrow{margin-top:36px;color:#536b9b}.cinema-hero h1{font-size:clamp(36px,5vw,58px);letter-spacing:-.055em;line-height:1.15;max-width:600px;margin:16px 0 24px}.cinema-lead{font-size:18px;line-height:1.85;max-width:520px;color:#526075}.cinema-actions{display:flex;align-items:center;gap:24px;flex-wrap:wrap;margin:30px 0 18px}.cinema-primary{display:inline-flex;gap:24px;padding:14px 23px;border-radius:100px;background:#315bba;color:white;font-weight:600;text-decoration:none}.cinema-primary:hover{background:#254b9e}.cinema-primary:focus-visible{outline:3px solid #859cdf;outline-offset:4px}.cinema-note{font-size:14px;line-height:1.8;color:#637186;max-width:480px}.cinema-art{position:absolute;width:320px;height:300px;right:35px;top:130px;z-index:-1;transform:rotate(-7deg)}.cinema-screen{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;height:230px;background:linear-gradient(145deg,#8098ce,#c5d1f1);border:9px solid #e6eaf4;border-radius:25px;box-shadow:0 30px 70px #5876b52b;color:white;letter-spacing:.3em}.cinema-screen span{font-size:32px;font-weight:600}.cinema-screen i{font-size:38px;font-style:normal}.cinema-screen small{font-size:10px}.cinema-glow{height:20px;width:70%;margin:22px auto;background:#8a9fc0;filter:blur(20px);opacity:.3}.cinema-features{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:22px 0}.cinema-features .panel{padding:26px}.cinema-number{font-size:14px;letter-spacing:.15em;color:#5772aa}.cinema-features h2,.cinema-guide h2{font-size:23px;margin:16px 0}.cinema-features p,.cinema-guide p,.cinema-guide li{font-size:16px;line-height:1.85;color:#586376}.cinema-guide{padding:30px;margin-bottom:20px}.cinema-guide li{padding:6px 0}.cinema-links{display:flex;gap:24px;flex-wrap:wrap}.cinema-links a{color:#315bba}@media(max-width:1050px){.cinema-art{opacity:.3;right:-100px}.cinema-lead,.cinema-note{max-width:600px}}@media(max-width:700px){.cinema-hero{padding:25px;min-height:auto}.cinema-art{display:none}.cinema-features{grid-template-columns:1fr}.cinema-guide{padding:24px}.cinema-actions{gap:18px}.cinema-hero h1{font-size:39px}}
</style>
<style scoped>
.cinema-hero > .eyebrow { display: block; margin-top: 28px; }
.cinema-primary:disabled { opacity: .6; cursor: not-allowed; border: 0; font: inherit; }
</style>
