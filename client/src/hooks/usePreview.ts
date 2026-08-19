import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'

import { fetchPreview, type PreviewResponse } from '../utils/api'

/**
 * 30초 미리듣기.
 *
 * **한 번에 한 곡만 나온다.** 카드마다 오디오를 두면 여러 곡이 겹쳐 나오므로
 * 재생기는 모듈 수준에 하나만 두고, 지금 울리는 곡이 누구인지만 공유한다.
 * 앨범아트는 카드마다 다르니 각자 들고 있는다.
 */
let audio: HTMLAudioElement | null = null
let playingKey: string | null = null

const listeners = new Set<() => void>()

function emit() {
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function handleEnd() {
  stopPreview()
}

/**
 * 지금 쓰는 재생기를 떼어 내고 돌려준다.
 *
 * **리스너를 먼저 뗀다.** 아래에서 `src`를 비우면 error 이벤트가 나는데,
 * 붙어 있으면 그 핸들러가 방금 시작한 *다음* 곡까지 꺼버린다.
 * (곡을 이어서 누르면 두 번째가 재생되자마자 멈추던 원인)
 */
function detach() {
  const el = audio
  if (!el) return null
  el.removeEventListener('ended', handleEnd)
  el.removeEventListener('error', handleEnd)
  audio = null
  playingKey = null
  return el
}

function release(el: HTMLAudioElement) {
  el.pause()
  // 내려받기를 끊는다. 안 그러면 멈춘 뒤에도 30초치를 계속 받는다.
  el.src = ''
}

export function stopPreview() {
  const el = detach()
  if (!el) return
  release(el)
  emit()
}

function play(key: string, url: string) {
  const previous = detach()
  if (previous) release(previous)

  const el = new Audio(url)
  el.addEventListener('ended', handleEnd)
  el.addEventListener('error', handleEnd)
  audio = el
  playingKey = key
  emit()

  // 브라우저가 자동재생을 막으면 거부된다. 조용히 멈춘 상태로 되돌린다 —
  // 이때 응답은 이미 받아 뒀으므로 한 번 더 누르면 곧바로 재생된다.
  return el.play().catch(() => {
    // 그새 다른 곡으로 넘어갔다면 건드리지 않는다
    if (audio === el) stopPreview()
  })
}

/**
 * @param id 이 카드를 가리키는 값. 제목+가수로 만들면 같은 제목·가수를 가진
 *           다른 그룹까지 함께 재생 중으로 보이므로 `match_key`를 받는다.
 */
export function usePreview(id: string, title: string, singer: string) {
  const current = useSyncExternalStore(subscribe, () => playingKey)
  const playing = current === id

  const [data, setData] = useState<PreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)

  // 조회 중인지를 ref로도 들고 있는다. `loading` 상태만 보면 리렌더가
  // 끼어들기 전에 또 누른 경우를 못 막는다 — 연타는 바로 그 경우다.
  const inFlight = useRef(false)

  // 재생 중인 카드가 사라지면(검색어를 바꾸면) 소리도 멈춰야 한다
  const playingRef = useRef(playing)
  playingRef.current = playing
  useEffect(() => () => {
    if (playingRef.current) stopPreview()
  }, [])

  const toggle = useCallback(async () => {
    // 조회를 기다리는 중에 또 누르면 요청이 겹친다
    if (inFlight.current) return

    if (playing) {
      stopPreview()
      return
    }

    let info = data
    if (!info) {
      inFlight.current = true
      setLoading(true)
      setFailed(false)
      try {
        info = await fetchPreview(title, singer)
        setData(info)
      } catch {
        // 통신 실패다. `data`를 비워 둬야 다시 누를 때 재시도된다 —
        // 여기서 '없는 곡'으로 굳히면 잠깐 끊긴 것 때문에 버튼이 영영 잠긴다.
        setFailed(true)
        return
      } finally {
        inFlight.current = false
        setLoading(false)
      }
    }

    if (info.available && info.preview_url) await play(id, info.preview_url)
  }, [playing, data, title, singer, id])

  return {
    playing,
    loading,
    /** 눌러서 받아온 뒤에만 있다. 그전에는 아트워크를 그리지 않는다. */
    artwork: data?.artwork_url,
    /** iTunes에 미리듣기가 없는 곡. 통신 실패와 달리 다시 눌러도 소용없다. */
    missing: Boolean(data && !data.available),
    /** 통신 실패. 다시 누르면 재시도한다. */
    failed,
    toggle,
  }
}
