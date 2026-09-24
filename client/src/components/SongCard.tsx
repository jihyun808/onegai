import { useState } from 'react'

import { usePreview } from '../hooks/usePreview'
import type { Brand, SongGroup } from '../types/karaoke'
import { PauseIcon, PlayIcon } from './icons'
import { LyricsModal } from './LyricsModal'
import { Spinner } from './Spinner'
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
  // 팝업을 열 때 비로소 가사를 불러온다. 카드 50장이면 요청도 50번이라
  // 미리 받아둘 수는 없다.
  const [showLyrics, setShowLyrics] = useState(false)
  const preview = usePreview(group.match_key, group.title, group.singer)

  return (
    <li className="song sketch">
      {/*
        누르기 전에는 빈 ▶ 자리다. 앨범아트도 이때 처음 받아온다 —
        카드마다 미리 부르면 목록 한 장에 iTunes 요청이 50번 나간다.
      */}
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
        {/*
          번역 제목은 원어 아래에 작게 둔다. 노래방 기계에 찍혀 있는 것은
          원어라, 그쪽이 커야 번호를 찾아 누를 때 헷갈리지 않는다.
        */}
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
