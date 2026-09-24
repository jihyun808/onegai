/**
 * 웹(client/src/styles/global.css)의 변수를 그대로 옮겼다.
 * 아이보리 배경 + 손그림 느낌.
 */
export const colors = {
  ivory: '#f7f3e8',
  ivoryDeep: '#efe8d6',
  paper: '#fffdf6',

  ink: '#2f2a24',
  inkSoft: '#7d7264',
  inkFaint: '#aca08c',

  line: '#2f2a24',
  lineThin: '#cdc3ad',

  tj: '#2f6fd0',
  kumyoung: '#d2453f',
  accent: '#e0863a',
}

/** App.tsx에서 불러오는 글꼴 이름. 본문은 Noto Sans KR, 제목·숫자는 손글씨. */
export const fonts = {
  body: 'NotoSansKR_400Regular',
  bodyBold: 'NotoSansKR_700Bold',
  hand: 'Gaegu_400Regular',
  handBold: 'Gaegu_700Bold',
  logo: 'Jalnan',
}

/**
 * 손그림 테두리. 웹은 SVG 왜곡 필터로 선을 구불거리게 했지만 네이티브엔 없다.
 * 모서리마다 반경을 다르게 줘서 "대충 그린" 느낌만 살린다.
 * 카드마다 조금씩 다르게 — 같은 도형이 반복되면 손그림 느낌이 죽는다.
 */
const SKETCH_CORNERS = [
  [22, 10, 20, 12],
  [10, 22, 12, 20],
  [18, 12, 22, 10],
] as const

export function sketch(index = 0) {
  const [tl, tr, br, bl] = SKETCH_CORNERS[index % SKETCH_CORNERS.length]
  return {
    backgroundColor: colors.paper,
    borderWidth: 2,
    borderColor: colors.line,
    borderTopLeftRadius: tl,
    borderTopRightRadius: tr,
    borderBottomRightRadius: br,
    borderBottomLeftRadius: bl,
  }
}
