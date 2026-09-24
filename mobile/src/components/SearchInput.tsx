import { ActivityIndicator, Pressable, StyleSheet, TextInput } from 'react-native'

import { colors, fonts } from '../theme'
import { CloseIcon, SearchIcon } from './icons'
import { Sketch } from './Sketch'

interface Props {
  value: string
  onChange: (value: string) => void
  busy?: boolean
}

export function SearchInput({ value, onChange, busy }: Props) {
  return (
    <Sketch style={styles.search}>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChange}
        placeholder="곡명 또는 가수명으로 검색"
        placeholderTextColor={colors.inkFaint}
        accessibilityLabel="곡명 또는 가수명으로 검색"
        autoCapitalize="none"
        autoCorrect={false}
        spellCheck={false}
        returnKeyType="search"
        maxLength={100}
      />

      {value.length > 0 && (
        <Pressable
          style={styles.clear}
          onPress={() => onChange('')}
          hitSlop={8}
          accessibilityRole="button"
          accessibilityLabel="검색어 지우기"
        >
          <CloseIcon size={11} color={colors.inkSoft} />
        </Pressable>
      )}

      {busy ? (
        <ActivityIndicator color={colors.accent} size="small" />
      ) : (
        <SearchIcon size={18} color={colors.ink} />
      )}
    </Sketch>
  )
}

const styles = StyleSheet.create({
  search: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 4,
    paddingLeft: 22,
    paddingRight: 20,
  },
  input: {
    flex: 1,
    minWidth: 0,
    paddingVertical: 12,
    color: colors.ink,
    fontFamily: fonts.body,
    fontSize: 16,
  },
  clear: {
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.ivoryDeep,
  },
})
