import { ActivityIndicator, StyleSheet, Text, View } from 'react-native'

import { colors, fonts } from '../theme'

export function Spinner({ label, inline }: { label?: string; inline?: boolean }) {
  return (
    <View style={inline ? undefined : styles.wrap} accessibilityLiveRegion="polite">
      <ActivityIndicator color={colors.ink} size="small" />
      {label && <Text style={styles.label}>{label}</Text>}
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', gap: 8, paddingTop: 18, paddingBottom: 6 },
  label: { color: colors.inkFaint, fontFamily: fonts.body, fontSize: 12 },
})
