import os
from fastapi import FastAPI
import psycopg

app = FastAPI(title="MetaAutomate MVP API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "service": "metaautomate-api"}

@app.get("/ready")
def ready():
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    return {"status": "ready", "database": "connected"}
