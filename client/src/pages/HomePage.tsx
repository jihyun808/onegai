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

/**
 * 검색 상태는 App이 들고 있다.
 *
 * 여기서 useState로 두면 설정 탭에 다녀오는 순간 컴포넌트가 사라지면서
 * 검색어까지 날아간다. 설정을 바꾸고 돌아와 결과를 확인하는 흐름이
 * 깨지므로 위로 올렸다.
 */
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
        <>
          <SearchTips />

          {/*
            뱃지는 한글로 보이지만 검색창에는 원어가 들어간다.
            노래방 검색은 원어가 가장 잘 걸리는데 이용자는 한글로 기억한다.
            가수 검색으로 함께 바꿔 준다 — 곡명으로 두면 0건이 나온다.
          */}
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

          {/*
            검색 전 화면을 비워두지 않는다. 인기곡은 손으로 넣은 스냅샷이라
            서버를 부르지 않는다 (data/popular.ts).
            카드는 검색 결과와 같은 SongCard라 즐겨찾기·가사·미리듣기가 그대로 된다.
          */}
          <h2 className="home__heading home__heading--popular">
            J-POP 인기곡 <span className="home__count">50</span>
          </h2>
          <p className="home__source">{POPULAR_SOURCE}</p>
          {/*
            50장을 다 늘어놓으면 홈이 끝없이 길어진다. 다섯 장 높이로 잘라
            상자 안에서만 스크롤한다. overscroll-behavior가 상자 끝에서
            페이지로 스크롤이 넘어가는 것을 막는다.
          */}
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

      {/*
        공식까지 뒤지는 중에는 '없음'이라고 단정하지 않는다.
        groups까지 보는 이유 — 카드가 떠 있는데 '없어요'가 함께 뜨는 일을 막는다.
        다음 페이지 응답이 0건이면 total만 0으로 덮여서 그렇게 됐었다.
      */}
      {hasQuery && !error && total === 0 && groups.length === 0 && !busy && !loadingMore2 && (
        <>
          <StateMessage
            title="검색 결과가 없어요"
            description="다른 검색어나 검색 타입으로 시도해 보세요"
          />

          {/* 0곡일 때야말로 공식까지 확인할 이유가 가장 크다 */}
          <MoreSearch query={query} onLoadMore={searchMore} canLoadMore={canSearchMore} />
        </>
      )}

      {hasQuery && !error && total > 0 && (
        <>
          <h2 className="home__heading">
            검색 결과 <span className="home__count">{total.toLocaleString()}</span>
            {/*
              0일 때도 보여준다. 감추면 '겹치는 곡이 없다'와 '아직 안 세었다'가
              구분되지 않는다 — 브랜드 하나에만 있는 검색어(`미쿠`는 태진 0건)에서
              숫자가 통째로 사라져 보였다.
              브랜드 탭을 고르면 감춘다. 그때는 한쪽만 남겨 세는 것이라
              '양쪽 다'가 항상 0이 된다.
            */}
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
            공식까지 확인하거나 브라우저로 나갈 수 있게 한다.
          */}
          {!hasMore && (
            <MoreSearch
              query={query}
              onLoadMore={searchMore}
              canLoadMore={canSearchMore}
            />
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
