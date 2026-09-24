import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'

import { fetchPreview, type PreviewResponse } from '../utils/api'

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

  return el.play().catch(() => {
    if (audio === el) stopPreview()
  })
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
  useEffect(() => () => {
    if (playingRef.current) stopPreview()
  }, [])

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
