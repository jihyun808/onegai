"""크롤링용 CLI.

    flask --app run crawl-backfill        전체 백필 (최초 1회, 1~2시간)
    flask --app run crawl-daily           매일 돌릴 작업
    flask --app run crawl-ky-book         금영 일본곡 색인 전량 (약 15분)
    flask --app run translate-titles      곡 제목을 한국어로 옮겨 적재
    flask --app run purge-access-log      보관 기간이 지난 접속기록 삭제
    flask --app run crawl-status          적재 현황
    flask --app run init-db               db/*.sql 중 아직 안 돌린 것만 실행
"""

from pathlib import Path

import click
import mysql.connector
from flask import current_app
from flask.cli import with_appcontext

from app.models import song
from app.services import crawler


def register_cli(app):
    app.cli.add_command(crawl_backfill)
    app.cli.add_command(crawl_daily)
    app.cli.add_command(crawl_status)
    app.cli.add_command(crawl_fill_gap)
    app.cli.add_command(crawl_ky_book)
    app.cli.add_command(translate_titles)
    app.cli.add_command(purge_access_log)
    app.cli.add_command(init_db)


@click.command("crawl-backfill")
@click.option("--brand", default=None, help="tj 또는 kumyoung. 생략하면 둘 다.")
@click.option("--redo", is_flag=True, help="이미 받은 달도 다시 받는다.")
@with_appcontext
def crawl_backfill(brand, redo):
    """월별로 전량 백필한다. 중단해도 이어서 받을 수 있다."""
    brands = (brand,) if brand else ("tj", "kumyoung")
    result = crawler.backfill(brands=brands, skip_done=not redo)
    click.echo(
        f"{result['months']}개월 처리 · {result['found']}곡 확인 · {result['saved']}행 반영"
    )


@click.command("crawl-daily")
@with_appcontext
def crawl_daily():
    """최근 두 달 + 금영 신곡을 갱신한다."""
    result = crawler.daily()
    click.echo(f"월별: {result['found']}곡 · 금영 신곡: {result['kysing_latest']}")


@click.command("crawl-fill-gap")
@click.option("--brand", default="kumyoung", help="공백을 메울 브랜드")
@click.option("--limit", default=None, type=int, help="가수 수 제한 (시험용)")
@click.option("--redo", is_flag=True, help="이미 훑은 가수도 다시 본다.")
@with_appcontext
def crawl_fill_gap(brand, limit, redo):
    """가수별로 공식을 훑어 카탈로그 공백을 메운다. 느리다(1~2시간)."""
    result = crawler.fill_gap(brand=brand, limit=limit, skip_done=not redo)
    click.echo(
        f"{result['artists']}명 조회 · {result['found']}곡 확인 · {result['saved']}행 반영"
    )


@click.command("crawl-ky-book")
@click.option("--chars", default=None, help="색인 문자를 쉼표로. 생략하면 107종 전부.")
@with_appcontext
def crawl_ky_book(chars):
    """금영 일본곡을 색인으로 전량 훑는다 (약 15분, 3초 간격).

    가수 이름을 몰라도 빠짐없이 가져온다. 하루 한 번이면 충분하다.
    """
    picked = [c.strip() for c in chars.split(",")] if chars else None
    result = crawler.crawl_kysing_book(index_chars=picked)
    click.echo(f"{result['found']}곡 확인 · {result['saved']}행 반영")
    if result["failed"]:
        click.echo(f"실패한 색인: {', '.join(result['failed'])}")


