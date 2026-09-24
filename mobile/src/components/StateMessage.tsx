import { StyleSheet, Text, View } from 'react-native'

import { colors, fonts } from '../theme'

export function StateMessage({ title, description }: { title: string; description?: string }) {
  return (
    <View style={styles.state}>
      <Text style={styles.title}>{title}</Text>
      {description && <Text style={styles.desc}>{description}</Text>}
    </View>
  )
}

const styles = StyleSheet.create({
  state: { alignItems: 'center', paddingVertical: 60, paddingHorizontal: 20 },
  title: { color: colors.ink, fontFamily: fonts.handBold, fontSize: 19 },
  desc: {
    marginTop: 6,
    color: colors.inkSoft,
    fontFamily: fonts.body,
    fontSize: 13,
    lineHeight: 21,
    textAlign: 'center',
  },
})
