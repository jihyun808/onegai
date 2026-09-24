-- 검색어 → 가수 원표기 별칭.
--
-- 한글 발음('미쿠')이나 로마자로 검색하면 자체 DB가 답하지 못한다.
-- DB에는 가수명이 일본어 원표기('初音ミク')로만 들어 있고, 발음은
-- 금영·태진의 **검색 인덱스에만** 있어 크롤링으로 가져올 수 없기 때문이다.
-- (화면에는 원표기만 나온다.)
--
-- 그런데 공식에 한 번 물어보면 답이 결과 안에 들어 있다 —
-- '미쿠'로 찾은 행의 가수명이 '初音ミク'다. 그 연결을 여기 적어 둔다.
--
--   1회차: 미쿠 → 공식 조회(느림) → 初音ミク 발견 → 여기 저장
--   2회차: 미쿠 → 여기서 初音ミク → songs 조회 → 0.06초, 공식 호출 없음
--
-- **공식 사이트 부담을 줄이는 것이 주 목적이다.** 같은 발음 검색이
-- 반복돼도 남의 서버를 다시 치지 않는다.

CREATE TABLE IF NOT EXISTS singer_alias (
  -- 정규화한 검색어. app/utils/normalize.py의 normalize_text()와 같은 규칙.
  alias_norm VARCHAR(120) NOT NULL PRIMARY KEY,
  -- 공식이 알려준 원표기. songs.singer와 같은 형태로 저장한다.
  singer     VARCHAR(255) NOT NULL,
  -- 몇 번이나 이 길로 답했는지. 어떤 발음이 실제로 쓰이는지 보려고 센다.
  hits       INT UNSIGNED NOT NULL DEFAULT 1,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
