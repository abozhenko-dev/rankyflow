"""
API v1 router — aggregates all endpoint routers.
"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.competitors import router as competitors_router
from app.api.v1.geo import router as geo_router
from app.api.v1.agents import router as agents_router
from app.api.v1.data import router as data_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(competitors_router)
api_router.include_router(geo_router)
api_router.include_router(agents_router)
api_router.include_router(data_router)
