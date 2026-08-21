FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Seed the DB on first boot if it doesn't already exist, then start the server.
CMD ["sh", "-c", "test -f datalens.db || python seed_db.py; uvicorn main:app --host 0.0.0.0 --port 8000"]
