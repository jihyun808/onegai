import { useRef, useState } from 'react'

import type { Session } from '../hooks/useAuth'
import { AuthRequestError } from '../utils/auth'
import { ACCEPT_ATTR, ImageError, toAvatarDataUrl } from '../utils/image'
import './AuthForm.css'
import './ProfileForm.css'

const ID_MIN = 5
const ID_MAX = 20

interface Props {
  session: Session
  onSave: (patch: { username?: string; avatar?: string }) => Promise<void>
}

export function ProfileForm({ session, onSave }: Props) {
  const [username, setUsername] = useState(session.username)
  const [avatar, setAvatar] = useState(session.avatar ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  async function pickImage(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    try {
      setAvatar(await toAvatarDataUrl(file))
      setErrors({})
    } catch (err) {
      setErrors({
        avatar: err instanceof ImageError ? err.message : '이미지를 처리하지 못했어요.',
      })
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()

    if (username.length < ID_MIN || username.length > ID_MAX) {
      setErrors({ username: `아이디는 ${ID_MIN}~${ID_MAX}자로 입력해 주세요.` })
      return
    }
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      setErrors({ username: '아이디는 영문, 숫자, 밑줄만 쓸 수 있어요.' })
      return
    }

    setErrors({})
    setBusy(true)
    try {
      await onSave({ username, avatar })
    } catch (err) {
      if (err instanceof AuthRequestError && err.field) {
        setErrors({ [err.field]: err.message })
      } else {
        setErrors({
          form: err instanceof Error ? err.message : '잠시 후 다시 시도해 주세요.',
        })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="auth" onSubmit={handleSubmit} noValidate>
      <div className="profile-edit__avatar-row">
        <div className="profile-edit__avatar">
          {avatar ? <img src={avatar} alt="" /> : <span aria-hidden="true" />}
        </div>
        <div className="profile-edit__avatar-actions">
          <button
            type="button"
            className="profile-edit__pick"
            onClick={() => fileRef.current?.click()}
          >
            사진 바꾸기
          </button>
          {avatar && (
            <button
              type="button"
              className="profile-edit__clear"
              onClick={() => setAvatar('')}
            >
              지우기
            </button>
          )}
          <p className="profile-edit__hint">JPG · PNG · WEBP / 5MB 이하</p>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT_ATTR}
          onChange={pickImage}
          hidden
        />
      </div>

      <label className="auth__field">
        <span className="auth__label">아이디</span>
        <input
          className="auth__input"
          value={username}
          onChange={(e) => setUsername(e.target.value.trim())}
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          maxLength={ID_MAX}
          aria-invalid={Boolean(errors.username)}
        />
        {errors.username && <span className="auth__hint">{errors.username}</span>}
      </label>

      {(errors.avatar || errors.form) && (
        <p className="auth__error" role="alert">
          {errors.avatar || errors.form}
        </p>
      )}

      <button className="auth__submit" type="submit" disabled={busy}>
        {busy ? '저장 중…' : '저장'}
      </button>
    </form>
  )
}
