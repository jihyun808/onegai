import { useCallback, useEffect, useState } from 'react'

import type { BrandFilter, SearchType } from '../types/karaoke'

const STORAGE_KEY = 'kada:settings:v1'
const CHANGED = 'kada:settings:changed'

export type SortOrder = 'release' | 'no'

export interface Settings {
  searchType: SearchType
  brand: BrandFilter
  showKorean: boolean
  sort: SortOrder
}

export const DEFAULTS: Settings = {
  searchType: 'song',
  brand: 'all',
  showKorean: false,
  sort: 'release',
}

function read(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : DEFAULTS
  } catch {
    return DEFAULTS
  }
}

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(read)

  useEffect(() => {
    const sync = () => setSettings(read())
    window.addEventListener(CHANGED, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(CHANGED, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const update = useCallback((patch: Partial<Settings>) => {
    const next = { ...read(), ...patch }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    window.dispatchEvent(new Event(CHANGED))
    setSettings(next)
  }, [])

  return { settings, update }
}
