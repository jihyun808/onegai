import AsyncStorage from '@react-native-async-storage/async-storage'

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
