# karaokedayo (오네가이, onegai)

일본 노래방 번호 검색 전용 모바일 웹앱.

## 기술 스택

| 영역   | 스택                                      |
| ------ | ----------------------------------------- |
| Client | React + TypeScript (Vite), 추후 Expo 래핑 |
| Server | Python Flask                              |
| DB     | MySQL                                     |
| Cache  | Redis                                     |

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

### Mobile (iOS 앱)

```bash
cd mobile
npm install
npx expo start --go --ios   # 시뮬레이터의 Expo Go로 실행 (서버는 localhost:5001)
```

`client/`(웹)와 같은 서버 API를 쓴다. 서버 주소는 `EXPO_PUBLIC_API_URL`로 넣는다
(`eas.json`의 profile별 env).

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

| 파라미터 | 값                             | 기본값    |
| -------- | ------------------------------ | --------- |
| `q`      | 검색어 (필수)                  | -         |
| `type`   | `song` \| `singer` \| `lyrics` | `song`    |
| `brand`  | `tj` \| `kumyoung` \| `all`    | `all`     |
| `limit`  | 1 ~ 200                        | `50`      |
| `offset` | 0 이상                         | `0`       |
| `sort`   | `release` \| `no`              | `release` |
| `korean` | `1`이면 한국어 곡도 표시       | 감춤      |

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

| 규칙                     | 예시                                                               |
| ------------------------ | ------------------------------------------------------------------ |
| 1. 공백 제거             | `세월이 가면` = `세월이가면`                                       |
| 2. 전각/반각 통일 (NFKC) | `Ｔｏｔ　Ｍｕｓｉｃａ` = `Tot Musica`, `ﾚﾃﾞｨﾒｲﾄﾞ` = `レディメイド` |
| 3. 괄호 안 부가정보 제거 | `花に亡霊 ("泣きたい私は猫をかぶる"OST)` = `花に亡霊`              |
| 4. 대소문자 무시         | `Take A Bow` = `Take a bow`                                        |
| 5. 카타카나 → 히라가나   | `レディメイド` = `れでぃめいど`                                    |

- 가수명은 `A,B` / `B,A` 같은 순서 차이도 흡수한다 (분리 후 정렬).
- 장음 부호 `ー`는 남긴다. `メイド`와 `メード`는 실제로 다른 표기다.
- 결과의 `match_key`가 이 규칙을 거친 비교용 키다. 원본 필드는 손대지 않는다.
- 정규화 규칙을 바꾸면 `app/utils/cache.py`의 `CACHE_VERSION`을 올려 기존 캐시를 무효화해야 한다.
- 검색 결과는 Redis에 24시간 캐싱된다 (manana API 갱신 주기 기준). 결과가 없는 검색은 10분만 캐싱한다. `cached` 필드로 캐시 히트 여부를 알 수 있다.
- manana API는 `joysound` / `dam`(일본 기기)도 지원하지만, 한국 노래방에서 일본곡을 찾는 것이 기획 의도이므로 노출하지 않는다. [DECISIONS.md](DECISIONS.md) 참고.

에러 응답: `400 invalid_request` (잘못된 파라미터), `502 upstream_error` (manana API 실패)

### 인증

```
POST   /api/auth/register  {username, password}
POST   /api/auth/login     {username, password}
POST   /api/auth/logout
GET    /api/auth/me        로그인 안 했으면 null
PATCH  /api/auth/me        {username?, avatar?}
```

bcrypt 해싱, httpOnly 세션 쿠키, 계정당 로그인 5회 제한, IP 단위 요청 제한.
실패 응답에 `field`가 실려 와 어느 입력창 아래에 메시지를 붙일지 알 수 있다.
자세한 내용은 [DECISIONS.md](DECISIONS.md) 27번.

### 즐겨찾기

```
GET    /api/favorites             곡 단위로 묶어서 반환
POST   /api/favorites  {songs}
DELETE /api/favorites/<brand>/<no>
```

로그인 전에는 기기(localStorage)에, 로그인하면 서버에 저장한다.
로그인하는 순간 기기에 담아둔 것이 서버로 옮겨진다.

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

