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
  { version: 'v4.1', date: '2026-10-05', title: '加载更轻，聊天更顺', text: '组件样式按页面加载；聊天支持历史阅读位置保留、新消息提示和切换会话暂存草稿，明确私聊发送状态，网络失败自动退避。游戏遵循减少动态效果偏好。', tags: ['Performance', 'Chat UX', 'Accessibility'] },
  { version: 'v4', date: '2026-10-04', title: '左右的Space：连接与冒险', text: '统一Space品牌，新增持久化用户头像、公共大厅、邀请制小群和双向同意私聊；上线原创文字游戏末世模拟器，支持本机存档与生存日记。', tags: ['Avatar', 'Chat', 'Wasteland'] },
  { version: 'v3', date: '2026-05-28', title: '内容管理完整化', text: '新增后台内容管理、留言板、分页、软删除和 Element Plus 交互。', tags: ['Admin', 'Messages', 'Pagination'] },
  { version: 'v2', date: '2026-05-27', title: 'Space 全栈化', text: '新增 Vue Router、文章、帖子、小说阅读、点赞收藏和个人中心。', tags: ['Vue Router', 'FastAPI', 'MySQL'] },
  { version: 'v1', date: '2026-05-24', title: '首页搭建', text: '完成 Space 首页和基础视觉。', tags: ['HTML', 'CSS', 'Vue'] },
]
</script>
