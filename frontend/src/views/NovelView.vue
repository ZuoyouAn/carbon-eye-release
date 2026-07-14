<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Novel Shelf</p>
        <h1>{{ selectedNovel ? selectedNovel.name : '小说阅读' }}</h1>
        <p>支持搜索、收藏、阅读模式、字号调整和阅读进度保存。阅读数据基于 novel1 的 xs_id。</p>
      </div>

      <div v-if="!selectedNovel" class="toolbar">
        <input v-model="keyword" type="search" placeholder="搜索小说名字或内容">
        <button type="button" @click="fetchNovels">搜索</button>
      </div>

      <p v-if="message" class="message">{{ message }}</p>
      <p v-if="loading" class="state-text">正在读取小说...</p>

      <div v-if="!selectedNovel" class="card-grid two-grid">
        <article v-for="novel in novels" :key="novel.id" class="list-card">
          <span class="number-badge">{{ novel.id.toString().padStart(2, '0') }}</span>
          <div class="list-card-main">
            <RouterLink class="card-title-button" :to="`/novels/${novel.id}`">{{ novel.name }}</RouterLink>
            <small>{{ novel.favorite_count }} 人收藏 · 进度 {{ novel.progress }}%</small>
          </div>
          <button type="button" class="mini-button" @click="toggleFavorite(novel)">
            {{ novel.is_favorited ? '已收藏' : '收藏' }}
          </button>
        </article>
      </div>

      <div v-else class="reader-layout">
        <div class="reader-tools">
          <RouterLink class="button button-secondary" to="/novels">返回列表</RouterLink>
          <button class="button button-secondary" type="button" :disabled="!prevNovel" @click="goNovel(prevNovel)">上一篇</button>
          <button class="button button-secondary" type="button" :disabled="!nextNovel" @click="goNovel(nextNovel)">下一篇</button>
          <button class="button button-primary" type="button" @click="toggleFavorite(selectedNovel)">
            {{ selectedNovel.is_favorited ? '取消收藏' : '收藏小说' }}
          </button>
        </div>

        <div class="reader-settings">
          <label>
            字号 {{ reader.font_size }}px
            <input v-model.number="reader.font_size" type="range" min="14" max="26">
          </label>
          <label>
            阅读进度 {{ reader.progress }}%
            <input v-model.number="reader.progress" type="range" min="0" max="100">
          </label>
          <label>
            主题
            <select v-model="reader.theme">
              <option value="dark">深色</option>
              <option value="light">浅色</option>
            </select>
          </label>
          <button type="button" class="button button-primary" @click="saveProgress">保存进度</button>
        </div>

        <article class="reader-box" :class="reader.theme" :style="{ fontSize: `${reader.font_size}px` }">
          <p>{{ selectedNovel.content || '这篇小说还没有内容。' }}</p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { apiRequest, deleteRequest, postJson, putJson } from '../api/client'
import { isLoggedIn } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const novels = ref([])
const selectedNovel = ref(null)
const keyword = ref('')
const loading = ref(false)
const message = ref('')
const reader = ref({ progress: 0, font_size: 18, theme: 'dark' })

const currentIndex = computed(() => novels.value.findIndex((item) => item.id === selectedNovel.value?.id))
const prevNovel = computed(() => (currentIndex.value > 0 ? novels.value[currentIndex.value - 1] : null))
const nextNovel = computed(() => (currentIndex.value >= 0 && currentIndex.value < novels.value.length - 1 ? novels.value[currentIndex.value + 1] : null))

onMounted(fetchNovels)

watch(() => route.params.id, async (id) => {
  if (!id) {
    selectedNovel.value = null
    return
  }
  await fetchNovelDetail(id)
}, { immediate: true })

async function fetchNovels() {
  loading.value = true
  message.value = ''
  try {
    const q = keyword.value ? `?q=${encodeURIComponent(keyword.value)}` : ''
    novels.value = await apiRequest(`/api/novels${q}`)
  } catch (error) {
    message.value = error.message
  } finally {
    loading.value = false
  }
}

async function fetchNovelDetail(id) {
  message.value = ''
  try {
    if (!novels.value.length) {
      await fetchNovels()
    }
    const data = await apiRequest(`/api/novels/${id}`)
    selectedNovel.value = data.novel
    reader.value = {
      progress: data.novel.progress || 0,
      font_size: data.novel.font_size || 18,
      theme: data.novel.theme || 'dark',
    }
  } catch (error) {
    message.value = error.message
  }
}

function goNovel(novel) {
  if (novel) {
    router.push(`/novels/${novel.id}`)
  }
}

async function toggleFavorite(novel) {
  if (!isLoggedIn.value) {
    message.value = '请先登录后再收藏小说。'
    return
  }

  try {
    const data = novel.is_favorited
      ? await deleteRequest(`/api/novels/${novel.id}/favorite`)
      : await postJson(`/api/novels/${novel.id}/favorite`, {})
    message.value = data.message
    await fetchNovels()
    if (selectedNovel.value?.id === novel.id) {
      selectedNovel.value = data.novel
    }
  } catch (error) {
    message.value = error.message
  }
}

async function saveProgress() {
  if (!isLoggedIn.value) {
    message.value = '请先登录后再保存阅读进度。'
    return
  }

  try {
    const data = await putJson(`/api/novels/${selectedNovel.value.id}/progress`, reader.value)
    message.value = data.message
  } catch (error) {
    message.value = error.message
  }
}
</script>
