-- 아이디 기반 인증으로 전환.
--
-- 처음 스키마는 email을 필수로 잡았지만, 가입을 간단히 하려고 아이디만 받는다.
-- 이메일은 비밀번호 찾기를 붙일 때 선택 항목으로 되살린다.

ALTER TABLE users
  ADD COLUMN username VARCHAR(20) NOT NULL DEFAULT '' AFTER id,
  ADD COLUMN avatar   MEDIUMTEXT NULL AFTER nickname,
  MODIFY COLUMN email    VARCHAR(255) NULL,
  MODIFY COLUMN nickname VARCHAR(50)  NOT NULL DEFAULT '';

-- 아이디는 대소문자를 구분하지 않는다.
-- 'Jihyeon'으로 가입한 뒤 'jihyeon'으로 또 가입되면 서로를 사칭할 수 있다.
ALTER TABLE users
  ADD UNIQUE KEY uq_users_username (username);

-- 기존 email 유니크 제약은 NULL을 허용하므로 그대로 둔다.
