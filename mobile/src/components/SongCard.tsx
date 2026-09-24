import { memo, useState } from 'react'
import { Image, Pressable, StyleSheet, Text, View } from 'react-native'

import { usePreview } from '../hooks/usePreview'
import { colors, fonts } from '../theme'
import type { Brand, SongGroup } from '../types/karaoke'
import { BookmarkIcon, PauseIcon, PlayIcon } from './icons'
import { LyricsModal } from './LyricsModal'
import { hashSeed, Sketch } from './Sketch'
import { Spinner } from './Spinner'

/** 뱃지 순서를 고정한다 (태진 먼저). 데이터 순서에 흔들리지 않게. */
const BRAND_ORDER: Brand[] = ['tj', 'kumyoung']

const BRAND_LABEL: Record<Brand, string> = {
  tj: '태진',
  kumyoung: '금영',
}

interface Props {
  group: SongGroup
  bookmarked: boolean
  onToggleBookmark: (group: SongGroup) => void
  /** 카드 모양을 조금씩 달리하는 데만 쓴다 */
  index?: number
}

export const SongCard = memo(function SongCard({
  group,
  bookmarked,
  onToggleBookmark,
  index = 0,
}: Props) {
  // 팝업을 열 때 비로소 가사를 불러온다. 카드 50장이면 요청도 50번이라
  // 미리 받아둘 수는 없다.
  const [showLyrics, setShowLyrics] = useState(false)
  const preview = usePreview(group.match_key, group.title, group.singer)

  return (
    <Sketch variant={index} seed={hashSeed(group.match_key)} style={styles.song}>
      {/*
        누르기 전에는 빈 ▶ 자리다. 앨범아트도 이때 처음 받아온다 —
        카드마다 미리 부르면 목록 한 장에 iTunes 요청이 50번 나간다.
      */}
      <Pressable
        style={[
          styles.play,
          preview.playing && styles.playOn,
          preview.missing && styles.playDisabled,
        ]}
        onPress={preview.toggle}
        disabled={preview.missing}
        accessibilityRole="button"
        accessibilityLabel={
          preview.missing
            ? `${group.title} 미리듣기 없음`
            : preview.failed
              ? `${group.title} 미리듣기 다시 시도`
              : `${group.title} 미리듣기 ${preview.playing ? '정지' : '재생'}`
        }
      >
        {preview.artwork && (
          <Image source={{ uri: preview.artwork }} style={StyleSheet.absoluteFill} />
        )}
        <View style={preview.artwork ? styles.playBadge : undefined}>
          {preview.loading ? (
            <Spinner />
          ) : preview.playing ? (
            <PauseIcon size={18} color={preview.artwork ? '#fff' : colors.accent} />
          ) : (
            <PlayIcon size={18} color={preview.artwork ? '#fff' : colors.inkSoft} />
          )}
        </View>
      </Pressable>

      <View style={styles.body}>
        <Text style={styles.title}>{group.title}</Text>
        {/*
          번역 제목은 원어 아래에 작게 둔다. 노래방 기계에 찍혀 있는 것은
          원어라, 그쪽이 커야 번호를 찾아 누를 때 헷갈리지 않는다.
        */}
        {group.title_ko && group.title_ko !== group.title && (
          <Text style={styles.titleKo}>{group.title_ko}</Text>
        )}
        <Text style={styles.singer}>{group.singer || '가수 정보 없음'}</Text>
        <Pressable
          style={styles.lyrics}
          onPress={() => setShowLyrics(true)}
          accessibilityRole="button"
        >
          <Text style={styles.lyricsText}>가사보기</Text>
        </Pressable>
      </View>

      {/* 번호가 이 화면의 주인공이라 우측에 크게 나란히 둔다 */}
      <View style={styles.numbers}>
        {BRAND_ORDER.map((brand) => {
          const numbers = group.brands[brand]
          return (
            <View key={brand} style={styles.brand}>
              <Text style={styles.brandName}>{BRAND_LABEL[brand]}</Text>
              {numbers?.length ? (
                numbers.map((no, i) => (
                  <Text
                    key={no}
                    selectable
                    style={[styles.no, { color: colors[brand] }, i >= 2 && styles.noExtra]}
                  >
                    {no}
                  </Text>
                ))
              ) : (
                // 한쪽에만 있는 곡도 자리를 비워 표의 열을 맞춘다
                <Text style={[styles.no, { color: colors.inkFaint }]}>—</Text>
              )}
            </View>
          )
        })}
      </View>

      <Pressable
        style={styles.mark}
        onPress={() => onToggleBookmark(group)}
        hitSlop={8}
        accessibilityRole="button"
        accessibilityState={{ selected: bookmarked }}
        accessibilityLabel={`${group.title} 즐겨찾기 ${bookmarked ? '해제' : '추가'}`}
      >
        <BookmarkIcon filled={bookmarked} color={bookmarked ? colors.ink : colors.inkFaint} />
      </Pressable>

      {showLyrics && (
        <LyricsModal
          title={group.title}
          singer={group.singer}
          onClose={() => setShowLyrics(false)}
        />
      )}
    </Sketch>
  )
})

const styles = StyleSheet.create({
  song: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 13,
    paddingHorizontal: 14,
  },
  play: {
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 10,
  },
  playOn: { borderColor: colors.accent },
  playDisabled: { opacity: 0.35 },
  playBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(23,20,16,0.55)',
  },
  body: { flex: 1, minWidth: 0 },
  title: { color: colors.ink, fontFamily: fonts.bodyBold, fontSize: 15, lineHeight: 19.5 },
  titleKo: {
    marginTop: 2,
    color: colors.inkSoft,
    fontFamily: fonts.body,
    fontSize: 12.5,
    lineHeight: 17,
  },
  singer: { marginTop: 3, color: colors.inkSoft, fontFamily: fonts.body, fontSize: 12 },
  lyrics: {
    alignSelf: 'flex-start',
    marginTop: 6,
    paddingVertical: 3,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  lyricsText: { color: colors.inkSoft, fontFamily: fonts.bodySemi, fontSize: 11 },
  numbers: { flexDirection: 'row', gap: 12 },
  brand: { alignItems: 'center', minWidth: 46 },
  brandName: { color: colors.inkSoft, fontFamily: fonts.bodySemi, fontSize: 11 },
  no: { fontFamily: fonts.handBold, fontSize: 21, lineHeight: 24, fontVariant: ['tabular-nums'] },
  noExtra: { fontSize: 15, opacity: 0.6 },
  mark: { padding: 4 },
})
