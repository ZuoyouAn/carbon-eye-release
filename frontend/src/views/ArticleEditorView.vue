<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/articles">返回文章列表</RouterLink>
        <p class="eyebrow">Markdown Editor</p>
        <h1>{{ isEdit ? '编辑文章' : '发布文章' }}</h1>
        <p>左边写 Markdown，右边实时预览。文章可以保存为草稿、发布或隐藏。</p>
      </div>

      <div class="editor-layout">
        <form class="form-stack editor-form" @submit.prevent="submitArticle">
          <label>
            标题
            <input v-model="form.title" type="text" placeholder="文章标题">
          </label>
          <label>
            摘要
            <input v-model="form.summary" type="text" placeholder="文章摘要，会显示在列表页">
          </label>
          <div class="form-row">
            <label>
              分类
              <input v-model="form.category" type="text" placeholder="例如 前端">
            </label>
            <label>
              标签
              <input v-model="form.tags" type="text" placeholder="例如 Vue,FastAPI,MySQL">
            </label>
          </div>
          <div class="form-row">
            <label>
              状态
              <select v-model="form.status">
                <option value="draft">草稿</option>
                <option value="published">发布</option>
                <option value="hidden">隐藏</option>
              </select>
            </label>
            <label class="checkbox-line">
              <input v-model="form.is_pinned" type="checkbox">
              置顶文章
            </label>
          </div>
          <label>
            Markdown 内容
            <textarea v-model="form.content" rows="16" placeholder="# 标题"></textarea>
          </label>
          <button class="button button-primary" type="submit">{{ isEdit ? '保存修改' : '发布文章' }}</button>
        </form>

        <article class="markdown-body preview-panel" v-html="previewHtml"></article>
      </div>

      <p v-if="message" class="message">{{ message }}</p>
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { apiRequest, postJson, putJson } from '../api/client'

const router = useRouter()
const route = useRoute()
const message = ref('')
const form = ref({
  title: '',
  summary: '',
  category: '随笔',
  tags: 'Vue,FastAPI,MySQL',
  content: '# 新文章\n\n从这里开始写你的 Markdown 内容。',
  status: 'published',
  is_pinned: false,
})

const isEdit = computed(() => Boolean(route.params.id))
const previewHtml = computed(() => marked.parse(form.value.content || ''))

onMounted(loadArticle)

async function loadArticle() {
  if (!isEdit.value) return

  try {
    const data = await apiRequest(`/api/articles/${route.params.id}`)
    form.value = {
      title: data.article.title,
      summary: data.article.summary,
      category: data.article.category,
      tags: data.article.tags_text,
      content: data.article.content,
      status: data.article.status,
      is_pinned: data.article.is_pinned,
    }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function submitArticle() {
  message.value = ''
  try {
    const data = isEdit.value
      ? await putJson(`/api/admin/articles/${route.params.id}`, form.value)
      : await postJson('/api/articles', form.value)
    ElMessage.success(data.message)
    router.push(`/articles/${data.article.id}`)
  } catch (error) {
    ElMessage.error(error.message)
  }
}
</script>
