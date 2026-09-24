import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio'

import { fetchPreview, type PreviewResponse } from '../utils/api'

/**
 * 30초 미리듣기.
 *
 * **한 번에 한 곡만 나온다.** 카드마다 플레이어를 두면 여러 곡이 겹쳐 나오므로
 * 플레이어는 모듈 수준에 하나만 두고, 지금 울리는 곡이 누구인지만 공유한다.
 * 앨범아트는 카드마다 다르니 각자 들고 있는다.
 */
let player: AudioPlayer | null = null
let finishSub: { remove: () => void } | null = null
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

// 무음 스위치가 켜져 있어도 들리게 한다. 미리듣기는 사용자가 눌러야만 나오므로
// 무음 모드에서 조용히 무시되면 고장 난 것처럼 보인다.
let audioModeSet = false
async function ensureAudioMode() {
  if (audioModeSet) return
  audioModeSet = true
  await setAudioModeAsync({ playsInSilentMode: true }).catch(() => undefined)
}

/**
 * 지금 쓰는 플레이어를 멈추고 치운다.
 *
 * **리스너를 먼저 뗀다.** 치우는 도중 상태 이벤트가 나면 그 핸들러가
 * 방금 시작한 *다음* 곡까지 꺼버린다 (웹에서 겪은 문제).
 */
export function stopPreview() {
  finishSub?.remove()
  finishSub = null
  if (player) {
    player.pause()
    player.remove()
    player = null
  }
  if (playingKey !== null) {
    playingKey = null
    emit()
  }
}

async function play(key: string, url: string) {
  stopPreview()
  await ensureAudioMode()

  const next = createAudioPlayer(url)
  player = next
  playingKey = key
  finishSub = next.addListener('playbackStatusUpdate', (status) => {
    // 그새 다른 곡으로 넘어갔다면 건드리지 않는다
    if (status.didJustFinish && player === next) stopPreview()
  })
  emit()
  next.play()
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
  useEffect(
    () => () => {
      if (playingRef.current) stopPreview()
    },
    [],
  )

  const toggle = useCallback(async () => {
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
