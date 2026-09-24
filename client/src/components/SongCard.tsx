import { useState } from 'react'

import { usePreview } from '../hooks/usePreview'
import type { Brand, SongGroup } from '../types/karaoke'
import { PauseIcon, PlayIcon } from './icons'
import { LyricsModal } from './LyricsModal'
import { Spinner } from './Spinner'
import './SongCard.css'

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
  const [showLyrics, setShowLyrics] = useState(false)
  const preview = usePreview(group.match_key, group.title, group.singer)

  return (
    <li className="song sketch">
      <button
        className={`song__play ${preview.playing ? 'is-on' : ''}`}
        type="button"
        onClick={preview.toggle}
        disabled={preview.missing}
        aria-label={
          preview.missing
            ? `${group.title} 미리듣기 없음`
            : preview.failed
              ? `${group.title} 미리듣기 다시 시도`
              : `${group.title} 미리듣기 ${preview.playing ? '정지' : '재생'}`
        }
      >
        {preview.artwork && (
          <img className="song__art" src={preview.artwork} alt="" loading="lazy" />
        )}
        <span className="song__play-icon">
          {preview.loading ? (
            <Spinner />
          ) : preview.playing ? (
            <PauseIcon size={18} />
          ) : (
            <PlayIcon size={18} />
          )}
        </span>
      </button>

      <div className="song__body">
        <p className="song__title">{group.title}</p>
        {group.title_ko && group.title_ko !== group.title && (
          <p className="song__title-ko">{group.title_ko}</p>
        )}
        <p className="song__singer">{group.singer || '가수 정보 없음'}</p>
        <button
          className="song__lyrics"
          type="button"
          onClick={() => setShowLyrics(true)}
        >
          가사보기
        </button>
      </div>

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

      {showLyrics && (
        <LyricsModal
          title={group.title}
          singer={group.singer}
          onClose={() => setShowLyrics(false)}
        />
      )}
    </li>
  )
}
