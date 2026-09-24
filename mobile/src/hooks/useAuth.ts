import { useCallback, useEffect, useState } from 'react'

import * as api from '../utils/auth'
import { migrateLocal } from './useBookmarks'

export interface Session {
  id: number
  username: string
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

  async function carryOverBookmarks() {
    try {
      await migrateLocal()
    } catch {
    }
  }

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
