"""Unit tests for the IDPS planner with controlled providers."""

import json
import asyncio
import pytest
from sqlmodel import Session, SQLModel, select, create_engine
from sqlmodel.pool import StaticPool
from app.models import Project, IDPSPlan
from app.pipeline.idps_planner import run_idps
from app.providers.base import ModelProvider

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


class GoodMockProvider(ModelProvider):
    @property
    def name(self) -> str:
        return "good_mock"
    async def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        return json.dumps({
            "problem_restatement": "A restated problem.",
            "constraints": ["C1"],
            "assumptions": ["A1"],
            "dimensions": [{"name": "D1", "description": "Desc", "subquestions": ["Q1"], "falsification_tests": ["F1"]}],
            "initial_search_queries": ["search"],
            "risk_flags": ["risk"],
        })


class BadJSONProvider(ModelProvider):
    @property
    def name(self) -> str:
        return "bad_json"
    async def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        return "not valid json at all {{{"


class InvalidSchemaProvider(ModelProvider):
    @property
    def name(self) -> str:
        return "invalid_schema"
    async def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        return json.dumps({"problem_restatement": "missing fields"})


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def manage_tables():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def session():
    with Session(engine) as s:
        yield s


@pytest.fixture
def project(session):
    p = Project(topic="Test topic")
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


class TestIDPSPlanner:
    def test_valid_plan_saved(self, session, project):
        plan = _run(run_idps(project, GoodMockProvider(), session))
        assert plan.problem_restatement == "A restated problem."
        assert plan.provider_used == "good_mock"
        assert plan.raw_model_output is not None
        assert len(plan.dimensions) == 1
    def test_project_status_updated(self, session, project):
        _run(run_idps(project, GoodMockProvider(), session))
        session.refresh(project)
        assert project.status == "running"
    def test_bad_json_raises_value_error(self, session, project):
        with pytest.raises(ValueError, match="invalid JSON"):
            _run(run_idps(project, BadJSONProvider(), session))
    def test_invalid_schema_raises_value_error(self, session, project):
        with pytest.raises(ValueError, match="schema validation"):
            _run(run_idps(project, InvalidSchemaProvider(), session))
    def test_plan_not_persisted_on_error(self, session, project):
        try:
            _run(run_idps(project, BadJSONProvider(), session))
        except ValueError:
            pass
        plans = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project.id)).all()
        assert len(plans) == 0
