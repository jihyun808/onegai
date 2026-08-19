import { describe, expect, it, vi } from 'vitest'

import { ApiRequestError, fetchLyrics, fetchPreview, searchSongs } from './api'

function mockResponse(body: unknown, ok = true, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok,
    status,
    json: async () => body,
  } as Response)
}

function calledUrl(spy: ReturnType<typeof mockResponse>) {
  return String(spy.mock.calls[0][0])
}

describe('searchSongs', () => {
  it('켜진 설정만 질의로 보낸다', async () => {
    const spy = mockResponse({ groups: [] })
    await searchSongs({ q: '夜', type: 'song', brand: 'all' })

    const url = calledUrl(spy)
    expect(url).toContain('q=%E5%A4%9C')
    // 안 켠 것은 아예 붙이지 않는다 — 서버 기본값을 덮어쓰면 안 된다
    expect(url).not.toContain('full=')
    expect(url).not.toContain('korean=')
  })

  it('전체 조회와 한국곡 포함을 플래그로 넘긴다', async () => {
    const spy = mockResponse({ groups: [] })
    await searchSongs({ q: 'a', type: 'song', brand: 'tj', full: true, korean: true })

    expect(calledUrl(spy)).toContain('full=1')
    expect(calledUrl(spy)).toContain('korean=1')
  })

  it('서버가 준 메시지를 그대로 전달한다', async () => {
    mockResponse({ message: '검색어가 너무 짧아요.' }, false, 400)

    await expect(searchSongs({ q: 'a', type: 'song', brand: 'all' })).rejects.toThrow(
      '검색어가 너무 짧아요.',
    )
  })

  it('본문이 JSON이 아니어도 안내 문구를 만든다', async () => {
    // 프록시가 HTML 에러 페이지를 돌려주는 경우
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error('not json')
      },
    } as unknown as Response)

    await expect(searchSongs({ q: 'a', type: 'song', brand: 'all' })).rejects.toBeInstanceOf(
      ApiRequestError,
    )
  })
})

describe('fetchLyrics / fetchPreview', () => {
  /*
   * 서버는 "못 찾았다"를 200 + available:false로 답한다.
   * 그러니 !ok는 프록시·네트워크 문제뿐이고, 이건 다시 시도할 만한 실패다.
   * 둘을 같은 값으로 뭉치면 잠깐 끊긴 것 때문에 버튼이 영영 잠긴다.
   */
  it('못 찾은 것은 예외가 아니다', async () => {
    mockResponse({ available: false, reason: '금영에 등록된 가사가 없어요.' })
    await expect(fetchLyrics('A', 'B')).resolves.toMatchObject({ available: false })

    mockResponse({ available: false, reason: '미리듣기를 찾지 못했어요.' })
    await expect(fetchPreview('A', 'B')).resolves.toMatchObject({ available: false })
  })

  it('통신 실패는 예외로 던진다', async () => {
    mockResponse({}, false, 502)
    await expect(fetchLyrics('A', 'B')).rejects.toBeInstanceOf(ApiRequestError)

    mockResponse({}, false, 502)
    await expect(fetchPreview('A', 'B')).rejects.toBeInstanceOf(ApiRequestError)
  })

  it('제목과 가수를 그대로 실어 보낸다', async () => {
    const spy = mockResponse({ available: true })
    await fetchLyrics('夜に駆ける', 'YOASOBI')

    expect(calledUrl(spy)).toContain('/api/lyrics?')
    expect(calledUrl(spy)).toContain('singer=YOASOBI')
  })
})
