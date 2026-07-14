<template>
  <main class="content-page">
    <section class="panel admin-panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Admin</p>
        <h1>管理后台</h1>
        <p>这里统一管理用户、文章、帖子、评论和留言。</p>
      </div>

      <div v-if="dashboard" class="stat-grid">
        <div><strong>{{ dashboard.users }}</strong><span>用户</span></div>
        <div><strong>{{ dashboard.muted_users }}</strong><span>禁言</span></div>
        <div><strong>{{ dashboard.articles }}</strong><span>文章</span></div>
        <div><strong>{{ dashboard.posts }}</strong><span>帖子</span></div>
        <div><strong>{{ dashboard.post_comments + dashboard.article_comments }}</strong><span>评论</span></div>
        <div><strong>{{ dashboard.messages }}</strong><span>留言</span></div>
      </div>

      <div class="admin-actions">
        <RouterLink class="button button-primary" to="/admin/articles/new">写新文章</RouterLink>
        <RouterLink class="button button-secondary" to="/messages">查看留言板</RouterLink>
      </div>

      <el-tabs v-model="activeTab" class="admin-tabs" @tab-change="loadCurrentTab">
        <el-tab-pane label="用户" name="users">
          <form class="form-stack publish-box" @submit.prevent="createUser">
            <h2>创建普通用户</h2>
            <div class="form-row">
              <input v-model="createForm.username" type="text" placeholder="新用户名">
              <input v-model="createForm.password" type="password" placeholder="新密码">
            </div>
            <el-button type="primary" native-type="submit">创建用户</el-button>
          </form>

          <el-table :data="users" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="用户名">
              <template #default="{ row }">
                <input v-model="row.editUsername" :disabled="row.role === 'admin'">
              </template>
            </el-table-column>
            <el-table-column prop="role" label="角色" width="100" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">{{ row.is_deleted ? '已删除' : row.is_muted ? '已禁言' : '正常' }}</template>
            </el-table-column>
            <el-table-column label="新密码">
              <template #default="{ row }">
                <input v-model="row.editPassword" :disabled="row.role === 'admin'" placeholder="留空不改">
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300">
              <template #default="{ row }">
                <el-button size="small" :disabled="row.role === 'admin'" @click="updateUser(row)">更新</el-button>
                <el-button size="small" :disabled="row.role === 'admin' || row.is_muted" @click="muteUser(row)">禁言</el-button>
                <el-button size="small" :disabled="row.role === 'admin' || !row.is_muted" @click="unmuteUser(row)">解禁</el-button>
                <el-button size="small" type="danger" :disabled="row.role === 'admin' || row.is_deleted" @click="deleteUser(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="文章" name="articles">
          <div class="toolbar admin-toolbar">
            <select v-model="articleFilters.status" @change="fetchArticles(1)">
              <option value="">全部</option>
              <option value="published">已发布</option>
              <option value="draft">草稿</option>
              <option value="hidden">隐藏</option>
              <option value="deleted">已删除</option>
            </select>
            <input v-model="articleFilters.q" type="search" placeholder="搜索文章">
            <el-button @click="fetchArticles(1)">搜索</el-button>
          </div>

          <el-table :data="articles.items" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">{{ articleStatusText(row) }}</template>
            </el-table-column>
            <el-table-column label="置顶" width="90">
              <template #default="{ row }">{{ row.is_pinned ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170" />
            <el-table-column label="操作" width="360">
              <template #default="{ row }">
                <el-button size="small" @click="$router.push(`/admin/articles/${row.id}/edit`)">编辑</el-button>
                <el-button size="small" @click="toggleArticlePin(row)">{{ row.is_pinned ? '取消置顶' : '置顶' }}</el-button>
                <el-button size="small" @click="changeArticleStatus(row, row.status === 'published' ? 'hidden' : 'published')">
                  {{ row.status === 'published' ? '隐藏' : '发布' }}
                </el-button>
                <el-button size="small" type="danger" :disabled="row.is_deleted" @click="deleteArticle(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="el-pager" background layout="prev, pager, next" :current-page="articles.page" :page-size="articles.page_size" :total="articles.total" @current-change="fetchArticles" />
        </el-tab-pane>

        <el-tab-pane label="帖子" name="posts">
          <div class="toolbar admin-toolbar">
            <input v-model="postFilters.q" type="search" placeholder="搜索帖子">
            <el-button @click="fetchPosts(1)">搜索</el-button>
          </div>
          <el-table :data="posts.items" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column prop="author" label="作者" width="140" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">{{ row.is_deleted ? '已删除' : '正常' }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170" />
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" @click="$router.push(`/posts/${row.id}`)">查看</el-button>
                <el-button size="small" type="danger" :disabled="row.is_deleted" @click="deletePost(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="el-pager" background layout="prev, pager, next" :current-page="posts.page" :page-size="posts.page_size" :total="posts.total" @current-change="fetchPosts" />
        </el-tab-pane>

        <el-tab-pane label="评论" name="comments">
          <div class="toolbar admin-toolbar">
            <select v-model="commentFilters.comment_type" @change="fetchComments(1)">
              <option value="all">全部</option>
              <option value="post">帖子评论</option>
              <option value="article">文章评论</option>
            </select>
            <el-button @click="fetchComments(1)">刷新</el-button>
          </div>
          <el-table :data="comments.items" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="type" label="类型" width="110" />
            <el-table-column prop="author" label="作者" width="140" />
            <el-table-column prop="content" label="内容" min-width="220" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">{{ row.is_deleted ? '已删除' : '正常' }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="170" />
            <el-table-column label="操作" width="110">
              <template #default="{ row }">
                <el-button size="small" type="danger" :disabled="row.is_deleted" @click="deleteComment(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="el-pager" background layout="prev, pager, next" :current-page="comments.page" :page-size="comments.page_size" :total="comments.total" @current-change="fetchComments" />
        </el-tab-pane>

        <el-tab-pane label="留言" name="messages">
          <div class="toolbar admin-toolbar">
            <select v-model="messageFilters.status" @change="fetchMessages(1)">
              <option value="">全部</option>
              <option value="published">显示中</option>
              <option value="hidden">已隐藏</option>
              <option value="deleted">已删除</option>
            </select>
            <el-button @click="fetchMessages(1)">刷新</el-button>
          </div>
          <el-table :data="messages.items" border>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="author" label="昵称" width="140" />
            <el-table-column prop="content" label="内容" min-width="240" />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">{{ row.is_deleted ? '已删除' : row.status === 'hidden' ? '已隐藏' : '显示中' }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="170" />
            <el-table-column label="操作" width="230">
              <template #default="{ row }">
                <el-button size="small" :disabled="row.is_deleted" @click="changeMessageStatus(row, row.status === 'published' ? 'hidden' : 'published')">
                  {{ row.status === 'published' ? '隐藏' : '显示' }}
                </el-button>
                <el-button size="small" type="danger" :disabled="row.is_deleted" @click="deleteMessage(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="el-pager" background layout="prev, pager, next" :current-page="messages.page" :page-size="messages.page_size" :total="messages.total" @current-change="fetchMessages" />
        </el-tab-pane>
      </el-tabs>
    </section>
  </main>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiRequest, deleteRequest, postJson, putJson } from '../api/client'

