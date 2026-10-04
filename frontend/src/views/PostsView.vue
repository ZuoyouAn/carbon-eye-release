<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Forum</p>
        <h1>{{ selectedPost ? selectedPost.title : '帖子广场' }}</h1>
        <p>帖子支持搜索、发布、点赞和评论。被禁言用户可以浏览和点赞，但不能发帖或评论。</p>
      </div>

      <form v-if="!isDetail" class="toolbar" @submit.prevent="fetchPosts(1)">
        <input v-model="keyword" type="search" aria-label="搜索帖子" placeholder="搜索帖子标题或内容">
        <button type="submit">搜索</button>
      </form>

      <form v-if="!isDetail && canPublish" class="form-stack publish-box" @submit.prevent="createPost">
        <label>
          帖子标题
          <input v-model="postForm.title" type="text" placeholder="写一个标题">
        </label>
        <label>
          帖子内容
          <textarea v-model="postForm.content" rows="4" placeholder="写点内容"></textarea>
        </label>
        <button class="button button-primary" type="submit">发布帖子</button>
      </form>

      <p v-else-if="!isDetail" class="state-text">{{ publishTip }}</p>
      <p v-if="loading" class="state-text" role="status">正在读取帖子...</p>
      <div v-if="readError" class="request-error" role="alert"><p>{{ readError }}</p><button class="button button-secondary" @click="retryRead">重新读取</button><RouterLink v-if="isDetail" class="back-button" to="/posts">返回帖子列表</RouterLink></div>

      <el-empty v-if="!isDetail && !loading && !readError && !posts.length" description="暂无帖子" />
      <div v-if="!isDetail && posts.length && !readError" class="card-grid">
        <article v-for="post in posts" :key="post.id" class="content-card">
          <div class="card-meta">
            <span>{{ post.author }}</span>
            <span>{{ post.created_at }}</span>
          </div>
          <RouterLink class="card-heading-button" :to="`/posts/${post.id}`">{{ post.title }}</RouterLink>
          <p>{{ post.content }}</p>
          <div class="action-row">
            <button type="button" class="mini-button" @click="toggleLike(post)">
              {{ post.is_liked ? '已赞' : '点赞' }} {{ post.like_count }}
            </button>
            <small>{{ post.comment_count }} 条评论</small>
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

      <article v-else-if="isDetail && selectedPost" class="detail-panel-inner">
        <div class="card-meta">
          <span>{{ selectedPost.author }}</span>
          <span>{{ selectedPost.created_at }}</span>
        </div>
        <div class="detail-box">
          <p>{{ selectedPost.content }}</p>
        </div>
        <div class="reader-tools">
          <RouterLink class="button button-secondary" to="/posts">返回帖子列表</RouterLink>
          <button class="button button-primary" type="button" @click="toggleLike(selectedPost)">
            {{ selectedPost.is_liked ? '取消点赞' : '点赞' }} {{ selectedPost.like_count }}
          </button>
        </div>

        <form v-if="canPublish" class="form-stack comment-box" @submit.prevent="createComment">
          <label>
            评论帖子
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
import { computed, ref, watch } from 'vue'
import { useReadRequest } from '../composables/useReadRequest.js'
import { RouterLink, useRoute } from 'vue-router'
import { apiRequest, deleteRequest, postJson } from '../api/client'
import { canPublish, isLoggedIn, isMuted } from '../stores/auth'

const route = useRoute()
const posts = ref([])
const selectedPost = ref(null)
const comments = ref([])
const keyword = ref('')
const message = ref('')
const page = ref({ page: 1, page_size: 9, total: 0, pages: 1 })
const postForm = ref({ title: '', content: '' })
const commentForm = ref({ content: '' })
const isDetail = computed(() => Boolean(route.params.id))
const listRead = useReadRequest(data => { posts.value = data.items; page.value = data })
const detailRead = useReadRequest(data => { selectedPost.value = data.post; comments.value = data.comments })
const loading = computed(() => (isDetail.value ? detailRead : listRead).loading.value)
const readError = computed(() => (isDetail.value ? detailRead : listRead).error.value)

const publishTip = computed(() => {
  if (!isLoggedIn.value) return '请先登录后再发布或评论。'
  if (isMuted.value) return '你已被禁言，不能发帖或评论。'
  if (!canPublish.value) return '当前为低权限账号，请联系管理员提升为高权限后发帖或评论。'
  return ''
})

watch(() => route.params.id, (id) => {
  selectedPost.value = null; comments.value = []; commentForm.value = { content: '' }
  if (id) { listRead.cancel(); fetchPostDetail(id) }
  else { detailRead.cancel(); fetchPosts() }
}, { immediate: true })

function fetchPosts(nextPage = page.value.page) {
  if (isDetail.value) return
  const params = new URLSearchParams({ page: nextPage, page_size: page.value.page_size })
  if (keyword.value) params.set('q', keyword.value)
  return listRead.run(signal => apiRequest(`/api/posts?${params.toString()}`, { signal }))
}

function fetchPostDetail(id) {
  if (String(route.params.id) !== String(id)) return
  return detailRead.run(signal => apiRequest(`/api/posts/${encodeURIComponent(id)}`, { signal }))
}

function retryRead() { return isDetail.value ? fetchPostDetail(route.params.id) : fetchPosts() }

async function createPost() {
  message.value = ''
  try {
    const data = await postJson('/api/posts', postForm.value)
    ElMessage.success(data.message)
    postForm.value = { title: '', content: '' }
    await fetchPosts(1)
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function createComment() {
  const id = selectedPost.value?.id
  if (!id) return
  message.value = ''
  try {
    const data = await postJson(`/api/posts/${id}/comments`, commentForm.value)
    ElMessage.success(data.message)
    if (String(route.params.id) === String(id)) { commentForm.value = { content: '' }; await fetchPostDetail(id) }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function toggleLike(post) {
  if (!isLoggedIn.value) {
    ElMessage.warning('请先登录后再点赞。')
    return
  }

  try {
    const data = post.is_liked
      ? await deleteRequest(`/api/posts/${post.id}/like`)
      : await postJson(`/api/posts/${post.id}/like`, {})
    ElMessage.success(data.message)
    if (selectedPost.value?.id === post.id) {
      await fetchPostDetail(post.id)
    } else {
      await fetchPosts()
    }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function changePage(nextPage) {
  fetchPosts(nextPage)
}
</script>
