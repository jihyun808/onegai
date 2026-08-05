import { useMemo, useState } from 'react'

import { SearchInput } from '../components/SearchInput'
import { Segmented, type SegmentOption } from '../components/Segmented'
import { SongCard } from '../components/SongCard'
import { Spinner } from '../components/Spinner'
import { StateMessage } from '../components/StateMessage'
import { useAuth } from '../hooks/useAuth'
import { useBookmarks } from '../hooks/useBookmarks'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useSearch } from '../hooks/useSearch'
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

export function HomePage() {
  const [query, setQuery] = useState('')
  const [type, setType] = useState<SearchType>('song')
  const [brand, setBrand] = useState<BrandFilter>('all')

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
  } = useSearch(query, type)
  const { session } = useAuth()
  const { toggle, has } = useBookmarks(Boolean(session))

  // 브랜드 탭은 이미 받아둔 결과에서 거른다 — 서버를 다시 부르지 않는다
  const groups = useMemo(() => filterByBrand(allGroups, brand), [allGroups, brand])
  const matched = useMemo(() => countMatched(groups), [groups])

  // 전체 탭은 서버가 알려준 총 곡 수를 쓴다(아직 안 불러온 것 포함).
  // 브랜드를 걸렀을 때는 서버 총계와 맞지 않으므로 화면에 있는 수를 센다.
  const total = brand === 'all' ? serverTotal : groups.length

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

      {/* 공식까지 뒤지는 중에는 '없음'이라고 단정하지 않는다 */}
      {hasQuery && !error && total === 0 && !busy && !loadingMore2 && (
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

          {!hasMore && !loadingMore2 && groups.length > 0 && (
            <p className="home__end">모든 결과를 다 봤어요</p>
          )}

          {/*
            자체 DB는 크롤링 시점까지만 담고 있다. 찾는 곡이 안 보이면
            눌러서 노래방 공식 사이트까지 확인할 수 있게 한다.
          */}
          {canSearchMore && !hasMore && (
            <button type="button" className="home__more" onClick={searchMore}>
              찾는 곡이 없나요? 노래방 사이트에서 더 찾아보기
            </button>
          )}
        </>
      )}

      {/*
        자체 DB로 먼저 보여준 뒤 공식 사이트를 뒤지는 동안 표시한다.
        결과가 아직 0건일 때도 보여야 하므로 목록 블록 밖에 둔다 —
        안에 두면 '결과 없음'도 스피너도 안 나와 빈 화면이 된다.
      */}
      {hasQuery && !error && loadingMore2 && <Spinner label="더 찾아보는 중…" />}
    </>
  )
}
