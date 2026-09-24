# 기술 아키텍처

오네가이(onegai) — 일본 노래방 번호 검색 모바일 웹앱.

---

## 1. 전체 구성

```
 ┌──────────────┐        ┌──────────────────────────────────────┐
 │   브라우저    │        │            Docker Compose            │
 │  (모바일 웹)  │        │                                      │
 └──────┬───────┘        │  ┌────────────┐    ┌──────────────┐  │
        │ :5173          │  │   client   │    │    server    │  │
        └────────────────┼─▶│   Vite     │───▶│    Flask     │  │
                         │  │  React TS  │/api│   :5001      │  │
                         │  └────────────┘    └──┬────┬──────┘  │
                         │                       │    │         │
                         │            ┌──────────┘    └───────┐ │
                         │            ▼                       ▼ │
                         │      ┌──────────┐          ┌──────────┐
                         │      │  redis   │          │  mysql   │
                         │      │  :6379   │          │  :3306   │
                         │      │  캐시     │          │ 카탈로그  │
                         │      └──────────┘          └──────────┘
                         └──────────────────────────────────────┘
                                        │
                                        ▼ HTTPS
                              ┌────────────────────┐
                              │  api.manana.kr     │
                              │  (외부 비공식 API) │
                              └────────────────────┘
```

`client`가 `/api/*`를 `server`로 프록시하므로 브라우저 입장에서는 단일 오리진이다.
개발 중 CORS를 신경 쓸 일이 없다.

---

## 2. 스택

| 영역        | 기술                                        | 버전                              |
| ----------- | ------------------------------------------- | --------------------------------- |
| 프론트      | React + TypeScript, Vite                    | React 19 / Vite 8                 |
| 백엔드      | Python Flask                                | 3.13 / Flask 3.1                  |
| 캐시        | Redis                                       | 8 (alpine)                        |
| DB          | MySQL                                       | 8.0 — 곡 카탈로그 8.6만 건 (43MB) |
| 데이터 원천 | api.manana.kr (비공식) + kysing.kr 스크래핑 | v1                                |
| 실행        | Docker Compose                              | —                                 |

상태 관리 라이브러리, 라우터, CSS 프레임워크는 쓰지 않는다.
화면이 셋뿐이고 탭 전환만 있어 React 기본 기능과 순수 CSS로 충분하다.

---

## 3. 디렉터리

```
karaokedayo/
├── docker-compose.yml       개발 스택 정의
├── client/
│   ├── Dockerfile
│   ├── vite.config.ts       /api 프록시 (VITE_PROXY_TARGET으로 대상 전환)
│   └── src/
│       ├── components/      Logo, BottomNav, SongCard, SearchInput, Segmented, …
│       ├── pages/           HomePage(검색), MyPage(즐겨찾기), SettingsPage
│       ├── hooks/           useDebounce, useSearch, useInfiniteScroll, useBookmarks
│       ├── types/           karaoke.ts — 서버 응답 타입
│       ├── utils/           api.ts (fetch 래퍼), groups.ts (페이지 간 곡 병합)
│       └── styles/          global.css — 색·치수 CSS 변수
└── server/
    ├── Dockerfile
    ├── config.py            환경변수 기반 설정
    ├── run.py               진입점
    ├── db/schema.sql        MySQL 초기 스키마 (컨테이너 최초 기동 시 실행)
    ├── tests/               pytest 109개 (네트워크 미사용)
    └── app/
        ├── routes/          health.py, search.py, extras.py
        ├── services/        manana.py, kysing.py(금영공식), tjmedia.py(TJ공식),
        │                    search_service.py, health_service.py,
        │                    translate.py(DeepL), preview.py(iTunes), lyrics.py(금영)
        ├── models/          song.py — 카탈로그 조회/적재
        └── utils/           cache.py (Redis), normalize.py (정규화)
```

---

## 4. 요청 흐름

`GET /api/search?q=ヨルシカ&type=singer&brand=all`

```
1. 라우트          파라미터 검증 (400)
2. 캐시 조회       kada:search:v2:singer:all:ヨルシカ
   └ HIT  → 6번으로 (cached: true)
3. 자체 DB 조회    songs 테이블 (0.03초)
   ├ 3건 이상 → 그대로 사용
   └ 부족    → TJ·금영 공식 보강 → 실패/0건이면 manana 폴백
4. 정규화          공백/전각/괄호/대소문자/카나 → match_key 생성
5. 캐시 저장       TTL 24시간 (결과 없으면 10분)
6. 페이지 절단     limit/offset 적용
7. 그룹핑          match_key로 TJ·금영 같은 곡 병합
8. 응답
```

