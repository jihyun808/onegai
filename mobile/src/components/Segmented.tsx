import { Pressable, StyleSheet, Text, View } from 'react-native'

import { colors, fonts } from '../theme'

export interface SegmentOption<T extends string> {
  value: T
  label: string
  tone?: 'tj' | 'kumyoung'
}

interface Props<T extends string> {
  label: string
  options: SegmentOption<T>[]
  value: T
  onChange: (value: T) => void
}

export function Segmented<T extends string>({ label, options, value, onChange }: Props<T>) {
  return (
    <View style={styles.group} accessibilityRole="radiogroup" accessibilityLabel={label}>
      {options.map((option) => {
        const selected = option.value === value
        const tone = option.tone ? colors[option.tone] : colors.ink
        return (
          <Pressable
            key={option.value}
            style={[
              styles.item,
              selected && styles.itemOn,
              selected && { borderColor: option.tone ? tone : colors.line },
            ]}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            onPress={() => onChange(option.value)}
          >
            <Text style={[styles.text, selected && { color: tone }]} numberOfLines={1}>
              {option.label}
            </Text>
          </Pressable>
        )
      })}
    </View>
  )
}

const styles = StyleSheet.create({
  group: { flexDirection: 'row', gap: 6 },
  item: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 4,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  itemOn: { backgroundColor: colors.paper },
  text: { color: colors.inkSoft, fontFamily: fonts.bodySemi, fontSize: 12 },
})
