FROM python:3.13-slim

# 파이썬이 .pyc를 남기지 않고, 로그를 버퍼링 없이 바로 내보내게 한다
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 의존성을 먼저 복사해 레이어 캐시를 살린다.
# 소스만 바뀌면 pip install을 다시 하지 않는다.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 5001

CMD ["python", "run.py"]
