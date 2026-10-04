// Resize on device; the server independently validates and strips metadata again.
export async function prepareAvatar(file) {
  if (!file || !['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) throw new Error('请选择5MB以内的JPEG、PNG或WebP图片。')
  const url = URL.createObjectURL(file)
  try {
    const image = await new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = () => reject(new Error('图片无法读取，请换一张。'))
      image.src = url
    })
    const canvas = document.createElement('canvas'); canvas.width = 128; canvas.height = 128
    const context = canvas.getContext('2d')
    if (!context) throw new Error('当前浏览器无法处理图片。')
    const edge = Math.min(image.naturalWidth, image.naturalHeight)
    context.fillStyle = '#172435'; context.fillRect(0, 0, 128, 128)
    context.drawImage(image, (image.naturalWidth - edge) / 2, (image.naturalHeight - edge) / 2, edge, edge, 0, 0, 128, 128)
    const dataUrl = canvas.toDataURL('image/webp', .8)
    return { preview: dataUrl, image_base64: dataUrl.split(',')[1] }
  } finally { URL.revokeObjectURL(url) }
}
