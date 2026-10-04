import { onMounted, onUnmounted, ref } from 'vue'
export function useExpandedScene(onEscape = () => {}) {
  const expanded = ref(false)
  let previousOverflow = '', ownsLock = false
  function toggle() {
    if (!expanded.value) { previousOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden'; ownsLock = true; expanded.value = true }
    else collapse()
  }
  function collapse() { expanded.value = false; if (ownsLock) { document.body.style.overflow = previousOverflow; ownsLock = false } }
  function escape(event) { if (event.key === 'Escape' && expanded.value) { event.preventDefault(); event.stopImmediatePropagation(); collapse(); onEscape() } }
  onMounted(() => window.addEventListener('keydown', escape))
  onUnmounted(() => { collapse(); window.removeEventListener('keydown', escape) })
  return { expanded, toggle, collapse }
}
