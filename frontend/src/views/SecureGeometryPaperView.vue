<template>
  <main class="content-page">
    <section class="panel paper-note-page">
      <div class="section-heading">
        <div class="paper-note-actions">
          <RouterLink class="back-button" to="/secure-geometry">返回实验室</RouterLink>
          <RouterLink class="back-button" to="/projects">查看项目</RouterLink>
        </div>
        <p class="eyebrow">Paper Notes</p>
        <h1>空间位置关系的安全多方计算笔记</h1>
        <p>这页用自己的话整理论文思路，并解释当前网站里的 Python 算法代码是怎么把论文方案做成可交互实验的。</p>
      </div>

      <div class="paper-hero-card">
        <div>
          <p class="panel-label">论文主题</p>
          <h2>不暴露双方私有点、线、面参数，只计算空间位置关系</h2>
          <p>核心转化很漂亮：不直接求距离，也不反复比较比例，而是把“位置关系”变成“某个点是否满足某个方程”。这样点线、点面、线线、线面、面面都能用保密内积这个统一工具处理。</p>
        </div>
        <div class="paper-meta-list">
          <span>安全多方计算</span>
          <span>空间几何</span>
          <span>保密内积</span>
          <span>信息论安全思想</span>
        </div>
      </div>

      <div class="paper-note-grid">
        <article class="content-card paper-note-card">
          <div class="card-meta">
            <span>01</span>
            <span>Background</span>
          </div>
          <h2>背景：为什么要安全计算位置关系</h2>
          <p>现实里有些协作问题需要判断空间关系，但双方不愿公开自己的真实位置数据。例如两个参与方各自掌握一条空间轨迹，只想知道是否相交、平行或重合，而不想把轨迹方程告诉对方。</p>
          <p>传统方案常把问题转成距离、体积或比例判断，能解决的问题范围会受限，计算步骤也更重。论文的目标是用一个更统一的方法覆盖五类空间位置关系。</p>
        </article>

        <article class="content-card paper-note-card">
          <div class="card-meta">
            <span>02</span>
            <span>Core Idea</span>
          </div>
          <h2>核心思想：点是否为方程的解</h2>
          <p>如果 Bob 有一个平面方程 <code>Ax + By + Cz + D = 0</code>，Alice 有一个点 <code>[x, y, z]</code>，那么只要判断 <code>[x, y, z, 1]</code> 和 <code>[A, B, C, D]</code> 的内积是否为 0，就知道点是否在平面上。</p>
          <p>直线可以用两个平面的交线表示，所以“点在线上”就变成点同时满足两个平面方程。更复杂的线线、线面、面面关系，也能拆成几个点是否满足方程的问题。</p>
        </article>
      </div>

      <section class="paper-section">
        <div class="section-heading compact-heading">
          <p class="eyebrow">Scalar Product</p>
          <h2>保密内积协议怎么理解</h2>
          <p>Alice 有向量 X，Bob 有向量 Y。双方想知道 X 与 Y 的内积，但不想直接暴露自己的完整向量。</p>
        </div>

        <div class="protocol-flow">
          <article v-for="step in scalarSteps" :key="step.title" class="protocol-step">
            <span>{{ step.index }}</span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.text }}</p>
          </article>
        </div>
      </section>

      <section class="paper-section">
        <div class="section-heading compact-heading">
          <p class="eyebrow">Five Relations</p>
          <h2>五种点线面关系怎么拆</h2>
          <p>实验室里的五个按钮，对应论文中的五类协议。它们都围绕“取点、扩展成四维向量、做保密内积、判断是否为零”展开。</p>
        </div>

        <div class="relation-note-list">
          <article v-for="item in relationNotes" :key="item.title" class="relation-note-item">
            <div>
              <span>{{ item.protocol }}</span>
              <h3>{{ item.title }}</h3>
            </div>
            <p>{{ item.text }}</p>
          </article>
        </div>
      </section>

      <section class="paper-section">
        <div class="section-heading compact-heading">
          <p class="eyebrow">Implementation</p>
          <h2>我的代码是怎么实现的</h2>
          <p>当前项目没有把 PDF 原文搬进代码，而是把论文思想抽象成后端算法模块，再用 Vue 页面做交互演示。</p>
        </div>

        <div class="paper-note-grid">
          <article class="content-card paper-note-card">
            <h2>后端算法模块</h2>
            <p><code>secure_geometry.py</code> 负责解析点、线、面参数，使用 <code>Fraction</code> 做精确计算，避免浮点误差。</p>
            <p>直线统一用两个平面方程表示，平面统一用 <code>[A, B, C, D]</code> 表示，点统一用 <code>[x, y, z]</code> 表示。</p>
          </article>

          <article class="content-card paper-note-card">
            <h2>接口与页面</h2>
            <p>FastAPI 暴露 <code>/api/secure-geometry/calculate</code>，前端把 Alice 和 Bob 的 JSON 输入发给后端，后端返回关系结果和协议步骤。</p>
            <p>Vue 页面负责切换五种实验、填入示例参数、展示 Alice/Bob 输入区、结果区和协议说明。</p>
          </article>

          <article class="content-card paper-note-card">
            <h2>我做的增强</h2>
            <p>原始学习代码里线线关系主要判断重合、平行、相交；当前实验室额外补了“异面”情况，让三维直线关系更完整。</p>
            <p>同时补了非法平面、非法直线的输入校验，页面明确标注这是教学模拟，不是生产级密码系统。</p>
          </article>
        </div>
      </section>

      <section class="paper-section">
        <div class="paper-summary-card">
          <div>
            <p class="panel-label">Takeaway</p>
            <h2>这篇论文最值得学的点</h2>
          </div>
          <p>真正关键的不是公式有多复杂，而是建模方式：把空间几何问题统一转成“方程求值是否为零”，再用保密内积协议保护双方输入。这个思路很适合写进项目复盘，因为它同时体现了数学建模、后端算法封装和前端交互展示。</p>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { RouterLink } from 'vue-router'