@click.command("translate-titles")
@click.option("--limit", default=1000, type=int, help="이번에 옮길 제목 수")
@click.option("--dry-run", is_flag=True, help="호출만 해 보고 저장하지 않는다.")
@with_appcontext
def translate_titles(limit, dry_run):
    """일본어 곡 제목을 한국어로 옮겨 title_ko에 넣는다.

    `만찬가`로 `晩餐歌`를 찾기 위한 색인이다. 같은 제목은 한 번만 옮긴다.
    DeepL 무료 한도(월 50만 자)를 넘지 않도록 --limit으로 나눠 돌릴 수 있다.
    """
    from app.services import translate

    if not translate.is_enabled():
        click.echo("DEEPL_API_KEY가 없습니다. .env에 넣고 다시 실행하세요.")
        return

    titles = song.untranslated_titles(limit)
    if not titles:
        click.echo("옮길 제목이 없습니다.")
        return

    chars = sum(len(t) for t in titles)
    click.echo(f"{len(titles):,}개 제목 · {chars:,}자")

    done = 0
    for start in range(0, len(titles), translate.BATCH_SIZE):
        batch = titles[start : start + translate.BATCH_SIZE]
        pairs, error = translate.translate_many(batch)

        if error:
            click.echo(f"중단: {error}")
            break

        if not dry_run:
            song.save_translations(pairs)
        done += len(pairs)
        click.echo(f"  {done:,}/{len(titles):,}", nl=False)
        click.echo("\r", nl=False)

    click.echo(f"\n{done:,}개 반영{' (dry-run, 저장 안 함)' if dry_run else ''}")

    progress = song.translation_progress()
    if progress:
        click.echo(f"진행: 번역됨 {progress[0]:,}행 · 남은 제목 {progress[1]:,}행")


@click.command("purge-access-log")
@with_appcontext
def purge_access_log():
    """보관 기간(1년 이상)이 지난 접속기록을 지운다.

    보관 의무가 있는 만큼 **기간을 채우면 지워야 한다.** 필요 이상으로
    오래 들고 있는 것도 개인정보 최소 보관 원칙에 어긋난다.
    """
    from app.models import access_log

    removed = access_log.purge()
    click.echo(f"{removed:,}건 삭제 (보관 {access_log.RETENTION_DAYS}일)")


@click.command("crawl-status")
@with_appcontext
def crawl_status():
    """적재 현황을 보여준다."""
    total = song.count()
    if total is None:
        click.echo("DB에 연결할 수 없습니다.")
        return

    click.echo(f"전체 {total:,}곡")
    for brand in ("tj", "kumyoung"):
        click.echo(
            f"  {brand:9} {song.count(brand):>7,}곡   최신 {song.newest_release(brand) or '-'}"
        )


# schema.sql이 users를 만들고 003이 그 users를 고친다. 이름순으로 돌리면
# 's'가 숫자보다 뒤라 003이 먼저 돌아 깨지므로 schema.sql을 맨 앞에 둔다.
DB_DIR = Path(__file__).resolve().parent.parent / "db"


def _migration_files():
    files = sorted(DB_DIR.glob("[0-9]*.sql"))
    return [DB_DIR / "schema.sql", *files]


def _statements(sql):
    """주석 줄을 걷어내고 ';'로 나눈다. 우리 SQL엔 문자열 속 ';'가 없다."""
    body = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [stmt.strip() for stmt in body.split(";") if stmt.strip()]


@click.command("init-db")
@click.option(
    "--mark-applied",
    is_flag=True,
    help="실행하지 않고 전부 적용된 것으로 기록만 한다 (이미 스키마가 있는 DB용).",
)
@with_appcontext
def init_db(mark_applied):
    """db/*.sql 중 아직 적용하지 않은 파일만 순서대로 실행한다.

    Railway는 배포 직전에 이걸 돌린다(railway.toml의 preDeployCommand).
    ALTER TABLE은 두 번 돌리면 깨지므로 적용한 파일을 schema_migrations에 적어 둔다.
    """
    config = current_app.config
    conn = mysql.connector.connect(
        host=config["MYSQL_HOST"],
        port=config["MYSQL_PORT"],
        user=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        database=config["MYSQL_DATABASE"],
        connection_timeout=int(config["MYSQL_TIMEOUT"]),
    )
    try:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " filename VARCHAR(100) PRIMARY KEY,"
            " applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        cursor.execute("SELECT filename FROM schema_migrations")
        applied = {row[0] for row in cursor.fetchall()}

        pending = [f for f in _migration_files() if f.name not in applied]
        if not pending:
            click.echo("적용할 마이그레이션이 없습니다.")
            return

        for path in pending:
            if not mark_applied:
                # DDL은 MySQL에서 자동 커밋이라 트랜잭션으로 묶이지 않는다.
                # 중간에 깨지면 기록이 남지 않으므로 고친 뒤 다시 돌리면 된다.
                for stmt in _statements(path.read_text(encoding="utf-8")):
                    cursor.execute(stmt)
            cursor.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
            )
            conn.commit()
            click.echo(f"{'기록' if mark_applied else '적용'}: {path.name}")
    finally:
        conn.close()
