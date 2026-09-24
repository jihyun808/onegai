ALTER TABLE songs
  ADD COLUMN title_ko      VARCHAR(255) NULL AFTER title,
  ADD COLUMN title_ko_norm VARCHAR(255) NULL AFTER title_ko;

CREATE INDEX idx_songs_title_ko ON songs (title_ko_norm);
