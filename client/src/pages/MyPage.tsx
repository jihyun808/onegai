import { useMemo, useState } from 'react'

import { AuthForm, type AuthMode } from '../components/AuthForm'
import { Modal } from '../components/Modal'
import { ProfileForm } from '../components/ProfileForm'
import { SongCard } from '../components/SongCard'
import { StateMessage } from '../components/StateMessage'
import { useAuth } from '../hooks/useAuth'
import { useBookmarks, type Bookmark } from '../hooks/useBookmarks'
import type { SongGroup } from '../types/karaoke'
import './MyPage.css'

type Sort = 'recent' | 'oldest' | 'title'

const SORTS: { value: Sort; label: string }[] = [
  { value: 'recent', label: '최신순' },
  { value: 'oldest', label: '오래된순' },
  { value: 'title', label: '글자순' },
]

function toGroup(bookmark: Bookmark): SongGroup {
  return {
    title: bookmark.title,
    singer: bookmark.singer,
    match_key: bookmark.match_key,
    brands: bookmark.brands,
    both: Object.keys(bookmark.brands).length > 1,
  }
}

export function MyPage() {
  const { session, login, signup, logout, updateProfile } = useAuth()
  const { items, toggle, has } = useBookmarks(Boolean(session))
  const [sort, setSort] = useState<Sort>('recent')
  // 어떤 팝업을 띄울지. null이면 안 띄운다.
  const [auth, setAuth] = useState<AuthMode | null>(null)
  const [editing, setEditing] = useState(false)

  const sorted = useMemo(() => {
    const copy = [...items]
    if (sort === 'title') {
      return copy.sort((a, b) => a.title.localeCompare(b.title, 'ko'))
    }
    copy.sort((a, b) => a.saved_at.localeCompare(b.saved_at))
    return sort === 'recent' ? copy.reverse() : copy
  }, [items, sort])

  return (
    <>
      <section className="profile sketch">
        <div className="profile__avatar" aria-hidden="true">
          {session?.avatar && <img src={session.avatar} alt="" />}
        </div>
        <div className="profile__body">
          {session ? (
            <>
              <p className="profile__name">{session.username}</p>
              <div className="profile__links">
                <button
                  type="button"
                  className="profile__link"
                  onClick={() => setEditing(true)}
                >
                  내 정보 수정
                </button>
                <span className="profile__divider" aria-hidden="true">
                  |
                </span>
                <button type="button" className="profile__link" onClick={logout}>
                  로그아웃
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="profile__name">로그인 전이에요</p>
              <p className="profile__note">지금은 이 기기에만 저장돼요.</p>
              <div className="profile__buttons">
                <button
                  type="button"
                  className="profile__action"
                  onClick={() => setAuth('login')}
                >
                  로그인
                </button>
                <button
                  type="button"
                  className="profile__action"
                  onClick={() => setAuth('signup')}
                >
                  회원가입
                </button>
              </div>
            </>
          )}
        </div>
      </section>

      {auth && (
        <Modal
          title={auth === 'login' ? '로그인' : '회원가입'}
          onClose={() => setAuth(null)}
        >
          <AuthForm
            mode={auth}
            onSubmit={async (id, password) => {
              await (auth === 'login' ? login(id, password) : signup(id, password))
              setAuth(null)
            }}
          />
        </Modal>
      )}

      {editing && session && (
        <Modal title="내 정보 수정" onClose={() => setEditing(false)}>
          <ProfileForm
            session={session}
            onSave={async (patch) => {
              await updateProfile(patch)
              setEditing(false)
            }}
          />
        </Modal>
      )}

      <div className="mypage__head">
        <h2 className="mypage__heading">
          내가 좋아하는 노래 <span className="mypage__count">{items.length}</span>
        </h2>
        {items.length > 0 && (
          <div className="mypage__sorts">
            {SORTS.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`mypage__sort ${sort === option.value ? 'is-on' : ''}`}
                aria-pressed={sort === option.value}
                onClick={() => setSort(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {items.length === 0 ? (
        <StateMessage
          title="저장한 노래가 없어요"
          description="검색 결과에서 북마크를 눌러 담아보세요"
        />
      ) : (
        <ul className="mypage__list">
          {sorted.map((bookmark) => {
            const group = toGroup(bookmark)
            return (
              <SongCard
                key={group.match_key}
                group={group}
                bookmarked={has(group.match_key)}
                onToggleBookmark={toggle}
              />
            )
          })}
        </ul>
      )}
    </>
  )
}
