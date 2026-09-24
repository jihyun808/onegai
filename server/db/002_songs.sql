CREATE TABLE IF NOT EXISTS songs (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  brand       VARCHAR(20)  NOT NULL,
  no          VARCHAR(20)  NOT NULL,
  title       VARCHAR(255) NOT NULL,
  singer      VARCHAR(255) NOT NULL DEFAULT '',
  composer    VARCHAR(255) NOT NULL DEFAULT '',
  lyricist    VARCHAR(255) NOT NULL DEFAULT '',
  `release`   DATE         NULL,

  match_key   VARCHAR(512) NOT NULL DEFAULT '',
  title_norm  VARCHAR(255) NOT NULL DEFAULT '',
  singer_norm VARCHAR(255) NOT NULL DEFAULT '',

  source      VARCHAR(20)  NOT NULL DEFAULT '',
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uq_songs_brand_no (brand, no),
  KEY idx_songs_title_norm (title_norm),
  KEY idx_songs_singer_norm (singer_norm),
  KEY idx_songs_match_key (match_key(191)),
  KEY idx_songs_release (`release` DESC)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crawl_log (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source     VARCHAR(20)  NOT NULL,
  brand      VARCHAR(20)  NOT NULL,
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
