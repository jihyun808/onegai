import { useCallback, useEffect, useRef, useState } from 'react'

import type { BrandFilter, SearchType, SongGroup } from '../types/karaoke'
import { searchSongs } from '../utils/api'
import { appendNew, countMatched, mergeGroups } from '../utils/groups'
import { useDebounce } from './useDebounce'

const DEBOUNCE_MS = 300
const PAGE_SIZE = 50

interface UseSearchResult {
  groups: SongGroup[]
  total: number
  loaded: number
  matched: number
  hasMore: boolean
  loading: boolean
  loadingMore: boolean
  loadingMore2: boolean
  canSearchMore: boolean
  searchMore: () => void
  error: string | null
  pending: boolean
  loadMore: () => void
}

const EMPTY: SongGroup[] = []

export function useSearch(
  query: string,
  type: SearchType,
  options: { sort?: string; korean?: boolean } = {},
): UseSearchResult {
  const brand: BrandFilter = 'all'
  const { sort, korean } = options
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
  const [usedFull, setUsedFull] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const controllerRef = useRef<AbortController | null>(null)
  const loadingMoreRef = useRef(false)

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
      setUsedFull(false)
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
      sort,
      korean,
      signal: controller.signal,
    })
      .then((response) => {
        setGroups(response.groups)
        setTotal(response.songs)
        setLoaded(response.returned)
        setHasMore(response.has_more)
        setLoading(false)

        setComplete(response.complete)
        setUsedFull(false)

        if (response.complete) return
        setCompleting(true)

        return searchSongs({
          q: trimmed,
          type,
          brand,
          limit: PAGE_SIZE,
          offset: 0,
          full: true,
          sort,
          korean,
          signal: controller.signal,
        })
          .then((full) => {
            setGroups((prev) => appendNew(prev, full.groups))
            setTotal(full.songs)
            setLoaded(full.returned)
            setHasMore(full.has_more)
            setCompleting(false)
            setComplete(true)
            setUsedFull(true)
          })
          .catch(() => {
            if (!controller.signal.aborted) setCompleting(false)
          })
      })
      .catch((err: unknown) => {
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
  }, [trimmed, type, sort, korean])

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
      sort,
      korean,
      signal: controller.signal,
    })
      .then((full) => {
        setGroups((prev) => appendNew(prev, full.groups))
        setTotal(full.songs)
        setLoaded(full.returned)
        setHasMore(full.has_more)
        setCompleting(false)
        setComplete(true)
        setUsedFull(true)
      })
      .catch(() => {
        if (!controller.signal.aborted) setCompleting(false)
      })
  }, [trimmed, type, brand, sort, korean, completing])

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
      full: usedFull,
      sort,
      korean,
      signal: controller.signal,
    })
      .then((response) => {
        setGroups((prev) => mergeGroups(prev, response.groups))
        setTotal(response.songs)
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
  }, [trimmed, type, sort, korean, loaded, hasMore, loading, usedFull])

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
