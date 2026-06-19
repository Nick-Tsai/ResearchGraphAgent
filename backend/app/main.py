"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.db import create_db_and_tables, get_session
from app.models import Project, IDPSPlan, Source, Evidence, GraphNode, GraphEdge, Memory, Article
from app.schemas import (
    ProjectCreate,
    ProjectResponse,
    IDPSPlanResponse,
    IDPSDimensionSchema,
    SourceResponse,
    EvidenceResponse,
    RunPipelineResponse,
    GraphNodeResponse,
    GraphEdgeResponse,
    GraphResponse,
    MemoryResponse,
    ArticleResponse,
)
from app.pipeline.idps_planner import run_idps
from app.pipeline.search import run_search
from app.pipeline.summarize import summarize_sources
from app.pipeline.graph_builder import build_graph
from app.pipeline.expand_node import expand_node
from app.pipeline.challenge_node import challenge_node
from app.pipeline.premium_review import premium_review
from app.providers.factory import get_provider
from app.providers.search_factory import get_search_provider
from app.providers.base import ModelProvider


WORKFLOW_STAGES = ["draft", "plan", "sources", "evidence", "graph", "review", "article"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
    try:
        provider = get_provider()
        if hasattr(provider, "close"):
            await provider.close()
    except Exception:
        pass


app = FastAPI(title="Research Graph Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
@app.exception_handler(500)
async def global_exception_handler(request: Request, exc: Exception):
    detail = str(exc)
    status = 500
    if isinstance(exc, HTTPException):
        detail = exc.detail
        status = exc.status_code
    return JSONResponse(
        status_code=status,
        content={"detail": detail},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


def _set_workflow_state(project: Project, node: str, progress_state: str, status: str, session: Session):
    project.current_node = node
    project.progress_state = progress_state
    project.status = status
    project.updated_at = datetime.now(timezone.utc)
    session.add(project)
    session.commit()
    session.refresh(project)


def _mark_running(project: Project, node: str, session: Session):
    _set_workflow_state(project, node=node, progress_state="running", status="running", session=session)


def _mark_complete(project: Project, node: str, session: Session):
    _set_workflow_state(project, node=node, progress_state="complete", status="complete", session=session)


def _mark_failed(project: Project, node: str, session: Session):
    _set_workflow_state(project, node=node, progress_state="failed", status="failed", session=session)


def _delete_rows(session: Session, model, project_id: UUID):
    rows = session.exec(select(model).where(model.project_id == project_id)).all()
    for row in rows:
        session.delete(row)


def _invalidate_from(project_id: UUID, stage: str, session: Session):
    if stage not in WORKFLOW_STAGES:
        return
    invalidated = WORKFLOW_STAGES[WORKFLOW_STAGES.index(stage):]

    if "plan" in invalidated:
        _delete_rows(session, IDPSPlan, project_id)
    if "evidence" in invalidated:
        _delete_rows(session, Evidence, project_id)
    if "sources" in invalidated:
        _delete_rows(session, Source, project_id)
    if "graph" in invalidated:
        _delete_rows(session, GraphEdge, project_id)
        _delete_rows(session, GraphNode, project_id)
    if "article" in invalidated:
        _delete_rows(session, Article, project_id)

    memories = session.exec(select(Memory).where(Memory.project_id == project_id)).all()
    for memory in memories:
        if memory.stage in invalidated:
            session.delete(memory)

    # session.commit() removed — caller commits atomically



def _add_tokens(project: Project, tokens: int, session: Session):
    project.total_tokens_used = (project.total_tokens_used or 0) + tokens
    session.add(project)
    session.commit()


def _check_budget(project: Project) -> None:
    used = project.total_tokens_used or 0
    budget = project.token_budget or 200000
    if used >= budget:
        raise HTTPException(status_code=429, detail=f"Token budget exhausted: {used}/{budget}")
def _replace_memory(project_id: UUID, stage: str, content: str, session: Session):
    existing = session.exec(
        select(Memory).where(Memory.project_id == project_id).where(Memory.stage == stage)
    ).all()
    for item in existing:
        session.delete(item)
    session.add(Memory(project_id=project_id, stage=stage, content=content))
    session.commit()


def _plan_memory(plan: IDPSPlan) -> str:
    dimension_names = [d.get("name", "") for d in plan.dimensions]
    return (
        f"Problem: {plan.problem_restatement}\n"
        f"Constraints: {'; '.join(plan.constraints)}\n"
        f"Assumptions: {'; '.join(plan.assumptions)}\n"
        f"Dimensions: {', '.join(dimension_names)}\n"
        f"Risk flags: {'; '.join(plan.risk_flags)}"
    )


def _sources_memory(sources: list[Source]) -> str:
    lines = [f"{s.title} | {s.publisher} | query={s.search_query}" for s in sources[:10]]
    return "Retrieved sources:\n" + "\n".join(lines)


def _evidence_memory(evidence: list[Evidence]) -> str:
    lines = [f"{e.claim} (confidence={e.confidence:.2f})" for e in evidence[:12]]
    return "Extracted evidence:\n" + "\n".join(lines)


def _review_memory(review: dict) -> str:
    parts = [review.get("overall_assessment", "")]
    if review.get("critical_issues"):
        parts.append("Critical issues: " + "; ".join(review["critical_issues"]))
    if review.get("next_research_actions"):
        parts.append("Next actions: " + "; ".join(review["next_research_actions"]))
    return "\n".join(part for part in parts if part)


async def _generate_article(project: Project, provider: ModelProvider, session: Session) -> Article:
    memories = session.exec(
        select(Memory).where(Memory.project_id == project.id).order_by(Memory.created_at.asc())
    ).all()
    if not memories:
        raise ValueError("No memories found. Run at least one workflow stage first.")

    audience = project.audience_level or "high"
    audience_guide = {
        "elementary": "写给小学生的文章：用比喻、故事、图片思维。每段不超过3句话。避免任何公式。用生活里的例子。像在跟小朋友聊天一样。",
        "middle": "写给初中生的文章：用直观解释，偶尔用简单公式。每段不超过5句话。举实际的例子。像一位耐心的老师在讲解。",
        "high": "写给高中生的文章：可以用学术语言和数学公式。逻辑清晰，有推导过程。像大学教材的风格。",
        "college": "写给大学生的文章：保持学术严谨，完整的推导和引用。",
    }
    guide = audience_guide.get(audience, audience_guide["high"])
    prompt = (
        "You are the article synthesis module for a research graph agent.\n"
        f"{guide}\n\n"
        "Write the article following this learning path structure:\n"
        "1. 这是什么？（一句话概述）\n"
        "2. 为什么重要？（学会这个有什么用）\n"
        "3. 核心概念（2-5个，每个带一个例子）\n"
        "4. 深入理解（概念之间的关系）\n"
        "5. 实际应用（生活中的例子）\n"
        "6. 常见误解（容易搞错的地方）\n"
        "7. 小测验（3个思考题）\n"
        "Return strict JSON: {\"title\": \"...\", \"content\": \"...\"}.\n\n"
        f"Topic: {project.topic}\n"
        f"Structured memories:\n{json.dumps([{ 'stage': m.stage, 'content': m.content } for m in memories], ensure_ascii=False, indent=2)}"
    )
    raw = await provider.complete(prompt, max_tokens=8192)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Article generation returned invalid JSON: {exc}") from exc

    existing = session.exec(select(Article).where(Article.project_id == project.id)).all()
    for item in existing:
        session.delete(item)
    article = Article(
        project_id=project.id,
        title=data.get("title", f"{project.topic} — Article"),
        content=data.get("content", ""),
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    _replace_memory(project.id, "article", f"{article.title}\n\n{article.content}", session)
    return article


@app.post("/api/projects", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, session: Session = Depends(get_session)):
    if not body.topic.strip():
        raise HTTPException(status_code=400, detail="Topic must not be empty")
    project = Project(topic=body.topic.strip())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@app.get("/api/projects", response_model=list[ProjectResponse])
def list_projects(session: Session = Depends(get_session)):
    return session.exec(select(Project).order_by(Project.created_at.desc()).limit(20)).all()


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: UUID, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/api/projects/{project_id}/run-idps", response_model=IDPSPlanResponse)
async def run_idps_endpoint(
    project_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        _invalidate_from(project_id, "plan", session)
        _mark_running(project, "plan", session)
        _check_budget(project)
        plan = await run_idps(project, provider, session)
        _add_tokens(project, 4096, session)
        _replace_memory(project_id, "plan", _plan_memory(plan), session)
        _mark_complete(project, "plan", session)
    except ValueError as exc:
        _mark_failed(project, "plan", session)
        raise HTTPException(status_code=502, detail=str(exc))
    return _plan_to_response(plan)


@app.get("/api/projects/{project_id}/plan", response_model=IDPSPlanResponse)
def get_plan(project_id: UUID, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project_id)).first()
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found for this project")
    return _plan_to_response(plan)


@app.post("/api/projects/{project_id}/run-pipeline", response_model=RunPipelineResponse)
async def run_pipeline(
    project_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project_id)).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Run IDPS planning first")
    try:
        _invalidate_from(project_id, "sources", session)
        _mark_running(project, "sources", session)
        sources = await run_search(project, get_search_provider(), session)
        _replace_memory(project_id, "sources", _sources_memory(sources), session)
        _mark_running(project, "evidence", session)
        _check_budget(project)
        evidence = await summarize_sources(project, provider, session)
        _add_tokens(project, max(1, len(evidence)) * 4096, session)
        _replace_memory(project_id, "evidence", _evidence_memory(evidence), session)
        _mark_complete(project, "evidence", session)
    except Exception as exc:
        _mark_failed(project, project.current_node or "sources", session)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(exc))
    return RunPipelineResponse(sources_count=len(sources), evidence_count=len(evidence))


@app.post("/api/projects/{project_id}/search", response_model=list[SourceResponse])
async def search_endpoint(project_id: UUID, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project_id)).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Run IDPS planning first")
    try:
        _invalidate_from(project_id, "sources", session)
        _mark_running(project, "sources", session)
        sources = await run_search(project, get_search_provider(), session)
        _replace_memory(project_id, "sources", _sources_memory(sources), session)
        _mark_complete(project, "sources", session)
    except Exception as exc:
        _mark_failed(project, "sources", session)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(exc))
    return sources


