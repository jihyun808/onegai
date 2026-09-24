import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { LyricsModal } from './LyricsModal'

function mockLyrics(body: unknown, ok = true) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok,
    status: ok ? 200 : 502,
    json: async () => body,
  } as Response)
}

const FOUND = {
  available: true,
  provider: '금영',
  search_url: 'https://www.google.com/search?q=x',
  lines: [
    { ko: '시즈무요오니', ja: '沈むように' },
    { ko: '도케테 유쿠요오니', ja: '溶けてゆくように' },
  ],
}

describe('LyricsModal', () => {
  it('한글 발음과 일본어 원문을 짝지어 보여준다', async () => {
    mockLyrics(FOUND)
    render(<LyricsModal title="夜に駆ける" singer="YOASOBI" onClose={() => {}} />)

    expect(await screen.findByText('시즈무요오니')).toBeInTheDocument()
    expect(screen.getByText('沈むように')).toBeInTheDocument()
    expect(screen.getByText(/금영/)).toBeInTheDocument()
  })

  it('가사가 오기 전에도 검색 링크를 띄운다', async () => {
    // 기다리기 싫은 사람은 바로 나갈 수 있어야 한다
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))
    render(<LyricsModal title="夜に駆ける" singer="YOASOBI" onClose={() => {}} />)

    const link = screen.getByRole('link', { name: '인터넷에서 찾아보기' })
    expect(link).toHaveAttribute('href', expect.stringContaining('google.com/search'))
    expect(screen.getByText('가사를 찾는 중이에요')).toBeInTheDocument()
  })

  it('링크는 새 탭으로 안전하게 연다', async () => {
    mockLyrics(FOUND)
    render(<LyricsModal title="A" singer="B" onClose={() => {}} />)
    await screen.findByText('시즈무요오니')

    const link = screen.getByRole('link', { name: '인터넷에서 찾아보기' })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('금영에 없으면 사유를 알리고 링크를 남긴다', async () => {
    mockLyrics({
      available: false,
      reason: '금영에 등록된 가사가 없어요.',
      search_url: 'https://www.google.com/search?q=y',
    })
    render(<LyricsModal title="A" singer="B" onClose={() => {}} />)

    expect(await screen.findByText('금영에 등록된 가사가 없어요.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '인터넷에서 찾아보기' })).toHaveAttribute(
      'href',
      'https://www.google.com/search?q=y',
    )
  })

  it('통신이 실패해도 링크는 남는다', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('죽음'))
    render(<LyricsModal title="A" singer="B" onClose={() => {}} />)

    expect(await screen.findByText('가사를 가져오지 못했어요.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '인터넷에서 찾아보기' })).toBeInTheDocument()
  })

  it('닫기를 누르면 알린다', async () => {
    mockLyrics(FOUND)
    const onClose = vi.fn()
    render(<LyricsModal title="A" singer="B" onClose={onClose} />)
    await screen.findByText('시즈무요오니')

    await userEvent.click(screen.getByRole('button', { name: '닫기' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('닫는 중에 응답이 와도 터지지 않는다', async () => {
    // 가사를 다 받기 전에 닫으면 없는 컴포넌트에 상태를 쓰게 된다
    const abort = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            abort()
            reject(Object.assign(new Error('중단'), { name: 'AbortError' }))
          })
        }),
    )

    const { unmount } = render(<LyricsModal title="A" singer="B" onClose={() => {}} />)
    unmount()

    await waitFor(() => expect(abort).toHaveBeenCalled())
  })
})
