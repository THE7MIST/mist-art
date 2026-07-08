from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, cases, catalog, evidence, health, plugins, questions, reports
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-native digital forensics investigation and verification platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(cases.router, prefix=settings.api_prefix, tags=["cases"])
app.include_router(evidence.router, prefix=settings.api_prefix, tags=["evidence"])
app.include_router(catalog.router, prefix=settings.api_prefix, tags=["catalog"])
app.include_router(questions.router, prefix=settings.api_prefix, tags=["questions"])
app.include_router(analysis.router, prefix=settings.api_prefix, tags=["analysis"])
app.include_router(reports.router, prefix=settings.api_prefix, tags=["reports"])
app.include_router(plugins.router, prefix=settings.api_prefix, tags=["plugins"])
