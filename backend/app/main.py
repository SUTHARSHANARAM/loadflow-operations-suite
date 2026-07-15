from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, rbac, loads, compliance, rates, logs

from app.init_db import init_database

init_database()

app = FastAPI(title="LoadFlow - Freight Brokerage Operations Suite API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development communication
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

