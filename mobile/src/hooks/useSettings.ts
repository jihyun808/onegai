import { useCallback, useEffect, useState } from 'react'

import type { BrandFilter, SearchType } from '../types/karaoke'
import { readJson, subscribe, writeJson } from '../utils/storage'

/**
 * 앱 설정. 기기에 저장한다.
 *
 * 계정에 묶지 않는 이유 — 기기마다 다르게 쓰고 싶을 수 있고
 * (집 컴퓨터는 전체, 폰은 자주 가는 노래방 브랜드), 로그인 없이도
 * 설정은 유지돼야 하기 때문이다.
 */
const STORAGE_KEY = 'kada:settings:v1'

export type SortOrder = 'release' | 'no'

export interface Settings {
  searchType: SearchType
  brand: BrandFilter
  /** 한국어로 된 곡을 결과에 보일지 */
  showKorean: boolean
  sort: SortOrder
}

export const DEFAULTS: Settings = {
  searchType: 'song',
  brand: 'all',
  showKorean: false,
  sort: 'release',
}

// 저장된 뒤에 항목이 늘어났을 수 있으므로 기본값 위에 덮는다
const read = async (): Promise<Settings> => ({
  ...DEFAULTS,
  ...(await readJson<Partial<Settings>>(STORAGE_KEY, {})),
})

export function useSettings() {
  // 저장소는 비동기라 첫 그림은 기본값이다. 곧바로 저장된 값으로 바뀐다.
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