| 엔드포인트                           | 소스          | 키              | 캐시              |
| ------------------------------------ | ------------- | --------------- | ----------------- |
| `GET /api/translate?text=&target=KO` | DeepL         | `DEEPL_API_KEY` | 30일              |
| `GET /api/preview?title=&singer=`    | iTunes Search | **불필요**      | 7일               |
| `GET /api/lyrics?title=&singer=`     | 금영 공식     | **불필요**      | 30일 (없으면 1일) |

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
- **가사는 금영 검색 결과 HTML에 통째로 들어 있다.** 별도 요청도 키도 없고
  한글 발음까지 붙어 온다. `lines: [{ko, ja}, ...]` 형태로 내보낸다.
  ⚠️ **권리 확인은 진행 중이다** (DECISIONS.md 37번). `KYSING_ENABLED=false`로
  끄면 가사만 꺼지고 검색 링크는 그대로 나간다.
- 금영에 없는 곡(태진 전용이 41%)은 `available: false`와 함께 `search_url`을 준다.
  **`search_url`은 성공하든 실패하든 항상 채워지므로** 화면은 조건 없이 띄우면 된다.
- 조회에 5초쯤 걸린다(금영 페이지당 2초). 카드를 눌렀을 때만 부르고 30일 캐싱한다.
- DeepL 무료 키는 `:fx`로 끝난다. 키를 보고 엔드포인트를 자동으로 고른다.

### 발음 검색 별칭

`미쿠`처럼 발음으로 검색하면 자체 DB가 답하지 못한다 (DB에는 `初音ミク`로
저장돼 있고, 발음은 공식 검색 인덱스에만 있어 크롤링할 수 없다).
공식에 한 번 물어서 알아낸 연결을 `singer_alias`에 적어 두고 그다음부터는
DB로 답한다 — **16.6초 → 0.076초, 공식 호출 0회.** DECISIONS.md 39번.

```bash
# 스키마 적용 (한 번만)
docker compose exec -T mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" karaokedayo \
  < server/db/004_singer_alias.sql
```

### 데이터 소스

검색은 **자체 카탈로그 DB를 먼저 본다** (8.6만 곡, 0.03초).
결과가 적으면(3건 미만) 공식 사이트로 보강한다 — 한글 발음(`요루시카`)이나
로마자(`kakeru`)는 공식 검색 인덱스에만 있어 크롤링으로 못 가져오기 때문이다.

```bash
docker compose exec server flask --app run crawl-backfill   # 최초 1회 (~10분)
docker compose exec server flask --app run crawl-daily      # 매일
docker compose exec server flask --app run crawl-status     # 현황
```

| 브랜드 | 폴백 소스                                  |
| ------ | ------------------------------------------ |
| TJ     | **tjmedia.com 공식 → 실패 시 manana 폴백** |
| 금영   | **kysing.kr 공식 → 실패 시 manana 폴백**   |

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
# 서버 168개
cd server
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest

