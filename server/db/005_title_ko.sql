-- 곡 제목의 한국어 번역.
--
-- `만찬가`로 `晩餐歌`를 찾기 위한 컬럼이다.
--
-- **검색어를 번역해 던지는 방식은 안 된다.** `만찬가`를 일본어로 옮기면
-- `晩餐の歌` 같은 것이 나오지 실제 등록 제목 `晩餐歌`가 아니다. 의역된
-- 제목은 더 어긋난다. 그래서 방향을 뒤집어 **카탈로그 제목을 미리 번역해
-- 두고 그 컬럼을 검색한다** (DECISIONS.md 11번).
--
-- 태진·금영이 한국어 제목을 주는 경우도 있지만 그것은 대개 **한국 가수가
-- 부른 커버**다 (`만찬가/태연`, `잔혹한 천사의 테제/한로로`). 원곡과 다른
-- 곡이라 한국곡 필터가 걸러낸다. 이 컬럼은 원곡을 찾기 위한 것이다.

ALTER TABLE songs
  -- 화면에 함께 보여줄 번역 제목
  ADD COLUMN title_ko      VARCHAR(255) NULL AFTER title,
  -- 검색용. title_norm과 같은 규칙으로 정규화해 넣는다.
  ADD COLUMN title_ko_norm VARCHAR(255) NULL AFTER title_ko;

-- 부분 일치라 인덱스를 다 타지는 못하지만 접두 일치에는 쓰인다.
CREATE INDEX idx_songs_title_ko ON songs (title_ko_norm);
