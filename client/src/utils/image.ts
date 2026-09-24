export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const ACCEPT_ATTR = ACCEPTED_TYPES.join(',')

export const MAX_BYTES = 5 * 1024 * 1024

const SIZE = 256
const QUALITY = 0.82

export class ImageError extends Error {}

export async function toAvatarDataUrl(file: File): Promise<string> {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    throw new ImageError('JPG, PNG, WEBP 파일만 올릴 수 있어요.')
  }
  if (file.size > MAX_BYTES) {
    throw new ImageError(`이미지는 ${MAX_BYTES / 1024 / 1024}MB 이하만 올릴 수 있어요.`)
  }

  const bitmap = await createImageBitmap(file).catch(() => {
    throw new ImageError('이미지를 읽지 못했어요.')
  })

  const side = Math.min(bitmap.width, bitmap.height)
  const sx = (bitmap.width - side) / 2
  const sy = (bitmap.height - side) / 2

  const canvas = document.createElement('canvas')
  canvas.width = SIZE
  canvas.height = SIZE

  const ctx = canvas.getContext('2d')
  if (!ctx) throw new ImageError('이미지를 처리하지 못했어요.')

  ctx.drawImage(bitmap, sx, sy, side, side, 0, 0, SIZE, SIZE)
  bitmap.close()

  const webp = canvas.toDataURL('image/webp', QUALITY)
  return webp.startsWith('data:image/webp') ? webp : canvas.toDataURL('image/jpeg', QUALITY)
}
