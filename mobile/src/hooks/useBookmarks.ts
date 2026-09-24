import { useCallback, useEffect, useState } from 'react'

import type { SongGroup } from '../types/karaoke'
import * as api from '../utils/favorites'
import { flatten } from '../utils/favorites'
import { readJson, removeKey, subscribe, writeJson } from '../utils/storage'

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

export function clearLocal() {
  return removeKey(STORAGE_KEY)
}

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
