FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Seeding is a deliberate one-time step (docker compose exec backend python -m
# scripts.seed_db), not automatic on boot — auto-seeding would re-run against
# a real Postgres volume on every container restart.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
