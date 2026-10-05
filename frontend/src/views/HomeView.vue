<template>
  <main>
    <section class="hero-section">
      <div class="hero-copy">
        <p class="eyebrow">ZUOYOU'S SPACE</p>
        <h1>好奇心，<br><span>值得一个空间。</span></h1>
        <p class="hero-description">写下所想，连接彼此，探索未曾到过的世界。<br>这是左右的 Space，也是想法开始生长的地方。</p>

        <div class="hero-actions">
          <RouterLink class="button button-primary" to="/articles">查看文章</RouterLink>
          <RouterLink class="button button-secondary" to="/human3">探索四维成长地图 →</RouterLink>
        </div>
      </div>

      <div class="hero-sculpture" aria-hidden="true"><div class="sculpture-shadow"></div><div class="sculpture-orbit"></div><span class="sculpture-chip one">想法 / STORIES</span><span class="sculpture-chip two">探索 / POSSIBILITIES ↗</span></div>
      <aside class="identity-panel home-identity" v-reveal>
        <div class="profile-head">
          <div class="avatar">左</div>
          <div>
            <p class="panel-label">左右 / 持续探索中</p><p class="panel-text">写下来，做出来，再向前一点。</p>
          </div>
        </div>

        <div class="stat-grid compact">
          <div>
            <strong>{{ stats?.novels ?? '—' }}</strong>
            <span>小说</span>
          </div>
          <div>
            <strong>{{ stats?.posts ?? '—' }}</strong>
            <span>帖子</span>
          </div>
          <div>
            <strong>{{ stats?.articles ?? '—' }}</strong>
            <span>文章</span>
          </div>
        </div>
        <p v-if="statsLoading" class="panel-label" role="status">正在读取内容统计…首次唤醒服务可能稍慢。</p>
        <p v-else-if="statsError" class="panel-label" role="status">统计暂不可用。<button class="text-button" @click="fetchStats">重试</button></p>

        <div class="quote-widget">
          <div class="quote-heading">
            <span>范哥经典语录</span>
            <small>yname: fcx</small>
          </div>

          <p v-if="quoteLoading" class="quote-content">正在读取语录...</p>
          <p v-else-if="quoteError" class="quote-content muted">{{ quoteError }}</p>
          <blockquote v-else-if="quote" class="quote-content">“{{ quote.content }}”</blockquote>
          <p v-else class="quote-content muted">暂无语录。</p>

          <div class="quote-actions">
            <button type="button" class="mini-button" :disabled="quoteLoading" @click="fetchQuote">
              换一句
            </button>
            <button type="button" class="mini-button" :disabled="!quote || quoteLoading || Boolean(quoteError)" @click="copyQuote">
              复制
            </button>
          </div>
        </div>
      </aside>
    </section>

    <section class="section">
      <div class="home-featured">
        <article class="showcase-card green" v-reveal><p class="eyebrow">SPACE ARCADE · BASE SURVIVAL</p><h2>白天，把家建好。<br>夜晚，让灯亮着。</h2><p>采集木材，搭建围墙与炮塔，安排供电和补给。守住三夜，等到救援。</p><RouterLink class="text-button" to="/wasteland">建立余烬营地 ↗</RouterLink><span class="showcase-symbol" aria-hidden="true">⌁</span></article>
        <article class="showcase-card" v-reveal><p class="eyebrow">HUMAN 3.0 · REFLECTION</p><h2>更了解自己，<br>从一次停顿开始。</h2><p>四个生活维度，二十四道问题。不是一个标签，而是下一步行动的起点。</p><RouterLink class="text-button" to="/human3">探索成长地图 ↗</RouterLink><span class="showcase-symbol" aria-hidden="true">◌</span></article>
      </div>
      <div class="section-heading">
        <p class="eyebrow">Modules</p>
        <h2>快速入口</h2>
      </div>

      <div class="feature-grid">
        <RouterLink v-for="card in cards" :key="card.title" class="feature-card lift-card" :to="card.to" v-reveal>
          <span>{{ card.index }}</span>
          <h3>{{ card.title }}</h3>
          <p>{{ card.text }}</p>
        </RouterLink>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useReadRequest } from '../composables/useReadRequest.js'