const scalarSteps = [
  {
    index: '1',
    title: '双方准备输入',
    text: 'Alice 持有秘密向量 X，Bob 持有秘密向量 Y，目标是计算 X 和 Y 的内积。',
  },
  {
    index: '2',
    title: 'Alice 添加扰动',
    text: 'Alice 和 Bob 共同生成矩阵 C，Alice 再生成随机向量 R，用 C 和 R 构造扰动，把 X 变成被遮蔽后的向量。',
  },
  {
    index: '3',
    title: 'Bob 计算中间值',
    text: 'Bob 使用被遮蔽的向量和自己的 Y 计算一个临时内积，同时把矩阵投影结果发回 Alice。',
  },
  {
    index: '4',
    title: 'Alice 消掉扰动',
    text: 'Alice 根据 R 计算扰动项，再从临时内积里减掉它，得到真实内积结果。',
  },
]

const relationNotes = [
  {
    protocol: '协议 1',
    title: '点与直线',
    text: '直线由两个平面方程确定。点要在线上，就必须同时满足这两个方程，因此需要两次保密内积判断。',
  },
  {
    protocol: '协议 2',
    title: '点与平面',
    text: '把点扩展成四维向量，把平面写成四维系数向量。一次内积为零，就说明点在平面上。',
  },
  {
    protocol: '协议 3',
    title: '直线与直线',
    text: '先从 Alice 的直线上取两个点，判断它们是否都在 Bob 的直线上；不重合时再结合方向向量判断平行、相交或异面。',
  },
  {
    protocol: '协议 4',
    title: '直线与平面',
    text: '先判断直线上的两个点是否都在平面内；如果不是，再判断直线方向和平面法向量是否垂直，从而区分平行和相交。',
  },
  {
    protocol: '协议 5',
    title: '平面与平面',
    text: '从 Alice 的平面上取三个不共线点。三个点都满足 Bob 的平面方程则重合，否则根据法向量关系判断平行或相交。',
  },
]
</script>
