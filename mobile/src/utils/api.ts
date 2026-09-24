import { API_URL } from '../config'
import type { BrandFilter, SearchResponse, SearchType } from '../types/karaoke'

/** 서버가 400/502에 실어 보내는 메시지를 그대로 전달하기 위한 에러. */
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
  /** 공식 사이트까지 뒤진다. 느리지만 결과가 완전하다. */
  full?: boolean
  /** 'release' 최신순 | 'no' 곡번호순 */
  sort?: string
  /** 한국어로 된 곡도 보일지 */
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

  const response = await fetch(`${API_URL}/api/search?${params}`, { signal })

  if (!response.ok) {
    // 에러 응답도 JSON이지만, 게이트웨이 오류 등으로 아닐 수 있다.
    const message = await response
      .json()
      .then((body) => body.message as string)
      .catch(() => '검색에 실패했어요. 잠시 후 다시 시도해 주세요.')
    throw new ApiRequestError(message, response.status)
  }

  return response.json()
}

export interface LyricsLine {
  /** 한글 발음 */
  ko: string
  /** 일본어 원문 */
  ja: string
}

export interface LyricsResponse {
  available: boolean
  lines?: LyricsLine[]
  provider?: string
  matched_title?: string
  matched_singer?: string
  reason?: string
  /** 가사를 못 찾았을 때 안내할 검색 링크. 서버가 항상 채워 준다. */
  search_url?: string
  cached?: boolean
}

/**
 * 가사를 가져온다. 카드를 눌렀을 때만 부른다 —
 * 목록에 있는 카드마다 미리 부르면 금영에 50번씩 요청이 간다.
 */
export async function fetchLyrics(
  title: string,
  singer: string,
  signal?: AbortSignal,
): Promise<LyricsResponse> {
  const params = new URLSearchParams({ title, singer })
  const response = await fetch(`${API_URL}/api/lyrics?${params}`, { signal })

  // 서버는 가사를 못 찾아도 200 + available:false로 답한다.
  // 그러니 !ok는 서버·네트워크 문제뿐이고, 이건 다시 시도할 만한 실패다.
  if (!response.ok) {
    throw new ApiRequestError('가사를 가져오지 못했어요.', response.status)
  }

  return response.json()
}

export interface PreviewResponse {
  available: boolean
  /** 30초 미리듣기 (iTunes) */
  preview_url?: string
  artwork_url?: string
  track_url?: string
  album?: string
  reason?: string
  cached?: boolean
}

/**
 * 앨범아트와 미리듣기를 가져온다. 가사와 마찬가지로 눌렀을 때만 부른다 —
 * 목록에 있는 카드마다 미리 부르면 iTunes에 50번씩 요청이 간다.
 */
export async function fetchPreview(
  title: string,
  singer: string,
  signal?: AbortSignal,
): Promise<PreviewResponse> {
  const params = new URLSearchParams({ title, singer })
  const response = await fetch(`${API_URL}/api/preview?${params}`, { signal })

  // 미리듣기가 없어도 서버는 200 + available:false로 답한다.
  // !ok는 서버·네트워크 문제뿐이라 다시 시도할 만하다 — 그래서 던진다.
  if (!response.ok) {
    throw new ApiRequestError('미리듣기를 가져오지 못했어요.', response.status)
  }

  return response.json()
}
