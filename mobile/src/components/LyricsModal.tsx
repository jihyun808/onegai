import { useEffect, useState } from 'react'
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'

import { colors, fonts } from '../theme'
import { fetchLyrics, type LyricsResponse } from '../utils/api'
import { Modal } from './Modal'
import { Spinner } from './Spinner'

interface Props {
  title: string
  singer: string
  onClose: () => void
}

export function LyricsModal({ title, singer, onClose }: Props) {
  const [data, setData] = useState<LyricsResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    fetchLyrics(title, singer, controller.signal)
      .then(setData)
      .catch((error) => {
        if (error.name !== 'AbortError') setFailed(true)
      })

    return () => controller.abort()
  }, [title, singer])

  return (
    <Modal title={title} onClose={onClose}>
      <Text style={styles.singer}>{singer || '가수 정보 없음'}</Text>

      <ScrollView style={styles.body} nestedScrollEnabled>
        {!data && !failed && (
          <View style={styles.loading}>
            <Spinner inline />
            <Text style={styles.note}>가사를 찾는 중이에요</Text>
          </View>
        )}

        {data?.available &&
          data.lines?.map((line, index) => (
            <View key={index} style={index > 0 && styles.lineGap}>
              <Text style={styles.ko}>{line.ko}</Text>
              <Text style={styles.ja} selectable>
                {line.ja}
              </Text>
            </View>
          ))}

        {(failed || (data && !data.available)) && (
          <Text style={styles.reason}>{data?.reason ?? '가사를 가져오지 못했어요.'}</Text>
        )}
      </ScrollView>

      <View style={styles.foot}>
        <Pressable
          style={styles.search}
          onPress={() => Linking.openURL(data?.search_url ?? searchFallback(title, singer))}
          accessibilityRole="link"
        >
          <Text style={styles.searchText}>인터넷에서 찾아보기</Text>
        </Pressable>
        {data?.available && <Text style={styles.source}>가사 · {data.provider}</Text>}
      </View>
    </Modal>
  )
}

function searchFallback(title: string, singer: string) {
  const query = `"${title}" ${singer} 가사`.trim()
  return `https://www.google.com/search?q=${encodeURIComponent(query)}`
}

const styles = StyleSheet.create({
  singer: { marginTop: -10, marginBottom: 12, color: colors.inkSoft, fontFamily: fonts.body, fontSize: 12 },
  body: {
    maxHeight: 420,
    paddingTop: 4,
    paddingRight: 4,
    borderTopWidth: 1,
    borderTopColor: colors.lineThin,
  },
  loading: { alignItems: 'center', gap: 10, paddingVertical: 28 },
  note: { color: colors.inkSoft, fontFamily: fonts.body, fontSize: 13 },
  lineGap: { marginTop: 12 },
  ko: { color: colors.ink, fontFamily: fonts.bodySemi, fontSize: 15, lineHeight: 22 },
  ja: { marginTop: 2, color: colors.inkSoft, fontFamily: fonts.body, fontSize: 12.5, lineHeight: 17.5 },
  reason: {
    paddingVertical: 24,
    color: colors.inkSoft,
    fontFamily: fonts.body,
    fontSize: 13,
    textAlign: 'center',
  },
  foot: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    marginTop: 14,
  },
  search: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  searchText: { color: colors.ink, fontFamily: fonts.bodySemi, fontSize: 12.5 },
  source: { color: colors.inkFaint, fontFamily: fonts.body, fontSize: 11 },
})
