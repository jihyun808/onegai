import Svg, { Circle, Path } from 'react-native-svg'

import { colors } from '../theme'

/**
 * 아이콘. 손그림 톤에 맞춰 선으로만 그린다 (웹 icons.tsx와 같은 도형).
 */
interface IconProps {
  size?: number
  color?: string
}

function Icon({ size = 25, color = colors.ink, children }: IconProps & { children: React.ReactNode }) {
  return (
    <Svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke={color}
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </Svg>
  )
}

export function UserIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <Circle cx="12" cy="8.2" r="3.6" />
      <Path d="M4.9 20.2c0-3.7 3.2-5.9 7.1-5.9s7.1 2.2 7.1 5.9" />
    </Icon>
  )
}

export function HomeIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <Path d="M3.4 10.6 12 3.4l8.6 7.2" />
      <Path d="M5.9 9.5V20h12.2V9.5" />
      <Path d="M10 20v-4.6h4V20" />
    </Icon>
  )
}

export function SettingsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <Circle cx="12" cy="12" r="3.1" />
      <Path d="M19.6 14.5a7.7 7.7 0 0 0 0-5l1.6-1.5-1.9-3.2-2 .8a7.7 7.7 0 0 0-4.3-2.5L12.6 1h-3.7l-.4 2.1a7.7 7.7 0 0 0-4.3 2.5l-2-.8L.3 8l1.6 1.5a7.7 7.7 0 0 0 0 5L.3 16l1.9 3.2 2-.8a7.7 7.7 0 0 0 4.3 2.5l.4 2.1h3.7l.4-2.1a7.7 7.7 0 0 0 4.3-2.5l2 .8 1.9-3.2z" />
    </Icon>
  )
}

export function PlayIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <Path d="M9 6.6 18 12l-9 5.4z" />
    </Icon>
  )
}

export function PauseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <Path d="M9.6 6.4v11.2M14.4 6.4v11.2" />
    </Icon>
  )
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <Circle cx="10" cy="10" r="6.4" />
      <Path d="m14.8 14.8 5 5" />
    </Icon>
  )
}

export function CloseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <Path d="M6 6l12 12M18 6 6 18" />
    </Icon>
  )
}

export function BookmarkIcon({ filled, ...props }: IconProps & { filled: boolean }) {
  const color = props.color ?? colors.ink
  return (
    <Svg viewBox="0 0 14 18" width={14} height={18}>
      <Path
        d="M1 1.5h12v15l-6-4.5-6 4.5z"
        fill={filled ? color : 'none'}
        stroke={color}
        strokeWidth={1.6}
        strokeLinejoin="round"
      />
    </Svg>
  )
}
