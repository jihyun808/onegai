import { useCallback, useEffect, useRef, useState } from 'react'

import type { BrandFilter, SearchType, SongGroup } from '../types/karaoke'
import { searchSongs } from '../utils/api'
import { appendNew, countMatched, mergeGroups } from '../utils/groups'
import { useDebounce } from './useDebounce'

const DEBOUNCE_MS = 300
const PAGE_SIZE = 50

interface UseSearchResult {
  groups: SongGroup[]
  /** 전체 결과 수 (지금까지 불러온 수가 아니다) */
  total: number
  /** 지금까지 불러온 원본 항목 수 — 다음 페이지 offset으로도 쓴다 */
  loaded: number
  matched: number
  hasMore: boolean
  loading: boolean
  loadingMore: boolean
  /** 공식 사이트까지 뒤지는 중 — 목록 아래에 스피너를 띄운다 */
  loadingMore2: boolean
  /** 아직 공식을 안 뒤졌다 — '더 찾아보기'를 띄울 수 있다 */
  canSearchMore: boolean
  /** 공식 사이트까지 마저 뒤진다 */
  searchMore: () => void
  error: string | null
  /** 디바운스 대기 중인지 — 입력 직후 이전 결과를 그대로 두기 위해 쓴다 */
  pending: boolean
  loadMore: () => void
}

const EMPTY: SongGroup[] = []

/**
 * 브랜드는 인자로 받지 않는다. 항상 '전체'로 받아 두고 화면에서 거른다.
 * 탭을 누를 때마다 서버를 다시 부르면 4초를 또 기다리게 된다.
 */
export function useSearch(query: string, type: SearchType): UseSearchResult {
  const brand: BrandFilter = 'all'
  const debouncedQuery = useDebounce(query, DEBOUNCE_MS)
  const trimmed = debouncedQuery.trim()

  const [groups, setGroups] = useState<SongGroup[]>(EMPTY)
  const [total, setTotal] = useState(0)
  const [loaded, setLoaded] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [complete, setComplete] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 이전 요청을 취소해서, 늦게 도착한 응답이 최신 결과를 덮어쓰지 않게 한다
  const controllerRef = useRef<AbortController | null>(null)
  // 스크롤 이벤트가 연속으로 들어와도 같은 페이지를 두 번 부르지 않게 한다
  const loadingMoreRef = useRef(false)

  // 첫 페이지 — 검색어/타입/브랜드가 바뀔 때마다 처음부터 다시 불러온다
  useEffect(() => {
    controllerRef.current?.abort()
    loadingMoreRef.current = false

    if (!trimmed) {
      setGroups(EMPTY)
      setTotal(0)
      setLoaded(0)
      setHasMore(false)
      setError(null)
      setLoading(false)
      setCompleting(false)
      setComplete(true)
      return
    }

    const controller = new AbortController()
    controllerRef.current = controller

    setLoading(true)
    setError(null)

    searchSongs({
      q: trimmed,
      type,
      brand,
      limit: PAGE_SIZE,
      offset: 0,
      signal: controller.signal,
    })
      .then((response) => {
        setGroups(response.groups)
        setTotal(response.total)
        setLoaded(response.returned)
        setHasMore(response.has_more)
        setLoading(false)

        setComplete(response.complete)

        // 1차는 자체 DB만 본 결과다. 나머지는 공식에서 뒤져 뒤에 덧붙인다.
        if (response.complete) return
        setCompleting(true)

        return searchSongs({
          q: trimmed,
          type,
          brand,
          limit: PAGE_SIZE,
          offset: 0,
          full: true,
          signal: controller.signal,
        })
          .then((full) => {
            setGroups((prev) => appendNew(prev, full.groups))
            setTotal(full.total)
            setLoaded(full.returned)
            setHasMore(full.has_more)
            setCompleting(false)
            setComplete(true)
          })
          .catch(() => {
            // 공식이 실패해도 1차 결과는 그대로 둔다
            if (!controller.signal.aborted) setCompleting(false)
          })
      })
      .catch((err: unknown) => {
        // 사용자가 계속 타이핑해서 취소된 것은 오류가 아니다
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : '검색에 실패했어요.')
        setGroups(EMPTY)
        setTotal(0)
        setLoaded(0)
        setHasMore(false)
        setLoading(false)
        setCompleting(false)
      })

    return () => controller.abort()
  }, [trimmed, type])

  /**
   * 사용자가 직접 공식까지 뒤지게 한다.
   *
   * DB가 완전하지 않을 수 있어서(크롤링 시점 이후 신곡 등) 결과가 충분해 보여도
   * 원하는 곡이 빠져 있을 수 있다. 그럴 때 눌러 확인한다.
   */
  const searchMore = useCallback(() => {
    if (completing || !trimmed) return

    setCompleting(true)
    const controller = new AbortController()
    controllerRef.current = controller

    searchSongs({
      q: trimmed,
      type,
      brand,
      limit: PAGE_SIZE,
      offset: 0,
      full: true,
      signal: controller.signal,
    })
      .then((full) => {
        setGroups((prev) => appendNew(prev, full.groups))
        setTotal(full.total)
        setLoaded(full.returned)
        setHasMore(full.has_more)
        setCompleting(false)
        setComplete(true)
      })
      .catch(() => {
        if (!controller.signal.aborted) setCompleting(false)
      })
  }, [trimmed, type, brand, completing])

  const loadMore = useCallback(() => {
    if (loadingMoreRef.current || loading || !hasMore || !trimmed) return

    loadingMoreRef.current = true
    setLoadingMore(true)

    const controller = new AbortController()
    controllerRef.current = controller

    searchSongs({
      q: trimmed,
      type,
      brand,
      limit: PAGE_SIZE,
      offset: loaded,
      signal: controller.signal,
    })
      .then((response) => {
        // 같은 곡이 페이지에 걸쳐 나뉘어 올 수 있어 match_key로 합친다
        setGroups((prev) => mergeGroups(prev, response.groups))
        setTotal(response.total)
        setLoaded((prev) => prev + response.returned)
        setHasMore(response.has_more)
        setLoadingMore(false)
        loadingMoreRef.current = false
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : '검색에 실패했어요.')
        setLoadingMore(false)
        loadingMoreRef.current = false
      })
  }, [trimmed, type, loaded, hasMore, loading])

  return {
    groups,
    total,
    loaded,
    matched: countMatched(groups),
    hasMore,
    loading,
    loadingMore,
    loadingMore2: completing,
    canSearchMore: complete && !completing,
    searchMore,
    error,
    pending: query.trim() !== trimmed,
    loadMore,
  }
}
