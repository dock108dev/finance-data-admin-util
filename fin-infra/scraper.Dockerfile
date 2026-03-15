FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies — extract from pyproject.toml and install
COPY scraper/pyproject.toml .
RUN python -c "import tomllib,pathlib;d=tomllib.loads(pathlib.Path('pyproject.toml').read_text());print(chr(10).join(d['project']['dependencies']))" > /tmp/reqs.txt && pip install --no-cache-dir -r /tmp/reqs.txt && rm /tmp/reqs.txt

# Application code
COPY scraper/ .

CMD ["celery", "-A", "fin_scraper.celery_app", "worker", "-l", "info", "-Q", "fin-scraper"]
