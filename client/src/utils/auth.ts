import type { Session } from '../hooks/useAuth'

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

export function me(): Promise<Session | null> {
  return request('/me')
}

export function updateMe(patch: {
  username?: string
  avatar?: string
}): Promise<Session> {
  return request('/me', { method: 'PATCH', body: JSON.stringify(patch) })
}

export function remove(): Promise<void> {
  return request('/me', { method: 'DELETE' })
}
