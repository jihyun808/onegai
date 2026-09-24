-- 개인정보처리시스템 접속기록.
--
-- 「개인정보의 안전성 확보조치 기준」 제8조에 따라 **1년 이상 보관**한다.
-- 누가·언제·어디서·무엇을 했는지를 남겨 오남용을 사후에 확인할 수 있게 한다.
--
-- 남기는 것은 **개인정보에 접근하는 요청뿐**이다 (로그인·회원정보·즐겨찾기).
-- 곡 검색처럼 개인정보와 무관한 요청은 대상이 아니고, 남기면 오히려
-- 이용자의 취향 기록이 쌓인다.
--
-- 요청 본문은 저장하지 않는다. 비밀번호가 섞여 들어올 자리를 아예 만들지 않는다.

CREATE TABLE IF NOT EXISTS access_log (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  -- 비로그인 요청(로그인 시도 실패 등)은 NULL이다.
  user_id    BIGINT UNSIGNED NULL,
  -- 수행업무. 'POST /api/auth/login' 형태.
  action     VARCHAR(80)  NOT NULL,
  -- 접속지 정보. 프록시 뒤에서는 X-Forwarded-For의 첫 값이다.
  ip         VARCHAR(45)  NOT NULL DEFAULT '',
  status     SMALLINT UNSIGNED NOT NULL,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_access_user (user_id, created_at),
  KEY idx_access_created (created_at)
  -- users를 참조하지 **않는다.** 탈퇴로 계정이 지워져도 접속기록은 1년을
  -- 채워야 하므로, 외래키를 걸면 CASCADE로 함께 지워져 의무를 못 지킨다.
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
