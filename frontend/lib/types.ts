export type ProjectStatus = "draft" | "running" | "complete" | "failed";
export type ProgressState = "running" | "complete" | "failed";
export type WorkflowNode = "draft" | "plan" | "sources" | "evidence" | "graph" | "review" | "article";

export interface Project {
  id: string;
  topic: string;
  status: ProjectStatus;
  current_node: WorkflowNode;
  progress_state: ProgressState;
  total_tokens_used: number;
  token_budget: number;  created_at: string;
  audience_level: string;  updated_at: string;
}

export interface IDPSDimension {
  name: string;
  description: string;
  subquestions: string[];
  falsification_tests: string[];
}

export interface IDPSPlan {
  problem_restatement: string;
  constraints: string[];
  assumptions: string[];
  dimensions: IDPSDimension[];
  initial_search_queries: string[];
  risk_flags: string[];
}

export interface Source {
  id: string;
  project_id: string;
  url: string;
  title: string;
  publisher: string;
  source_type: string;
  reliability_score: number;
  extracted_text: string;
  search_query: string;
  created_at: string;
}

export interface Evidence {
  id: string;
  project_id: string;
  source_id: string;
  claim: string;
  support_text: string;
  confidence: number;
  tags: string[];
  created_at: string;
}

export interface RunPipelineResult {
  sources_count: number;
  evidence_count: number;
}

export interface GraphNode {
  id: string;
  title: string;
  summary: string;
  node_type: string;
  confidence: number;
  source_ids: string[];
  evidence_ids: string[];
  parent_node_id: string | null;
  x: number | null;
  y: number | null;
}

export interface GraphEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relation: string;
  confidence: number;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ExpandNodeSearchResult {
  title: string;
  url: string;
  snippet: string;
}

export interface ExpandNodeResult {
  node_id: string;
  subquestions: string[];
  counterarguments: string[];
  missing_evidence: string[];
  search_queries: string[];
  summary: string;
  search_results: ExpandNodeSearchResult[];
}

export interface ChallengeNodeResult {
  node_id: string;
  weak_assumptions: string[];
  missing_evidence: string[];
  counterarguments: string[];
  alternate_explanations: string[];
  search_queries: string[];
  summary: string;
}

export interface PremiumReviewEdit {
  node_title: string;
  edit: string;
}

export interface PremiumReviewResult {
  overall_assessment: string;
  critical_issues: string[];
  missing_dimensions: string[];
  contradictions_to_resolve: string[];
  recommended_node_edits: PremiumReviewEdit[];
  next_research_actions: string[];
  confidence_improvement: number;
}

export interface MemoryItem {
  id: string;
  project_id: string;
  stage: WorkflowNode;
  content: string;
  created_at: string;
}

export interface Article {
  id: string;
  project_id: string;
  title: string;
  content: string;
  created_at: string;
}
