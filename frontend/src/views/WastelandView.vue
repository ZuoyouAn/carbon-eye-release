<template>
  <div class="arcade-modes"><span>SPACE / PLAY</span><nav aria-label="游戏模式"><RouterLink to="/wasteland" :aria-current="mode==='camp' ? 'page' : undefined">基地建造与生存</RouterLink><RouterLink to="/wasteland?mode=exploration" :aria-current="mode==='exploration' ? 'page' : undefined">城市探索</RouterLink><RouterLink to="/wasteland?mode=story" :aria-current="mode==='story' ? 'page' : undefined">三十天剧情</RouterLink></nav></div>
  <Suspense><component :is="mode==='story' ? Story : mode==='exploration' ? Expedition : Settlement" /><template #fallback><main class="content-page"><p class="state-text" role="status">正在加载游戏…</p></main></template></Suspense>
</template>
<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
const route = useRoute()
const mode = computed(() => ['story','exploration'].includes(route.query.mode) ? route.query.mode : 'camp')
const Settlement = defineAsyncComponent(() => import('./WastelandSettlementView.vue'))
const Story = defineAsyncComponent(() => import('./WastelandStoryView.vue'))
const Expedition = defineAsyncComponent(() => import('./WastelandExpeditionView.vue'))
</script>
<style scoped>
.arcade-modes{width:var(--container);margin:20px auto 0;display:flex;align-items:center;justify-content:space-between;gap:18px;color:var(--muted);font-size:14px;letter-spacing:.08em}.arcade-modes nav{display:flex;gap:4px;padding:5px;background:#e9ebef;border-radius:18px;letter-spacing:0;flex-wrap:wrap}.arcade-modes a{padding:10px 18px;border-radius:14px;font-size:14px}.arcade-modes a[aria-current=page]{background:#fff;color:#0066cc;box-shadow:0 2px 7px #1d1d1f0a}@media(max-width:540px){.arcade-modes>span{display:none}.arcade-modes{justify-content:center}.arcade-modes a{padding:10px 12px}}
</style>
