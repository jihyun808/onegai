import { HomeIcon, SettingsIcon, UserIcon } from './icons'
import './BottomNav.css'

export type Tab = 'mypage' | 'home' | 'settings'

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

interface Props {
  value: Tab
  onChange: (tab: Tab) => void
}

export function BottomNav({ value, onChange }: Props) {
  return (
    <nav className="nav" aria-label="주요 메뉴">
      <div className="nav__bar">
        <svg
          className="nav__shape"
          viewBox="0 0 480 115"
          preserveAspectRatio="xMidYMax meet"
          aria-hidden="true"
        >
          <path className="nav__path" d={BAR_PATH} filter="url(#wobble)" />
        </svg>

        <div className="nav__items">
          <button
            type="button"
            className={`nav__item ${value === 'mypage' ? 'is-on' : ''}`}
            onClick={() => onChange('mypage')}
            aria-current={value === 'mypage' ? 'page' : undefined}
          >
            <UserIcon />
            <span className="nav__label">마이페이지</span>
          </button>

          <div className="nav__gap" aria-hidden="true" />

          <button
            type="button"
            className={`nav__item ${value === 'settings' ? 'is-on' : ''}`}
            onClick={() => onChange('settings')}
            aria-current={value === 'settings' ? 'page' : undefined}
          >
            <SettingsIcon />
            <span className="nav__label">설정</span>
          </button>
        </div>

        <button
          type="button"
          className={`nav__home ${value === 'home' ? 'is-on' : ''}`}
          onClick={() => onChange('home')}
          aria-current={value === 'home' ? 'page' : undefined}
        >
          <HomeIcon size={26} />
          <span className="sr-only">홈</span>
        </button>
      </div>
    </nav>
  )
}
