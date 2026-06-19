"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError
from app.schemas import ProjectCreate, IDPSPlanSchema, IDPSDimensionSchema


class TestProjectCreate:
    def test_valid_topic(self):
        p = ProjectCreate(topic="Should I build a research graph agent?")
        assert p.topic == "Should I build a research graph agent?"

    def test_empty_topic_rejected(self):
        with pytest.raises(ValidationError):
            ProjectCreate(topic="")

    def test_whitespace_topic_is_accepted_by_schema(self):
        """Schema only enforces min_length=1, whitespace check is in the endpoint."""
        p = ProjectCreate(topic="   ")
        assert p.topic == "   "


class TestIDPSPlanSchema:
    valid_plan = {
        "problem_restatement": "Restated problem.",
        "constraints": ["Constraint 1"],
        "assumptions": ["Assumption 1"],
        "dimensions": [
            {
                "name": "Dimension 1",
                "description": "Description.",
                "subquestions": ["Q1"],
                "falsification_tests": ["Test 1"],
            }
        ],
        "initial_search_queries": ["query 1"],
        "risk_flags": ["risk 1"],
    }

    def test_valid_plan_passes(self):
        plan = IDPSPlanSchema.model_validate(self.valid_plan)
        assert plan.problem_restatement == "Restated problem."
        assert len(plan.dimensions) == 1

    def test_missing_required_field_fails(self):
        invalid = {**self.valid_plan}
        del invalid["problem_restatement"]
        with pytest.raises(ValidationError):
            IDPSPlanSchema.model_validate(invalid)

    def test_empty_dimensions_ok(self):
        plan_data = {**self.valid_plan, "dimensions": []}
        plan = IDPSPlanSchema.model_validate(plan_data)
        assert plan.dimensions == []

    def test_dimension_must_have_name(self):
        bad_dims = [
            {
                "description": "Missing name.",
                "subquestions": ["Q1"],
                "falsification_tests": [],
            }
        ]
        with pytest.raises(ValidationError):
            IDPSPlanSchema.model_validate({**self.valid_plan, "dimensions": bad_dims})


class TestIDPSDimensionSchema:
    def test_valid_dimension(self):
        dim = IDPSDimensionSchema(
            name="Test",
            description="A test dimension",
            subquestions=["Q1", "Q2"],
            falsification_tests=["F1"],
        )
        assert dim.name == "Test"
        assert len(dim.subquestions) == 2
