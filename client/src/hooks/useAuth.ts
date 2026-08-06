import { useCallback, useEffect, useState } from 'react'

import * as api from '../utils/auth'
import { migrateLocal } from './useBookmarks'

/**
 * 로그인 상태.
 *
 * 세션은 httpOnly 쿠키라 자바스크립트가 읽을 수 없다.
 * 그래서 앱이 뜰 때 `/api/auth/me`로 한 번 물어보고, 그 뒤로는 상태로 들고 있는다.
 */
export interface Session {
  id: number
  username: string
  /** 프로필 이미지 data URL. 256px로 줄여 저장한다. */
  avatar?: string | null
}

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let alive = true
    api
      .me()
      .then((found) => alive && setSession(found))
      .catch(() => alive && setSession(null))
      .finally(() => alive && setReady(true))
    return () => {
      alive = false
    }
  }, [])

  /** 가입 전 기기에 담아둔 즐겨찾기를 계정으로 옮긴다. 실패해도 가입은 유지한다. */
  async function carryOverBookmarks() {
    try {
      await migrateLocal()
    } catch {
      // 옮기지 못해도 로컬에 그대로 남아 있으므로 데이터를 잃지는 않는다
    }
  }

  // 로그인은 합치지 않는다. 이미 서버에 담아둔 목록이 있는데
  // 그 기기에서 남이 담아둔 것까지 섞이면 곤란하다.
  const login = useCallback(async (username: string, password: string) => {
    setSession(await api.login(username, password))
  }, [])

  const signup = useCallback(async (username: string, password: string) => {
    const created = await api.register(username, password)
    await carryOverBookmarks()
    setSession(created)
  }, [])

  const logout = useCallback(async () => {
    await api.logout().catch(() => undefined)
    setSession(null)
  }, [])

  const updateProfile = useCallback(
    async (patch: { username?: string; avatar?: string }) => {
      setSession(await api.updateMe(patch))
    },
    [],
  )

  return { session, ready, login, signup, logout, updateProfile }
}
