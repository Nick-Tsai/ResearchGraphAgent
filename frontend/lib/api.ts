import type {
  Project,
  IDPSPlan,
  Source,
  Evidence,
  RunPipelineResult,
  GraphResponse,
  ExpandNodeResult,
  ChallengeNodeResult,
  PremiumReviewResult,
  MemoryItem,
  Article,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api";

async function request<T>(url: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const timeoutMs = options?.timeoutMs;
  const controller = timeoutMs ? new AbortController() : undefined;
  const signal = controller?.signal;

  if (controller) {
    setTimeout(() => controller.abort(), timeoutMs);
  }

  const res = await fetch(url, { ...options, signal });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail || res.statusText;
    throw new Error(detail);
  }
  return res.json();
}

export function listProjects(): Promise<Project[]> {
  return request<Project[]>(`${API_BASE}/projects`);
}

export function createProject(topic: string): Promise<Project> {
  return request<Project>(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
}

export function getProject(id: string): Promise<Project> {
  return request<Project>(`${API_BASE}/projects/${id}`);
}

export function runIDPS(projectId: string): Promise<IDPSPlan> {
  return request<IDPSPlan>(`${API_BASE}/projects/${projectId}/run-idps`, { method: "POST" });
}

export function getPlan(projectId: string): Promise<IDPSPlan> {
  return request<IDPSPlan>(`${API_BASE}/projects/${projectId}/plan`);
}

export function runPipeline(projectId: string): Promise<RunPipelineResult> {
  return request<RunPipelineResult>(`${API_BASE}/projects/${projectId}/run-pipeline`, {
    method: "POST",
    timeoutMs: 120_000,
  });
}

export function listSources(projectId: string): Promise<Source[]> {
  return request<Source[]>(`${API_BASE}/projects/${projectId}/sources`);
}

export function listEvidence(projectId: string): Promise<Evidence[]> {
  return request<Evidence[]>(`${API_BASE}/projects/${projectId}/evidence`);
}

export function buildGraph(projectId: string): Promise<GraphResponse> {
  return request<GraphResponse>(`${API_BASE}/projects/${projectId}/build-graph`, {
    method: "POST",
    timeoutMs: 180_000,
  });
}

export function getGraph(projectId: string): Promise<GraphResponse> {
  return request<GraphResponse>(`${API_BASE}/projects/${projectId}/graph`);
}

export function expandNode(projectId: string, nodeId: string): Promise<ExpandNodeResult> {
  return request<ExpandNodeResult>(`${API_BASE}/projects/${projectId}/nodes/${nodeId}/expand`, { method: "POST" });
}

export function challengeNode(projectId: string, nodeId: string): Promise<ChallengeNodeResult> {
  return request<ChallengeNodeResult>(`${API_BASE}/projects/${projectId}/nodes/${nodeId}/challenge`, { method: "POST" });
}

export function premiumReview(projectId: string): Promise<PremiumReviewResult> {
  return request<PremiumReviewResult>(`${API_BASE}/projects/${projectId}/review`, { method: "POST", timeoutMs: 60_000 });
}

export function listMemories(projectId: string): Promise<MemoryItem[]> {
  return request<MemoryItem[]>(`${API_BASE}/projects/${projectId}/memories`);
}

export function generateArticle(projectId: string): Promise<Article> {
  return request<Article>(`${API_BASE}/projects/${projectId}/generate-article`, {
    method: "POST",
    timeoutMs: 120_000,
  });
}

export function getArticle(projectId: string): Promise<Article> {
  return request<Article>(`${API_BASE}/projects/${projectId}/article`);
}
