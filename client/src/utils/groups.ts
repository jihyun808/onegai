import type { Brand, BrandFilter, SongGroup } from '../types/karaoke'

export function mergeGroups(prev: SongGroup[], next: SongGroup[]): SongGroup[] {
  const merged = new Map<string, SongGroup>()

  for (const group of [...prev, ...next]) {
    const found = merged.get(group.match_key)

    if (!found) {
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