const activeTab = ref('users')
const dashboard = ref(null)
const users = ref([])
const articles = ref(emptyPage())
const posts = ref(emptyPage())
const comments = ref(emptyPage())
const messages = ref(emptyPage())
const createForm = ref({ username: '', password: '' })
const articleFilters = ref({ status: '', q: '' })
const postFilters = ref({ q: '' })
const commentFilters = ref({ comment_type: 'all' })
const messageFilters = ref({ status: '' })

onMounted(loadAdmin)

function emptyPage() {
  return { items: [], total: 0, page: 1, page_size: 10, pages: 1 }
}

function articleStatusText(row) {
  if (row.is_deleted) return '已删除'
  if (row.status === 'draft') return '草稿'
  if (row.status === 'hidden') return '隐藏'
  return '发布'
}

async function confirmAction(text) {
  await ElMessageBox.confirm(text, '确认操作', { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' })
}

async function loadAdmin() {
  await Promise.all([fetchDashboard(), fetchUsers()])
}

async function loadCurrentTab() {
  if (activeTab.value === 'users') await fetchUsers()
  if (activeTab.value === 'articles') await fetchArticles()
  if (activeTab.value === 'posts') await fetchPosts()
  if (activeTab.value === 'comments') await fetchComments()
  if (activeTab.value === 'messages') await fetchMessages()
  await fetchDashboard()
}

async function fetchDashboard() {
  dashboard.value = await apiRequest('/api/admin/dashboard')
}

async function fetchUsers() {
  const data = await apiRequest('/api/admin/users')
  users.value = data.map((user) => ({ ...user, editUsername: user.username, editPassword: '' }))
}

async function createUser() {
  try {
    const data = await postJson('/api/admin/users', createForm.value)
    ElMessage.success(data.message)
    createForm.value = { username: '', password: '' }
    await loadAdmin()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function updateUser(user) {
  try {
    const body = { username: user.editUsername, password: user.editPassword || undefined, is_muted: user.is_muted }
    const data = await putJson(`/api/admin/users/${user.id}`, body)
    ElMessage.success(data.message)
    await fetchUsers()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function muteUser(user) {
  const data = await putJson(`/api/admin/users/${user.id}/mute`, {})
  ElMessage.success(data.message)
  await fetchUsers()
}

async function unmuteUser(user) {
  const data = await putJson(`/api/admin/users/${user.id}/unmute`, {})
  ElMessage.success(data.message)
  await fetchUsers()
}

async function deleteUser(user) {
  try {
    await confirmAction(`确认删除用户「${user.username}」吗？`)
    const data = await deleteRequest(`/api/admin/users/${user.id}`)
    ElMessage.success(data.message)
    await loadAdmin()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error.message || '已取消')
  }
}

async function fetchArticles(nextPage = articles.value.page || 1) {
  const params = new URLSearchParams({ page: nextPage, page_size: 10 })
  if (articleFilters.value.status) params.set('status', articleFilters.value.status)
  if (articleFilters.value.q) params.set('q', articleFilters.value.q)
  articles.value = await apiRequest(`/api/admin/articles?${params.toString()}`)
}

async function changeArticleStatus(row, status) {
  const data = await putJson(`/api/admin/articles/${row.id}/status`, { status })
  ElMessage.success(data.message)
  await fetchArticles()
}

async function toggleArticlePin(row) {
  const data = await putJson(`/api/admin/articles/${row.id}/pin`, { is_pinned: !row.is_pinned })
  ElMessage.success(data.message)
  await fetchArticles()
}

async function deleteArticle(row) {
  try {
    await confirmAction(`确认删除文章「${row.title}」吗？`)
    const data = await deleteRequest(`/api/admin/articles/${row.id}`)
    ElMessage.success(data.message)
    await fetchArticles()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error.message || '已取消')
  }
}

async function fetchPosts(nextPage = posts.value.page || 1) {
  const params = new URLSearchParams({ page: nextPage, page_size: 10 })
  if (postFilters.value.q) params.set('q', postFilters.value.q)
  posts.value = await apiRequest(`/api/admin/posts?${params.toString()}`)
}

async function deletePost(row) {
  try {
    await confirmAction(`确认删除帖子「${row.title}」吗？`)
    const data = await deleteRequest(`/api/admin/posts/${row.id}`)
    ElMessage.success(data.message)
    await fetchPosts()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error.message || '已取消')
  }
}

async function fetchComments(nextPage = comments.value.page || 1) {
  const params = new URLSearchParams({ page: nextPage, page_size: 10, comment_type: commentFilters.value.comment_type })
  comments.value = await apiRequest(`/api/admin/comments?${params.toString()}`)
}

async function deleteComment(row) {
  try {
    await confirmAction('确认删除这条评论吗？')
    const data = await deleteRequest(`/api/admin/comments/${row.type}/${row.id}`)
    ElMessage.success(data.message)
    await fetchComments()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error.message || '已取消')
  }
}

async function fetchMessages(nextPage = messages.value.page || 1) {
  const params = new URLSearchParams({ page: nextPage, page_size: 10 })
  if (messageFilters.value.status) params.set('status', messageFilters.value.status)
  messages.value = await apiRequest(`/api/admin/messages?${params.toString()}`)
}

async function changeMessageStatus(row, status) {
  const data = await putJson(`/api/admin/messages/${row.id}/status`, { status })
  ElMessage.success(data.message)
  await fetchMessages()
}

async function deleteMessage(row) {
  try {
    await confirmAction('确认删除这条留言吗？')
    const data = await deleteRequest(`/api/admin/messages/${row.id}`)
    ElMessage.success(data.message)
    await fetchMessages()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error.message || '已取消')
  }
}
</script>
