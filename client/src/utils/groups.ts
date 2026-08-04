import type { Brand, SongGroup } from '../types/karaoke'

/**
 * 페이지를 이어 붙일 때 같은 곡을 하나로 합친다.
 *
 * 서버는 페이지 단위로만 그룹을 묶는다. 그런데 정렬 기준이 발매일이라
 * 같은 곡의 TJ 등록분과 금영 등록분이 서로 다른 페이지에 떨어질 수 있다.
 * (예: TJ 2026-07 등록, 금영 2026-01 등록)
 * 그대로 두면 한 곡이 카드 두 장으로 보이므로 match_key로 다시 합친다.
 */
export function mergeGroups(prev: SongGroup[], next: SongGroup[]): SongGroup[] {
  const merged = new Map<string, SongGroup>()

  for (const group of [...prev, ...next]) {
    const found = merged.get(group.match_key)

    if (!found) {
      // 원본을 건드리지 않도록 복사해서 넣는다
      merged.set(group.match_key, {
        ...group,
        brands: { ...group.brands },
      })
      continue
    }

    for (const [brand, numbers] of Object.entries(group.brands)) {
      const current = found.brands[brand as Brand] ?? []
      found.brands[brand as Brand] = [
        ...current,
        ...(numbers ?? []).filter((no) => !current.includes(no)),
      ]
    }
    found.both = Object.keys(found.brands).length > 1
  }

  return [...merged.values()]
}

export function countMatched(groups: SongGroup[]): number {
  return groups.filter((group) => group.both).length
}
