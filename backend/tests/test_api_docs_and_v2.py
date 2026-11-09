import asyncio

from fastapi.testclient import TestClient

from app.api.health import router as health_api
from main import app

client = TestClient(app)


def test_versioned_redoc_and_scalar_references_are_available() -> None:
    for path in ("/v1/redoc", "/v2/redoc"):
        response = client.get(path)

        assert response.status_code == 200
        assert "redoc" in response.text.lower()

    for path in ("/scalar/v1", "/scalar/v2"):
        response = client.get(path)

        assert response.status_code == 200
        assert "Scalar" in response.text

    for path in ("/docs", "/redoc", "/openapi.json", "/scalar", "/scalar/common"):
        assert client.get(path).status_code == 404


def test_versioned_openapi_schemas_include_only_shared_and_versioned_apis() -> None:
    all_paths = app.openapi()["paths"]
    v1_paths = client.get("/openapi/v1.json").json()["paths"]
    v2_paths = client.get("/openapi/v2.json").json()["paths"]

    assert "/iam/members/" not in all_paths
    assert "/api/v1/iam/members/" in all_paths
    assert "/api/v2/iam/members/" not in all_paths

    for paths in (v1_paths, v2_paths):
        assert "/auth/login" in paths
        assert "/health" in paths

    assert "/api/v1/iam/members/" in v1_paths
    assert "/api/v1/iam/members/" not in v2_paths
    assert "/iam/members/" not in v1_paths
    assert "/iam/members/" not in v2_paths
    assert "/health" in v1_paths
    assert "/health" in v2_paths
    assert "/api/v1/health" not in v1_paths
    assert "/api/v2/health" not in v2_paths
    assert list(v1_paths)[0] == "/health"
    assert list(v2_paths)[0] == "/health"
    assert v1_paths["/health"]["get"]["summary"].startswith("Check readiness")
    assert v2_paths["/health"]["get"]["summary"].startswith("Check readiness")
    assert client.get("/openapi/v1.json").json()["tags"][0]["name"] == "System"
    assert client.get("/openapi/v2.json").json()["tags"][0]["name"] == "System"
    assert {
        tag["name"] for tag in client.get("/openapi/v1.json").json()["tags"]
    } >= {"System", "Authentication", "IAM - Members"}
    assert {
        tag["name"] for tag in client.get("/openapi/v2.json").json()["tags"]
    } == {"System", "Authentication"}
    assert not any(path.startswith("/api/v2/") for path in v1_paths)
    assert not any(path.startswith("/api/v1/") for path in v2_paths)
    assert client.get("/iam/members/").status_code == 404
    assert client.get("/api/v1/iam/members/").status_code != 404
    assert client.get("/api/v2/iam/members/").status_code == 404


def test_health_endpoints_report_all_dependencies(monkeypatch) -> None:
    async def healthy_service() -> health_api.ServiceStatus:
        return health_api.ServiceStatus(status="healthy")

    monkeypatch.setattr(health_api, "_check_postgres", healthy_service)
    monkeypatch.setattr(health_api, "_check_redis", healthy_service)
    monkeypatch.setattr(health_api, "_check_smtp", healthy_service)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert set(response.json()["services"]) == {"postgres", "redis", "smtp"}
    assert all(
        dependency["status"] == "healthy"
        for dependency in response.json()["services"].values()
    )
    assert client.get("/api/v1/health").status_code == 404
    assert client.get("/api/v2/health").status_code == 404


def test_health_endpoint_returns_503_when_a_dependency_is_unavailable(
    monkeypatch,
) -> None:
    async def healthy_service() -> health_api.ServiceStatus:
        return health_api.ServiceStatus(status="healthy")

    async def unavailable_service() -> health_api.ServiceStatus:
        return health_api.ServiceStatus(status="unhealthy", details="Not reachable")

    monkeypatch.setattr(health_api, "_check_postgres", healthy_service)
    monkeypatch.setattr(health_api, "_check_redis", unavailable_service)
    monkeypatch.setattr(health_api, "_check_smtp", healthy_service)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["services"]["redis"]["status"] == "unhealthy"


def test_smtp_probe_authenticates_when_credentials_are_configured(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    class MockSMTP:
        def __init__(self, **kwargs) -> None:
            calls.append(("connect",))

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def login(self, username: str, password: str) -> None:
            calls.append(("login", username, password))

    monkeypatch.setattr(health_api, "SMTP", MockSMTP)
    monkeypatch.setattr(health_api.settings, "SMTP_USER", "health-user")
    monkeypatch.setattr(health_api.settings, "SMTP_PASSWORD", "health-password")

    result = asyncio.run(health_api._check_smtp())

    assert result.status == "healthy"
    assert calls == [("connect",), ("login", "health-user", "health-password")]