# 클라이언트 45개
cd client
npm test
```

**둘 다 네트워크를 타지 않는다** (외부 API·DB·Redis·오디오 모두 대체).
서버는 pytest, 클라이언트는 vitest + Testing Library를 쓴다.

## 배포

이미지의 기본 실행은 gunicorn이다.

```bash
gunicorn -c gunicorn.conf.py run:app
```

스레드 워커(gthread)를 쓴다 — 이 서버는 계산이 아니라 **남의 서버를 기다리는**
시간이 대부분이라, 기본 sync 워커면 느린 스크래핑 하나가 워커를 통째로 막는다.
조절용 환경변수: `WEB_WORKERS`, `WEB_THREADS`, `WEB_TIMEOUT`, `FORWARDED_ALLOW_IPS`.

개발은 `docker compose`가 `python run.py`(리로더)로 덮어쓰므로 그대로 쓰면 된다.
자세한 내용은 [DECISIONS.md](DECISIONS.md) 34번.

### Railway

서비스 4개를 한 프로젝트에 둔다.

| 서비스 | 만드는 법              | 설정                                                              |
| ------ | ---------------------- | ----------------------------------------------------------------- |
| MySQL  | New → Database → MySQL | 그대로                                                            |
| Redis  | New → Database → Redis | 그대로                                                            |
| server | New → GitHub Repo      | Root Directory `/server`, Config file `/server/railway.toml`      |
| crawl  | 같은 레포로 하나 더    | Root Directory `/server`, Config file `/server/railway.cron.toml` |

server와 crawl에 넣을 환경변수 (`${{...}}`는 Railway가 다른 서비스 값으로 채운다):

```
FLASK_ENV=production
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))" 결과>
MYSQL_HOST=${{MySQL.MYSQLHOST}}
MYSQL_PORT=${{MySQL.MYSQLPORT}}
MYSQL_USER=${{MySQL.MYSQLUSER}}
MYSQL_PASSWORD=${{MySQL.MYSQLPASSWORD}}
MYSQL_DATABASE=${{MySQL.MYSQLDATABASE}}
REDIS_HOST=${{Redis.REDISHOST}}
REDIS_PORT=${{Redis.REDISPORT}}
REDIS_PASSWORD=${{Redis.REDISPASSWORD}}
FORWARDED_ALLOW_IPS=*
CORS_ORIGINS=<프론트 도메인. 없으면 비워 둔다>
DEEPL_API_KEY=<선택>
```

- `FLASK_ENV=production`인데 `SECRET_KEY`가 기본값이면 서버가 뜨지 않는다 (일부러 막았다).
- 스키마는 배포마다 `flask --app run init-db`가 자동으로 맞춘다. 적용한 파일은
  `schema_migrations`에 적어 두므로 새 SQL 파일만 돌고, ALTER가 두 번 돌지 않는다.
  로컬 도커 DB처럼 이미 스키마가 있는 DB는 한 번 `init-db --mark-applied`로 기록만 남긴다.
- 서버 서비스의 Networking에서 **Generate Domain**을 눌러야 공개 주소가 생긴다.
- 최초 백필은 한 번만 직접 돌린다 (1~2시간):

  ```bash
  railway ssh --service server
  nohup flask --app run crawl-backfill > backfill.log 2>&1 &
  ```

  도중에 재배포되면 끊기지만, 받은 달은 건너뛰므로 다시 돌리면 이어서 받는다.

- 매일 크롤링은 crawl 서비스가 한국 시간 04:00에 돈다 (`railway.cron.toml`).

#### 자동 배포 (CI/CD)

별도 배포 워크플로 없이 Railway의 GitHub 연동을 쓴다. 토큰을 GitHub에 둘 필요가 없다.

```
push → GitHub Actions CI (pytest · vitest) → 통과하면 → Railway 빌드 → init-db → 교체
```

server·crawl 서비스 Settings에서 한 번만 맞춘다:

- **Branch**: `main` — dev에 푸시해서는 배포되지 않는다
- **Wait for CI**: 켠다 — CI가 실패한 커밋은 배포하지 않는다
- 감시 경로는 `railway.toml`의 `watchPatterns`(`/server/**`)라 프론트만 바꾼 커밋은 재배포하지 않는다

### App Store (EAS)

`mobile/`을 EAS로 빌드해 App Store Connect에 올린다. Xcode 프로젝트는 두지 않는다 —
`ios/`는 `app.json`에서 빌드할 때마다 만들어진다.

```bash
cd mobile
npx eas-cli@latest login
npx eas-cli@latest build --platform ios --profile production
npx eas-cli@latest submit --platform ios --latest
```

제출 전에 확인할 것:

- `eas.json`의 `EXPO_PUBLIC_API_URL`을 Railway 서버 주소로 바꾼다 (`REPLACE-ME`)
- `EXPO_PUBLIC_LEGAL_BASE_URL`(약관·개인정보 처리방침)을 GitHub Pages 주소로 넣는다 —
  심사에서 개인정보 처리방침 URL이 필수다
- `assets/icon.png`(1024×1024), `splash-icon.png`를 실제 앱 아이콘으로 바꾼다
- 번들 ID는 `com.eeez.onegai` (`app.json`)
