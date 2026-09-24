import { StyleSheet, Text, View } from 'react-native'
import Svg, { Ellipse, G, Path } from 'react-native-svg'

import { colors, fonts } from '../theme'

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
  logo: { alignSelf: 'flex-start' },
  notes: { position: 'absolute', left: 49, top: -19 },
  text: { fontFamily: fonts.logo, fontSize: 26, lineHeight: 31, letterSpacing: -0.26 },
})
