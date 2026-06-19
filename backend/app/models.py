"""SQLModel database models."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column, JSON


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    topic: str = Field(index=True)
    status: str = Field(default="draft")
    current_node: str = Field(default="draft")
    progress_state: str = Field(default="complete")
    total_tokens_used: int = Field(default=0)
    token_budget: int = Field(default=200000)
    audience_level: str = Field(default="high")  # elementary / middle / high / college
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IDPSPlan(SQLModel, table=True):
    __tablename__ = "idps_plans"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    problem_restatement: str = Field(default="")
    constraints: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    assumptions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    dimensions: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    initial_search_queries: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    risk_flags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    raw_model_output: Optional[str] = Field(default=None)
    provider_used: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    url: str = Field(default="")
    title: str = Field(default="")
    publisher: str = Field(default="")
    published_at: str = Field(default="")
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extracted_text: str = Field(default="")
    search_query: str = Field(default="")
    source_type: str = Field(default="secondary")
    reliability_score: float = Field(default=0.5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Evidence(SQLModel, table=True):
    __tablename__ = "evidence"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    source_id: UUID = Field(foreign_key="sources.id", index=True)
    claim: str = Field(default="")
    support_text: str = Field(default="")
    confidence: float = Field(default=0.5)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphNode(SQLModel, table=True):
    __tablename__ = "graph_nodes"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    title: str = Field(default="")
    summary: str = Field(default="")
    node_type: str = Field(default="claim")
    confidence: float = Field(default=0.5)
    source_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    parent_node_id: Optional[str] = Field(default=None)
    x: Optional[float] = Field(default=None)
    y: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphEdge(SQLModel, table=True):
    __tablename__ = "graph_edges"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    source_node_id: str = Field(default="")
    target_node_id: str = Field(default="")
    relation: str = Field(default="supports")
    confidence: float = Field(default=0.5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Memory(SQLModel, table=True):
    __tablename__ = "memories"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    stage: str = Field()
    content: str = Field()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Article(SQLModel, table=True):
    __tablename__ = "articles"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", index=True)
    title: str = Field()
    content: str = Field()
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
