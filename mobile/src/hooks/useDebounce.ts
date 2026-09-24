import { useEffect, useState } from 'react'

/** value가 delay 동안 그대로일 때만 갱신된다. 타이핑 중 검색 폭주를 막는다. */
export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}
