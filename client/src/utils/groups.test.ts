import { describe, expect, it } from 'vitest'

import type { SongGroup } from '../types/karaoke'
import { appendNew, countMatched, filterByBrand, mergeGroups } from './groups'

function group(partial: Partial<SongGroup> & { match_key: string }): SongGroup {
  return {
    title: partial.match_key,
    singer: 'YOASOBI',
    brands: {},
    both: false,
    ...partial,
  }
}

describe('mergeGroups', () => {
  it('페이지가 갈려 들어온 같은 곡을 한 장으로 합친다', () => {
    const merged = mergeGroups(
      [group({ match_key: '夜に駆ける', brands: { tj: ['68506'] } })],
      [group({ match_key: '夜に駆ける', brands: { kumyoung: ['44796'] } })],
    )

    expect(merged).toHaveLength(1)
    expect(merged[0].brands).toEqual({ tj: ['68506'], kumyoung: ['44796'] })
    expect(merged[0].both).toBe(true)
  })

  it('같은 번호가 두 번 와도 한 번만 남긴다', () => {
    const merged = mergeGroups(
      [group({ match_key: '群青', brands: { tj: ['68506'] } })],
      [group({ match_key: '群青', brands: { tj: ['68506', '68507'] } })],
    )

    expect(merged[0].brands.tj).toEqual(['68506', '68507'])
  })

  it('넘겨받은 배열을 건드리지 않는다', () => {
    const prev = [group({ match_key: '群青', brands: { tj: ['1'] } })]
    mergeGroups(prev, [group({ match_key: '群青', brands: { kumyoung: ['2'] } })])

    expect(prev[0].brands).toEqual({ tj: ['1'] })
  })

  it('한쪽에만 있는 곡은 both가 아니다', () => {
    const merged = mergeGroups([], [group({ match_key: 'A', brands: { tj: ['1'] } })])
    expect(merged[0].both).toBe(false)
  })
})

describe('appendNew', () => {
  it('처음 보는 곡은 끝에 붙인다', () => {
    const result = appendNew(
      [group({ match_key: 'A' }), group({ match_key: 'B' })],
      [group({ match_key: 'C' })],
    )

    expect(result.map((g) => g.match_key)).toEqual(['A', 'B', 'C'])
  })

  it('이미 있는 곡은 자리를 지키고 번호만 채운다', () => {
    const result = appendNew(
      [
        group({ match_key: 'A', brands: { tj: ['1'] } }),
        group({ match_key: 'B' }),
      ],
      [group({ match_key: 'A', brands: { kumyoung: ['9'] } })],
    )

    expect(result.map((g) => g.match_key)).toEqual(['A', 'B'])
    expect(result[0].brands).toEqual({ tj: ['1'], kumyoung: ['9'] })
    expect(result[0].both).toBe(true)
  })

  it('같은 곡이 여러 번 와도 한 장만 붙는다', () => {
    const result = appendNew([], [group({ match_key: 'A' }), group({ match_key: 'A' })])
    expect(result).toHaveLength(1)
  })
})

describe('filterByBrand', () => {
  const groups = [
    group({ match_key: '둘다', brands: { tj: ['1'], kumyoung: ['2'] }, both: true }),
    group({ match_key: 'TJ만', brands: { tj: ['3'] } }),
  ]

  it("'전체'는 그대로 돌려준다", () => {
    expect(filterByBrand(groups, 'all')).toBe(groups)
  })

  it('고른 브랜드에 번호가 없는 곡은 뺀다', () => {
    const filtered = filterByBrand(groups, 'kumyoung')

    expect(filtered).toHaveLength(1)
    expect(filtered[0].match_key).toBe('둘다')
  })

  it('한 브랜드만 볼 때는 both를 끈다', () => {
    expect(filterByBrand(groups, 'kumyoung')[0].both).toBe(false)
  })

  it('원본을 건드리지 않는다', () => {
    filterByBrand(groups, 'tj')
    expect(groups[0].both).toBe(true)
    expect(groups[0].brands.kumyoung).toEqual(['2'])
  })
})

describe('countMatched', () => {
  it('양쪽에 다 있는 곡만 센다', () => {
    expect(
      countMatched([
        group({ match_key: 'A', both: true }),
        group({ match_key: 'B' }),
        group({ match_key: 'C', both: true }),
      ]),
    ).toBe(2)
  })
})
