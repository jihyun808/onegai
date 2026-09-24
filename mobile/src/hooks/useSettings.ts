import { useCallback, useEffect, useState } from 'react'

import type { BrandFilter, SearchType } from '../types/karaoke'
import { readJson, subscribe, writeJson } from '../utils/storage'

const STORAGE_KEY = 'kada:settings:v1'

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

const read = async (): Promise<Settings> => ({
  ...DEFAULTS,
  ...(await readJson<Partial<Settings>>(STORAGE_KEY, {})),
})

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(DEFAULTS)

  useEffect(() => {
    const sync = () => void read().then(setSettings)
    sync()
    return subscribe(STORAGE_KEY, sync)
  }, [])

  const update = useCallback(async (patch: Partial<Settings>) => {
    const next = { ...(await read()), ...patch }
    setSettings(next)
    await writeJson(STORAGE_KEY, next)
  }, [])

  return { settings, update }
}
