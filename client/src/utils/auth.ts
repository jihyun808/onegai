import type { Session } from '../hooks/useAuth'

/**
 * 서버가 어느 입력이 문제인지 `field`로 알려준다.
 * 그래야 해당 입력창 아래에 메시지를 붙일 수 있다.
 */
export class AuthRequestError extends Error {
  field?: 'username' | 'password' | 'avatar'

  constructor(message: string, field?: AuthRequestError['field']) {
    super(message)
    this.name = 'AuthRequestError'
    this.field = field
  }
}

async function request(path: string, init: RequestInit = {}) {
  const response = await fetch(`/api/auth${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init.headers },
    // 세션 쿠키를 주고받으려면 필요하다
    credentials: 'same-origin',
  })

  const body = await response.json().catch(() => null)

  if (!response.ok) {
    throw new AuthRequestError(
      body?.message ?? '잠시 후 다시 시도해 주세요.',
      body?.field,
    )
  }

  return body
}

export function register(username: string, password: string): Promise<Session> {
  return request('/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function login(username: string, password: string): Promise<Session> {
  return request('/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logout(): Promise<void> {
  return request('/logout', { method: 'POST' })
}

/** 로그인 상태 확인. 안 했으면 null. */
export function me(): Promise<Session | null> {
  return request('/me')
}

export function updateMe(patch: {
  username?: string
  avatar?: string
}): Promise<Session> {
  return request('/me', { method: 'PATCH', body: JSON.stringify(patch) })
}
