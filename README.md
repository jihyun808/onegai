# karaokedayo (가라오케다요, Ka-da)

일본 노래방 번호 검색 전용 모바일 웹앱.

## 기술 스택

| 영역 | 스택 |
| --- | --- |
| Client | React + TypeScript (Vite), 추후 Expo 래핑 |
| Server | Python Flask |
| DB | MySQL |
| Cache | Redis |

## 폴더 구조

```
karaokedayo/
├── client/          # React + TypeScript
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── utils/
│   │   ├── types/
│   │   └── styles/
│   └── package.json
├── server/          # Python Flask
│   ├── app/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── utils/
│   ├── config.py
│   └── requirements.txt
└── README.md
```

전체 구조와 설계 배경은 [ARCHITECTURE.md](ARCHITECTURE.md), 미결정 사항은 [DECISIONS.md](DECISIONS.md) 참고.

## 실행 방법

### 도커 (권장)

```bash
docker compose up -d                     # mysql + redis + server
docker compose --profile client up -d    # 프론트까지 컨테이너로
docker compose down                      # 중지 (-v 를 붙이면 DB 볼륨까지 삭제)
```

프론트는 기본으로 뜨지 않는다. Vite는 호스트에서 `npm run dev`로 돌리는 쪽이
HMR이 빠르고, 서버 포트(5001)가 열려 있어 프록시가 그대로 붙는다.

아래는 도커 없이 직접 실행하는 방법이다.

### Client

```bash
cd client
npm install
npm run dev        # http://localhost:5173
```

### Server

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py      # http://localhost:5001
```

> macOS에서는 5000번 포트를 AirPlay가 점유하므로 5001번을 사용한다.

### Redis

```bash
brew install redis
brew services start redis
redis-cli ping   # PONG
```

Redis 없이도 서버는 정상 동작한다 (캐시를 건너뛰고 매번 manana API를 호출).
연결이 끊기면 30초 뒤 자동으로 재연결을 시도한다.
현재 상태는 `GET /api/health`의 `redis` 필드로 확인한다.

> Homebrew redis 8.10은 설치되지 않은 모듈을 로드하려다 기동에 실패한다.
> `/opt/homebrew/etc/redis.conf`의 `loadmodule ./modules/...` 4줄을 주석 처리하면 된다.
> (원본 백업: `redis.conf.bak-kada`)

## API

### `GET /api/search`

| 파라미터 | 값 | 기본값 |
| --- | --- | --- |
| `q` | 검색어 (필수) | - |
| `type` | `song` \| `singer` \| `lyrics` | `song` |
| `brand` | `tj` \| `kumyoung` \| `all` | `all` |
| `limit` | 1 ~ 200 | `50` |
| `offset` | 0 이상 | `0` |

검색어는 최대 100자.

넓은 검색어는 결과가 2만 건을 넘으므로(`q=a` → 24,162건) 페이지 단위로 잘라 보낸다.
`total`은 전체 건수, `returned`는 이번 페이지 건수다.
`counts` / `matched` / `groups`는 **현재 페이지 기준**이다.
클라이언트는 무한스크롤로 페이지를 이어 붙이며, 같은 곡이 페이지에 걸쳐 나뉘어 오면
`match_key`로 다시 합친다 (`client/src/utils/groups.ts`).
전체 결과는 서버 캐시에 있으므로 페이지를 넘겨도 manana를 다시 부르지 않는다.

```bash
curl "http://localhost:5001/api/search?q=Ado&type=singer&brand=tj"
```

```json
{
  "query": "Ado",
  "type": "singer",
  "brand": "tj",
  "cached": false,
  "total": 70,
  "returned": 50,
  "limit": 50,
  "offset": 0,
  "has_more": true,
  "counts": { "tj": 50 },
  "results": {
    "tj": [
      {
        "brand": "tj",
        "no": "52554",
        "title": "ビバリウム",
        "singer": "Ado",
        "composer": "Ado",
        "lyricist": "Ado",
        "release": "2026-07-09",
        "match_key": "ビバリウム::ado"
      }
    ]
  }
}
```

- `results`는 브랜드별로 그룹핑되며, 요청한 브랜드는 결과가 없어도 빈 배열로 내려간다.
- `groups`는 **같은 곡을 브랜드 넘어 묶은 목록**이다. TJ와 금영 번호를 한 번에 보여줄 때 쓴다. `both: true`면 양쪽 기기에 모두 있는 곡이고, `matched`는 그 개수다.

```json
{
  "title": "花に亡霊(映画'泣きたい私は猫をかぶる' OST)",
  "singer": "ヨルシカ",
  "match_key": "花に亡霊::よるしか",
  "brands": { "tj": ["68230"], "kumyoung": ["44693"] },
  "both": true
}
```

### 정규화

`app/utils/normalize.py`. TJ와 금영이 같은 곡을 다르게 등록하는 문제를 흡수한다.

| 규칙 | 예시 |
| --- | --- |
| 1. 공백 제거 | `세월이 가면` = `세월이가면` |
| 2. 전각/반각 통일 (NFKC) | `Ｔｏｔ　Ｍｕｓｉｃａ` = `Tot Musica`, `ﾚﾃﾞｨﾒｲﾄﾞ` = `レディメイド` |
| 3. 괄호 안 부가정보 제거 | `花に亡霊 ("泣きたい私は猫をかぶる"OST)` = `花に亡霊` |
| 4. 대소문자 무시 | `Take A Bow` = `Take a bow` |
| 5. 카타카나 → 히라가나 | `レディメイド` = `れでぃめいど` |

- 가수명은 `A,B` / `B,A` 같은 순서 차이도 흡수한다 (분리 후 정렬).
- 장음 부호 `ー`는 남긴다. `メイド`와 `メード`는 실제로 다른 표기다.
- 결과의 `match_key`가 이 규칙을 거친 비교용 키다. 원본 필드는 손대지 않는다.
- 정규화 규칙을 바꾸면 `app/utils/cache.py`의 `CACHE_VERSION`을 올려 기존 캐시를 무효화해야 한다.
- 검색 결과는 Redis에 24시간 캐싱된다 (manana API 갱신 주기 기준). 결과가 없는 검색은 10분만 캐싱한다. `cached` 필드로 캐시 히트 여부를 알 수 있다.
- manana API는 `joysound` / `dam`(일본 기기)도 지원하지만, 한국 노래방에서 일본곡을 찾는 것이 기획 의도이므로 노출하지 않는다. [DECISIONS.md](DECISIONS.md) 참고.

에러 응답: `400 invalid_request` (잘못된 파라미터), `502 upstream_error` (manana API 실패)

### `GET /api/health`

서버 및 Redis 연결 상태. `?deep=1`을 붙이면 외부 소스까지 실제로 조회해 확인한다.

```json
{
  "status": "ok",
  "redis": true,
  "sources": {
    "kysing": { "ok": true, "detail": "20 rows" },
    "manana": { "ok": true, "detail": "31 rows" }
  }
}
```

`status`는 `ok` / `partial`(금영 공식만 깨짐 — manana 폴백으로 서비스는 정상) /
`degraded`(manana까지 실패)다. 점검 결과는 5분 캐싱된다.

### 부가 기능

셋 다 **키가 없거나 외부 API가 죽어도 200을 준다.** 에러 대신
`available: false`와 사람이 읽을 `reason`을 돌려주므로,
클라이언트는 해당 영역만 감추면 된다. 검색은 영향받지 않는다.

`GET /api/health`의 `features`로 어떤 기능이 켜져 있는지 미리 알 수 있다.

| 엔드포인트 | 소스 | 키 | 캐시 |
| --- | --- | --- | --- |
| `GET /api/translate?text=&target=KO` | DeepL | `DEEPL_API_KEY` | 30일 |
| `GET /api/preview?title=&singer=` | iTunes Search | **불필요** | 7일 |
| `GET /api/lyrics?title=&singer=` | Musixmatch | `MUSIXMATCH_API_KEY` | 30일 |

```json
{ "available": true, "preview_url": "https://…m4a",
  "artwork_url": "https://…300x300bb.jpg", "track_url": "https://music.apple.com/…" }

