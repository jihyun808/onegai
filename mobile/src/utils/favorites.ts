import { API_URL } from '../config'
import type { Brand, SongGroup } from '../types/karaoke'

export interface FavoritesResponse {
  total: number
  groups: SongGroup[]
}

export interface FavoriteSong {
  brand: Brand
  no: string
  title: string
  singer: string
}

export function flatten(group: SongGroup): FavoriteSong[] {
  const out: FavoriteSong[] = []
  for (const [brand, numbers] of Object.entries(group.brands)) {
    for (const no of numbers ?? []) {
      out.push({ brand: brand as Brand, no, title: group.title, singer: group.singer })
    }
  }
  return out
}

async function request(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_URL}/api/favorites${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
    credentials: 'include',
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.message ?? '즐겨찾기를 처리하지 못했어요.')
  }
  return response.json()
}

export function list(): Promise<FavoritesResponse> {
  return request('')
}

export function add(songs: FavoriteSong[]): Promise<{ saved: number }> {
  return request('', { method: 'POST', body: JSON.stringify({ songs }) })
}

export function remove(song: FavoriteSong): Promise<void> {
  return request(`/${song.brand}/${encodeURIComponent(song.no)}`, { method: 'DELETE' })
}

export function clear(): Promise<void> {
  return request('', { method: 'DELETE' })
}
