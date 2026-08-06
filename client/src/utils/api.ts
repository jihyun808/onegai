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

  const response = await fetch(`/api/search?${params}`, { signal })

  if (!response.ok) {
    // 에러 응답도 JSON이지만, 프록시 문제 등으로 아닐 수 있다.
    const message = await response
      .json()
      .then((body) => body.message as string)
      .catch(() => '검색에 실패했어요. 잠시 후 다시 시도해 주세요.')
    throw new ApiRequestError(message, response.status)
  }

  return response.json()
}
