interface IconProps {
  size?: number
}

function Icon({ size = 25, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  )
}

export function UserIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="8.2" r="3.6" />
      <path d="M4.9 20.2c0-3.7 3.2-5.9 7.1-5.9s7.1 2.2 7.1 5.9" />
    </Icon>
  )
}

export function HomeIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3.4 10.6 12 3.4l8.6 7.2" />
      <path d="M5.9 9.5V20h12.2V9.5" />
      <path d="M10 20v-4.6h4V20" />
    </Icon>
  )
}

export function SettingsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="3.1" />
      <path d="M19.6 14.5a7.7 7.7 0 0 0 0-5l1.6-1.5-1.9-3.2-2 .8a7.7 7.7 0 0 0-4.3-2.5L12.6 1h-3.7l-.4 2.1a7.7 7.7 0 0 0-4.3 2.5l-2-.8L.3 8l1.6 1.5a7.7 7.7 0 0 0 0 5L.3 16l1.9 3.2 2-.8a7.7 7.7 0 0 0 4.3 2.5l.4 2.1h3.7l.4-2.1a7.7 7.7 0 0 0 4.3-2.5l2 .8 1.9-3.2z" />
    </Icon>
  )
}

export function PlayIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 6.6 18 12l-9 5.4z" />
    </Icon>
  )
}

export function PauseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9.6 6.4v11.2M14.4 6.4v11.2" />
    </Icon>
  )
}
