"""Pydantic schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ProjectCreate(BaseModel):
    topic: str = Field(..., min_length=1, description="Research topic")


class ProjectResponse(BaseModel):
    id: UUID
    topic: str
    status: str
    current_node: str
    progress_state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IDPSDimensionSchema(BaseModel):
    name: str
    description: str
    subquestions: list[str]
    falsification_tests: list[str]


class IDPSPlanSchema(BaseModel):
    problem_restatement: str
    constraints: list[str]
    assumptions: list[str]
    dimensions: list[IDPSDimensionSchema]
    initial_search_queries: list[str]
    risk_flags: list[str]


class IDPSPlanResponse(BaseModel):
    audience_level: str = "high"
    problem_restatement: str
    constraints: list[str]
    assumptions: list[str]
    dimensions: list[IDPSDimensionSchema]
    initial_search_queries: list[str]
    risk_flags: list[str]


class SourceResponse(BaseModel):
    id: UUID
    project_id: UUID
    url: str
    title: str
    publisher: str
    source_type: str
    reliability_score: float
    extracted_text: str
    search_query: str
    created_at: datetime
    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    id: UUID
    project_id: UUID
    source_id: UUID
    claim: str
    support_text: str
    confidence: float
    tags: list[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class RunPipelineResponse(BaseModel):
    sources_count: int
    evidence_count: int


class GraphNodeResponse(BaseModel):
    id: UUID
    title: str
    summary: str
    node_type: str
    confidence: float
    source_ids: list[str]
    evidence_ids: list[str]
    parent_node_id: str | None
    x: float | None
    y: float | None
    model_config = {"from_attributes": True}


class GraphEdgeResponse(BaseModel):
    id: UUID
    source_node_id: str
    target_node_id: str
    relation: str
    confidence: float
    model_config = {"from_attributes": True}


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class MemoryResponse(BaseModel):
    id: UUID
    project_id: UUID
    stage: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ArticleResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}
