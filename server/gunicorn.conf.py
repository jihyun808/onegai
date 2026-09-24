import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"

worker_class = "gthread"

workers = int(os.getenv("WEB_WORKERS", max(2, multiprocessing.cpu_count() // 2)))
threads = int(os.getenv("WEB_THREADS", 8))

timeout = int(os.getenv("WEB_TIMEOUT", 120))
graceful_timeout = 30

max_requests = 1000
max_requests_jitter = 100

preload_app = False

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
