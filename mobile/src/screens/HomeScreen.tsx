import { useCallback, useMemo } from 'react'
import { FlatList, Keyboard, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'

import { MoreSearch } from '../components/MoreSearch'
import { SearchInput } from '../components/SearchInput'
import { SearchTips } from '../components/SearchTips'
import { Segmented, type SegmentOption } from '../components/Segmented'
import { SongCard } from '../components/SongCard'
import { Spinner } from '../components/Spinner'
import { StateMessage } from '../components/StateMessage'
import { HOT_SEARCHES } from '../data/hotSearches'
import { POPULAR, POPULAR_SOURCE } from '../data/popular'
import { useAuth } from '../hooks/useAuth'
import { useBookmarks } from '../hooks/useBookmarks'
import { useSearch } from '../hooks/useSearch'
import { useSettings } from '../hooks/useSettings'
import { colors, fonts } from '../theme'
import type { BrandFilter, SearchType, SongGroup } from '../types/karaoke'
import { countMatched, filterByBrand } from '../utils/groups'

const TYPE_OPTIONS: SegmentOption<SearchType>[] = [
  { value: 'song', label: '곡명' },
  { value: 'singer', label: '가수명' },
]

const BRAND_OPTIONS: SegmentOption<BrandFilter>[] = [
  { value: 'all', label: '전체' },
  { value: 'tj', label: '태진', tone: 'tj' },
  { value: 'kumyoung', label: '금영', tone: 'kumyoung' },
]

/** 인기곡 상자 높이 — 카드 다섯 장(약 74px)과 사이 여백 11px. 웹과 같다. */
const POPULAR_BOX_HEIGHT = 74 * 5 + 11 * 4

export interface SearchState {
  query: string
  setQuery: (value: string) => void
  type: SearchType
  setType: (value: SearchType) => void
  brand: BrandFilter
  setBrand: (value: BrandFilter) => void
}

/**
 * 검색 상태는 App이 들고 있다. 여기서 들고 있으면 설정 탭에 다녀오는 순간
 * 화면이 사라지면서 검색어까지 날아간다.
 *
 * 검색창과 필터는 목록 밖 위쪽에 고정한다 (웹의 position: sticky).
 */
export function HomeScreen({ query, setQuery, type, setType, brand, setBrand }: SearchState) {
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
  const total = brand === 'all' ? serverTotal : groups.length

  const hasQuery = query.trim().length > 0
  // 디바운스 대기 중에도 이전 결과를 그대로 둔다. 화면이 깜빡이지 않게.
  const busy = loading || pending
  const showResults = hasQuery && !error && total > 0

  const renderResult = useCallback(
    ({ item, index }: { item: SongGroup; index: number }) => (
      <SongCard
        group={item}
        index={index}
        bookmarked={has(item.match_key)}
        onToggleBookmark={toggle}
      />
    ),
    [has, toggle],
  )

  const controls = (
    <View style={styles.controls}>
      <SearchInput value={query} onChange={setQuery} busy={busy} />
      <View style={styles.filters}>
        <View style={styles.typeFilter}>
          <Segmented label="검색 타입" options={TYPE_OPTIONS} value={type} onChange={setType} />
        </View>
        <View style={styles.brandFilter}>
          <Segmented
            label="노래방 브랜드"
            options={BRAND_OPTIONS}
            value={brand}
            onChange={setBrand}
          />
        </View>
      </View>
    </View>
  )

  if (!hasQuery) {
    return (
      <>
        {controls}
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
        >
          <SearchTips />

          {/*
            뱃지는 한글로 보이지만 검색창에는 원어가 들어간다.
            가수 검색으로 함께 바꿔 준다 — 곡명으로 두면 0건이 나온다.
          */}
          <Text style={[styles.heading, styles.headingHot]}>많이 찾는 검색어</Text>
          <View style={styles.hot}>
            {HOT_SEARCHES.map((hot) => (
              <Pressable
                key={hot.query}
                style={styles.badge}
                accessibilityRole="button"
                onPress={() => {
                  setQuery(hot.query)
                  setType('singer')
                }}
              >
                <Text style={styles.badgeText}>{hot.label}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={[styles.heading, styles.headingPopular]}>
            J-POP 인기곡 <Text style={styles.count}>50</Text>
          </Text>
          <Text style={styles.source}>{POPULAR_SOURCE}</Text>

          {/*
            50장을 다 늘어놓으면 홈이 끝없이 길어진다. 다섯 장 높이로 잘라
            상자 안에서만 스크롤한다.
          */}
          <ScrollView style={styles.popularBox} nestedScrollEnabled>
            {POPULAR.map((group, index) => (
              <View key={group.match_key} style={[styles.ranked, index > 0 && styles.gap]}>
                <Text style={styles.rank} accessibilityLabel={`${index + 1}위`}>
                  {index + 1}
                </Text>
                <View style={styles.rankedCard}>
                  <SongCard
                    group={group}
                    index={index}
                    bookmarked={has(group.match_key)}
                    onToggleBookmark={toggle}
                  />
                </View>
              </View>
            ))}
          </ScrollView>
        </ScrollView>
      </>
    )
  }

  const header = (
    <>
      {error && <StateMessage title="검색에 실패했어요" description={error} />}

      {/*
        공식까지 뒤지는 중에는 '없음'이라고 단정하지 않는다.
        groups까지 보는 이유 — 카드가 떠 있는데 '없어요'가 함께 뜨는 일을 막는다.
      */}
      {!error && total === 0 && groups.length === 0 && !busy && !loadingMore2 && (
        <>
          <StateMessage
            title="검색 결과가 없어요"
            description="다른 검색어나 검색 타입으로 시도해 보세요"
          />
          {/* 0곡일 때야말로 공식까지 확인할 이유가 가장 크다 */}
          <MoreSearch query={query} onLoadMore={searchMore} canLoadMore={canSearchMore} />
        </>
      )}

      {showResults && (
        <Text style={styles.heading}>
          검색 결과 <Text style={styles.count}>{total.toLocaleString()}</Text>
          {/* 브랜드 탭을 고르면 감춘다. 한쪽만 남겨 세면 '양쪽 다'가 항상 0이다. */}
          {brand === 'all' && (
            <Text style={styles.matched}>
              <Text style={styles.dot}>{'  ·  '}</Text>양쪽 다 있는 곡 {matched}
            </Text>
          )}
        </Text>
      )}
    </>
  )

  const footer = (
    <>
      {showResults && loadingMore && <Text style={styles.end}>불러오는 중…</Text>}
      {showResults && !hasMore && !loadingMore2 && groups.length > 0 && (
        <Text style={styles.end}>모든 결과를 다 봤어요</Text>
      )}
      {/* 자체 DB는 크롤링 시점까지만 담고 있다. 공식까지 확인하거나 브라우저로 나간다. */}
      {showResults && !hasMore && (
        <MoreSearch query={query} onLoadMore={searchMore} canLoadMore={canSearchMore} />
      )}
      {/* 결과가 아직 0건일 때도 보여야 하므로 목록 조건과 따로 둔다 */}
      {!error && loadingMore2 && <Spinner label="더 찾아보는 중…" />}
    </>
  )

  return (
    <>
      {controls}
      <FlatList
        data={showResults ? groups : []}
        keyExtractor={(item) => item.match_key}
        renderItem={renderResult}
        ItemSeparatorComponent={Separator}
        ListHeaderComponent={header}
        ListFooterComponent={footer}
        // 바닥에 닿기 전에 미리 불러와 끊김을 줄인다
        onEndReached={() => {
          if (showResults && hasMore && !loading) loadMore()
        }}
        onEndReachedThreshold={0.6}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        onScrollBeginDrag={Keyboard.dismiss}
        contentContainerStyle={styles.content}
      />
    </>
  )
}

function Separator() {
  return <View style={styles.gap} />
}

const styles = StyleSheet.create({
  controls: { paddingTop: 10, paddingHorizontal: 16, paddingBottom: 12 },
  filters: { flexDirection: 'row', gap: 8, marginTop: 11, paddingHorizontal: 4 },
  // 웹: grid-template-columns 3fr 4fr
  typeFilter: { flex: 3 },
  brandFilter: { flex: 4 },
  content: { paddingHorizontal: 16, paddingBottom: 20 },
  heading: {
    marginTop: 14,
    marginBottom: 10,
    marginHorizontal: 4,
    color: colors.ink,
    fontFamily: fonts.handBold,
    fontSize: 21,
  },
  headingHot: { marginTop: 22 },
  headingPopular: { marginTop: 24 },
  count: { color: colors.accent },
  matched: { color: colors.inkSoft, fontFamily: fonts.body, fontSize: 12 },
  dot: { color: colors.inkFaint },
  source: { marginTop: -6, marginBottom: 10, color: colors.inkFaint, fontFamily: fonts.body, fontSize: 11 },
  hot: { flexDirection: 'row', flexWrap: 'wrap', gap: 7, marginBottom: 4, paddingHorizontal: 2 },
  badge: {
    paddingVertical: 7,
    paddingHorizontal: 13,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  badgeText: { color: colors.ink, fontFamily: fonts.bodySemi, fontSize: 13 },
  popularBox: { maxHeight: POPULAR_BOX_HEIGHT, paddingTop: 2, paddingHorizontal: 2 },
  ranked: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  rankedCard: { flex: 1, minWidth: 0 },
  rank: {
    width: 22,
    color: colors.inkSoft,
    fontFamily: fonts.handBold,
    fontSize: 15,
    textAlign: 'center',
  },
  gap: { marginTop: 11 },
  end: {
    marginTop: 16,
    color: colors.inkFaint,
    fontFamily: fonts.body,
    fontSize: 12,
    textAlign: 'center',
  },
})
