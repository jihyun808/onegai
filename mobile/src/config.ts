/**
 * 앱이 바라보는 주소.
 *
 * 웹은 같은 오리진의 `/api`를 Vite 프록시로 넘겼지만, 앱은 오리진이 없어서
 * 서버 주소를 통째로 알아야 한다. 빌드할 때 EXPO_PUBLIC_API_URL로 넣는다
 * (eas.json의 profile별 env). 비어 있으면 개발용 로컬 서버를 본다 —
 * iOS 시뮬레이터에서는 localhost가 맥을 가리킨다.
 */
export const API_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:5001"
).replace(/\/$/, "");

// 약관·개인정보 처리방침. 웹과 같은 문서(docs/)를 GitHub Pages로 연다.
// TODO: GitHub Pages를 켠 뒤 실제 주소로 바꾼다 (심사 제출 전 필수).
const LEGAL_BASE =
  process.env.EXPO_PUBLIC_LEGAL_BASE_URL ??
  "https://example.github.io/karaokedayo";

export const TERMS_URL = `${LEGAL_BASE}/terms.html`;
export const PRIVACY_URL = `${LEGAL_BASE}/privacy.html`;

export const CONTACT = "contact.eeez@gmail.com";
