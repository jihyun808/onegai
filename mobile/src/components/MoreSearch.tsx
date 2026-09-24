import { Linking, Pressable, StyleSheet, Text, View } from 'react-native'

import { colors, fonts } from '../theme'
import { webSearchUrl } from '../utils/links'

interface Props {
  /** 지금 검색어. 브라우저 검색 링크를 만드는 데 쓴다 */
  query: string
  /** 노래방 공식 사이트까지 다시 조회 */
  onLoadMore: () => void
  /** 공식 조회가 이미 진행 중이면 버튼을 감춘다 */
  canLoadMore: boolean
}

/**
 * 결과 끝과 '결과 없음' 아래에 함께 두는 마무리 영역.
 *   1. 노래방 공식까지 **우리가** 다시 조회 (자체 DB는 크롤 시점까지만 담는다)
 *   2. 그래도 없으면 **브라우저로** 나가기
 */
export function MoreSearch({ query, onLoadMore, canLoadMore }: Props) {
  return (
    <View style={styles.more}>
      {canLoadMore && (
        <Pressable style={styles.button} onPress={onLoadMore} accessibilityRole="button">
          <Text style={styles.buttonText}>찾는 곡이 없나요? 공식 사이트에서 결과 더 불러오기</Text>
        </Pressable>
      )}
      <Pressable
        style={styles.webWrap}
        onPress={() => Linking.openURL(webSearchUrl(query))}
        accessibilityRole="link"
      >
        <Text style={styles.web}>브라우저에서 검색하기</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  more: { alignItems: 'center' },
  button: {
    alignSelf: 'stretch',
    marginTop: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  buttonText: {
    color: colors.inkSoft,
    fontFamily: fonts.bodySemi,
    fontSize: 12.5,
    textAlign: 'center',
  },
  webWrap: { marginTop: 5, marginBottom: 4, padding: 4 },
  web: {
    color: colors.inkSoft,
    fontFamily: fonts.body,
    fontSize: 12,
    textDecorationLine: 'underline',
  },
})
