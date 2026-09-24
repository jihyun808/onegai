import AsyncStorage from '@react-native-async-storage/async-storage'

/**
 * 기기 저장소. 웹의 localStorage 자리다.
 *
 * 웹은 `storage` 이벤트로 다른 화면에 변경을 알렸는데 앱엔 없다.
 * 같은 키를 보는 훅끼리 여기 구독해서 서로 맞춘다.
 */
const listeners = new Map<string, Set<() => void>>()

export function subscribe(key: string, listener: () => void) {
  if (!listeners.has(key)) listeners.set(key, new Set())
  listeners.get(key)!.add(listener)
  return () => {
    listeners.get(key)?.delete(listener)
  }
}

function emit(key: string) {
  for (const listener of listeners.get(key) ?? []) listener()
}

export async function readJson<T>(key: string, fallback: T): Promise<T> {
  try {
    const raw = await AsyncStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    // 손상된 값이 들어 있으면 기본값으로 시작한다
    return fallback
  }
}

export async function writeJson(key: string, value: unknown) {
  await AsyncStorage.setItem(key, JSON.stringify(value))
  emit(key)
}

export async function removeKey(key: string) {
  await AsyncStorage.removeItem(key)
  emit(key)
}
