import { HomeIcon, SettingsIcon, UserIcon } from './icons'
import './BottomNav.css'

export type Tab = 'mypage' | 'home' | 'settings'

/*
 * 바 모양. 가운데가 원형으로 파여 있고 그 자리에 홈 버튼이 떠 있다.
 *
 * viewBox 비율을 유지한 채 폭에 맞춰 축소되므로(높이 auto) 노치가 타원으로
 * 찌그러지지 않는다. preserveAspectRatio="none"으로 늘리면 원이 깨진다.
 */
const BAR_PATH = [
  'M0,115',
  'V70',
  'A24,24 0 0 1 24,46', // 좌상단 모서리
  'H175',
  // 가운데가 위로 솟는 언덕. 홈 버튼을 살짝 감싸 올린다.
  // 제어점의 y를 시작/끝과 같게 두어 진입·이탈이 수평이 되고, 꺾인 데 없이 이어진다.
  'C208,46 207,24 240,24',
  'C273,24 272,46 305,46',
  'H456',
  'A24,24 0 0 1 480,70', // 우상단 모서리
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
          {/*
            색은 CSS에서 준다. SVG 프레젠테이션 속성에는 var()를 쓸 수 없어
            fill="var(--paper)" 로 적으면 무효값이 되어 투명해진다.
            카드와 같은 왜곡 필터를 걸어 손그림 톤을 맞춘다.
          */}
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

          {/* 가운데 홈 버튼이 들어갈 자리 */}
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
