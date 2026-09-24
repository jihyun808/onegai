CREATE TABLE IF NOT EXISTS access_log (
  id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id    BIGINT UNSIGNED NULL,
  action     VARCHAR(80)  NOT NULL,
  ip         VARCHAR(45)  NOT NULL DEFAULT '',
  status     SMALLINT UNSIGNED NOT NULL,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_access_user (user_id, created_at),
  KEY idx_access_created (created_at)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
