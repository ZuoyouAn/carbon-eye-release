export function visibleLabels(candidates, width, height) {
  const boxes = [], visible = new Set()
  for (const item of [...candidates].sort((a, b) => (b.priority || 0) - (a.priority || 0))) {
    if (!item.visible || ![item.x, item.y, item.width, item.height].every(Number.isFinite)) continue
    const box = { left: item.x - item.width / 2, right: item.x + item.width / 2, top: item.y - item.height / 2, bottom: item.y + item.height / 2 }
    if (box.left < 6 || box.right > width - 6 || box.top < 62 || box.bottom > height - 52) continue
    if (boxes.some(b => box.left < b.right + 5 && box.right > b.left - 5 && box.top < b.bottom + 5 && box.bottom > b.top - 5)) continue
    boxes.push(box); visible.add(item.id)
  }
  return visible
}
