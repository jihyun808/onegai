/** 프로필 이미지 처리. */

export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const ACCEPT_ATTR = ACCEPTED_TYPES.join(',')

/** 원본 파일 크기 상한. 이보다 크면 읽지도 않는다. */
export const MAX_BYTES = 5 * 1024 * 1024

/**
 * 저장 크기. 프로필은 작게 나오므로 256px이면 충분하다.
 *
 * 원본을 그대로 두면 안 된다 — 지금은 서버가 없어 localStorage에 담는데
 * 용량이 5MB 남짓이라 사진 한 장으로 꽉 찬다.
 */
const SIZE = 256
const QUALITY = 0.82

export class ImageError extends Error {}

/** 정사각형으로 잘라 축소한 뒤 data URL로 돌려준다. */
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

  // 짧은 변 기준으로 가운데를 정사각형으로 잘라낸다
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

  // 투명 배경이 검게 나오지 않도록 JPEG 대신 WEBP를 먼저 시도한다
  const webp = canvas.toDataURL('image/webp', QUALITY)
  return webp.startsWith('data:image/webp') ? webp : canvas.toDataURL('image/jpeg', QUALITY)
}
