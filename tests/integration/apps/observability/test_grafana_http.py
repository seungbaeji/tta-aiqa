"""Grafana Cloud HTTP adapter contract tests."""

from grafana_dashboard_importer.adapters import GrafanaHttpGateway
from grafana_dashboard_importer.domain import DashboardImport


class FakeResponse:
    def __init__(self, document: dict[str, str] | None = None) -> None:
        self._document = document or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return self._document


class FakeSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.gets: list[tuple[str, int]] = []
        self.posts: list[tuple[str, dict[str, object], int]] = []

    def get(self, url: str, timeout: int) -> FakeResponse:
        self.gets.append((url, timeout))
        return FakeResponse()

    def post(self, url: str, json: dict[str, object], timeout: int) -> FakeResponse:
        self.posts.append((url, json, timeout))
        return FakeResponse(
            {
                "uid": "tta-aiqa-quality",
                "url": "/d/tta-aiqa-quality",
                "status": "success",
            }
        )


def test_gateway_verifies_datasource_and_overwrites_stable_uid() -> None:
    session = FakeSession()
    gateway = GrafanaHttpGateway(
        base_url="https://student.grafana.net",
        token="dashboard-only-token",
        session=session,  # type: ignore[arg-type]
    )

    gateway.verify_datasource("prometheus-uid")
    result = gateway.import_dashboard(
        DashboardImport(
            dashboard={"uid": "tta-aiqa-quality", "title": "AIQA"},
            folder_uid="course",
        )
    )

    assert session.headers["Authorization"] == "Bearer dashboard-only-token"
    assert session.gets[0][0].endswith("/api/datasources/uid/prometheus-uid")
    payload = session.posts[0][1]
    assert payload["overwrite"] is True
    assert payload["folderUid"] == "course"
    assert result.url == "https://student.grafana.net/d/tta-aiqa-quality"
