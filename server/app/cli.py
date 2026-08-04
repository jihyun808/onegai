"""크롤링용 CLI.

    flask --app run crawl-backfill        전체 백필 (최초 1회, 1~2시간)
    flask --app run crawl-daily           매일 돌릴 작업
    flask --app run crawl-status          적재 현황
"""

import click
from flask.cli import with_appcontext

from app.models import song
from app.services import crawler


def register_cli(app):
    app.cli.add_command(crawl_backfill)
    app.cli.add_command(crawl_daily)
    app.cli.add_command(crawl_status)


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
