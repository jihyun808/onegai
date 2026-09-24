-- 노래방 곡 카탈로그.
--
-- 검색할 때마다 외부 사이트를 치면 5초가 걸린다(금영이 느림).
-- 주기적으로 크롤링해 여기에 쌓아두고, 검색은 이 테이블만 본다.
--
-- 크롤러가 깨져도 이미 쌓인 데이터로 서비스가 계속된다는 것이 큰 이점이다.

CREATE TABLE IF NOT EXISTS songs (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  brand       VARCHAR(20)  NOT NULL,
  -- 곡번호는 숫자가 아닐 수 있다 (DAM의 '1128-51' 등). 문자열로 둔다.
  no          VARCHAR(20)  NOT NULL,
  title       VARCHAR(255) NOT NULL,
  singer      VARCHAR(255) NOT NULL DEFAULT '',
  composer    VARCHAR(255) NOT NULL DEFAULT '',
  lyricist    VARCHAR(255) NOT NULL DEFAULT '',
  `release`   DATE         NULL,

  -- 정규화 키. app/utils/normalize.py 와 같은 규칙으로 채운다.
  -- 브랜드 간 동일 곡 매칭에 쓴다.
  match_key   VARCHAR(512) NOT NULL DEFAULT '',
  -- 검색용. 공백·기호를 제거한 형태라 부분 일치가 표기 흔들림을 넘는다.
  title_norm  VARCHAR(255) NOT NULL DEFAULT '',
  singer_norm VARCHAR(255) NOT NULL DEFAULT '',

  -- 어디서 가져왔는지 (manana / kysing / tjmedia). 문제 추적용.
  source      VARCHAR(20)  NOT NULL DEFAULT '',
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uq_songs_brand_no (brand, no),
  -- 검색은 '포함' 조건이라 인덱스를 다 타지는 못하지만,
  -- 접두 일치와 정렬에는 쓰인다.
  KEY idx_songs_title_norm (title_norm),
  KEY idx_songs_singer_norm (singer_norm),
  KEY idx_songs_match_key (match_key(191)),
  KEY idx_songs_release (`release` DESC)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- 크롤링 진행 상황. 어디까지 긁었는지 기억해 재시작할 수 있게 한다.
CREATE TABLE IF NOT EXISTS crawl_log (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source     VARCHAR(20)  NOT NULL,
  brand      VARCHAR(20)  NOT NULL,
  -- 월별 백필이면 '202601', 그 외에는 'latest' 같은 라벨
  scope      VARCHAR(32)  NOT NULL,
  found      INT UNSIGNED NOT NULL DEFAULT 0,
  inserted   INT UNSIGNED NOT NULL DEFAULT 0,
  status     ENUM('ok','failed') NOT NULL DEFAULT 'ok',
  message    VARCHAR(255) NOT NULL DEFAULT '',
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_crawl_scope (source, brand, scope),
  KEY idx_crawl_created (created_at DESC)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
