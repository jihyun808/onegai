import { Linking, Pressable, StyleSheet, Text, View } from 'react-native'

import { colors, fonts } from '../theme'
import { webSearchUrl } from '../utils/links'

interface Props {
  query: string
  onLoadMore: () => void
  canLoadMore: boolean
}

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
