import { useMemo } from 'react'

import { SearchInput } from '../components/SearchInput'
import { Segmented, type SegmentOption } from '../components/Segmented'
import { SongCard } from '../components/SongCard'
import { Spinner } from '../components/Spinner'
import { MoreSearch } from '../components/MoreSearch'
import { SearchTips } from '../components/SearchTips'
import { StateMessage } from '../components/StateMessage'
import { HOT_SEARCHES } from '../data/hotSearches'
import { POPULAR, POPULAR_SOURCE } from '../data/popular'
import { useAuth } from '../hooks/useAuth'
import { useBookmarks } from '../hooks/useBookmarks'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useSearch } from '../hooks/useSearch'
import { useSettings } from '../hooks/useSettings'
import { countMatched, filterByBrand } from '../utils/groups'
import type { BrandFilter, SearchType } from '../types/karaoke'
import './HomePage.css'

const TYPE_OPTIONS: SegmentOption<SearchType>[] = [
  { value: 'song', label: '곡명' },
  { value: 'singer', label: '가수명' },
]

const BRAND_OPTIONS: SegmentOption<BrandFilter>[] = [
  { value: 'all', label: '전체' },
  { value: 'tj', label: '태진', tone: 'tj' },
  { value: 'kumyoung', label: '금영', tone: 'kumyoung' },
]

export interface SearchState {
  query: string
  setQuery: (value: string) => void
  type: SearchType
  setType: (value: SearchType) => void
  brand: BrandFilter
  setBrand: (value: BrandFilter) => void
}

export function HomePage({ query, setQuery, type, setType, brand, setBrand }: SearchState) {
  const { settings } = useSettings()

  const {
    groups: allGroups,
    total: serverTotal,
    hasMore,
    loading,
    loadingMore,
    loadingMore2,
    canSearchMore,
    searchMore,
    error,
    pending,
    loadMore,
  } = useSearch(query, type, { sort: settings.sort, korean: settings.showKorean })
  const { session } = useAuth()
  const { toggle, has } = useBookmarks(Boolean(session))

  const groups = useMemo(() => filterByBrand(allGroups, brand), [allGroups, brand])
  const matched = useMemo(() => countMatched(groups), [groups])

  const total = brand === 'all' ? serverTotal : groups.length

  const sentinelRef = useInfiniteScroll(hasMore && !loading, loadMore)

  const hasQuery = query.trim().length > 0
  const busy = loading || pending

  return (
    <>
      <div className="home__controls">
        <SearchInput value={query} onChange={setQuery} busy={busy} />
        <div className="home__filters">
          <Segmented
            label="검색 타입"
            options={TYPE_OPTIONS}
            value={type}
            onChange={setType}
          />
          <Segmented
            label="노래방 브랜드"
            options={BRAND_OPTIONS}
            value={brand}
            onChange={setBrand}
          />
        </div>
      </div>

      {!hasQuery && (
        <>
          <SearchTips />

          <h2 className="home__heading home__heading--hot">많이 찾는 검색어</h2>
          <ul className="home__hot">
            {HOT_SEARCHES.map((hot) => (
              <li key={hot.query}>
                <button
                  type="button"
                  className="home__hot-badge"
                  onClick={() => {
                    setQuery(hot.query)
                    setType('singer')
                  }}
                >
                  {hot.label}
                </button>
              </li>
            ))}
          </ul>

          <h2 className="home__heading home__heading--popular">
            J-POP 인기곡 <span className="home__count">50</span>
          </h2>
          <p className="home__source">{POPULAR_SOURCE}</p>
          <div className="home__popular-box">
            <ol className="home__list home__list--ranked">
              {POPULAR.map((group, index) => (
                <li key={group.match_key} className="home__ranked-item">
                  <span className="home__rank" aria-label={`${index + 1}위`}>
                    {index + 1}
                  </span>
                  <SongCard
                    group={group}
                    bookmarked={has(group.match_key)}
                    onToggleBookmark={toggle}
                  />
                </li>
              ))}
            </ol>
          </div>
        </>
      )}

      {hasQuery && error && (
        <StateMessage title="검색에 실패했어요" description={error} />
      )}

      {hasQuery && !error && total === 0 && groups.length === 0 && !busy && !loadingMore2 && (
        <>
          <StateMessage
            title="검색 결과가 없어요"
            description="다른 검색어나 검색 타입으로 시도해 보세요"
          />

          <MoreSearch query={query} onLoadMore={searchMore} canLoadMore={canSearchMore} />
        </>
      )}

      {hasQuery && !error && total > 0 && (
        <>
          <h2 className="home__heading">
            검색 결과 <span className="home__count">{total.toLocaleString()}</span>
            {brand === 'all' && (
              <span className="home__matched">양쪽 다 있는 곡 {matched}</span>
            )}
          </h2>

          <ul className="home__list">
            {groups.map((group) => (
              <SongCard
                key={group.match_key}
                group={group}
                bookmarked={has(group.match_key)}
                onToggleBookmark={toggle}
              />
            ))}
          </ul>

          {hasMore && <div ref={sentinelRef} className="home__sentinel" />}

          {loadingMore && (
            <p className="home__loading" aria-live="polite">
              불러오는 중…
            </p>
          )}

          {!hasMore && !loadingMore2 && groups.length > 0 && (
            <p className="home__end">모든 결과를 다 봤어요</p>
          )}

          {!hasMore && (
            <MoreSearch
              query={query}
              onLoadMore={searchMore}
              canLoadMore={canSearchMore}
            />
          )}
        </>
      )}

      {hasQuery && !error && loadingMore2 && <Spinner label="더 찾아보는 중…" />}
    </>
  )
}
