import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiRequestError } from '../utils/api'
import { stopPreview, usePreview } from './usePreview'

const created: HTMLAudioElement[] = []
let playImpl: () => Promise<void>

function setPaused(el: HTMLMediaElement, paused: boolean) {
  Object.defineProperty(el, 'paused', { value: paused, configurable: true })
}

beforeEach(() => {
  created.length = 0
  playImpl = () => Promise.resolve()

  vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockImplementation(function (
    this: HTMLAudioElement,
  ) {
    setPaused(this, false)
    if (!created.includes(this)) created.push(this)
    return playImpl()
  })

  vi.spyOn(window.HTMLMediaElement.prototype, 'pause').mockImplementation(function (
    this: HTMLAudioElement,
  ) {
    setPaused(this, true)
  })
})

afterEach(() => {
  act(() => stopPreview())
})

function mockFetch(body: unknown, ok = true) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok,
    status: ok ? 200 : 502,
    json: async () => body,
  } as Response)
}

const FOUND = {
  available: true,
  preview_url: 'https://x/a.m4a',
  artwork_url: 'https://x/art.jpg',
}

describe('usePreview', () => {
  it('누르면 그때 조회하고 재생한다', async () => {
    const fetchSpy = mockFetch(FOUND)
    const { result } = renderHook(() => usePreview('id-1', '夜に駆ける', 'YOASOBI'))

    expect(fetchSpy).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.toggle()
    })

    expect(fetchSpy).toHaveBeenCalledOnce()
    expect(result.current.playing).toBe(true)
    expect(result.current.artwork).toBe('https://x/art.jpg')
  })

  it('다시 누르면 멈춘다', async () => {
    mockFetch(FOUND)
    const { result } = renderHook(() => usePreview('id-1', '曲', '가수'))

    await act(async () => {
      await result.current.toggle()
    })
    await act(async () => {
      await result.current.toggle()
    })

    expect(result.current.playing).toBe(false)
  })

  it('멈춘 뒤에는 다시 조회하지 않는다', async () => {
    const fetchSpy = mockFetch(FOUND)
    const { result } = renderHook(() => usePreview('id-1', '曲', '가수'))

    await act(async () => {
      await result.current.toggle()
    })
    await act(async () => {
      await result.current.toggle()
    })
    await act(async () => {
      await result.current.toggle()
    })

    expect(fetchSpy).toHaveBeenCalledOnce()
  })

  it('한 번에 한 곡만 울린다', async () => {
    mockFetch(FOUND)
    const first = renderHook(() => usePreview('id-1', 'A', '가수'))
    const second = renderHook(() => usePreview('id-2', 'B', '가수'))

    await act(async () => {
      await first.result.current.toggle()
    })
    await act(async () => {
      await second.result.current.toggle()
    })

    expect(first.result.current.playing).toBe(false)
    expect(second.result.current.playing).toBe(true)
    expect(created.filter((el) => !el.paused)).toHaveLength(1)
  })

  it('앞 곡을 정리하다가 다음 곡을 끄지 않는다', async () => {
    mockFetch(FOUND)
    const first = renderHook(() => usePreview('id-1', 'A', '가수'))
    const second = renderHook(() => usePreview('id-2', 'B', '가수'))

    await act(async () => {
      await first.result.current.toggle()
    })
    const previous = created[0]

    await act(async () => {
      await second.result.current.toggle()
    })
    act(() => {
      previous.dispatchEvent(new Event('error'))
    })

    expect(second.result.current.playing).toBe(true)
  })

  it('같은 곡이 끝나면 재생 표시가 풀린다', async () => {
    mockFetch(FOUND)
    const { result } = renderHook(() => usePreview('id-1', 'A', '가수'))

    await act(async () => {
      await result.current.toggle()
    })
    act(() => {
      created[0].dispatchEvent(new Event('ended'))
    })

    expect(result.current.playing).toBe(false)
  })

  it('카드가 사라지면 소리도 멎는다', async () => {
    mockFetch(FOUND)
    const { result, unmount } = renderHook(() => usePreview('id-1', 'A', '가수'))

    await act(async () => {
      await result.current.toggle()
    })
    unmount()

    expect(created.every((el) => el.paused)).toBe(true)
  })

  it('조회 중 연타해도 한 번만 부른다', async () => {
    const fetchSpy = mockFetch(FOUND)
    const { result } = renderHook(() => usePreview('id-1', 'A', '가수'))

    await act(async () => {
      const pending = result.current.toggle()
      result.current.toggle()
      result.current.toggle()
      await pending
    })

    expect(fetchSpy).toHaveBeenCalledOnce()
  })

  it('iTunes에 없는 곡은 missing으로 굳는다', async () => {
    mockFetch({ available: false, reason: '미리듣기를 찾지 못했어요.' })
    const { result } = renderHook(() => usePreview('id-1', 'A', '가수'))

    await act(async () => {
      await result.current.toggle()
    })

    expect(result.current.missing).toBe(true)
    expect(result.current.failed).toBe(false)
  })

  it('통신 실패는 missing이 아니라 failed다 — 다시 누르면 살아난다', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(new ApiRequestError('실패', 502))
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => FOUND } as Response)

    const { result } = renderHook(() => usePreview('id-1', 'A', '가수'))

    await act(async () => {
      await result.current.toggle()
    })
    expect(result.current.failed).toBe(true)
    expect(result.current.missing).toBe(false)

    await act(async () => {
      await result.current.toggle()
    })

    expect(result.current.playing).toBe(true)
    expect(result.current.failed).toBe(false)
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it('자동재생이 막히면 조용히 멈춘다', async () => {
    mockFetch(FOUND)
    playImpl = () => Promise.reject(new Error('NotAllowedError'))
    const { result } = renderHook(() => usePreview('id-1', 'A', '가수'))

    await act(async () => {
      await result.current.toggle()
    })

    expect(result.current.playing).toBe(false)
  })
})
