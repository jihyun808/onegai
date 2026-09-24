/**
 * 많이 찾는 가수. 검색 전 화면에 뱃지로 띄운다.
 *
 * **보이는 것은 한글, 넣는 것은 원어다.** 노래방 검색은 원어가 가장 잘
 * 걸리는데(11번), 한국 이용자는 한글로 기억한다. 그 간극을 뱃지가 메운다.
 *
 * 인기곡 50에 곡이 많이 오른 가수 위주로 골랐다.
 * 눌렀을 때 우리 검색이 실제로 답하는지 확인하고 넣었다 (2026-08-19):
 * 初音ミク 98곡 · 米津玄師 45곡 · あいみょん 43곡 · ヨルシカ 38곡 ·
 * Official髭男dism 35곡 · YOASOBI 32곡 · Ado 41곡 · King Gnu 24곡.
 */
export interface HotSearch {
  /** 화면에 보이는 한글 */
  label: string
  /** 검색창에 들어갈 원어 */
  query: string
}

export const HOT_SEARCHES: HotSearch[] = [
  { label: '하츠네미쿠', query: '初音ミク' },
  { label: '요네즈 켄시', query: '米津玄師' },
  { label: '요아소비', query: 'YOASOBI' },
  { label: '요루시카', query: 'ヨルシカ' },
  { label: '아이묭', query: 'あいみょん' },
  { label: '아도', query: 'Ado' },
  { label: '킹누', query: 'King Gnu' },
  { label: '히게단', query: 'Official髭男dism' },
]
