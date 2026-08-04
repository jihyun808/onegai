import { useCallback, useEffect, useState } from 'react'

import type { SongGroup } from '../types/karaoke'

/**
 * 즐겨찾기.
 *
 * 서버에 인증/즐겨찾기 API가 아직 없어서 기기 로컬(localStorage)에 저장한다.
 * 로그인이 붙으면 이 데이터를 서버로 옮기는 마이그레이션이 필요하다.
 * DECISIONS.md 참고.
 */
const STORAGE_KEY = 'kada:bookmarks:v1'

export interface Bookmark {
  match_key: string
  title: string
  singer: string
  brands: SongGroup['brands']
  saved_at: string
}

function read(): Bookmark[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Bookmark[]) : []
  } catch {
    // 손상된 값이 들어 있으면 빈 목록으로 시작한다
    return []
  }
}

/** 탭이 여러 개 열려 있을 때 서로 반영되도록 하는 신호 */
const CHANGED = 'kada:bookmarks:changed'

export function useBookmarks() {
  const [items, setItems] = useState<Bookmark[]>(read)

  useEffect(() => {
    const sync = () => setItems(read())
    window.addEventListener(CHANGED, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(CHANGED, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const save = useCallback((next: Bookmark[]) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    window.dispatchEvent(new Event(CHANGED))
  }, [])

  const toggle = useCallback(
    (group: SongGroup) => {
      const current = read()
      const exists = current.some((b) => b.match_key === group.match_key)
      save(
        exists
          ? current.filter((b) => b.match_key !== group.match_key)
          : [
              {
                match_key: group.match_key,
                title: group.title,
                singer: group.singer,
                brands: group.brands,
                saved_at: new Date().toISOString(),
              },
              ...current,
            ],
      )
    },
    [save],
  )

  const has = useCallback(
    (matchKey: string) => items.some((b) => b.match_key === matchKey),
    [items],
  )

  return { items, toggle, has }
}
