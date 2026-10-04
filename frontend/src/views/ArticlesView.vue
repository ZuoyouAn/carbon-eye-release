<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Articles</p>
        <h1>{{ selectedArticle ? selectedArticle.title : '作品文章' }}</h1>
        <p>文章支持 Markdown、分类、标签、搜索、点赞、收藏和评论。</p>
      </div>

      <form v-if="!isDetail" class="toolbar filter-toolbar" @submit.prevent="fetchArticles(1)">
        <input v-model="filters.q" type="search" aria-label="搜索文章" placeholder="搜索标题、摘要或正文">
        <select v-model="filters.category" aria-label="文章分类">
          <option value="">全部分类</option>
          <option v-for="category in categories" :key="category" :value="category">{{ category }}</option>
        </select>
        <input v-model="filters.tag" type="text" aria-label="文章标签" placeholder="标签，例如 Vue">
        <select v-model="filters.sort" aria-label="文章排序">
          <option value="latest">最新</option>
          <option value="oldest">最早</option>
        </select>
        <button type="submit">筛选</button>
        <RouterLink v-if="isAdmin" class="button button-primary" to="/admin/articles/new">发布文章</RouterLink>
      </form>

      <p v-if="loading" class="state-text" role="status">正在读取文章...</p>
      <div v-if="readError" class="request-error" role="alert"><p>{{ readError }}</p><button class="button button-secondary" @click="retryRead">重新读取</button><RouterLink v-if="isDetail" class="back-button" to="/articles">返回文章列表</RouterLink></div>

      <el-empty v-if="!isDetail && !loading && !readError && !articles.length" description="暂无文章" />
      <div v-if="!isDetail && articles.length && !readError" class="card-grid">
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
        v-if="!isDetail && !readError"
        class="el-pager"
        background
        layout="prev, pager, next"
        :current-page="page.page"
        :page-size="page.page_size"
        :total="page.total"
        @current-change="changePage"
      />

      <article v-else-if="isDetail && selectedArticle" class="detail-panel-inner">
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
import { ElMessage, ElEmpty, ElPagination } from 'element-plus'
import 'element-plus/es/components/empty/style/css'
import 'element-plus/es/components/pagination/style/css'
import { renderMarkdown } from '../utils/markdown'
import { computed, ref, watch } from 'vue'
import { useReadRequest } from '../composables/useReadRequest.js'
import { RouterLink, useRoute } from 'vue-router'
import { apiRequest, deleteRequest, postJson } from '../api/client'
import { canPublish, isAdmin, isLoggedIn, isMuted } from '../stores/auth'

const route = useRoute()
const articles = ref([])
const categories = ref([])
const selectedArticle = ref(null)
const comments = ref([])
const message = ref('')
const filters = ref({ q: '', category: '', tag: '', sort: 'latest' })
const page = ref({ page: 1, page_size: 9, total: 0, pages: 1 })
const commentForm = ref({ content: '' })
const isDetail = computed(() => Boolean(route.params.id))
const listRead = useReadRequest(data => { articles.value = data.items; page.value = data })
const detailRead = useReadRequest(data => { selectedArticle.value = data.article; comments.value = data.comments })
const categoryRead = useReadRequest(data => { categories.value = data })
const loading = computed(() => (isDetail.value ? detailRead : listRead).loading.value)
const readError = computed(() => (isDetail.value ? detailRead : listRead).error.value)

const publishTip = computed(() => {
  if (!isLoggedIn.value) return '请先登录后再评论。'
  if (isMuted.value) return '你已被禁言，不能评论。'
  if (!canPublish.value) return '当前为低权限账号，请联系管理员提升为高权限后评论。'
  return ''
})

const renderedArticle = computed(() => renderMarkdown(selectedArticle.value?.content || ''))

watch(() => route.params.id, (id) => {
  selectedArticle.value = null; comments.value = []; commentForm.value = { content: '' }
  if (id) { listRead.cancel(); categoryRead.cancel(); fetchArticleDetail(id) }
  else { detailRead.cancel(); fetchCategories(); fetchArticles() }
}, { immediate: true })

function fetchCategories() {
  return categoryRead.run(signal => apiRequest('/api/articles/categories', { signal }))
}

function fetchArticles(nextPage = page.value.page) {
  if (isDetail.value) return
  const params = new URLSearchParams({ page: nextPage, page_size: page.value.page_size, sort: filters.value.sort })
  if (filters.value.q) params.set('q', filters.value.q)
  if (filters.value.category) params.set('category', filters.value.category)
  if (filters.value.tag) params.set('tag', filters.value.tag)
  return listRead.run(signal => apiRequest(`/api/articles?${params.toString()}`, { signal }))
}

function fetchArticleDetail(id) {
  if (String(route.params.id) !== String(id)) return
  return detailRead.run(signal => apiRequest(`/api/articles/${encodeURIComponent(id)}`, { signal }))
}

function retryRead() { return isDetail.value ? fetchArticleDetail(route.params.id) : fetchArticles() }

async function createComment() {
  const id = selectedArticle.value?.id
  if (!id) return
  message.value = ''
  try {
    const data = await postJson(`/api/articles/${id}/comments`, commentForm.value)
    ElMessage.success(data.message)
    if (String(route.params.id) === String(id)) { commentForm.value = { content: '' }; await fetchArticleDetail(id) }
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
