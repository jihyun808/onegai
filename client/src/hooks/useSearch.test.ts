import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { useSearch } from './useSearch'

/** 서버 응답 한 장. */
function page({
  songs,
  returned,
  has_more = false,
  complete = true,
  titles = [],
}: {
  songs: number
  returned: number
  has_more?: boolean
  complete?: boolean
  titles?: string[]
}) {
  return {
    ok: true,
    status: 200,
    json: async () => ({
      groups: titles.map((title) => ({
        title,
        singer: '初音ミク',
        match_key: title,
        brands: { kumyoung: ['1'] },
      })),
      songs,
      returned,
      has_more,
      complete,
    }),
  } as Response
}

/** 호출된 URL을 순서대로 남긴다. */
function mockPages(pages: Response[]) {
  const urls: string[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    urls.push(String(url))
    return Promise.resolve(pages[Math.min(urls.length - 1, pages.length - 1)])
  })
  return urls
}

describe('useSearch 페이지 넘기기', () => {
  it('공식까지 뒤진 결과였다면 다음 페이지도 공식으로 부른다', async () => {
    // 1차(DB만)가 0건 → 2차(공식)에서 115곡 → 스크롤로 다음 장
    const urls = mockPages([
      page({ songs: 0, returned: 0, complete: false }),
      page({ songs: 115, returned: 50, has_more: true, titles: ['メズマライザー'] }),
      page({ songs: 115, returned: 50, has_more: true, titles: ['ヴァンパイア'] }),
    ])

    const { result } = renderHook(() => useSearch('미쿠', 'singer'))

    await waitFor(() => expect(result.current.total).toBe(115))
    act(() => result.current.loadMore())
    await waitFor(() => expect(urls).toHaveLength(3))

    // 이게 빠지면 서버가 1차 캐시를 보고 0건을 돌려준다 → '검색 결과가 없어요'
    expect(urls[2]).toContain('full=1')
    expect(urls[2]).toContain('offset=50')
  })

  it('다음 페이지가 0건이어도 이미 받은 결과를 지우지 않는다', async () => {
    const urls = mockPages([
      page({ songs: 60, returned: 50, has_more: true, titles: ['神っぽいな'] }),
      page({ songs: 0, returned: 0 }),
    ])

    const { result } = renderHook(() => useSearch('미쿠', 'singer'))

    await waitFor(() => expect(result.current.total).toBe(60))
    act(() => result.current.loadMore())
    await waitFor(() => expect(urls).toHaveLength(2))

    expect(result.current.groups).toHaveLength(1)
  })
})
