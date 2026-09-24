import { StyleSheet, Text, View } from 'react-native'

import { colors, fonts } from '../theme'

const TIPS: { text: [string, string, string]; eg: string }[] = [
  { text: ['', '띄어쓰기 없이', ' 붙여서'], eg: '요루니카케루 ⭘ / 요루니 카케루 ✕' },
  { text: ['곡명이 안 나오면 ', '가수명으로', ''], eg: '긴 일본어 제목은 잘 안 걸려요' },
  {
    text: ['', '한국에서 쓰는 표기', '로. 안 되면 일본어로'],
    eg: '실루엣 ⭘ / 시루엣토 ✕ · シルエット ⭘',
  },
]

export function SearchTips() {
  return (
    <View style={styles.tips}>
      <Text style={styles.title}>이렇게 검색해 보세요</Text>
      <View style={styles.list}>
        {TIPS.map((tip, index) => (
          <View key={tip.eg} style={styles.row}>
            <View style={styles.no}>
              <Text style={styles.noText}>{index + 1}</Text>
            </View>
            <View style={styles.textCol}>
              <Text style={styles.text}>
                {tip.text[0]}
                <Text style={styles.bold}>{tip.text[1]}</Text>
                {tip.text[2]}
              </Text>
              <Text style={styles.eg}>{tip.eg}</Text>
            </View>
          </View>
        ))}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  tips: { paddingTop: 28, paddingHorizontal: 20, paddingBottom: 8 },
  title: {
    marginBottom: 14,
    color: colors.ink,
    fontFamily: fonts.handBold,
    fontSize: 18,
    textAlign: 'center',
  },
  list: { gap: 10 },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  no: {
    width: 20,
    height: 20,
    marginTop: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.ink,
    borderRadius: 10,
  },
  noText: { color: colors.ink, fontFamily: fonts.bodyBold, fontSize: 11.5, lineHeight: 14 },
  textCol: { flex: 1 },
  text: { color: colors.ink, fontFamily: fonts.body, fontSize: 13.5, lineHeight: 20 },
  bold: { fontFamily: fonts.bodyBold },
  eg: { marginTop: 2, color: colors.inkSoft, fontFamily: fonts.body, fontSize: 12 },
})
