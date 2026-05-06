FROM python:3.12-slim

# cairo 시스템 라이브러리 설치 (pycairo/xhtml2pdf 의존성)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libcairo2-dev \
    pkg-config \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE $PORT

CMD gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --worker-class gevent --worker-connections 100 --timeout 300 --keep-alive 5
