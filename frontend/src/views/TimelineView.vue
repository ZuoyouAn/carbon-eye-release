<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Timeline</p>
        <h1>成长时间线</h1>
        <p>这里记录网站从 0 到 1 的演进过程，也可以当作你的学习轨迹。</p>
      </div>

      <div class="timeline-list">
        <article v-for="item in timeline" :key="item.title" class="content-card">
          <div class="card-meta">
            <span>{{ item.date }}</span>
            <span>{{ item.type }}</span>
          </div>
          <h2>{{ item.title }}</h2>
          <p>{{ item.text }}</p>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'

const timeline = [
  { date: 'v1', type: '静态页面', title: '个人网站首页', text: '先完成首页视觉、个人介绍、作品入口和联系入口。' },
  { date: 'v2', type: '全栈跑通', title: '接入 FastAPI 和 MySQL', text: '完成登录、文章、帖子、小说、点赞、收藏和个人中心。' },
  { date: 'v3', type: '内容管理', title: '后台管理和留言板', text: '补齐文章管理、评论治理、留言板、分页和状态控制。' },
]
</script>
