<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Messages</p>
        <h1>留言板</h1>
        <p>所有人可浏览留言，高权限账号和管理员可以发布留言。</p>
      </div>

      <form v-if="canPublish" class="form-stack publish-box" @submit.prevent="submitMessage">
        <label v-if="!isLoggedIn">
          昵称
          <input v-model="form.nickname" type="text" placeholder="怎么称呼你">
        </label>
        <label>
          留言内容
          <textarea v-model="form.content" rows="4" placeholder="留下你想说的话"></textarea>
        </label>
        <el-button type="primary" native-type="submit">发布留言</el-button>
      </form>
      <p v-else class="state-text">{{ !isLoggedIn ? '请登录高权限账号后留言。' : isMuted ? '你已被禁言，不能留言。' : '当前为低权限账号，请联系管理员提升权限后留言。' }}</p>

      <el-skeleton v-if="loading" :rows="4" animated />
      <el-empty v-else-if="!messages.length" description="还没有留言" />

      <div v-else class="comment-list">
        <article v-for="item in messages" :key="item.id" class="comment-card">
          <div class="card-meta">
            <span>{{ item.author }}</span>
            <span>{{ item.created_at }}</span>
          </div>
          <p>{{ item.content }}</p>
        </article>
      </div>

      <el-pagination
        class="el-pager"
        background
        layout="prev, pager, next"
        :current-page="page.page"
        :page-size="page.page_size"
        :total="page.total"
        @current-change="changePage"
      />
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiRequest, postJson } from '../api/client'
import { canPublish, isLoggedIn, isMuted } from '../stores/auth'

const loading = ref(false)
const messages = ref([])
const page = ref({ page: 1, page_size: 10, total: 0, pages: 1 })
const form = ref({ nickname: '游客', content: '' })

onMounted(fetchMessages)

async function fetchMessages(nextPage = page.value.page) {
  loading.value = true
  try {
    const data = await apiRequest(`/api/messages?page=${nextPage}&page_size=${page.value.page_size}`)
    messages.value = data.items
    page.value = data
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function submitMessage() {
  try {
    const data = await postJson('/api/messages', form.value)
    ElMessage.success(data.message)
    form.value = { nickname: '游客', content: '' }
    await fetchMessages(1)
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function changePage(nextPage) {
  fetchMessages(nextPage)
}
</script>
