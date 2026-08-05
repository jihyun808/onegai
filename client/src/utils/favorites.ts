import type { Brand, SongGroup } from '../types/karaoke'

export interface FavoritesResponse {
  total: number
  groups: SongGroup[]
}

/** 저장 단위는 브랜드별 번호 하나다. 화면의 곡(그룹)을 여기에 맞춰 펼친다. */
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
  const response = await fetch(`/api/favorites${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
    credentials: 'same-origin',
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
