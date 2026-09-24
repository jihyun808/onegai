import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import Svg, { Path } from 'react-native-svg'

import { colors, fonts } from '../theme'
import { HomeIcon, SettingsIcon, UserIcon } from './icons'

export type Tab = 'mypage' | 'home' | 'settings'

const VIEW_W = 480
const VIEW_H = 115
const BAR_PATH = [
  'M0,115',
  'V70',
  'A24,24 0 0 1 24,46',
  'H175',
  'C208,46 207,24 240,24',
  'C273,24 272,46 305,46',
  'H456',
  'A24,24 0 0 1 480,70',
  'V115',
  'Z',
].join(' ')

const HOME_SIZE = 58

interface Props {
  value: Tab
  onChange: (tab: Tab) => void
}

function Item({
  on,
  label,
  Icon,
  onPress,
}: {
  on: boolean
  label: string
  Icon: typeof UserIcon
  onPress: () => void
}) {
  const color = on ? colors.ink : colors.inkFaint
  return (
    <Pressable
      style={styles.item}
      onPress={onPress}
      accessibilityRole="tab"
      accessibilityState={{ selected: on }}
      accessibilityLabel={label}
    >
      <Icon color={color} />
      <Text style={[styles.label, { color }]}>{label}</Text>
    </Pressable>
  )
}

export function BottomNav({ value, onChange }: Props) {
  const { width } = useWindowDimensions()
  const { bottom } = useSafeAreaInsets()
  const height = (VIEW_H * width) / VIEW_W
  const homeOn = value === 'home'

  return (
    <View accessibilityRole="tablist">
      <View style={{ height }}>
        <Svg
          width={width}
          height={height}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          style={StyleSheet.absoluteFill}
        >
          <Path d={BAR_PATH} fill={colors.paper} stroke={colors.line} strokeWidth={1} />
        </Svg>

        <View style={[styles.items, { top: height * 0.4 }]}>
          <Item
            on={value === 'mypage'}
            label="마이페이지"
            Icon={UserIcon}
            onPress={() => onChange('mypage')}
          />
          <View style={styles.gap} />
          <Item
            on={value === 'settings'}
            label="설정"
            Icon={SettingsIcon}
            onPress={() => onChange('settings')}
          />
        </View>

        <Pressable
          style={[
            styles.home,
            { top: height * 0.574 - HOME_SIZE / 2, left: width / 2 - HOME_SIZE / 2 },
            homeOn && styles.homeOn,
          ]}
          onPress={() => onChange('home')}
          accessibilityRole="tab"
          accessibilityState={{ selected: homeOn }}
          accessibilityLabel="홈"
        >
          <HomeIcon size={26} color={homeOn ? colors.paper : colors.inkFaint} />
        </Pressable>
      </View>
      <View style={{ height: bottom, backgroundColor: colors.paper }} />
    </View>
  )
}

const styles = StyleSheet.create({
  items: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    flexDirection: 'row',
    alignItems: 'center',
  },
  item: { flex: 1, alignItems: 'center', gap: 4, paddingVertical: 4 },
  gap: { width: '30%' },
  label: { fontFamily: fonts.bodySemi, fontSize: 11.5 },
  home: {
    position: 'absolute',
    width: HOME_SIZE,
    height: HOME_SIZE,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: HOME_SIZE / 2,
    backgroundColor: colors.paper,
  },
  homeOn: { backgroundColor: colors.accent },
})