@app.post("/api/projects/{project_id}/summarize", response_model=list[EvidenceResponse])
async def summarize_endpoint(
    project_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    sources = session.exec(select(Source).where(Source.project_id == project_id)).all()
    if not sources:
        raise HTTPException(status_code=400, detail="Run search first")
    try:
        _invalidate_from(project_id, "evidence", session)
        _mark_running(project, "evidence", session)
        _check_budget(project)
        evidence = await summarize_sources(project, provider, session)
        _add_tokens(project, max(1, len(evidence)) * 4096, session)
        _replace_memory(project_id, "evidence", _evidence_memory(evidence), session)
        _mark_complete(project, "evidence", session)
    except Exception as exc:
        _mark_failed(project, "evidence", session)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(exc))
    return evidence


@app.get("/api/projects/{project_id}/sources", response_model=list[SourceResponse])
def list_sources(project_id: UUID, session: Session = Depends(get_session)):
    return session.exec(select(Source).where(Source.project_id == project_id).order_by(Source.created_at.desc())).all()


@app.get("/api/projects/{project_id}/evidence", response_model=list[EvidenceResponse])
def list_evidence(project_id: UUID, session: Session = Depends(get_session)):
    return session.exec(select(Evidence).where(Evidence.project_id == project_id).order_by(Evidence.confidence.desc())).all()


