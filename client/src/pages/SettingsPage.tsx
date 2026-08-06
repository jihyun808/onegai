import { useState } from 'react'

import { Modal } from '../components/Modal'
import { Segmented } from '../components/Segmented'
import { useAuth } from '../hooks/useAuth'
import { useBookmarks } from '../hooks/useBookmarks'
import { useSettings, type SortOrder } from '../hooks/useSettings'
import * as authApi from '../utils/auth'
import * as favoritesApi from '../utils/favorites'
import './SettingsPage.css'

const SORT_OPTIONS = [
  { value: 'release' as SortOrder, label: '최신 발매순' },
  { value: 'no' as SortOrder, label: '곡번호순' },
]

const APP_VERSION = '0.1.0'
const CONTACT = 'dlwlgushi@gmail.com'

export function SettingsPage() {
  const { settings, update } = useSettings()
  const { session, logout } = useAuth()
  const { items, reload } = useBookmarks(Boolean(session))
  const [confirming, setConfirming] = useState<'clear' | 'withdraw' | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  async function exportFavorites() {
    if (items.length === 0) {
      setNotice('내보낼 즐겨찾기가 없어요.')
      return
    }

    const text = items
      .map((song) => {
        const numbers = Object.entries(song.brands)
          .map(([brand, list]) => `${brand === 'tj' ? '태진' : '금영'} ${list?.join(', ')}`)
          .join(' / ')
        return `${song.title} - ${song.singer}\n  ${numbers}`
      })
      .join('\n')

    try {
      await navigator.clipboard.writeText(text)
      setNotice(`${items.length}곡을 복사했어요.`)
    } catch {
      // 클립보드 권한이 없거나 https가 아닐 때
      setNotice('복사하지 못했어요.')
    }
  }

  async function clearFavorites() {
    if (session) await favoritesApi.clear().catch(() => undefined)
    else localStorage.removeItem('kada:bookmarks:v1')
    await reload()
    setConfirming(null)
    setNotice('즐겨찾기를 모두 지웠어요.')
  }

  async function withdraw() {
    await authApi.remove().catch(() => undefined)
    await logout()
    setConfirming(null)
    setNotice('탈퇴가 완료됐어요.')
  }

  return (
    <div className="settings">
      <section className="settings__group">
        <h2 className="settings__title">검색</h2>

        <div className="settings__row">
          <div className="settings__label">
            한국어 노래 표시
            <span className="settings__desc">
              일본곡 전용이라 기본으로 감춰요. 애니 주제가의 한국어판을 찾는다면 켜세요.
            </span>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={settings.showKorean}
            className={`settings__switch ${settings.showKorean ? 'is-on' : ''}`}
            onClick={() => update({ showKorean: !settings.showKorean })}
          >
            <span className="settings__knob" />
          </button>
        </div>

        <div className="settings__row settings__row--stack">
          <div className="settings__label">
            정렬 기준
            <span className="settings__desc">검색 결과를 늘어놓는 순서예요.</span>
          </div>
          <Segmented
            label="정렬 기준"
            options={SORT_OPTIONS}
            value={settings.sort}
            onChange={(sort) => update({ sort })}
          />
        </div>
      </section>

      <section className="settings__group">
        <h2 className="settings__title">데이터</h2>

        <button type="button" className="settings__action" onClick={exportFavorites}>
          즐겨찾기 내보내기
          <span className="settings__desc">번호까지 텍스트로 복사해요.</span>
        </button>

        <button
          type="button"
          className="settings__action"
          onClick={() => setConfirming('clear')}
        >
          즐겨찾기 전체 삭제
          <span className="settings__desc">
            {session ? '계정에 담아둔 곡을 모두 지워요.' : '이 기기에 담아둔 곡을 모두 지워요.'}
          </span>
        </button>
      </section>

      <section className="settings__group">
        <h2 className="settings__title">정보</h2>

        <div className="settings__info">
          <span>앱 버전</span>
          <span>{APP_VERSION}</span>
        </div>
        <div className="settings__info">
          <span>노래 정보</span>
          <span>태진 · 금영 · manana</span>
        </div>
        <div className="settings__info">
          <span>글꼴</span>
          <span>여기어때 잘난체</span>
        </div>
        <a className="settings__info settings__info--link" href={`mailto:${CONTACT}`}>
          <span>문의</span>
          <span>{CONTACT}</span>
        </a>

        <p className="settings__legal">
          이 페이지에는 ㈜여기어때컴퍼니가 제공한 여기어때 잘난체가 적용되어 있습니다.
          곡 정보는 태진미디어·금영엔터테인먼트 및 manana API에서 가져옵니다.
        </p>
        {/* TODO: 출시 전 개인정보처리방침·이용약관 링크를 여기에 건다 */}
      </section>

      {session && (
        <section className="settings__group">
          <button
            type="button"
            className="settings__withdraw"
            onClick={() => setConfirming('withdraw')}
          >
            회원탈퇴
          </button>
        </section>
      )}

      {notice && (
        <p className="settings__notice" role="status">
          {notice}
        </p>
      )}

      {confirming && (
        <Modal
          title={confirming === 'clear' ? '즐겨찾기 전체 삭제' : '회원탈퇴'}
          onClose={() => setConfirming(null)}
        >
          <p className="settings__confirm">
            {confirming === 'clear'
              ? '담아둔 곡이 모두 사라져요. 되돌릴 수 없어요.'
              : '계정과 담아둔 곡이 모두 사라져요. 되돌릴 수 없어요.'}
          </p>
          <div className="settings__confirm-buttons">
            <button
              type="button"
              className="settings__cancel"
              onClick={() => setConfirming(null)}
            >
              취소
            </button>
            <button
              type="button"
              className="settings__danger"
              onClick={confirming === 'clear' ? clearFavorites : withdraw}
            >
              {confirming === 'clear' ? '삭제' : '탈퇴'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}
