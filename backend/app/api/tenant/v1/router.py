"""Tenant API v1 route assembly."""

from fastapi import APIRouter

from app.api.tenant.v1.endpoints import members

api_router = APIRouter()
api_router.include_router(members.router, prefix="/iam/members", tags=["IAM - Members"])
