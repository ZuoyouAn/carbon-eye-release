<template>
  <main class="content-page store-page">
    <section class="section-heading"><p class="eyebrow">DIGITAL GOODS / COMING SOON</p><h1>好内容，<br>也可以被交付。</h1><p>未来的数字商品与卡密服务空间。先把体验搭好，再让有价值的作品上架。</p></section>
    <div class="store-notice" role="status"><strong>筹备中 · 暂不交易</strong><span>以下为商品类型规划，不代表已经上架。当前没有价格、库存、收款或卡密兑换。</span></div>
    <div class="store-filters" role="group" aria-label="商品类型"><button v-for="item in filters" :key="item" class="text-button" :aria-pressed="category === item" @click="category = item">{{ item }}</button></div>
    <section class="card-grid" aria-label="商品规划"><article v-for="item in visible" :key="item.name" class="content-card store-card"><span class="eyebrow">{{ item.type }} / 规划中</span><div class="store-symbol" aria-hidden="true">{{ item.symbol }}</div><h2>{{ item.name }}</h2><p>{{ item.text }}</p><div class="store-card-bottom"><span>未开放销售</span><button class="button button-secondary" @click="selected = selected === item.name ? '' : item.name" :aria-expanded="selected === item.name">{{ selected === item.name ? '收起规划' : '了解规划' }}</button></div><p v-if="selected === item.name" class="store-detail">{{ item.detail }} 正式上架前会明确授权范围、交付方式和售后条款。</p></article></section>
    <section class="panel store-roadmap"><p class="eyebrow">BEFORE LAUNCH</p><h2>上线前，还要准备这些</h2><div class="two-grid card-grid"><article><h3>透明的购买体验</h3><p class="panel-text">商品详情、授权来源、订单记录、退款和售后说明。只有确认服务可交付后，才开放购买。</p></article><article><h3>安全的数字交付</h3><p class="panel-text">后端确认支付、库存原子扣减、卡密加密保存、订单权限校验。不会把卡密列表放在浏览器或源码里。</p></article></div><RouterLink class="text-button" to="/projects">先看看已上线的项目 →</RouterLink></section>
  </main>
</template>
<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
const filters = ['全部', '学习资料', '工具授权', '站内权益']
const category = ref('全部')
const selected = ref('')
const catalog = [
  { name: '学习与创作资源', type: '学习资料', symbol: '↗', text: '整理可复用的笔记、模板与原创内容，让经验成为可以带走的作品。', detail: '计划使用账号内下载或订单下载链接交付。' },
  { name: '数字工具与授权', type: '工具授权', symbol: '⌘', text: '为自有或获得正规授权的工具预留展示位置，未来支持安全的卡密交付。', detail: '仅销售拥有分发权的产品，授权码仅向订单所有者展示。' },
  { name: '网站增值体验', type: '站内权益', symbol: '✦', text: '探索更深入的服务形式，基础内容与本地成长测评继续保持开放。', detail: '付费权益与管理员权限分离，购买不会获得后台管理权限。' },
]
const visible = computed(() => catalog.filter(item => category.value === '全部' || item.type === category.value))
</script>
<style scoped>
.store-page { padding-top: 56px; }.store-notice { display: flex; flex-wrap: wrap; gap: 14px; padding: 20px 24px; border: 1px solid var(--border); border-radius: 16px; background: var(--surface); line-height: 1.8; color: var(--muted); }.store-notice strong { color: var(--yellow); }.store-filters { display: flex; flex-wrap: wrap; gap: 10px; margin: 28px 0; }.store-filters [aria-pressed="true"] { background: var(--surface); border-color: var(--border); color: white; }.store-card { padding: 28px; border-radius: 18px; }.store-symbol { font-size: 48px; color: var(--blue); margin: 16px 0; }.store-card h2 { font-size: 23px; }.store-card p { line-height: 1.85; min-height: 84px; }.store-card-bottom { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px; margin-top: 28px; color: var(--muted); font-size: 13px; }.store-detail { padding-top: 18px; border-top: 1px solid var(--border); }.store-roadmap { margin-top: 34px; border-radius: 18px; }.store-roadmap > a { display: inline-block; margin-top: 24px; }
</style>
