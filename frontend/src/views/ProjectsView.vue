<template>
  <main class="content-page">
    <section class="panel">
      <div class="section-heading">
        <RouterLink class="back-button" to="/">返回首页</RouterLink>
        <p class="eyebrow">Projects</p>
        <h1>项目作品详情</h1>
        <p>这里专门沉淀可以拿出来展示的项目：既有完整网站，也有算法实验和数据决策原型。</p>
      </div>

      <div class="card-grid two-grid">
        <article class="content-card project-detail-card">
          <div class="card-meta">
            <span>Project 01</span>
            <span>本地全栈项目</span>
          </div>
          <h2>左右的个人网站</h2>
          <p>一个从静态页面逐步升级到 Vue + FastAPI + MySQL 的个人网站，包含文章、帖子、小说、留言和后台管理。</p>
          <div class="tag-list">
            <span>Vue 3</span>
            <span>Vite</span>
            <span>FastAPI</span>
            <span>MySQL</span>
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
          <h2>园区碳眼</h2>
          <p>基于苏州空气质量、2024 气象和城市级 CO2 背景数据，构建面向苏州工业园区治理场景的减污降碳协同预警原型。</p>
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
