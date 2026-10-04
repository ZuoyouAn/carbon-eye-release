<template><span class="user-avatar" :style="{ '--avatar-size': `${size}px` }"><img v-if="user?.id && !failed" :src="`${API_BASE}/api/users/${user.id}/avatar?v=${revision}`" :alt="`${user.username || '用户'}的头像`" @error="failed = true"><span v-else aria-hidden="true">{{ (user?.username || '左').slice(0, 1).toUpperCase() }}</span></span></template>
<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { API_BASE } from '../api/client.js'
const props = defineProps({ user: Object, size: { type: Number, default: 38 } })
const failed = ref(false), revision = ref('')
function updated(event) { if (event.detail?.userId === props.user?.id) { failed.value = false; revision.value = event.detail.version || Date.now() } }
window.addEventListener('avatar-updated', updated)
onUnmounted(() => window.removeEventListener('avatar-updated', updated))
watch(() => props.user?.id, () => { failed.value = false; revision.value = '' })
</script>
<style scoped>.user-avatar { display: inline-flex; flex-shrink: 0; align-items: center; justify-content: center; width: var(--avatar-size); height: var(--avatar-size); border-radius: 30%; background: linear-gradient(140deg, #abebd2, #aebdff); color: #102436; font-weight: 800; overflow: hidden; vertical-align: middle; }.user-avatar img { width: 100%; height: 100%; object-fit: cover; }</style>
