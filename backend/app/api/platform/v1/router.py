"""Platform API v1 route assembly."""

from fastapi import APIRouter

from app.api.platform.v1.endpoints import (
    audit,
    iam,
    master_data,
    operators,
    plans,
    tenants,
)

router = APIRouter(prefix="/platform/v1", tags=["Platform Administration"])

router.include_router(iam.router)
router.include_router(operators.router)
router.include_router(tenants.router)
router.include_router(plans.router)
router.include_router(audit.router)
router.include_router(master_data.router)
