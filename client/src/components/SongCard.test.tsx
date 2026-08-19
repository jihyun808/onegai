import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { SongGroup } from '../types/karaoke'
import { SongCard } from './SongCard'

const BOTH: SongGroup = {
  title: '夜に駆ける',
  singer: 'YOASOBI',
  match_key: 'yorunikakeru',
  brands: { tj: ['68506'], kumyoung: ['44796'] },
  both: true,
}

const TJ_ONLY: SongGroup = { ...BOTH, brands: { tj: ['68506'] }, both: false }

function renderCard(group = BOTH, onToggle = vi.fn()) {
  render(<SongCard group={group} bookmarked={false} onToggleBookmark={onToggle} />)
  return onToggle
}

describe('SongCard', () => {
  it('브랜드별 번호를 나란히 보여준다', () => {
    renderCard()

    expect(screen.getByText('태진')).toBeInTheDocument()
    expect(screen.getByText('68506')).toBeInTheDocument()
    expect(screen.getByText('금영')).toBeInTheDocument()
    expect(screen.getByText('44796')).toBeInTheDocument()
  })

  it('한쪽에만 있는 곡도 자리를 비워 열을 맞춘다', () => {
    renderCard(TJ_ONLY)

    // 금영 칸이 사라지면 카드마다 번호 위치가 달라져 읽기 힘들다
    expect(screen.getByText('금영')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('가수 정보가 없으면 그렇다고 적는다', () => {
    renderCard({ ...BOTH, singer: '' })
    expect(screen.getByText('가수 정보 없음')).toBeInTheDocument()
  })

  it('즐겨찾기를 누르면 그룹째 넘긴다', async () => {
    const onToggle = renderCard()

    await userEvent.click(screen.getByRole('button', { name: /즐겨찾기 추가/ }))
    expect(onToggle).toHaveBeenCalledWith(BOTH)
  })

  it('즐겨찾기 상태를 aria-pressed로 알린다', () => {
    render(<SongCard group={BOTH} bookmarked onToggleBookmark={vi.fn()} />)
    expect(screen.getByRole('button', { name: /즐겨찾기 해제/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('가사보기를 누르면 팝업이 열린다', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ available: false, reason: '금영에 등록된 가사가 없어요.' }),
    } as Response)

    renderCard()
    await userEvent.click(screen.getByRole('button', { name: '가사보기' }))

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
  })

  it('그리기만 해서는 미리듣기를 부르지 않는다', () => {
    // 카드 50장이면 iTunes 요청도 50번이 된다
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    renderCard()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('미리듣기를 누른 뒤에야 앨범아트를 받아온다', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        available: true,
        preview_url: 'https://x/a.m4a',
        artwork_url: 'https://x/art.jpg',
      }),
    } as Response)
    vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)

    renderCard()
    expect(document.querySelector('.song__art')).toBeNull()

    await userEvent.click(screen.getByRole('button', { name: /미리듣기 재생/ }))

    await vi.waitFor(() =>
      expect(document.querySelector('.song__art')).toHaveAttribute(
        'src',
        'https://x/art.jpg',
      ),
    )
  })
})
