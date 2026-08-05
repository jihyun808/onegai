import type { Brand, BrandFilter, SongGroup } from '../types/karaoke'

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

/**
 * 뒤늦게 도착한 결과를 기존 목록 뒤에 붙인다.
 *
 * 서버는 발매순으로 정렬해 주지만, 그 순서대로 끼워 넣으면 이미 보고 있던
 * 카드가 아래로 밀려 **누르려던 것과 다른 것을 누르게 된다.**
 * 그래서 이미 있는 곡은 번호만 보태고, 처음 보는 곡은 끝에 덧붙인다.
 * 순서가 완벽하진 않아도 화면이 튀지 않는 편이 낫다.
 */
export function appendNew(current: SongGroup[], incoming: SongGroup[]): SongGroup[] {
  const byKey = new Map(current.map((group) => [group.match_key, group]))
  const appended: SongGroup[] = []

  for (const group of incoming) {
    const found = byKey.get(group.match_key)

    if (!found) {
      const copy = { ...group, brands: { ...group.brands } }
      byKey.set(group.match_key, copy)
      appended.push(copy)
      continue
    }

    // 이미 있는 곡이면 빠진 번호만 채운다 (카드 위치는 그대로)
    for (const [brand, numbers] of Object.entries(group.brands)) {
      const existing = found.brands[brand as Brand] ?? []
      found.brands[brand as Brand] = [
        ...existing,
        ...(numbers ?? []).filter((no) => !existing.includes(no)),
      ]
    }
    found.both = Object.keys(found.brands).length > 1
  }

  return [...current, ...appended]
}

/**
 * 브랜드 탭을 눌렀을 때 이미 받아둔 결과에서 걸러낸다.
 *
 * 서버를 다시 부르면 4초를 또 기다린다. '전체'로 받아온 결과에는
 * 두 브랜드가 다 들어 있으므로 화면에서 거르기만 하면 즉시 바뀐다.
 */
export function filterByBrand(groups: SongGroup[], brand: BrandFilter): SongGroup[] {
  if (brand === 'all') return groups

  const filtered: SongGroup[] = []
  for (const group of groups) {
    const numbers = group.brands[brand]
    if (!numbers?.length) continue
    filtered.push({ ...group, brands: { [brand]: numbers }, both: false })
  }
  return filtered
}
