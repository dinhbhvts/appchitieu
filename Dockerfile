# Container image for the VibeApp backend.
#
# This lets the backend run on any container host that does NOT require a credit
# card, e.g. Koyeb or Hugging Face Spaces. The host injects a PORT environment
# variable; we start uvicorn on it (defaulting to 8000 for local use).

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better build caching). requirements-prod.txt
# pulls in requirements.txt plus the PostgreSQL driver for production.
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy the application code.
COPY . .

# Default port for local runs; hosts (Koyeb / HF Spaces) override PORT.
ENV PORT=8000
EXPOSE 8000

# On startup the app creates its tables and seeds defaults automatically
# (see app/main.py lifespan), so no separate migration step is required for a
# fresh database. Point DATABASE_URL at your Supabase/Neon Postgres.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
