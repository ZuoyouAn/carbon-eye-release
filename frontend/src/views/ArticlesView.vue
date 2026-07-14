<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Articles</p>
        <h1>{{ selectedArticle ? selectedArticle.title : '作品文章' }}</h1>
        <p>文章支持 Markdown、分类、标签、搜索、点赞、收藏和评论。</p>
      </div>

      <div v-if="!selectedArticle" class="toolbar filter-toolbar">
        <input v-model="filters.q" type="search" placeholder="搜索标题、摘要或正文">
        <select v-model="filters.category">
          <option value="">全部分类</option>
          <option v-for="category in categories" :key="category" :value="category">{{ category }}</option>
        </select>
        <input v-model="filters.tag" type="text" placeholder="标签，例如 Vue">
        <select v-model="filters.sort">
          <option value="latest">最新</option>
          <option value="oldest">最早</option>
        </select>
        <button type="button" @click="fetchArticles(1)">筛选</button>
        <RouterLink v-if="isAdmin" class="button button-primary" to="/admin/articles/new">发布文章</RouterLink>
      </div>

      <p v-if="loading" class="state-text">正在读取文章...</p>

      <el-empty v-if="!selectedArticle && !loading && !articles.length" description="暂无文章" />
      <div v-if="!selectedArticle && articles.length" class="card-grid">
        <article v-for="article in articles" :key="article.id" class="content-card">
          <div class="card-meta">
            <span>{{ article.category }}</span>
            <span>{{ article.created_at }}</span>
          </div>
          <RouterLink class="card-heading-button" :to="`/articles/${article.id}`">{{ article.title }}</RouterLink>
          <p>{{ article.summary || article.content }}</p>
          <div class="tag-list">
            <button v-for="tag in article.tags" :key="tag" type="button" @click="filters.tag = tag; fetchArticles()">{{ tag }}</button>
          </div>
          <div class="action-row">
            <button type="button" class="mini-button" @click="toggleLike(article)">
              {{ article.is_liked ? '已赞' : '点赞' }} {{ article.like_count }}
            </button>
            <button type="button" class="mini-button" @click="toggleFavorite(article)">
              {{ article.is_favorited ? '已收藏' : '收藏' }} {{ article.favorite_count }}
            </button>
            <small>{{ article.comment_count }} 条评论</small>
          </div>
        </article>
      </div>

      <el-pagination
        v-if="!selectedArticle"
        class="el-pager"
        background
        layout="prev, pager, next"
        :current-page="page.page"
        :page-size="page.page_size"
        :total="page.total"
        @current-change="changePage"
      />

      <article v-else class="detail-panel-inner">
        <div class="card-meta">
          <span>{{ selectedArticle.category }}</span>
          <span>{{ selectedArticle.created_at }}</span>
        </div>
        <div class="tag-list">
          <span v-for="tag in selectedArticle.tags" :key="tag">{{ tag }}</span>
        </div>
        <div class="reader-tools">
          <RouterLink class="button button-secondary" to="/articles">返回文章列表</RouterLink>
          <button class="button button-primary" type="button" @click="toggleLike(selectedArticle)">
            {{ selectedArticle.is_liked ? '取消点赞' : '点赞' }} {{ selectedArticle.like_count }}
          </button>
          <button class="button button-secondary" type="button" @click="toggleFavorite(selectedArticle)">
            {{ selectedArticle.is_favorited ? '取消收藏' : '收藏文章' }} {{ selectedArticle.favorite_count }}
          </button>
        </div>

        <div class="markdown-body" v-html="renderedArticle"></div>

        <form v-if="canPublish" class="form-stack comment-box" @submit.prevent="createComment">
          <label>
            评论文章
            <textarea v-model="commentForm.content" rows="3" placeholder="写下你的评论"></textarea>
          </label>
          <button class="button button-primary" type="submit">提交评论</button>
        </form>
        <p v-else class="state-text">{{ publishTip }}</p>

        <div class="comment-list">
          <article v-for="comment in comments" :key="comment.id" class="comment-card">
            <div class="card-meta">
              <span>{{ comment.author }}</span>
              <span>{{ comment.created_at }}</span>
            </div>
            <p>{{ comment.content }}</p>
          </article>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { apiRequest, deleteRequest, postJson } from '../api/client'
import { canPublish, isAdmin, isLoggedIn, isMuted } from '../stores/auth'

const route = useRoute()
const articles = ref([])
const categories = ref([])
const selectedArticle = ref(null)
const comments = ref([])
const loading = ref(false)
const message = ref('')
const filters = ref({ q: '', category: '', tag: '', sort: 'latest' })
const page = ref({ page: 1, page_size: 9, total: 0, pages: 1 })
const commentForm = ref({ content: '' })

const publishTip = computed(() => {
  if (!isLoggedIn.value) return '请先登录后再评论。'
  if (isMuted.value) return '你已被禁言，不能评论。'
  return ''
})

const renderedArticle = computed(() => marked.parse(selectedArticle.value?.content || ''))

onMounted(async () => {
  await Promise.all([fetchCategories(), fetchArticles()])
})

watch(() => route.params.id, async (id) => {
  if (!id) {
    selectedArticle.value = null
    comments.value = []
    return
  }
  await fetchArticleDetail(id)
}, { immediate: true })

async function fetchCategories() {
  try {
    categories.value = await apiRequest('/api/articles/categories')
  } catch {
    categories.value = []
  }
}

async function fetchArticles(nextPage = page.value.page) {
  loading.value = true
  message.value = ''
  try {
    const params = new URLSearchParams({ page: nextPage, page_size: page.value.page_size, sort: filters.value.sort })
    if (filters.value.q) params.set('q', filters.value.q)
    if (filters.value.category) params.set('category', filters.value.category)
    if (filters.value.tag) params.set('tag', filters.value.tag)
    const data = await apiRequest(`/api/articles?${params.toString()}`)
    articles.value = data.items
    page.value = data
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function fetchArticleDetail(id) {
  message.value = ''
  try {
    const data = await apiRequest(`/api/articles/${id}`)
    selectedArticle.value = data.article
    comments.value = data.comments
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function createComment() {
  message.value = ''
  try {
    const data = await postJson(`/api/articles/${selectedArticle.value.id}/comments`, commentForm.value)
    ElMessage.success(data.message)
    commentForm.value = { content: '' }
    await fetchArticleDetail(selectedArticle.value.id)
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function toggleLike(article) {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录后再点赞。')
    return
  }

  try {
    const data = article.is_liked
      ? await deleteRequest(`/api/articles/${article.id}/like`)
      : await postJson(`/api/articles/${article.id}/like`, {})
    ElMessage.success(data.message)
    if (selectedArticle.value?.id === article.id) {
      await fetchArticleDetail(article.id)
    } else {
      await fetchArticles()
    }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function toggleFavorite(article) {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录后再收藏文章。')
    return
  }

  try {
    const data = article.is_favorited
      ? await deleteRequest(`/api/articles/${article.id}/favorite`)
      : await postJson(`/api/articles/${article.id}/favorite`, {})
    ElMessage.success(data.message)
    if (selectedArticle.value?.id === article.id) {
      await fetchArticleDetail(article.id)
    } else {
      await fetchArticles()
    }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function changePage(nextPage) {
  fetchArticles(nextPage)
}
</script>
