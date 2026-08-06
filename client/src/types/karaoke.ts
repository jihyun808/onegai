export type Brand = 'tj' | 'kumyoung'
export type BrandFilter = Brand | 'all'
export type SearchType = 'song' | 'singer'

/** 검색 결과 한 곡. 서버가 브랜드별 목록(results)으로 내려준다. */
export interface Song {
  brand: Brand
  no: string
  title: string
  singer: string
  composer: string
  lyricist: string
  release: string
  /** 브랜드 간 동일 곡 매칭용 정규화 키 */
  match_key: string
}

/**
 * 같은 곡을 브랜드 넘어 묶은 단위.
 * TJ와 금영이 제목을 다르게 등록해도 서버 정규화가 흡수해 한 그룹이 된다.
 */
export interface SongGroup {
  title: string
  singer: string
  match_key: string
  /** 브랜드별 곡번호. 같은 브랜드에 버전이 여러 개면 번호도 여러 개다. */
  brands: Partial<Record<Brand, string[]>>
  /** TJ와 금영 양쪽에 모두 있는 곡인지 */
  both: boolean
}

export interface SearchResponse {
  query: string
  type: SearchType
  brand: BrandFilter
  cached: boolean
  /** 전체 번호 수 — 같은 곡이 두 브랜드에 있으면 2로 센다 */
  total: number
  /** 전체 곡 수 = 화면에 보일 카드 수. 표시에는 이걸 쓴다. */
  songs: number
  returned: number
  limit: number
  offset: number
  has_more: boolean
  /** 현재 페이지 기준 브랜드별 건수 */
  counts: Partial<Record<Brand, number>>
  /** 현재 페이지에서 양쪽 브랜드에 모두 있는 곡 수 */
  matched: number
  /**
   * false면 아직 전부가 아니다 — 자체 DB만 본 1차 응답이라는 뜻.
   * 클라이언트는 곧바로 full=1로 다시 불러 나머지를 채운다.
   */
  complete: boolean
  results: Partial<Record<Brand, Song[]>>
  groups: SongGroup[]
}

export interface ApiError {
  error: 'invalid_request' | 'upstream_error'
  message: string
}
