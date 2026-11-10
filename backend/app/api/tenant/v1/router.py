"""Tenant API v1 route assembly."""

from fastapi import APIRouter

from app.api.tenant.v1.endpoints import master_data, members, menus

api_router = APIRouter()
api_router.include_router(members.router, prefix="/iam/members", tags=["IAM - Members"])
api_router.include_router(menus.router, prefix="/navigation/menus", tags=["Navigation"])
api_router.include_router(
    master_data.router,
    prefix="/master-data",
    tags=["Tenant Master Data"],
)
