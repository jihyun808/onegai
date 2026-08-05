import { useState } from 'react'

import { AuthRequestError } from '../utils/auth'
import './AuthForm.css'

export type AuthMode = 'login' | 'signup'

/** 서버 스키마(users.email)와 맞춘 제한. 지금은 화면에서만 검사한다. */
const ID_MIN = 5
const ID_MAX = 20
// 비밀번호는 최소 길이만 본다. 상한을 두면 긴 암호구절을 쓰는 사람이 막힌다.
const PW_MIN = 8

interface Props {
  mode: AuthMode
  /** 실제 요청. 아직 서버 API가 없어 화면에서만 호출한다. */
  onSubmit: (id: string, password: string) => Promise<void>
}

export function AuthForm({ mode, onSubmit }: Props) {
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  // 어느 입력이 문제인지에 따라 그 아래에 메시지를 붙인다
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const isSignup = mode === 'signup'

  function validate(): Record<string, string> {
    const found: Record<string, string> = {}

    if (id.length < ID_MIN || id.length > ID_MAX) {
      found.username = `아이디는 ${ID_MIN}~${ID_MAX}자로 입력해 주세요.`
    } else if (!/^[a-zA-Z0-9_]+$/.test(id)) {
      found.username = '아이디는 영문, 숫자, 밑줄만 쓸 수 있어요.'
    }

    if (password.length < PW_MIN) {
      found.password = `비밀번호는 ${PW_MIN}자 이상으로 입력해 주세요.`
    }

    if (isSignup && password !== confirm) {
      found.confirm = '비밀번호가 서로 달라요.'
    }

    return found
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()

    const problems = validate()
    if (Object.keys(problems).length > 0) {
      setErrors(problems)
      return
    }

    setErrors({})
    setBusy(true)
    try {
      await onSubmit(id, password)
    } catch (err) {
      // 서버가 알려준 필드에 붙인다. 모르면 폼 전체 오류로 둔다.
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
      <label className="auth__field">
        <span className="auth__label">아이디</span>
        <input
          className="auth__input"
          value={id}
          onChange={(e) => setId(e.target.value.trim())}
          autoComplete="username"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          maxLength={ID_MAX}
          placeholder={`${ID_MIN}~${ID_MAX}자 영문·숫자`}
          aria-invalid={Boolean(errors.username)}
        />
        {errors.username && <span className="auth__hint">{errors.username}</span>}
      </label>

      <label className="auth__field">
        <span className="auth__label">비밀번호</span>
        <input
          className="auth__input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={isSignup ? 'new-password' : 'current-password'}
          placeholder={`${PW_MIN}자 이상`}
          aria-invalid={Boolean(errors.password)}
        />
        {errors.password && <span className="auth__hint">{errors.password}</span>}
      </label>

      {isSignup && (
        <label className="auth__field">
          <span className="auth__label">비밀번호 확인</span>
          <input
            className="auth__input"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            placeholder="한 번 더 입력해 주세요"
            aria-invalid={Boolean(errors.confirm)}
          />
          {errors.confirm && <span className="auth__hint">{errors.confirm}</span>}
        </label>
      )}

      {errors.form && (
        <p className="auth__error" role="alert">
          {errors.form}
        </p>
      )}

      <button className="auth__submit" type="submit" disabled={busy}>
        {busy ? '잠시만요…' : isSignup ? '가입하기' : '로그인'}
      </button>

    </form>
  )
}
