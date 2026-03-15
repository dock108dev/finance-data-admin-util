FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies — copy pyproject.toml and install deps only
COPY scraper/pyproject.toml .
RUN pip install --no-cache-dir $(python -c "
import tomllib, pathlib
d = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
print(' '.join(d['project']['dependencies']))
")

# Application code
COPY scraper/ .

CMD ["celery", "-A", "fin_scraper.celery_app", "worker", "-l", "info", "-Q", "fin-scraper"]
