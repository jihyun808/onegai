import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio'

import { fetchPreview, type PreviewResponse } from '../utils/api'

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

let audioModeSet = false
async function ensureAudioMode() {
  if (audioModeSet) return
  audioModeSet = true
  await setAudioModeAsync({ playsInSilentMode: true }).catch(() => undefined)
}

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
    if (status.didJustFinish && player === next) stopPreview()
  })
  emit()
  next.play()
}

export function usePreview(id: string, title: string, singer: string) {
  const current = useSyncExternalStore(subscribe, () => playingKey)
  const playing = current === id

  const [data, setData] = useState<PreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)

  const inFlight = useRef(false)

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
    artwork: data?.artwork_url,
    missing: Boolean(data && !data.available),
    failed,
    toggle,
  }
}
