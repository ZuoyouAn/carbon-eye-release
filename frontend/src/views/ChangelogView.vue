<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Changelog</p>
        <h1>站点更新日志</h1>
        <p>以后每做一个版本，都可以在这里记下来。</p>
      </div>

      <div class="timeline-list">
        <article v-for="log in logs" :key="log.version" class="content-card">
          <div class="card-meta">
            <span>{{ log.version }}</span>
            <span>{{ log.date }}</span>
          </div>
          <h2>{{ log.title }}</h2>
          <p>{{ log.text }}</p>
          <div class="tag-list">
            <span v-for="tag in log.tags" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'

const logs = [
  { version: 'v3', date: '2026-05-28', title: '内容管理完整化', text: '新增后台内容管理、留言板、分页、软删除和 Element Plus 交互。', tags: ['Admin', 'Messages', 'Pagination'] },
  { version: 'v2', date: '2026-05-27', title: '个人网站全栈化', text: '新增 Vue Router、文章、帖子、小说阅读、点赞收藏和个人中心。', tags: ['Vue Router', 'FastAPI', 'MySQL'] },
  { version: 'v1', date: '2026-05-24', title: '首页搭建', text: '完成个人网站首页和基础视觉。', tags: ['HTML', 'CSS', 'Vue'] },
]
</script>