{ "available": false, "reason": "번역 기능이 설정되지 않았어요." }
```

- **미리듣기는 공식 Apple Music API가 아니라 iTunes Search API를 쓴다.**
  Apple Music API는 유료 개발자 계정으로 발급한 JWT가 필요하고 키 없이는 401이다.
  iTunes Search는 키 없이 같은 30초 프리뷰 URL과 앨범아트를 준다.
- iTunes는 검색이 느슨해 엉뚱한 곡이 섞이므로, 우리 정규화 규칙(`match_key`와
  같은 방식)으로 제목·가수를 대조해 거른다.
- Musixmatch 무료 플랜은 **가사 앞부분 30% 발췌**만 준다 (`partial: true`).
  그리고 오류일 때도 HTTP 200을 주므로 본문의 `status_code`를 봐야 한다.
- DeepL 무료 키는 `:fx`로 끝난다. 키를 보고 엔드포인트를 자동으로 고른다.

### 데이터 소스

검색은 **자체 카탈로그 DB를 먼저 본다** (8.6만 곡, 0.03초).
결과가 적으면(3건 미만) 공식 사이트로 보강한다 — 한글 발음(`요루시카`)이나
로마자(`kakeru`)는 공식 검색 인덱스에만 있어 크롤링으로 못 가져오기 때문이다.

```bash
docker compose exec server flask --app run crawl-backfill   # 최초 1회 (~10분)
docker compose exec server flask --app run crawl-daily      # 매일
docker compose exec server flask --app run crawl-status     # 현황
```

| 브랜드 | 폴백 소스 |
| --- | --- |
| TJ | **tjmedia.com 공식 → 실패 시 manana 폴백** |
| 금영 | **kysing.kr 공식 → 실패 시 manana 폴백** |

둘 다 공식을 먼저 보는 이유가 다르다.

- **금영**: manana 데이터가 2026-04 이후 멈춰 최신곡이 통째로 빠진다 (가수당 9~62곡 차이)
- **TJ**: manana에는 **한글 발음 검색이 없다** (`요루시카` → 공식 33건 / manana 0건)

`KYSING_ENABLED=false`, `TJMEDIA_ENABLED=false`로 각각 끌 수 있다 (끄면 manana만 쓴다).

TJ 공식에는 발매일이 없어서 manana로 채워 넣는다. 안 채우면 정렬에서 밀린다.

**`type=lyrics`는 가사로 검색한다.** 가사 인덱스는 금영에만 있어서,
금영에서 곡을 찾고 그 제목으로 TJ 번호를 역조회해 붙인다. 20초 안팎 걸린다.

스크래핑은 사이트 구조가 바뀌면 깨지므로 세 겹으로 막아 뒀다 —
폴백 체인, `?deep=1` 헬스체크, 7일짜리 비상용 캐시(응답에 `stale: true`).
자세한 내용은 [DECISIONS.md](DECISIONS.md) 5번.

## 테스트

```bash
cd server
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest
```

네트워크를 타지 않는다 (외부 API·DB·Redis 모두 대체). 109개.
