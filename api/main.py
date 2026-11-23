from contextlib import asynccontextmanager

import evidence
import investigations
import psycopg
from fastapi import FastAPI
from pydantic import BaseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    with psycopg.connect() as db:
        evidence.init(db)
        investigations.init(db)
        db.execute("CREATE TABLE IF NOT EXISTS projects (slug text PRIMARY KEY, name text NOT NULL)")
        db.execute("INSERT INTO projects VALUES (%s, %s) ON CONFLICT DO NOTHING", ("demo", "Demo store"))
    yield


app = FastAPI(title="RootCause AI", lifespan=lifespan)


app.include_router(evidence.router)
app.include_router(investigations.router)


class Project(BaseModel):
    slug: str
    name: str


@app.get("/health")
def health():
    with psycopg.connect(connect_timeout=2) as db:
        db.execute("SELECT 1")
    return {"status": "ready"}


@app.get("/projects/demo", response_model=Project)
def demo():
    with psycopg.connect(connect_timeout=2) as db:
        slug, name = db.execute("SELECT slug, name FROM projects WHERE slug = 'demo'").fetchone()
    return Project(slug=slug, name=name)