**전체 결과를 캐시에 담고 응답에서만 자른다.** 페이지를 넘겨도 manana를 다시 부르지 않는다.

---

## 5. 핵심 설계 결정

### 5.1 브랜드는 항상 개별 호출

manana에서 브랜드를 생략하면 전 기기 합집합이 아니라 **잘린 다른 데이터셋**이 온다.

| 검색             | 무브랜드 응답의 tj | tj 직접 호출 |
| ---------------- | ------------------ | ------------ |
| `singer=Ado`     | 10건               | 70건         |
| `singer=YOASOBI` | 0건                | 32건         |

그래서 `brand=all`도 `tj`, `kumyoung`을 각각 호출해 합친다.

### 5.2 정규화는 두 종류

| 용도    | 함수                | 규칙                                                               |
| ------- | ------------------- | ------------------------------------------------------------------ |
| 곡 매칭 | `make_match_key()`  | 공백/기호 제거, 전각→반각, 괄호 안 제거, 소문자, 카타카나→히라가나 |
| 캐시 키 | `normalize_query()` | 대소문자·전각·연속공백만 흡수                                      |

**캐시 키에 공백 제거를 적용하면 안 된다.** manana는 `ONE PIECE`(0건)와
`ONEPIECE`(다수)를 다르게 취급하므로, 같은 키가 되면 서로의 결과가 섞인다.

### 5.3 캐시 TTL

| 대상      | TTL    | 이유                                          |
| --------- | ------ | --------------------------------------------- |
| 검색 결과 | 24시간 | manana가 하루 1회 갱신                        |
| 결과 없음 | 10분   | 업스트림 일시 장애나 오타가 하루 굳는 것 방지 |

`CACHE_VERSION`(현재 `v2`)이 키에 들어간다. **정규화 규칙을 바꾸면 올려야 한다** —
캐시에 저장된 `match_key`가 옛 규칙으로 만들어진 값이기 때문이다.

### 5.4 두 브랜드 모두 공식 사이트를 먼저 본다

| 브랜드 | 공식을 쓰는 이유                                                         |
| ------ | ------------------------------------------------------------------------ |
| 금영   | manana가 2026-04 이후 멈춰 최신곡이 빠짐 (가수당 9~62곡)                 |
| TJ     | manana에 **한글 발음 검색이 없음** (`요루시카` → 공식 33건 / manana 0건) |

TJ 공식에는 발매일이 없어 manana로 채운다. 안 채우면 정렬 기준이 비어
TJ 결과가 통째로 목록 아래로 밀린다.

스크래핑은 깨지기 마련이므로 세 겹으로 막는다.

| 방어       | 동작                                                 |
| ---------- | ---------------------------------------------------- |
| 폴백 체인  | 예외·크래시·조용한 0건 모두 manana로 되돌아감        |
| 헬스체크   | `/api/health?deep=1` — 표본 검색으로 파서 생사 확인  |
| stale 캐시 | 전부 실패 시 7일짜리 사본 사용, 응답에 `stale: true` |

스크래핑이 앱이 아니라 서버에서 일어나므로, 깨져도 앱 스토어 심사 없이 고칠 수 있다.

### 5.5 부가 기능은 절대 검색을 막지 않는다

번역·미리듣기·가사는 검색을 거들 뿐이다. 키가 없거나 외부가 죽어도
**200 + `available: false`**를 돌려주고, 예외를 위로 던지지 않는다.
키가 없으면 외부를 호출조차 하지 않는다.

| 기능     | 소스                                                            | 키              |
| -------- | --------------------------------------------------------------- | --------------- |
| 번역     | DeepL                                                           | `DEEPL_API_KEY` |
| 미리듣기 | **iTunes Search** (Apple Music API 아님 — 그쪽은 유료 JWT 필요) | 불필요          |
| 가사     | **금영 공식** (검색 결과 HTML에 전문 + 한글 발음이 딸려 온다)   | 불필요          |

`/api/health`의 `features`로 클라이언트가 UI를 미리 감출 수 있다.

### 5.6 Redis는 선택 사항

