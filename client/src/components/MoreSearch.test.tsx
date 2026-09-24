import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { webSearchUrl } from '../utils/links'
import { MoreSearch } from './MoreSearch'

describe('MoreSearch', () => {
  it('공식 조회 버튼을 누르면 알린다', async () => {
    const onLoadMore = vi.fn()
    render(<MoreSearch query="晩餐歌" onLoadMore={onLoadMore} canLoadMore />)

    await userEvent.click(screen.getByRole('button', { name: /결과 더 불러오기/ }))
    expect(onLoadMore).toHaveBeenCalled()
  })

  it('공식 조회가 진행 중이면 버튼만 감추고 링크는 남긴다', () => {
    render(<MoreSearch query="晩餐歌" onLoadMore={() => {}} canLoadMore={false} />)

    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByRole('link', { name: '브라우저에서 검색하기' })).toBeInTheDocument()
  })

  it('브라우저 링크는 새 탭으로 안전하게 연다', () => {
    render(<MoreSearch query="晩餐歌" onLoadMore={() => {}} canLoadMore />)

    const link = screen.getByRole('link', { name: '브라우저에서 검색하기' })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('검색어를 따옴표로 묶어 인코딩한다', () => {
    // 묶지 않으면 낱말이 흩어져 엉뚱한 결과가 나온다
    const url = webSearchUrl(' 夜に駆ける ')
    expect(url).toContain(encodeURIComponent('"夜に駆ける" 노래방 번호'))
  })
})
