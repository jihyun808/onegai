import { useCallback, useEffect, useState } from 'react'

import type { BrandFilter, SearchType } from '../types/karaoke'

/**
 * 앱 설정. 기기에 저장한다.
 *
 * 계정에 묶지 않는 이유 — 기기마다 다르게 쓰고 싶을 수 있고
 * (집 컴퓨터는 전체, 폰은 자주 가는 노래방 브랜드), 로그인 없이도
 * 설정은 유지돼야 하기 때문이다.
 */
const STORAGE_KEY = 'kada:settings:v1'
const CHANGED = 'kada:settings:changed'

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

function read(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    // 저장된 뒤에 항목이 늘어났을 수 있으므로 기본값 위에 덮는다
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