연결에 실패해도 캐시만 건너뛰고 검색은 동작한다. 30초 쿨다운 후 자동 재연결하며,
실제 상태는 `/api/health`가 매번 ping해서 보고한다.

### 5.7 페이지네이션

넓은 검색어는 결과가 2만 건을 넘는다(`q=a` → 24,162건 / 13.7MB).
기본 50건, 최대 200건으로 자른다. `total`은 전체, `returned`는 현재 페이지.

⚠️ `counts` / `matched` / `groups`는 **현재 페이지 기준**이다.

---

## 6. 프론트엔드

- **검색 입력**: 300ms 디바운스. 검색 타입·브랜드 변경은 디바운스 없이 즉시 반영.
- **경쟁 상태 방지**: `AbortController`로 이전 요청을 취소해, 늦게 도착한 응답이
  최신 결과를 덮어쓰지 못하게 한다.
- **결과 렌더링**: `results`(브랜드별 원본)가 아니라 `groups`(곡 단위)를 그린다.
  한 카드에 TJ·금영 번호가 나란히 놓인다.
- **무한스크롤**: `IntersectionObserver`로 목록 끝을 감시한다. 바닥 400px 전에
  미리 부른다. 서버는 페이지 단위로만 그룹을 묶으므로, 같은 곡의 TJ 등록분과
  금영 등록분이 다른 페이지에 떨어질 수 있다. `mergeGroups()`가 `match_key`로
  다시 합쳐 한 곡이 카드 두 장으로 보이는 것을 막는다.
- **스타일**: 색·반경·폰트는 전부 `:root` CSS 변수. 디자이너가 값만 바꾸면 된다.
  손그림 테두리는 SVG 왜곡 필터(`#wobble`)를 테두리 전용 `::before`에만 적용한다.
  요소 전체에 걸면 글자까지 일그러진다.

---

## 7. 실행

### 도커 (권장)

```bash
docker compose up -d              # mysql + redis + server
docker compose --profile client up -d   # 프론트까지 컨테이너로
docker compose logs -f server
docker compose down               # 중지 (-v를 붙이면 DB 볼륨까지 삭제)
```

프론트는 기본으로 뜨지 않는다. Vite는 호스트에서 `npm run dev`로 돌리는 쪽이
HMR이 빠르고, 서버 포트(5001)가 열려 있어 프록시가 그대로 붙는다.

| 서비스 | 포트 |
| ------ | ---- |
| client | 5173 |
| server | 5001 |
| mysql  | 3306 |
| redis  | 6379 |

> macOS는 5000번을 AirPlay가 점유하므로 서버는 5001을 쓴다.

### 도커 없이

```bash
# 서버
cd server && python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt && python run.py

# 프론트
cd client && npm install && npm run dev
```

Redis는 `brew install redis && brew services start redis`.
없어도 캐시만 건너뛰고 동작한다.

### 테스트

```bash
docker compose exec server python -m pytest     # 또는 호스트에서 pytest
```

109개. 네트워크를 타지 않는다 (외부 API·DB·Redis 모두 대체).

---

## 8. 아직 없는 것

| 항목                           | 상태                                           |
| ------------------------------ | ---------------------------------------------- |
| `/api/auth/register`, `/login` | 미착수                                         |
| `/api/favorites`               | 미착수                                         |
| **MySQL 연동 코드**            | 미착수 — 스키마(`server/db/schema.sql`)만 존재 |
| 무한스크롤                     | 완료                                           |

MySQL 컨테이너는 뜨고 테이블 3개(`users`, `favorites`, `search_history`)도
생성되지만, **애플리케이션은 아직 접속하지 않는다.**
`config.py`의 `MYSQL_*` 설정을 읽는 코드가 없고 `app/models/`는 비어 있다.

---

## 9. 외부 의존성 리스크

**금영 데이터가 2026-04부터 수집되지 않는다.** manana 측 문제이며 v1·v2 동일하다.
구곡은 검색되지만 최근 2~3년 신곡은 금영 번호가 나오지 않는다.
자세한 근거와 문의 경로는 [DECISIONS.md](DECISIONS.md) 참고.

manana는 개인이 무료 운영하는 비공식 API다. SLA가 없고 언제든 중단될 수 있다.
서비스 핵심 데이터가 여기 묶여 있다는 점이 이 프로젝트의 가장 큰 구조적 위험이다.
