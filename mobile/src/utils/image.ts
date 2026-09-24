import * as ImagePicker from 'expo-image-picker'
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator'

export const MAX_BYTES = 5 * 1024 * 1024

const SIZE = 256
const QUALITY = 0.82

export class ImageError extends Error {}

export async function pickAvatarDataUrl(): Promise<string | null> {
  const picked = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    allowsEditing: true,
    aspect: [1, 1],
    quality: 1,
  })
  if (picked.canceled || !picked.assets[0]) return null

  const asset = picked.assets[0]
  if (asset.fileSize && asset.fileSize > MAX_BYTES) {
    throw new ImageError(`이미지는 ${MAX_BYTES / 1024 / 1024}MB 이하만 올릴 수 있어요.`)
  }

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
