import * as ImagePicker from 'expo-image-picker'
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator'

/** 프로필 이미지 처리. */

/** 원본 파일 크기 상한. 이보다 크면 읽지도 않는다. */
export const MAX_BYTES = 5 * 1024 * 1024

/**
 * 저장 크기. 프로필은 작게 나오므로 256px이면 충분하다.
 * 서버 상한(AVATAR_MAX_BYTES 400KB)을 넉넉히 밑돈다.
 */
const SIZE = 256
const QUALITY = 0.82

export class ImageError extends Error {}

/**
 * 사진첩에서 골라 정사각형으로 잘라 축소한 뒤 data URL로 돌려준다.
 * 고르지 않고 닫으면 null.
 */
export async function pickAvatarDataUrl(): Promise<string | null> {
  const picked = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    // 시스템 편집기로 정사각형을 직접 맞추게 한다
    allowsEditing: true,
    aspect: [1, 1],
    quality: 1,
  })
  if (picked.canceled || !picked.assets[0]) return null

  const asset = picked.assets[0]
  if (asset.fileSize && asset.fileSize > MAX_BYTES) {
    throw new ImageError(`이미지는 ${MAX_BYTES / 1024 / 1024}MB 이하만 올릴 수 있어요.`)
  }

  // 편집기를 거쳐도 기기에 따라 정사각형이 아닐 수 있어 가운데를 한 번 더 자른다
  const side = Math.min(asset.width, asset.height)
  try {
    const image = await ImageManipulator.manipulate(asset.uri)
      .crop({
        originX: (asset.width - side) / 2,
        originY: (asset.height - side) / 2,
        width: side,
        height: side,
      })
      .resize({ width: SIZE, height: SIZE })
      .renderAsync()
    const saved = await image.saveAsync({
      format: SaveFormat.JPEG,
      compress: QUALITY,
      base64: true,
    })
    if (!saved.base64) throw new Error('no base64')
    return `data:image/jpeg;base64,${saved.base64}`
  } catch {
    throw new ImageError('이미지를 처리하지 못했어요.')
  }
}
