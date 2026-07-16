FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md NOTICE.md ./
COPY bible_bot ./bible_bot

RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 biblebot \
    && mkdir -p /app/runtime \
    && chown -R biblebot:biblebot /app/runtime

USER biblebot

VOLUME ["/app/runtime"]

CMD ["python", "-m", "bible_bot"]
