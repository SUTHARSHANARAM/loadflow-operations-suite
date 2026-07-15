from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio, httpx, os
from app.routers import auth, rbac, loads, compliance, rates, logs
from app.init_db import init_database

init_database()

# Keep-alive: ping self every 14 minutes to prevent Render free-tier cold starts
async def keep_alive():
    await asyncio.sleep(60)  # Wait 1 min after startup before first ping
    while True:
        try:
            base = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
            async with httpx.AsyncClient() as client:
                await client.get(f"{base}/", timeout=10)
        except Exception:
            pass
        await asyncio.sleep(14 * 60)  # Every 14 minutes

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(keep_alive())
    yield

app = FastAPI(
    title="LoadFlow - Freight Brokerage Operations Suite API",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://loadflow-operations-suite-eta.vercel.app",
        "https://loadflow-operations-suite.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(rbac.router, prefix="/api")
app.include_router(loads.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(rates.router, prefix="/api")
app.include_router(logs.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to LoadFlow API. Visit /docs for OpenAPI documentation."}
