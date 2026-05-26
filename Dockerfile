FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# system deps for some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    postgresql-client \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV DOWNLOADS_DIR=.downloads

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "bot.main"]
