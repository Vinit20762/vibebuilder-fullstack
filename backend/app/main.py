# ─────────────────────────────────────────────────────────────────────────────
#  main.py  —  Application entry point
# ─────────────────────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.auth import authenticate_user, create_access_token
from app.config.database import seed_database
from app.routes.employee_routes import router as employee_router


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_database()
    yield


# ── Create the FastAPI app ────────────────────────────────────────────────────
app = FastAPI(
    title="Employee Management API",
    description="FastAPI + MongoDB + JWT Authentication",
    version="4.0.0",
    lifespan=lifespan,
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"message": "Hello World — Employee API is running!"}


# ── LOGIN endpoint ────────────────────────────────────────────────────────────
@app.post("/auth/login", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Exchange username + password for a JWT access token.

    Send as form data (not JSON):
      username: admin
      password: admin123

    Returns:
      { "access_token": "<token>", "token_type": "bearer" }

    Use the returned token in subsequent requests:
      Authorization: Bearer <token>
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(username=user["username"], role=user["role"])
    return {"access_token": token, "token_type": "bearer"}


# ── Mount routers ─────────────────────────────────────────────────────────────
app.include_router(employee_router)
