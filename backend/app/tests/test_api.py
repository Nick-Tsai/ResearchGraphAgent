"""Integration tests for the API endpoints."""

import os
os.environ["MODEL_PROVIDER"] = "mock"
os.environ["SEARCH_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.db import get_session


TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)


def override_get_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def manage_tables():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


class TestCreateProject:
    def test_create_project_succeeds(self, client):
        resp = client.post("/api/projects", json={"topic": "Test topic"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["topic"] == "Test topic"
        assert data["status"] == "draft"
        assert data["current_node"] == "draft"
        assert data["progress_state"] == "complete"


class TestResearchWorkflow:
    def test_full_workflow_with_memories_and_article(self, client):
        create_resp = client.post("/api/projects", json={"topic": "Test"})
        project_id = create_resp.json()["id"]

        idps_resp = client.post(f"/api/projects/{project_id}/run-idps")
        assert idps_resp.status_code == 200
        project = client.get(f"/api/projects/{project_id}").json()
        assert project["current_node"] == "plan"
        assert project["progress_state"] == "complete"

        search_resp = client.post(f"/api/projects/{project_id}/search")
        assert search_resp.status_code == 200
        assert len(search_resp.json()) > 0
        project = client.get(f"/api/projects/{project_id}").json()
        assert project["current_node"] == "sources"
        assert project["progress_state"] == "complete"

        summarize_resp = client.post(f"/api/projects/{project_id}/summarize")
        assert summarize_resp.status_code == 200
        assert len(summarize_resp.json()) > 0
        project = client.get(f"/api/projects/{project_id}").json()
        assert project["current_node"] == "evidence"
        assert project["progress_state"] == "complete"

        build_graph_resp = client.post(f"/api/projects/{project_id}/build-graph")
        assert build_graph_resp.status_code == 200
        graph = build_graph_resp.json()
        assert len(graph["nodes"]) > 0
        project = client.get(f"/api/projects/{project_id}").json()
        assert project["current_node"] == "graph"
        assert project["progress_state"] == "complete"

        review_resp = client.post(f"/api/projects/{project_id}/review")
        assert review_resp.status_code == 200
        assert "overall_assessment" in review_resp.json()
        project = client.get(f"/api/projects/{project_id}").json()
        assert project["current_node"] == "review"
        assert project["progress_state"] == "complete"

        memories_resp = client.get(f"/api/projects/{project_id}/memories")
        assert memories_resp.status_code == 200
        stages = [item["stage"] for item in memories_resp.json()]
        assert stages == ["plan", "sources", "evidence", "graph", "review"]

        article_resp = client.post(f"/api/projects/{project_id}/generate-article")
        assert article_resp.status_code == 200
        article = article_resp.json()
        assert article["title"]
        assert article["content"]
        project = client.get(f"/api/projects/{project_id}").json()
        assert project["current_node"] == "article"
        assert project["progress_state"] == "complete"

        get_article_resp = client.get(f"/api/projects/{project_id}/article")
        assert get_article_resp.status_code == 200
        assert get_article_resp.json()["title"] == article["title"]

    def test_rerun_search_invalidates_downstream_outputs(self, client):
        create_resp = client.post("/api/projects", json={"topic": "Test"})
        project_id = create_resp.json()["id"]
        client.post(f"/api/projects/{project_id}/run-idps")
        client.post(f"/api/projects/{project_id}/search")
        client.post(f"/api/projects/{project_id}/summarize")
        client.post(f"/api/projects/{project_id}/build-graph")
        client.post(f"/api/projects/{project_id}/review")
        client.post(f"/api/projects/{project_id}/generate-article")

        rerun_search_resp = client.post(f"/api/projects/{project_id}/search")
        assert rerun_search_resp.status_code == 200

        graph_resp = client.get(f"/api/projects/{project_id}/graph")
        assert graph_resp.status_code == 404

        article_resp = client.get(f"/api/projects/{project_id}/article")
        assert article_resp.status_code == 404

        memories_resp = client.get(f"/api/projects/{project_id}/memories")
        stages = [item["stage"] for item in memories_resp.json()]
        assert stages == ["plan", "sources"]