@app.post("/api/projects/{project_id}/build-graph", response_model=GraphResponse)
async def build_graph_endpoint(
    project_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    evidence = session.exec(select(Evidence).where(Evidence.project_id == project_id)).all()
    if not evidence:
        raise HTTPException(status_code=400, detail="Run summarize first")
    try:
        _invalidate_from(project_id, "graph", session)
        _mark_running(project, "graph", session)
        plan = session.exec(select(IDPSPlan).where(IDPSPlan.project_id == project_id)).first()
        dim_count = len(plan.dimensions) if plan and plan.dimensions else 0
        _check_budget(project)
        nodes, edges, graph_memory = await build_graph(project, provider, session)
        _add_tokens(project, dim_count * 4096 + 8192, session)
        _replace_memory(project_id, "graph", graph_memory, session)
        _mark_complete(project, "graph", session)
    except Exception as exc:
        _mark_failed(project, "graph", session)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(exc))
    return GraphResponse(
        nodes=[GraphNodeResponse.model_validate(node) for node in nodes],
        edges=[GraphEdgeResponse.model_validate(edge) for edge in edges],
    )


@app.get("/api/projects/{project_id}/graph", response_model=GraphResponse)
def get_graph(project_id: UUID, session: Session = Depends(get_session)):
    nodes = session.exec(select(GraphNode).where(GraphNode.project_id == project_id)).all()
    edges = session.exec(select(GraphEdge).where(GraphEdge.project_id == project_id)).all()
    if not nodes and not edges:
        raise HTTPException(status_code=404, detail="No graph found. Run build-graph first.")
    return GraphResponse(
        nodes=[GraphNodeResponse.model_validate(node) for node in nodes],
        edges=[GraphEdgeResponse.model_validate(edge) for edge in edges],
    )


