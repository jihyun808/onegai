import type { BrandFilter, SearchResponse, SearchType } from '../types/karaoke'

export class ApiRequestError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
  }
}

interface SearchParams {
  q: string
  type: SearchType
  brand: BrandFilter
  limit?: number
  offset?: number
  full?: boolean
  sort?: string
  korean?: boolean
  signal?: AbortSignal
}

export async function searchSongs({
  q,
  type,
  brand,
  limit,
  offset,
  full,
  sort,
  korean,
  signal,
}: SearchParams): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, type, brand })
  if (limit !== undefined) params.set('limit', String(limit))
  if (offset !== undefined) params.set('offset', String(offset))
  if (full) params.set('full', '1')
  if (sort) params.set('sort', sort)
  if (korean) params.set('korean', '1')

  const response = await fetch(`/api/search?${params}`, { signal })

  if (!response.ok) {
    const message = await response
      .json()
      .then((body) => body.message as string)
      .catch(() => '검색에 실패했어요. 잠시 후 다시 시도해 주세요.')
    throw new ApiRequestError(message, response.status)
  }

  return response.json()
}

export interface LyricsLine {
  ko: string
  ja: string
}

export interface LyricsResponse {
  available: boolean
  lines?: LyricsLine[]
  provider?: string
  matched_title?: string
  matched_singer?: string
  reason?: string
  search_url?: string
  cached?: boolean
}

export async function fetchLyrics(
  title: string,
  singer: string,
  signal?: AbortSignal,
): Promise<LyricsResponse> {
  const params = new URLSearchParams({ title, singer })
  const response = await fetch(`/api/lyrics?${params}`, { signal })

  if (!response.ok) {
    throw new ApiRequestError('가사를 가져오지 못했어요.', response.status)
  }

  return response.json()
}

export interface PreviewResponse {
  available: boolean
  preview_url?: string
  artwork_url?: string
  track_url?: string
  album?: string
  reason?: string
  cached?: boolean
}

export async function fetchPreview(
  title: string,
  singer: string,
  signal?: AbortSignal,
): Promise<PreviewResponse> {
  const params = new URLSearchParams({ title, singer })
  const response = await fetch(`/api/preview?${params}`, { signal })

  if (!response.ok) {
    throw new ApiRequestError('미리듣기를 가져오지 못했어요.', response.status)
  }

  return response.json()
}
