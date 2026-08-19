/**
 * 약관·개인정보 처리방침 주소.
 *
 * 문서는 저장소의 `docs/`에 있고 GitHub Pages로 서비스한다.
 * 앱과 다른 도메인이라 새 탭으로 연다.
 *
 * 한 곳에 모아 두는 이유 — 가입 화면과 설정 화면 두 군데서 쓰는데,
 * 각자 문자열을 들고 있으면 주소가 바뀔 때 한쪽만 고치게 된다.
 */

// TODO: GitHub Pages를 켠 뒤 실제 주소로 바꾼다.
//       Settings > Pages > Source: main 브랜치 /docs
//       예) https://jihyun808.github.io/karaokedayo
const BASE = import.meta.env.VITE_LEGAL_BASE_URL ?? 'https://example.github.io/karaokedayo'

export const TERMS_URL = `${BASE}/terms.html`
export const PRIVACY_URL = `${BASE}/privacy.html`
