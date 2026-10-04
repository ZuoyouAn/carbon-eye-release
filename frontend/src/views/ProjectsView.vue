<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Projects</p>
        <h1>项目作品详情</h1>
      </div>

      <div class="card-grid two-grid">
        <article class="content-card project-detail-card"><div class="card-meta"><span>Solar Atlas</span><span>原创3D / NASA资料</span></div><h2>太阳系图谱</h2><p>转动视角，选择八颗行星，暂停并靠近观察。模型与轨道均为压缩示意，不用于天象预测；设备不支持3D时仍可阅读资料。</p><RouterLink class="text-button" to="/solar-system">抬头看看 ↗</RouterLink></article>
        <article class="content-card project-detail-card"><div class="card-meta"><span>Life Guide</span><span>原文阅读 / CC BY 4.0</span></div><h2>高性价比人生指南</h2><p>按章节、关键词、成本与证据筛选原书条目；完整保留来源和备注，公开标明作者、同步版本和许可。不需要模型API。</p><RouterLink class="text-button" to="/life-guide">打开人生指南 ↗</RouterLink></article>
        <article class="content-card project-detail-card">
          <div class="card-meta"><span>Original Game</span><span>3D 探索 / 剧情生存 / 免费游玩</span></div>
          <h2>末世模拟器</h2><p>原创低多边形城市，键盘或摇杆移动、碰撞避障、搜集资源与撤离。也可切换三十天剧情，继续原来的天赋与结局。无需登录，不调用AI。</p>
          <div class="tag-list"><span>实时3D</span><span>键盘与触屏</span><span>旧剧情存档保留</span></div>
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
