<template>
  <main class="ghosttrack-page">
    <div class="ghosttrack-heading"><RouterLink to="/" class="back-button">返回首页</RouterLink><a :href="standaloneUrl" target="_blank" rel="noopener noreferrer">独立打开查询工作台 ↗</a></div>
    <iframe ref="frame" :src="workbenchUrl" :style="{ height: `${height}px` }" title="GhostTrack 公开信息查询与原理说明" referrerpolicy="no-referrer" class="ghosttrack-frame"></iframe>
  </main>
</template>
<script setup>
import { RouterLink } from 'vue-router'
import { onMounted, onUnmounted, ref } from 'vue'
import { API_BASE } from '../api/client'
const frame = ref(null), height = ref(1900)
function resize(event) {
  if (event.origin === location.origin && event.source === frame.value?.contentWindow && event.data?.type === 'ghosttrack-height' && Number.isFinite(event.data.height)) height.value = Math.min(8000, Math.max(500, event.data.height))
}
onMounted(() => window.addEventListener('message', resize))
onUnmounted(() => window.removeEventListener('message', resize))
const workbenchUrl = `/ghosttrack-workbench/index.html?api=${encodeURIComponent(API_BASE.replace(/\/$/, ''))}`
const standaloneUrl = workbenchUrl
</script>
<style scoped>
.ghosttrack-page{max-width:1230px;margin:auto;padding:12px 16px 30px}.ghosttrack-heading{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:14px;padding:0 10px}.ghosttrack-frame{width:100%;height:1900px;border:0;background:#f5f5f7;display:block;border-radius:20px;margin-top:12px}@media(max-width:800px){.ghosttrack-frame{height:2850px}.ghosttrack-page{padding-inline:0}}
</style>
