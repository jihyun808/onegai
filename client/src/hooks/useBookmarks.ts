import { useCallback, useEffect, useState } from 'react'

import type { SongGroup } from '../types/karaoke'
import * as api from '../utils/favorites'
import { flatten } from '../utils/favorites'

const STORAGE_KEY = 'kada:bookmarks:v1'
const CHANGED = 'kada:bookmarks:changed'

export interface Bookmark {
  match_key: string
  title: string
  singer: string
  brands: SongGroup['brands']
  saved_at: string
}

function readLocal(): Bookmark[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Bookmark[]) : []
  } catch {
    return []
  }
}

function writeLocal(next: Bookmark[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  window.dispatchEvent(new Event(CHANGED))
}

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
  const [items, setItems] = useState<Bookmark[]>(readLocal)

  const reload = useCallback(async () => {
    if (!loggedIn) {
      setItems(readLocal())
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
    const sync = () => setItems(readLocal())
    window.addEventListener(CHANGED, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(CHANGED, sync)
      window.removeEventListener('storage', sync)
    }
  }, [loggedIn])

  const toggle = useCallback(
    async (group: SongGroup) => {
      const exists = items.some((b) => b.match_key === group.match_key)

      if (!loggedIn) {
        const current = readLocal()
        writeLocal(
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

export async function migrateLocal(): Promise<number> {
  const local = readLocal()
  if (local.length === 0) return 0

  const songs = local.flatMap((bookmark) =>
    flatten({ ...bookmark, both: Object.keys(bookmark.brands).length > 1 }),
  )
  if (songs.length === 0) return 0

  await api.add(songs)
  localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new Event(CHANGED))
  return local.length
}
