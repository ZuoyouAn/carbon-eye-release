<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Projects</p>
        <h1>项目作品详情</h1>
      </div>

      <div class="card-grid two-grid">
        <article class="content-card project-detail-card">
          <div class="card-meta"><span>Original Game</span><span>文字生存 / 免费游玩</span></div>
          <h2>末世模拟器</h2><p>原创末日世界，六种天赋、四项属性、随机遭遇与四种结局。无需登录，不调用AI；可选本机存档与导出生存日记。</p>
          <div class="tag-list"><span>30天生存</span><span>选择与后果</span><span>可复现世界种子</span></div>
          <RouterLink class="text-button" to="/wasteland">走进长夜 →</RouterLink>
        </article>
        <article class="content-card project-detail-card">
          <div class="card-meta"><span>Space Chat</span><span>持久化 / 成员权限</span></div>
          <h2>Space 聊天室</h2><p>公共大厅、邀请制小群和双向同意的私聊。支持头像、拉黑与撤回；消息保留30天，应用内管理员不能读取非成员私聊。</p>
          <div class="tag-list"><span>公共群聊</span><span>一对一私聊</span><span>隐私边界</span></div>
          <RouterLink class="text-button" to="/chat">进入聊天室 →</RouterLink>
        </article>
        <article class="content-card project-detail-card">
          <div class="card-meta"><span>Human 3.0</span><span>四维成长 / 自我反思</span></div>
          <h2>四维成长评估</h2>
          <p>24 道选择题与根据回答调整的追问，区分日常实践与压力下的差异。基础测评免费、无需登录，默认在浏览器内处理；AI补充需另行同意。</p>
          <div class="tag-list"><span>四象限</span><span>固定问卷</span><span>行动计划</span></div>
          <RouterLink class="text-button" to="/human3">开始了解自己</RouterLink>
        </article>
        <article class="content-card project-detail-card">
          <div class="card-meta">
            <span>Project 01</span>
            <span>已上线 / 全栈项目</span>
          </div>
          <h2>左右的Space</h2>
          <p>从静态页面逐步升级的 Vue + FastAPI 交流空间，现使用 Neon PostgreSQL 持久化数据，包含文章、帖子、小说、头像、聊天和分级权限管理。</p>
          <div class="tag-list">
            <span>Vue 3</span>
            <span>Vite</span>
            <span>FastAPI</span>
            <span>PostgreSQL</span>
            <span>Element Plus</span>
          </div>
          <RouterLink class="text-button" to="/">查看首页</RouterLink>
        </article>

        <article class="content-card project-detail-card">
          <div class="card-meta">
            <span>Project 02</span>
            <span>论文复现 / 算法实验</span>
          </div>
          <h2>安全多方计算空间位置关系实验室</h2>
          <p>基于“空间位置关系的安全多方计算及其应用”论文思路，把点线、点面、线线、线面、面面关系封装成可交互实验。</p>
          <div class="tag-list">
            <span>Python</span>
            <span>FastAPI</span>
            <span>保密内积</span>
            <span>计算几何</span>
            <span>论文复现</span>
          </div>
          <RouterLink class="text-button" to="/secure-geometry">进入实验室</RouterLink>
          <RouterLink class="text-button" to="/secure-geometry/paper">阅读论文笔记</RouterLink>
        </article>

        <article class="content-card project-detail-card">
          <div class="card-meta">
            <span>Project 03</span>
            <span>减污降碳 / 数据预警</span>
          </div>
          <h2>焦作园区碳眼</h2>
          <p>面向焦作工业园区治理场景的减污降碳协同预警原型。当前沿用苏州公开数据验证功能，待接入焦作本地数据后形成焦作实证分析。</p>
          <div class="tag-list">
            <span>Vue 3</span>
            <span>FastAPI</span>
            <span>ECharts</span>
            <span>空气质量</span>
            <span>双碳原型</span>
          </div>
          <RouterLink class="text-button" to="/carbon-eye">进入专题系统</RouterLink>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
