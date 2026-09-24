export function webSearchUrl(query: string) {
  const q = `"${query.trim()}" 노래방 번호`
  return `https://www.google.com/search?q=${encodeURIComponent(q)}`
}