@app.post("/api/projects/{project_id}/nodes/{node_id}/expand")
async def expand_node_endpoint(
    project_id: UUID,
    node_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return await expand_node(node_id, project_id, provider, get_search_provider(), session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/projects/{project_id}/nodes/{node_id}/challenge")
async def challenge_node_endpoint(
    project_id: UUID,
    node_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        return await challenge_node(node_id, project_id, provider, session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/projects/{project_id}/review")
async def premium_review_endpoint(
    project_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    nodes = session.exec(select(GraphNode).where(GraphNode.project_id == project_id)).all()
    if not nodes:
        raise HTTPException(status_code=400, detail="Build graph first")
    try:
        _invalidate_from(project_id, "review", session)
        _mark_running(project, "review", session)
        result = await premium_review(project_id, provider, session)
        _replace_memory(project_id, "review", _review_memory(result), session)
        _mark_complete(project, "review", session)
    except Exception as exc:
        _mark_failed(project, "review", session)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@app.get("/api/projects/{project_id}/memories", response_model=list[MemoryResponse])
def list_memories(project_id: UUID, session: Session = Depends(get_session)):
    return session.exec(select(Memory).where(Memory.project_id == project_id).order_by(Memory.created_at.asc())).all()


@app.post("/api/projects/{project_id}/generate-article", response_model=ArticleResponse)
async def generate_article_endpoint(
    project_id: UUID,
    session: Session = Depends(get_session),
    provider: ModelProvider = Depends(get_provider),
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        _invalidate_from(project_id, "article", session)
        _mark_running(project, "article", session)
        article = await _generate_article(project, provider, session)
        _mark_complete(project, "article", session)
    except ValueError as exc:
        _mark_failed(project, "article", session)
        raise HTTPException(status_code=400, detail=str(exc))
    return ArticleResponse.model_validate(article)


@app.get("/api/projects/{project_id}/article", response_model=ArticleResponse)
def get_article(project_id: UUID, session: Session = Depends(get_session)):
    article = session.exec(select(Article).where(Article.project_id == project_id).order_by(Article.created_at.desc())).first()
    if not article:
        raise HTTPException(status_code=404, detail="No article found. Generate article first.")
    return ArticleResponse.model_validate(article)


def _plan_to_response(plan: IDPSPlan) -> IDPSPlanResponse:
    return IDPSPlanResponse(
        problem_restatement=plan.problem_restatement,
        constraints=plan.constraints,
        assumptions=plan.assumptions,
        dimensions=[IDPSDimensionSchema(**d) for d in plan.dimensions],
        initial_search_queries=plan.initial_search_queries,
        risk_flags=plan.risk_flags,
    )
