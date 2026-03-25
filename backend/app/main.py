# ─────────────────────────────────────────────────────────────────────────────
#  main.py  —  Application entry point
# ─────────────────────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import seed_database
from app.routes.employee_routes import router as employee_router


# ── Lifespan: runs once on startup and once on shutdown ───────────────────────
# This replaces the older @app.on_event("startup") pattern.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # Seed the MongoDB collection with sample data if it's empty.
    seed_database()
    yield
    # --- SHUTDOWN ---
    # Nothing to clean up for now (pymongo closes connections automatically).


# ── Create the FastAPI app ────────────────────────────────────────────────────
app = FastAPI(
    title="Employee Management API",
    description="FastAPI + MongoDB Employee Database",
    version="3.0.0",
    lifespan=lifespan,
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"message": "Hello World — Employee API is running!"}


# ── Mount routers ─────────────────────────────────────────────────────────────
app.include_router(employee_router)
