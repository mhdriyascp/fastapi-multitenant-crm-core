# Pagination dependency for FastAPI endpoints using offset-based pagination.
from fastapi import Query


class PaginationParams:
    """Reusable query parameter contract for offset-based pagination."""

    def __init__(
        self,
        skip: int = Query(
            default=0,
            ge=0,
            description="Number of records to skip (offset)",
        ),
        limit: int = Query(
            default=20,
            ge=1,
            le=100,
            description="Maximum number of records to return (page size, max 100)",
        ),
    ):
        self.skip = skip
        self.limit = limit
