import { useEffect, useRef } from 'react'

/**
 * 목록 끝의 감시 요소가 화면에 들어오면 onLoadMore를 부른다.
 *
 * 스크롤 이벤트를 직접 듣지 않고 IntersectionObserver를 쓴다.
 * 매 프레임 위치를 계산하지 않아 저사양 기기에서도 부드럽다.
 */
export function useInfiniteScroll(enabled: boolean, onLoadMore: () => void) {
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  // 콜백이 매 렌더 새로 만들어져도 옵저버를 다시 붙이지 않도록 참조로 들고 있는다
  const callbackRef = useRef(onLoadMore)
  callbackRef.current = onLoadMore

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!enabled || !sentinel) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) callbackRef.current()
      },
      // 바닥에 닿기 전에 미리 불러와 끊김을 줄인다
      { rootMargin: '400px 0px' },
    )

    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [enabled])

  return sentinelRef
}
