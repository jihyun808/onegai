import { useState } from 'react'

import { PRIVACY_URL, TERMS_URL } from '../constants/legal'
import { AuthRequestError } from '../utils/auth'
import './AuthForm.css'

export type AuthMode = 'login' | 'signup'

const ID_MIN = 5
const ID_MAX = 20
const PW_MIN = 8

interface Props {
  mode: AuthMode
  onSubmit: (id: string, password: string) => Promise<void>
}

export function AuthForm({ mode, onSubmit }: Props) {
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [agreed, setAgreed] = useState({ terms: false, privacy: false })
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

    if (isSignup && !(agreed.terms && agreed.privacy)) {
      found.agree = '필수 항목에 동의해야 가입할 수 있어요.'
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

      {isSignup && (
        <fieldset className="auth__agree">
          <legend className="auth__agree-title">약관 동의</legend>

          <label className="auth__check">
            <input
              type="checkbox"
              checked={agreed.terms}
              onChange={(e) => setAgreed((prev) => ({ ...prev, terms: e.target.checked }))}
            />
            <span>
              <a href={TERMS_URL} target="_blank" rel="noopener noreferrer">
                이용약관
              </a>
              에 동의합니다 <b>(필수)</b>
            </span>
          </label>

          <label className="auth__check">
            <input
              type="checkbox"
              checked={agreed.privacy}
              onChange={(e) => setAgreed((prev) => ({ ...prev, privacy: e.target.checked }))}
            />
            <span>
              <a href={PRIVACY_URL} target="_blank" rel="noopener noreferrer">
                개인정보 수집·이용
              </a>
              에 동의합니다 <b>(필수)</b>
            </span>
          </label>

          <p className="auth__agree-note">
            아이디와 비밀번호만 저장하며, 탈퇴하면 즉시 지워져요.
          </p>

          {errors.agree && (
            <span className="auth__hint" role="alert">
              {errors.agree}
            </span>
          )}
        </fieldset>
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
