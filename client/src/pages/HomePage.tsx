import { useState } from 'react'

import { SearchInput } from '../components/SearchInput'
import { Segmented, type SegmentOption } from '../components/Segmented'
import { SongCard } from '../components/SongCard'
import { StateMessage } from '../components/StateMessage'
import { useBookmarks } from '../hooks/useBookmarks'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useSearch } from '../hooks/useSearch'
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

export function HomePage() {
  const [query, setQuery] = useState('')
  const [type, setType] = useState<SearchType>('song')
  const [brand, setBrand] = useState<BrandFilter>('all')

  const {
    groups,
    total,
    matched,
    hasMore,
    loading,
    loadingMore,
    error,
    pending,
    loadMore,
  } = useSearch(query, type, brand)
  const { toggle, has } = useBookmarks()

  const sentinelRef = useInfiniteScroll(hasMore && !loading, loadMore)

  const hasQuery = query.trim().length > 0
  // 디바운스 대기 중에도 이전 결과를 그대로 둔다. 화면이 깜빡이지 않게.
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
        <StateMessage
          title="곡명이나 가수명을 입력해 보세요"
          description="태진과 금영 번호를 한 번에 찾아드려요"
        />
      )}

      {hasQuery && error && (
        <StateMessage title="검색에 실패했어요" description={error} />
      )}

      {hasQuery && !error && total === 0 && !busy && (
        <StateMessage
          title="검색 결과가 없어요"
          description="다른 검색어나 검색 타입으로 시도해 보세요"
        />
      )}

      {hasQuery && !error && total > 0 && (
        <>
          <h2 className="home__heading">
            검색 결과 <span className="home__count">{total.toLocaleString()}</span>
            {matched > 0 && (
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

          {/* 이 요소가 화면에 들어오면 다음 페이지를 부른다 */}
          {hasMore && <div ref={sentinelRef} className="home__sentinel" />}

          {loadingMore && (
            <p className="home__loading" aria-live="polite">
              불러오는 중…
            </p>
          )}

          {!hasMore && groups.length > 0 && (
            <p className="home__end">모든 결과를 다 봤어요</p>
          )}
        </>
      )}
    </>
  )
}
