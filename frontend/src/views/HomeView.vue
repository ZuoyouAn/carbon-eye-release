<template>
  <main>
    <section class="hero-section">
      <div class="hero-copy">
        <p class="eyebrow">Vue Router / FastAPI / MySQL</p>
        <h1>左右</h1>
        <p class="hero-title">我是神</p>
        <p class="hero-slogan">买挂联系我</p>
        <p class="hero-description">功能：文章、发帖子、看小说、收藏、点赞、论文实现、</p>

        <div class="hero-actions">
          <RouterLink class="button button-primary" to="/articles">查看文章</RouterLink>
          <RouterLink class="button button-secondary" to="/posts">去帖子区</RouterLink>
        </div>
      </div>

      <aside class="identity-panel">
        <div class="profile-head">
          <div class="avatar">左</div>
          <div>
            <p class="panel-label">个人网站</p>
            <h2>买挂找我</h2>
          </div>
        </div>

        <div class="stat-grid compact">
          <div>
            <strong>{{ stats.novels }}</strong>
            <span>小说</span>
          </div>
          <div>
            <strong>{{ stats.posts }}</strong>
            <span>帖子</span>
          </div>
          <div>
            <strong>{{ stats.articles }}</strong>
            <span>文章</span>
          </div>
        </div>

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
            <button type="button" class="mini-button" :disabled="!quote" @click="copyQuote">
              复制
            </button>
          </div>
        </div>
      </aside>
    </section>

    <section class="section">
      <div class="section-heading">
        <p class="eyebrow">Modules</p>
        <h2>现在可以从这些入口开始玩</h2>
        <p>每个模块都已经接到后端接口，后续你学习 Vue、FastAPI、MySQL 时，可以按模块一点点拆开看。</p>
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
import { RouterLink } from 'vue-router'
import { apiRequest } from '../api/client'

const stats = ref({ novels: 0, posts: 0, articles: 0 })
const quote = ref(null)
const quoteLoading = ref(false)
const quoteError = ref('')

const cards = [
  { index: '01', title: '小说阅读', text: '搜索小说、进入阅读模式、调整字号和保存阅读进度。', to: '/novels' },
  { index: '02', title: '帖子广场', text: '登录后可以发帖、点赞和评论，适合做小社区雏形。', to: '/posts' },
  { index: '03', title: '作品文章', text: '文章支持分类、标签、Markdown、收藏、点赞和评论。', to: '/articles' },
  { index: '04', title: '学习路线', text: '按阶段整理前端、Vue、Python、FastAPI、MySQL 和部署。', to: '/roadmap' },
  { index: '05', title: '留言板', text: '游客和登录用户都可以留言，管理员可以在后台治理。', to: '/messages' },
  { index: '06', title: '更新日志', text: '记录这个网站从静态页面到全栈项目的每一步。', to: '/changelog' },
  { index: '07', title: '安全计算实验室', text: '基于保密内积协议，演示点线面空间位置关系的安全计算。', to: '/secure-geometry' },
]

async function fetchQuote() {
  quoteLoading.value = true
  quoteError.value = ''

  try {
    const exclude = quote.value?.id ? `&exclude_id=${quote.value.id}` : ''
    quote.value = await apiRequest(`/api/yulu/random?yname=fcx${exclude}`)
  } catch (error) {
    quote.value = null
    quoteError.value = error.message || '暂无语录'
  } finally {
    quoteLoading.value = false
  }
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

onMounted(async () => {
  fetchQuote()

  try {
    const [novels, posts, articles] = await Promise.all([
      apiRequest('/api/novels'),
      apiRequest('/api/posts'),
      apiRequest('/api/articles'),
    ])
    stats.value = { novels: novels.length, posts: posts.total || 0, articles: articles.total || 0 }
  } catch {
    stats.value = { novels: 0, posts: 0, articles: 0 }
  }
})
</script>
