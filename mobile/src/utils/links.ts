/** 앱 밖으로 내보내는 링크 주소를 만든다. */

/**
 * 브라우저 검색 주소.
 *
 * 우리가 못 찾는 것을 붙잡고 있지 말고 찾아갈 곳을 알려 준다
 * (가사보기의 '인터넷에서 찾아보기'와 같은 원리).
 * 검색어를 따옴표로 묶어야 낱말이 흩어져 엉뚱한 결과가 나오지 않는다.
 */
export function webSearchUrl(query: string) {
  const q = `"${query.trim()}" 노래방 번호`
  return `https://www.google.com/search?q=${encodeURIComponent(q)}`
}
