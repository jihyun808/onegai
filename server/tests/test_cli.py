from app.cli import _migration_files, _statements


def test_schema_runs_before_numbered_migrations():
    # 003이 schema.sql의 users를 ALTER하므로 순서가 뒤집히면 깨진다
    names = [path.name for path in _migration_files()]
    assert names[0] == "schema.sql"
    assert names[1:] == sorted(names[1:])


def test_statements_split_and_drop_comments():
    sql = "-- 주석; 무시\nCREATE TABLE a (id INT);\n\n-- 끝\nALTER TABLE a\n  ADD b INT;\n"
    assert _statements(sql) == ["CREATE TABLE a (id INT)", "ALTER TABLE a\n  ADD b INT"]


def test_every_migration_file_parses():
    for path in _migration_files():
        assert _statements(path.read_text(encoding="utf-8")), path.name
