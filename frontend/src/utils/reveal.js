// Content remains visible without JavaScript or with reduced-motion preference.
export const reveal = {
  mounted(element) {
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    element.classList.add('reveal-pending')
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { element.classList.add('reveal-visible'); observer.disconnect() }
    }, { threshold: 0.08, rootMargin: '0px 0px -12px 0px' })
    element.__spaceReveal = observer
    observer.observe(element)
  },
  unmounted(element) { element.__spaceReveal?.disconnect(); delete element.__spaceReveal },
}
