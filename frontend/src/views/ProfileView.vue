<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Profile</p>
        <h1>个人中心</h1>
        <p>这里能看到你的发布、评论、收藏和账号状态。</p>
      </div>

      <p v-if="message" class="message">{{ message }}</p>

      <div v-if="summary" class="stat-grid">
        <div>
          <strong>{{ summary.posts }}</strong>
          <span>我的帖子</span>
        </div>
        <div>
          <strong>{{ summary.post_comments + summary.article_comments }}</strong>
          <span>我的评论</span>
        </div>
        <div>
          <strong>{{ summary.article_favorites + summary.novel_favorites }}</strong>
          <span>我的收藏</span>
        </div>
        <div>
          <strong>{{ summary.user.is_muted ? '禁言' : '正常' }}</strong>
          <span>账号状态</span>
        </div>
      </div>

      <form class="form-stack publish-box" @submit.prevent="submitPassword">
        <h2>修改密码</h2>
        <div class="form-row">
          <label>
            旧密码
            <input v-model="passwordForm.old_password" type="password" placeholder="旧密码">
          </label>
          <label>
            新密码
            <input v-model="passwordForm.new_password" type="password" placeholder="新密码">
          </label>
        </div>
        <button class="button button-primary" type="submit">修改密码</button>
      </form>

      <div class="profile-grid">
        <section>
          <h2>我的帖子</h2>
          <article v-for="post in posts" :key="post.id" class="content-card compact-card">
            <RouterLink class="card-heading-button" :to="`/posts/${post.id}`">{{ post.title }}</RouterLink>
            <p>{{ post.content }}</p>
          </article>
        </section>

        <section>
          <h2>我的文章收藏</h2>
          <article v-for="article in favorites.articles" :key="article.id" class="content-card compact-card">
            <RouterLink class="card-heading-button" :to="`/articles/${article.id}`">{{ article.title }}</RouterLink>
            <p>{{ article.summary || article.content }}</p>
          </article>
        </section>

        <section>
          <h2>我的小说收藏</h2>
          <article v-for="novel in favorites.novels" :key="novel.id" class="content-card compact-card">
            <RouterLink class="card-heading-button" :to="`/novels/${novel.id}`">{{ novel.name }}</RouterLink>
            <p>阅读进度 {{ novel.progress }}%</p>
          </article>
        </section>

        <section>
          <h2>我的评论</h2>
          <article v-for="comment in allComments" :key="`${comment.type}-${comment.id}`" class="comment-card">
            <div class="card-meta">
              <span>{{ comment.type }}</span>
              <span>{{ comment.created_at }}</span>
            </div>
            <p>{{ comment.content }}</p>
          </article>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiRequest } from '../api/client'
import { changePassword, refreshMe } from '../stores/auth'

const message = ref('')
const summary = ref(null)
const posts = ref([])
const comments = ref({ post_comments: [], article_comments: [] })
const favorites = ref({ articles: [], novels: [] })
const passwordForm = ref({ old_password: '', new_password: '' })

const allComments = computed(() => [
  ...comments.value.post_comments.map((comment) => ({ ...comment, type: '帖子评论' })),
  ...comments.value.article_comments.map((comment) => ({ ...comment, type: '文章评论' })),
])

onMounted(loadProfile)

async function loadProfile() {
  message.value = ''
  try {
    const [summaryData, postData, commentData, favoriteData] = await Promise.all([
      apiRequest('/api/me/summary'),
      apiRequest('/api/me/posts'),
      apiRequest('/api/me/comments'),
      apiRequest('/api/me/favorites'),
    ])
    summary.value = summaryData
    posts.value = postData
    comments.value = commentData
    favorites.value = favoriteData
  } catch (error) {
    message.value = error.message
  }
}

async function submitPassword() {
  message.value = ''
  try {
    const data = await changePassword(passwordForm.value)
    message.value = data.message
    passwordForm.value = { old_password: '', new_password: '' }
    await refreshMe()
  } catch (error) {
    message.value = error.message
  }
}
</script>
