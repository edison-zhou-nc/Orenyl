FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY requirements.lock ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps . \
    && adduser --disabled-password --gecos "" --uid 10001 lore \
    && chown -R lore:lore /app

USER lore

EXPOSE 8000

CMD ["python", "-m", "lore.server"]
