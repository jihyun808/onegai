import { useCallback, useEffect, useState } from 'react'

import type { SongGroup } from '../types/karaoke'
import * as api from '../utils/favorites'
import { flatten } from '../utils/favorites'
import { readJson, removeKey, subscribe, writeJson } from '../utils/storage'

/**
 * 즐겨찾기.
 *
 * 로그인 여부에 따라 저장 위치가 다르다.
 *   비로그인 — 기기(AsyncStorage). 로그인 없이도 쓸 수 있어야 한다.
 *   로그인   — 서버. 기기를 바꿔도 남는다.
 *
 * 가입하는 순간 로컬에 쌓인 것을 서버로 한 번 올리고 로컬을 비운다
 * (`migrateLocal`). 안 그러면 그동안 담은 것이 사라진 것처럼 보인다.
 */
export const STORAGE_KEY = 'kada:bookmarks:v1'

export interface Bookmark {
  match_key: string
  title: string
  singer: string
  brands: SongGroup['brands']
  saved_at: string
}

const readLocal = () => readJson<Bookmark[]>(STORAGE_KEY, [])

function toBookmark(group: SongGroup): Bookmark {
  return {
    match_key: group.match_key,
    title: group.title,
    singer: group.singer,
    brands: group.brands,
    saved_at: new Date().toISOString(),
  }
}

/** 서버에서 온 그룹을 화면이 쓰는 형태로. */
function fromGroup(group: SongGroup): Bookmark {
  return { ...toBookmark(group), saved_at: '' }
}

export function useBookmarks(loggedIn: boolean) {
  const [items, setItems] = useState<Bookmark[]>([])

  const reload = useCallback(async () => {
    if (!loggedIn) {
      setItems(await readLocal())
      return
    }
    try {
      const { groups } = await api.list()
      setItems(groups.map(fromGroup))
    } catch {
      setItems([])
    }
  }, [loggedIn])

  useEffect(() => {
    void reload()
  }, [reload])

  useEffect(() => {
    if (loggedIn) return
    return subscribe(STORAGE_KEY, () => {
      void readLocal().then(setItems)
    })
  }, [loggedIn])

  const toggle = useCallback(
    async (group: SongGroup) => {
      const exists = items.some((b) => b.match_key === group.match_key)

      if (!loggedIn) {
        const current = await readLocal()
        await writeJson(
          STORAGE_KEY,
          exists
            ? current.filter((b) => b.match_key !== group.match_key)
            : [toBookmark(group), ...current],
        )
        return
      }

      // 화면을 먼저 바꾸고 서버에 보낸다. 실패하면 되돌린다.
      const snapshot = items
      setItems(
        exists
          ? items.filter((b) => b.match_key !== group.match_key)
          : [fromGroup(group), ...items],
      )

      try {
        const songs = flatten(group)
        if (exists) await Promise.all(songs.map(api.remove))
        else await api.add(songs)
      } catch {
        setItems(snapshot)
      }
    },
    [items, loggedIn],
  )

  const has = useCallback(
    (matchKey: string) => items.some((b) => b.match_key === matchKey),
    [items],
  )

  return { items, toggle, has, reload }
}

/** 기기에 담아둔 즐겨찾기를 모두 지운다 (비로그인 상태의 전체 삭제). */
export function clearLocal() {
  return removeKey(STORAGE_KEY)
}

/**
 * 가입 직후 로컬 즐겨찾기를 서버로 옮긴다.
 *
 * 서버에 이미 있는 곡은 조용히 무시되므로(UNIQUE 제약) 여러 번 불려도 안전하다.
 * 올리기에 성공해야만 로컬을 비운다 — 실패했는데 지우면 데이터가 사라진다.
 */
export async function migrateLocal(): Promise<number> {
  const local = await readLocal()
  if (local.length === 0) return 0

  const songs = local.flatMap((bookmark) =>
    flatten({ ...bookmark, both: Object.keys(bookmark.brands).length > 1 }),
  )
  if (songs.length === 0) return 0

  await api.add(songs)
  await removeKey(STORAGE_KEY)
  return local.length
}
