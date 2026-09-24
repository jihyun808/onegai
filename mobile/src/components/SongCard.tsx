import { memo, useState } from 'react'
import { Image, Pressable, StyleSheet, Text, View } from 'react-native'

import { usePreview } from '../hooks/usePreview'
import { colors, fonts } from '../theme'
import type { Brand, SongGroup } from '../types/karaoke'
import { BookmarkIcon, PauseIcon, PlayIcon } from './icons'
import { LyricsModal } from './LyricsModal'
import { hashSeed, Sketch } from './Sketch'
import { Spinner } from './Spinner'

const BRAND_ORDER: Brand[] = ['tj', 'kumyoung']

const BRAND_LABEL: Record<Brand, string> = {
  tj: '태진',
  kumyoung: '금영',
}

interface Props {
  group: SongGroup
  bookmarked: boolean
  onToggleBookmark: (group: SongGroup) => void
  index?: number
}

export const SongCard = memo(function SongCard({
  group,
  bookmarked,
  onToggleBookmark,
  index = 0,
}: Props) {
  const [showLyrics, setShowLyrics] = useState(false)
  const preview = usePreview(group.match_key, group.title, group.singer)

  return (
    <Sketch variant={index} seed={hashSeed(group.match_key)} style={styles.song}>
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
