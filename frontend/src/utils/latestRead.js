// Reads only. Cancelling a browser request does not roll back a server mutation.
export function createLatestRead({ start = () => {}, success = () => {}, failure = () => {}, finish = () => {} } = {}) {
  let active = null, disposed = false
  function cancel() {
    const previous = active
    active = null
    if (previous) { previous.abort(); finish() }
  }
  return {
    cancel,
    dispose() { disposed = true; cancel() },
    async run(request) {
      if (disposed) return
      cancel()
      const controller = new AbortController()
      active = controller
      start()
      try {
        const data = await request(controller.signal)
        if (active === controller && !controller.signal.aborted) { success(data); return data }
      } catch (error) {
        if (active === controller && !controller.signal.aborted) failure(error)
      } finally {
        if (active === controller) { active = null; finish() }
      }
    },
  }
}
