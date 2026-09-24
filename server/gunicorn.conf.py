"""운영용 gunicorn 설정.

개발은 `python run.py`(Flask 개발 서버)를 그대로 쓴다 — 리로더가 필요해서다.
배포는 이 파일을 쓴다. Dockerfile의 기본 CMD가 여기를 가리킨다.
"""

import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"

# 스레드 워커를 쓴다. 이 서버가 하는 일의 대부분은 계산이 아니라
# **남의 서버를 기다리는 것**이다 (금영·TJ 스크래핑, manana, iTunes).
# 기본 sync 워커는 기다리는 동안 통째로 막혀서, 느린 조회 하나가
# 그 워커에 들어온 다른 요청까지 세운다.
worker_class = "gthread"

# CPU가 아니라 대기 시간이 병목이라 워커를 많이 늘릴 이유가 없다.
# 동시 처리량은 workers × threads다 (기본 2 × 8 = 16).
workers = int(os.getenv("WEB_WORKERS", max(2, multiprocessing.cpu_count() // 2)))
threads = int(os.getenv("WEB_THREADS", 8))

# **기본값 30초로는 부족하다.** `full=1` 검색은 금영을 여러 페이지 훑어서
# 최악의 경우 1분을 넘긴다 (페이지당 최대 10초 × 재시도).
# 여기서 잘리면 워커가 죽고 사용자는 502를 본다.
timeout = int(os.getenv("WEB_TIMEOUT", 120))
graceful_timeout = 30

# 커넥션이 살아 있는 채로 재활용되며 생기는 누수를 끊는다
max_requests = 1000
max_requests_jitter = 100

# **워커를 포크하기 전에 앱을 올리지 않는다.** MySQL 커넥션 풀과 Redis
# 클라이언트가 부모에서 만들어지면 자식들이 같은 소켓을 나눠 쓰게 된다.
# 지금은 둘 다 첫 사용 시점에 만들어지지만, 그 가정에 기대지 않는다.
preload_app = False

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# 프록시(nginx 등) 뒤에 두면 X-Forwarded-* 를 신뢰해야
# 요청 제한이 실제 클라이언트 IP를 본다. 신뢰할 프록시가 없다면 비워 둔다.
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
