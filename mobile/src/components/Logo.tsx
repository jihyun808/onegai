import { StyleSheet, Text, View } from 'react-native'
import Svg, { Ellipse, G, Path } from 'react-native-svg'

import { colors, fonts } from '../theme'

/**
 * "오네가이" 워드마크.
 *
 * 앞의 '오네'는 먹색, 뒤의 '가이'는 코럴로 끊어 강조하고
 * 위에 음표를 흩뿌려 노래방 느낌을 낸다. 세 화면이 공유한다.
 */
function Note({ color, stem, heads }: { color: string; stem: string; heads: [number, number, number, number][] }) {
  return (
    <G>
      <Path d={stem} fill="none" stroke={color} strokeWidth={2.6} strokeLinecap="round" />
      {heads.map(([cx, cy, rx, ry]) => (
        <Ellipse key={cx} cx={cx} cy={cy} rx={rx} ry={ry} fill={color} />
      ))}
    </G>
  )
}

export function Logo() {
  return (
    <View style={styles.logo} accessibilityRole="header" accessibilityLabel="오네가이">
      {/* 붙임줄로 이어진 8분음표 쌍 세 개. 크기와 색을 조금씩 달리했다. */}
      <Svg viewBox="0 0 60 30" width={52} height={26} style={styles.notes}>
        <Note color={colors.kumyoung} stem="M8 21V9l7-2v12" heads={[[5.4, 21.4, 3.4, 2.8], [12.4, 19.4, 3.4, 2.8]]} />
        <Note color={colors.tj} stem="M28 18V4l10-2.6V16" heads={[[24.8, 18.6, 4, 3.3], [34.8, 16.6, 4, 3.3]]} />
        <Note color={colors.accent} stem="M50 22V12l6-1.6v9" heads={[[47.6, 22.4, 3.1, 2.6], [53.6, 19.4, 3.1, 2.6]]} />
      </Svg>
      <Text style={styles.text}>
        <Text style={{ color: colors.ink }}>오네</Text>
        <Text style={{ color: colors.accent }}>가이</Text>
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  // 웹처럼 글자 폭만큼만 차지하고 왼쪽에 붙는다
  logo: { alignSelf: 'flex-start' },
  // 웹은 left 48% / bottom 78%. 네이티브에서 %가 글자 폭이 아니라 더 넓은 상자를
  // 기준으로 잡혀 오른쪽으로 밀렸다. 글자 폭(26pt × 4자 ≈ 102pt) 기준으로 계산해 고정한다.
  notes: { position: 'absolute', left: 49, top: -19 },
  text: { fontFamily: fonts.logo, fontSize: 26, lineHeight: 31, letterSpacing: -0.26 },
})
