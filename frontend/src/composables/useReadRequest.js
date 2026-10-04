import { onUnmounted, ref } from 'vue'
import { createLatestRead } from '../utils/latestRead.js'

export function useReadRequest(success) {
  const loading = ref(false), error = ref('')
  const lane = createLatestRead({
    start() { loading.value = true; error.value = '' },
    success,
    failure(reason) { error.value = reason.message || '读取失败，请重试。' },
    finish() { loading.value = false },
  })
  onUnmounted(lane.dispose)
  return { ...lane, loading, error }
}
