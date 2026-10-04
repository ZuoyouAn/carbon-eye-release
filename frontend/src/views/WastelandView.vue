<template>
  <div class="arcade-modes"><span>SPACE / PLAY</span><nav aria-label="游戏模式"><RouterLink to="/wasteland" :aria-current="!story ? 'page' : undefined">3D 城市探索</RouterLink><RouterLink to="/wasteland?mode=story" :aria-current="story ? 'page' : undefined">三十天剧情</RouterLink></nav></div>
  <Suspense><component :is="story ? Story : Expedition" /><template #fallback><main class="content-page"><p class="state-text" role="status">正在加载游戏…</p></main></template></Suspense>
</template>
<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
const route = useRoute()
const story = computed(() => route.query.mode === 'story')
const Story = defineAsyncComponent(() => import('./WastelandStoryView.vue'))
const Expedition = defineAsyncComponent(() => import('./WastelandExpeditionView.vue'))
</script>
<style scoped>
.arcade-modes{width:var(--container);margin:20px auto 0;display:flex;align-items:center;justify-content:space-between;gap:18px;color:var(--muted);font-size:11px;letter-spacing:.08em}.arcade-modes nav{display:flex;gap:4px;padding:5px;background:#e9ebef;border-radius:999px;letter-spacing:0}.arcade-modes a{padding:10px 18px;border-radius:999px;font-size:12px}.arcade-modes a[aria-current=page]{background:#fff;color:#0066cc;box-shadow:0 2px 7px #1d1d1f0a}@media(max-width:540px){.arcade-modes>span{display:none}.arcade-modes{justify-content:center}}
</style>
