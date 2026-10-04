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
      <p v-if="summary" class="state-text">当前角色：{{ roleLabel(summary.user.role) }}。低权限可收藏和保存阅读进度；高权限可发布内容；管理员可管理站点。</p>
      <section class="avatar-settings"><div><img v-if="avatarDraft" class="avatar-preview" :src="avatarDraft.preview" alt="待上传头像预览"><UserAvatar v-else :user="authState.user" :size="90" /></div><div><h2>我的头像</h2><p class="panel-text">选择5MB以内的JPEG、PNG或WebP。自动居中裁剪并压缩为128像素；上传后头像公开可见，原图不保存。请使用你有权使用的图片。</p><label class="text-button avatar-picker">选择图片<input type="file" accept="image/jpeg,image/png,image/webp" :disabled="avatarBusy" @change="selectAvatar"></label><div class="hero-actions"><button class="button button-primary" :disabled="!avatarDraft || avatarBusy" @click="uploadAvatar">{{ avatarBusy ? '处理中…' : '保存头像' }}</button><button class="button button-secondary" :disabled="avatarBusy" @click="removeAvatar">移除头像</button><RouterLink class="button button-secondary" to="/chat">进入聊天室 →</RouterLink></div><p v-if="avatarNotice" role="status" class="panel-text">{{ avatarNotice }}</p></div></section>

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
import { RouterLink, useRouter } from 'vue-router'
import { apiRequest, putJson, deleteRequest } from '../api/client'
import { changePassword, authState } from '../stores/auth'
import { roleLabel } from '../utils/permissions'
import UserAvatar from '../components/UserAvatar.vue'
import { prepareAvatar } from '../utils/avatar.js'

const router = useRouter()

const message = ref('')
const summary = ref(null)
const posts = ref([])
const comments = ref({ post_comments: [], article_comments: [] })
const favorites = ref({ articles: [], novels: [] })
const passwordForm = ref({ old_password: '', new_password: '' })
const avatarDraft = ref(null), avatarBusy = ref(false), avatarNotice = ref('')
async function selectAvatar(event) {
  const file = event.target.files?.[0]; event.target.value = ''
  if (!file) return
  avatarDraft.value = null; avatarNotice.value = ''; avatarBusy.value = true
  try { avatarDraft.value = await prepareAvatar(file) } catch (error) { avatarNotice.value = error.message } finally { avatarBusy.value = false }
}
function refreshAvatar(version) { window.dispatchEvent(new CustomEvent('avatar-updated', { detail: { userId: authState.user?.id, version } })) }
async function uploadAvatar() {
  if (!avatarDraft.value || avatarBusy.value) return
  avatarBusy.value = true; avatarNotice.value = ''
  try { const result = await putJson('/api/me/avatar', { image_base64: avatarDraft.value.image_base64 }); avatarDraft.value = null; refreshAvatar(result.version); avatarNotice.value = '头像已保存，重新登录后仍会保留。' } catch (error) { avatarNotice.value = error.message } finally { avatarBusy.value = false }
}
async function removeAvatar() {
  if (avatarBusy.value || !window.confirm('移除已上传的头像？之后将显示默认头像。')) return
  avatarBusy.value = true
  try { await deleteRequest('/api/me/avatar'); avatarDraft.value = null; refreshAvatar(); avatarNotice.value = '头像已移除。' } catch (error) { avatarNotice.value = error.message } finally { avatarBusy.value = false }
}

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
    window.alert(data.message)
    await router.push('/login')
  } catch (error) {
    message.value = error.message
  }
}
</script>
<style scoped>.avatar-settings { display: grid; grid-template-columns: 90px minmax(0, 1fr); gap: 24px; padding: 24px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }.avatar-settings h2 { margin-top: 0; }.avatar-preview { width: 90px; height: 90px; object-fit: cover; border-radius: 30%; }.avatar-picker { display: inline-block; }.avatar-picker input { display: block; margin-top: 8px; max-width: 280px; min-height: auto; font-size: 13px; }@media(max-width:620px){.avatar-settings{grid-template-columns:1fr;}.avatar-picker{max-width:100%;}.avatar-picker input{max-width:100%;}}</style>
