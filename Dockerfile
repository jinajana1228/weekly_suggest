# Weekly Suggest — Backend Docker Image
#
# Docker context: 리포지토리 루트 (weekly_suggest/)
# 런타임 구조:
#   /app/backend/   ← FastAPI 앱 (WORKDIR)
#   /app/data/      ← mock 데이터 및 state.db
#
# MOCK_DATA_DIR 기본값 ../data/mock → /app/data/mock (정상 해석됨)
#
# Railway Variables 는 컨테이너 실행 시 os.environ 으로 직접 주입된다.
# Nixpacks 래퍼 스크립트 계층이 없으므로 env 누락 문제가 발생하지 않는다.

FROM python:3.11-slim

# 시스템 패키지 (최소화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 설치 (레이어 캐시 활용)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY backend/ ./backend/

# mock 데이터 복사 (MOCK_DATA_DIR=../data/mock 경로가 /app/data/mock 으로 해석됨)
COPY data/ ./data/

# uvicorn 실행 디렉토리
WORKDIR /app/backend

# PORT 는 Railway 가 런타임에 env로 주입한다.
# shell form 사용 — $PORT 변수 확장을 위해 sh -c 경유
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
