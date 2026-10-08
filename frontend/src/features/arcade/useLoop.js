import { onUnmounted } from 'vue'
export function useArcadeLoop(step, publish, paint, paintFps = 30) {
  const paintInterval = 1000 / Math.max(15, Math.min(60, Number(paintFps) || 30))
  let frame = 0, last = 0, lastPaint = 0, lastPublish = 0, running = false
  function tick(now) {
    if (!running) return
    const dt = last ? Math.min((now - last) / 1000, .05) : 0; last = now
    const keepRunning = step(dt)
    if (now - lastPublish >= 100 || !keepRunning) { publish(); lastPublish = now }
    if (now - lastPaint >= paintInterval - .5 || !keepRunning) { paint(); lastPaint = now }
    if (keepRunning && running) frame = requestAnimationFrame(tick); else running = false
  }
  function stop() { running = false; cancelAnimationFrame(frame) }
  function start() { stop(); running = true; last = lastPaint = lastPublish = 0; frame = requestAnimationFrame(tick) }
  onUnmounted(stop)
  return { start, stop }
}
