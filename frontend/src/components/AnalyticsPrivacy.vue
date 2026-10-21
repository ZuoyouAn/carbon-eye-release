<template>
  <details class="analytics-privacy">
    <summary>匿名访问统计</summary>
    <p>仅记录页面浏览与匿名浏览器数，不保存 IP、账号、搜索词或播放链接。标识 30 天轮换，统计展示近 90 天；过期明细在下次统计请求时清理，仅管理员查看汇总。尊重浏览器 DNT / GPC 设置。</p>
    <button type="button" @click="toggle">{{ disabled ? '已关闭统计 · 点击允许' : '关闭本机访问统计' }}</button>
  </details>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { optedOut, setOptOut } from '../../../shared/traffic-tracker.mjs'
const disabled = ref(false)
onMounted(() => { disabled.value = optedOut() })
function toggle() { disabled.value = !disabled.value; setOptOut(disabled.value) }
</script>
<style scoped>
.analytics-privacy{max-width:420px;font-size:13px;line-height:1.8}.analytics-privacy summary{cursor:pointer}.analytics-privacy p{margin:10px 0}.analytics-privacy button{border:1px solid #cdd5e2;border-radius:8px;padding:7px 11px;color:#315bb5;background:white;cursor:pointer}
</style>
