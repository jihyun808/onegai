export type Brand = 'tj' | 'kumyoung'
export type BrandFilter = Brand | 'all'
export type SearchType = 'song' | 'singer'

export interface Song {
  brand: Brand
  no: string
  title: string
  title_ko?: string
  singer: string
  composer: string
  lyricist: string
  release: string
  match_key: string
}

export interface SongGroup {
  title: string
  title_ko?: string
  singer: string
  match_key: string
  brands: Partial<Record<Brand, string[]>>
  both: boolean
}

export interface SearchResponse {
  query: string
  type: SearchType
  brand: BrandFilter
  cached: boolean
  total: number
  songs: number
  returned: number
  limit: number
  offset: number
  has_more: boolean
  counts: Partial<Record<Brand, number>>
  matched: number
  complete: boolean
  results: Partial<Record<Brand, Song[]>>
  groups: SongGroup[]
}

export interface ApiError {
  error: 'invalid_request' | 'upstream_error'
  message: string
}
