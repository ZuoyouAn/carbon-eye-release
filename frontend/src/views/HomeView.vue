<template>
  <main>
    <section class="hero-section">
      <div class="hero-copy">
        <p class="eyebrow">ZUOYOU / PERSONAL SPACE</p>
        <h1>记录热爱，<br>让想法生长。</h1>
        <p class="hero-description">我是左右。这是我的学习笔记、项目实验与阅读空间，也是一处探索生活与成长的小站。</p>

        <div class="hero-actions">
          <RouterLink class="button button-primary" to="/articles">查看文章</RouterLink>
          <RouterLink class="button button-secondary" to="/human3">探索四维成长地图 →</RouterLink>
        </div>
      </div>

      <aside class="identity-panel">
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
      <div class="section-heading">
        <p class="eyebrow">Modules</p>
        <h2>快速入口</h2>
      </div>

      <div class="feature-grid">
        <RouterLink v-for="card in cards" :key="card.title" class="feature-card lift-card" :to="card.to">
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
  { index: '↗', title: 'Space 聊天室', text: '进入公共大厅、加入小群，或向朋友发起双方同意的私聊。', to: '/chat' },
  { index: '30', title: '末世模拟器', text: '两个天赋，十二点属性，三十天长夜。你的选择，决定下一段路。', to: '/wasteland' },
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
