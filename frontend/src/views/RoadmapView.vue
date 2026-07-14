<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Learning Roadmap</p>
        <h1>学习路线</h1>
        <p>这条路线围绕当前个人网站项目展开，边学边改，学到的东西会直接长到项目里。</p>
      </div>

      <div class="timeline-list">
        <article v-for="stage in stages" :key="stage.title" class="content-card">
          <div class="card-meta">
            <span>{{ stage.step }}</span>
            <span>{{ stage.level }}</span>
          </div>
          <h2>{{ stage.title }}</h2>
          <p>{{ stage.text }}</p>
          <div class="tag-list">
            <span v-for="tag in stage.tags" :key="tag">{{ tag }}</span>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'

const stages = [
  { step: '01', level: '基础', title: 'HTML / CSS / JavaScript', text: '先把页面结构、样式、事件、数组和对象看懂。', tags: ['DOM', '事件', '响应式布局'] },
  { step: '02', level: '前端框架', title: 'Vue 3', text: '重点理解 ref、computed、组件、路由、接口请求和状态管理。', tags: ['Vue Router', '组件拆分', 'fetch'] },
  { step: '03', level: '后端', title: 'Python + FastAPI', text: '学习接口、请求体、依赖注入、权限判断和错误处理。', tags: ['REST API', 'Token', 'CORS'] },
  { step: '04', level: '数据库', title: 'MySQL + SQLAlchemy', text: '理解表、字段、主键、关联、分页、软删除和迁移。', tags: ['MySQL', 'ORM', '分页'] },
  { step: '05', level: '工程', title: '部署和维护', text: '最后学习环境变量、构建、部署、日志和数据备份。', tags: ['Vite Build', 'Netlify', 'Server'] },
]
</script>