import { RouterLink } from 'vue-router'
import { apiRequest } from '../api/client'

const stats = ref(null)
const quote = ref(null)
const statsRead = useReadRequest(data => { stats.value = data })
const quoteRead = useReadRequest(data => { quote.value = data })
const statsLoading = statsRead.loading, statsError = statsRead.error
const quoteLoading = quoteRead.loading, quoteError = quoteRead.error

const cards = [
  { index: '◉', title: '太阳系图谱', text: '拖动视角，靠近八颗行星。在一张浅色 3D 图谱里，重新发现宇宙。', to: '/solar-system' },
  { index: '↗', title: '高性价比人生指南', text: '34 节原文，按关键词、成本和证据查阅；保留完整来源与适用条件。', to: '/life-guide' },
  { index: '↗', title: 'Space 聊天室', text: '进入公共大厅、加入小群，或向朋友发起双方同意的私聊。', to: '/chat' },
  { index: '3D', title: '末世模拟器', text: '采集建造、供电与补给、抵御夜袭。城市探索与原来的三十天剧情也保留。', to: '/wasteland' },
  { index: '↔', title: 'PDF / Word 转换', text: '文件在浏览器内转换，先核对预览，再下载。扫描件可选图片保真模式。', to: '/document-tools' },
  { index: '01', title: '密码算法实验室', text: '输入示例，观察 AES、SHA、RSA 等算法的真实计算轨迹与原理图。', to: '/crypto-lab' },
  { index: '01', title: '小说阅读', text: '搜索小说、进入阅读模式、调整字号和保存阅读进度。', to: '/novels' },
  { index: '02', title: '帖子广场', text: '交流想法、收藏与点赞；高权限用户可以发布和评论。', to: '/posts' },
  { index: '03', title: '作品文章', text: '文章支持分类、标签、Markdown、收藏、点赞和评论。', to: '/articles' },
  { index: '04', title: '学习路线', text: '按阶段整理前端、Vue、Python、FastAPI、MySQL 和部署。', to: '/roadmap' },
  { index: '05', title: '留言板', text: '读一读大家留下的近况；高权限用户可以发布留言。', to: '/messages' },
  { index: '06', title: '更新日志', text: '记录这个网站从静态页面到全栈项目的每一步。', to: '/changelog' },
  { index: '07', title: '安全计算实验室', text: '基于保密内积协议，演示点线面空间位置关系的安全计算。', to: '/secure-geometry' },
  { index: '08', title: '四维成长地图', text: '24 道选择题，结合真实经历反思。默认本地处理、免费且无需登录。', to: '/human3' },
  { index: '09', title: '数字商品 · 筹备中', text: '未来的授权数字产品与卡密交付空间。当前仅为展示，不支持购买。', to: '/store' },
]

function fetchQuote() {
  const exclude = quote.value?.id ? `&exclude_id=${quote.value.id}` : ''
  return quoteRead.run(async signal => {
    try { return await apiRequest(`/api/yulu/random?yname=fcx${exclude}`, { signal }) }
    catch (error) { if (error.status === 404) error.message = '暂时没有可用语录，稍后再来看看。'; throw error }
  })
}

async function copyQuote() {
  if (!quote.value) {
    return
  }

  try {
    await navigator.clipboard.writeText(quote.value.content)
    ElMessage.success('语录已复制')
  } catch {
    ElMessage.error('复制失败，请手动选中文字复制')
  }
}

function fetchStats() {
  return statsRead.run(signal => apiRequest('/api/site-summary', { signal }))
}
onMounted(() => {
  fetchQuote()
  fetchStats()
})
</script>
