FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY matchmaker ./matchmaker

# The database lives on the volume (docker-compose.yml); the server runs as a
# plain user.
RUN useradd --system --uid 10001 matchmaker && mkdir -p /data && chown matchmaker /data
USER matchmaker
ENV DATA_DIR=/data PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "-m", "matchmaker.app"]
