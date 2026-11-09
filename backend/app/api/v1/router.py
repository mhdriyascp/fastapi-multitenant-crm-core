from fastapi import APIRouter

from app.api.v1.endpoints import members

api_router = APIRouter()

# Include the members router with a prefix and tags for organization
api_router.include_router(members.router, prefix="/iam/members", tags=["IAM - Members"])