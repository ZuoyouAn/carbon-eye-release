<template>
  <figure class="expedition-map"><figcaption>战术地图 <span>北 ↑</span></figcaption><svg viewBox="0 0 100 100" role="img" aria-label="固定北向地图：蓝点是你，红点是巡逻者，金色为下一目标；建筑不可穿越">
    <rect width="100" height="100" rx="4" fill="#f5f7ee" /><path d="M50 0V100M0 50H100M0 85H100M15 0V100" stroke="#e1e6d5" stroke-width="6" />
    <rect v-for="(building, i) in WORLD.buildings" :key="`b-${i}`" :x="mapPoint({x: building.x - building.w / 2,z: building.z}).x" :y="mapPoint({x: building.x,z: building.z - building.d / 2}).y" :width="building.w / 34 * 100" :height="building.d / 34 * 100" rx="1" fill="#b8b8a8" />
    <circle v-for="item in loot.filter(item => !item.taken)" :key="item.id" :cx="mapPoint(item).x" :cy="mapPoint(item).y" r="1.8" :fill="item.kind === 'cell' ? '#338fc4' : item.kind === 'med' ? '#b4574e' : '#987139'" />
    <path :d="`M${mapPoint(WORLD.beacon).x - 2} ${mapPoint(WORLD.beacon).y}h4m-2 -2v4`" stroke="#338fc4" stroke-width="1.4" />
    <rect :x="mapPoint(WORLD.exit).x - 2" :y="mapPoint(WORLD.exit).y - 2" width="4" height="4" fill="#33876a" />
    <circle v-for="(enemy, i) in enemies" :key="`e-${i}`" :cx="mapPoint(enemy).x" :cy="mapPoint(enemy).y" r="2" fill="#b84e4d" />
    <circle v-if="objective" :cx="mapPoint(objective).x" :cy="mapPoint(objective).y" r="3.7" fill="none" stroke="#c18b2a" stroke-width="1.2" />
    <circle :cx="mapPoint(player).x" :cy="mapPoint(player).y" r="2.8" fill="#0066cc" stroke="#fff" stroke-width="1" />
  </svg><p>蓝＝你 · 红＝巡逻者 · 金圈＝下一目标</p></figure>
</template>
<script setup>
import { WORLD } from '../features/wasteland/expedition'
import { mapPoint } from '../features/wasteland/navigation'
defineProps({ player: { type: Object, required: true }, loot: { type: Array, default: () => [] }, enemies: { type: Array, default: () => [] }, objective: { type: Object, default: null } })
</script>
<style scoped>
.expedition-map{margin:22px 0;padding:16px;border:1px solid var(--border);border-radius:16px;background:#fafbf8;min-width:0}.expedition-map figcaption{display:flex;justify-content:space-between;font-size:14px;color:#405b54;margin-bottom:10px}.expedition-map svg{display:block;width:100%;max-height:220px;border-radius:9px}.expedition-map p{font-size:14px;line-height:1.7;color:#54615c;margin:10px 0 0}@media(max-width:900px){.expedition-map{max-width:320px}}
</style>
