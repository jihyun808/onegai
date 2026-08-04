import type { Brand, SongGroup } from '../types/karaoke'
import './SongCard.css'

/** 뱃지 순서를 고정한다 (태진 먼저). 데이터 순서에 흔들리지 않게. */
const BRAND_ORDER: Brand[] = ['tj', 'kumyoung']

const BRAND_LABEL: Record<Brand, string> = {
  tj: '태진',
  kumyoung: '금영',
}

interface Props {
  group: SongGroup
  bookmarked: boolean
  onToggleBookmark: (group: SongGroup) => void
}

export function SongCard({ group, bookmarked, onToggleBookmark }: Props) {
  return (
    <li className="song sketch">
      <div className="song__body">
        <p className="song__title">{group.title}</p>
        <p className="song__singer">{group.singer || '가수 정보 없음'}</p>
      </div>

      {/* 번호가 이 화면의 주인공이라 우측에 크게 나란히 둔다 */}
      <div className="song__numbers">
        {BRAND_ORDER.map((brand) => {
          const numbers = group.brands[brand]
          return (
            <div key={brand} className={`song__brand song__brand--${brand}`}>
              <span className="song__brand-name">{BRAND_LABEL[brand]}</span>
              {numbers?.length ? (
                numbers.map((no) => (
                  <span key={no} className="song__no">
                    {no}
                  </span>
                ))
              ) : (
                // 한쪽에만 있는 곡도 자리를 비워 표의 열을 맞춘다
                <span className="song__no song__no--none">—</span>
              )}
            </div>
          )
        })}
      </div>

      <button
        className={`song__mark ${bookmarked ? 'is-on' : ''}`}
        type="button"
        onClick={() => onToggleBookmark(group)}
        aria-pressed={bookmarked}
        aria-label={`${group.title} 즐겨찾기 ${bookmarked ? '해제' : '추가'}`}
      >
        <svg viewBox="0 0 14 18" width="14" height="18" aria-hidden="true">
          <path
            d="M1 1.5h12v15l-6-4.5-6 4.5z"
            fill={bookmarked ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </li>
  )
}
