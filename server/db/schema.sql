-- karaokedayo 스키마.
-- MySQL 컨테이너가 처음 뜰 때 자동 실행된다 (docker-entrypoint-initdb.d).
--
-- 주의: 아직 이 테이블을 쓰는 애플리케이션 코드는 없다.
-- 인증/즐겨찾기 엔드포인트를 만들 때 연결한다. DECISIONS.md 참고.

CREATE TABLE IF NOT EXISTS users (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  nickname      VARCHAR(50)  NOT NULL,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS favorites (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NOT NULL,
  -- manana의 브랜드 코드. 현재 서비스 대상은 tj / kumyoung.
  brand      VARCHAR(20)  NOT NULL,
  -- 곡번호는 숫자가 아닐 수 있다 (예: DAM의 '1128-51'). 문자열로 둔다.
  song_no    VARCHAR(20)  NOT NULL,
  title      VARCHAR(255) NOT NULL,
  singer     VARCHAR(255) NOT NULL,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- 같은 곡을 두 번 담지 못하게 한다
  UNIQUE KEY uq_favorites_song (user_id, brand, song_no),
  KEY idx_favorites_user (user_id, created_at),
  CONSTRAINT fk_favorites_user
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS search_history (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     BIGINT UNSIGNED NOT NULL,
  keyword     VARCHAR(100) NOT NULL,
  search_type ENUM('song', 'singer') NOT NULL,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- 최근 검색어 조회용
  KEY idx_history_user (user_id, created_at DESC),
  CONSTRAINT fk_history_user
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
