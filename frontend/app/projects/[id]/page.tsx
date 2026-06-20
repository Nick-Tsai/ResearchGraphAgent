"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { preprocessMath } from "@/lib/math-utils";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import {
  getProject,
  getPlan,
  runIDPS,
  listSources,
  listEvidence,
  buildGraph,
  getGraph,
  expandNode,
  challengeNode,
  premiumReview,
  listMemories,
  generateArticle,
  getArticle,
} from "@/lib/api";
import type {
  Project,
  IDPSPlan,
  Source,
  Evidence,
  GraphNode,
  GraphEdge,
  ExpandNodeResult,
  ChallengeNodeResult,
  PremiumReviewResult,
  PremiumReviewEdit,
  MemoryItem,
  Article,
  WorkflowNode,
} from "@/lib/types";

type Tab = "plan" | "sources" | "evidence" | "graph" | "review" | "article";

const AUDIENCE: Record<string, string> = {
  elementary: "🔤 小学",
  middle: "📘 初中",
  high: "📚 高中",
  college: "🎓 大学",
};

const TYPE_COLORS: Record<string, string> = {
  dimension: "border-indigo-200 bg-indigo-50 text-indigo-700",
  claim: "border-emerald-200 bg-emerald-50 text-emerald-700",
  question: "border-amber-200 bg-amber-50 text-amber-700",
  gap: "border-orange-200 bg-orange-50 text-orange-700",
  contradiction: "border-rose-200 bg-rose-50 text-rose-700",
};

const NODE_LABELS: Record<WorkflowNode, string> = {
  draft: "Draft",
  plan: "Plan",
  sources: "Sources",
  evidence: "Evidence",
  graph: "Graph",
  review: "Review",
  article: "Article",
};

function getErrorMessage(error: unknown, fallback = "Request failed"): string {
  return error instanceof Error ? error.message : fallback;
}

function statusBadgeClass(project: Project): string {
  if (project.status === "failed") return "bg-red-100 text-red-700";
  if (project.progress_state === "running") return "bg-yellow-100 text-yellow-700 animate-pulse";
  if (project.current_node === "draft") return "bg-gray-100 text-gray-600";
  return "bg-green-100 text-green-700";
}

export default function ProjectDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [plan, setPlan] = useState<IDPSPlan | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [tab, setTab] = useState<Tab>("plan");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [activeStage, setActiveStage] = useState<WorkflowNode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [expandResult, setExpandResult] = useState<ExpandNodeResult | null>(null);
  const [challengeResult, setChallengeResult] = useState<ChallengeNodeResult | null>(null);
  const [reviewResult, setReviewResult] = useState<PremiumReviewResult | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const p = await getProject(id);
      setProject(p);
      try { setPlan(await getPlan(id)); } catch { setPlan(null); }
      try { setSources(await listSources(id)); } catch { setSources([]); }
      try { setEvidence(await listEvidence(id)); } catch { setEvidence([]); }
      try {
        const g = await getGraph(id);
        setGraphNodes(g.nodes);
        setGraphEdges(g.edges);
      } catch {
        setGraphNodes([]);
        setGraphEdges([]);
      }
      try { setMemories(await listMemories(id)); } catch { setMemories([]); }
      try { setArticle(await getArticle(id)); } catch { setArticle(null); }
    } catch (e: unknown) {
      setError(getErrorMessage(e, "Failed to load"));
    } finally {
      setLoading(false);
      setBusy(false);
      setActiveStage(null);
    }
  }, [id]);

  useEffect(() => {
    const timeout = window.setTimeout(() => { void loadAll(); }, 0);
    return () => { window.clearTimeout(timeout); };
  }, [loadAll]);

  function clearFrom(stage: WorkflowNode) {
    if (stage === "plan") {
      setPlan(null);
      setSources([]);
      setEvidence([]);
      setGraphNodes([]);
      setGraphEdges([]);
      setReviewResult(null);
      setMemories([]);
      setArticle(null);
      setSelectedNode(null);
      return;
    }
    if (stage === "sources") {
      setSources([]);
      setEvidence([]);
      setGraphNodes([]);
      setGraphEdges([]);
      setReviewResult(null);
      setMemories((prev) => prev.filter((m) => m.stage === "plan"));
      setArticle(null);
      setSelectedNode(null);
      return;
    }
    if (stage === "evidence") {
      setEvidence([]);
      setGraphNodes([]);
      setGraphEdges([]);
      setReviewResult(null);
      setMemories((prev) => prev.filter((m) => m.stage === "plan" || m.stage === "sources"));
      setArticle(null);
      setSelectedNode(null);
      return;
    }
    if (stage === "graph") {
      setGraphNodes([]);
      setGraphEdges([]);
      setReviewResult(null);
      setMemories((prev) => prev.filter((m) => ["plan", "sources", "evidence"].includes(m.stage)));
      setArticle(null);
      setSelectedNode(null);
      return;
    }
    if (stage === "review") {
      setReviewResult(null);
      setMemories((prev) => prev.filter((m) => ["plan", "sources", "evidence", "graph"].includes(m.stage)));
      setArticle(null);
      return;
    }
    if (stage === "article") {
      setArticle(null);
      setMemories((prev) => prev.filter((m) => m.stage !== "article"));
    }
  }

  async function runStage(stage: WorkflowNode, action: () => Promise<unknown>, nextTab: Tab) {
    setBusy(true);
    setActiveStage(stage);
    setError(null);
    clearFrom(stage);
    try {
      const result = await action();
      if (stage === "review" && result) setReviewResult(result as PremiumReviewResult);
      await loadAll();
      setTab(nextTab);
      setBusy(false);
      setActiveStage(null);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
      setBusy(false);
      setActiveStage(null);
    }
  }

  if (loading) return <main className="flex items-center justify-center min-h-screen"><p className="text-gray-400 text-sm">Loading...</p></main>;
  if (error && !project) return <main className="flex flex-col items-center justify-center min-h-screen p-8 gap-4"><p className="text-red-600 text-sm">{error}</p><button onClick={() => router.push("/")} className="text-sm underline text-gray-500">Back</button></main>;
  if (!project) return null;

  const isRunning = project.progress_state === "running" || busy;
  const stageRunning = (stage: WorkflowNode) => (busy && activeStage === stage) || (project.current_node === stage && project.progress_state === "running");
  const hasPlan = !!plan;
  const canSearch = hasPlan && !isRunning;
  const canSummarize = sources.length > 0 && !isRunning;
  const canBuildGraph = evidence.length > 0 && !isRunning;
  const canReview = graphNodes.length > 0 && !isRunning;
  const canGenerateArticle = memories.length > 0 && !isRunning;
  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "plan", label: "研究计划" },
    { key: "sources", label: "资料", count: sources.length },
    { key: "evidence", label: "证据", count: evidence.length },
    { key: "graph", label: "Graph Explorer", count: graphNodes.length },
    { key: "review", label: "审查", count: reviewResult ? 1 : 0 },
    { key: "article", label: "文章", count: article ? 1 : 0 },
  ];

  return (
    <main className="max-w-5xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => router.push("/")} className="text-sm text-gray-400 hover:text-gray-600">&larr;</button>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold truncate">{project.topic}</h1>
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5">Node: {NODE_LABELS[project.current_node]}</span>
            <span className="rounded-full border border-gray-200 bg-white px-2 py-0.5">State: {project.progress_state}</span>
          </div>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBadgeClass(project)}`}>{project.status}</span>{project.audience_level && <span className="text-xs px-1.5 py-0.5 rounded-full bg-purple-50 text-purple-600 ml-2">{AUDIENCE[project.audience_level] || project.audience_level}</span>}<span className="text-xs text-gray-300 mx-2">|</span><span className="text-xs text-gray-400 font-mono">{((project.total_tokens_used || 0) / 1000).toFixed(0)}k / {((project.token_budget || 200000) / 1000).toFixed(0)}k tokens</span>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>}
      {isRunning && <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">Running {NODE_LABELS[activeStage ?? project.current_node]}... downstream data will be regenerated.</div>}

      <div className="flex flex-wrap gap-2 mb-6">
        <button onClick={() => void runStage("plan", () => runIDPS(id), "plan")} disabled={isRunning} className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">{stageRunning("plan") ? "Planning..." : hasPlan ? "Re-run IDPS" : "运行 IDPS"}</button>
        {hasPlan && <button onClick={() => void runStage("sources", async () => { await fetch(`${(process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api")}/projects/${id}/search`, { method: "POST" }).then(async (r) => { if (!r.ok) { const b = await r.json().catch(() => ({})); throw new Error(b.detail || r.statusText); } }); }, "sources")} disabled={!canSearch} className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">{stageRunning("sources") ? "搜索中..." : sources.length > 0 ? "重新搜索" : "1. 搜索"}</button>}
        {sources.length > 0 && <button onClick={() => void runStage("evidence", async () => { await fetch(`${(process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api")}/projects/${id}/summarize`, { method: "POST" }).then(async (r) => { if (!r.ok) { const b = await r.json().catch(() => ({})); throw new Error(b.detail || r.statusText); } }); }, "evidence")} disabled={!canSummarize} className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">{stageRunning("evidence") ? "摘要中..." : evidence.length > 0 ? "重新摘要" : "2. 摘要"}</button>}
        {evidence.length > 0 && <button onClick={() => void runStage("graph", () => buildGraph(id), "graph")} disabled={!canBuildGraph} className="px-3 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50">{stageRunning("graph") ? "构建中..." : "3. 构建图谱"}</button>}
        {graphNodes.length > 0 && <button onClick={() => void runStage("review", () => premiumReview(id), "review")} disabled={!canReview} className="px-3 py-1.5 bg-purple-600 text-white text-xs font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50">{stageRunning("review") ? "审查中..." : "高级审查"}</button>}
        {memories.length > 0 && <button onClick={() => void runStage("article", () => generateArticle(id), "article")} disabled={!canGenerateArticle} className="px-3 py-1.5 bg-slate-700 text-white text-xs font-medium rounded-lg hover:bg-slate-800 disabled:opacity-50">{stageRunning("article") ? "Writing..." : article ? "Re-generate Article" : "生成文章"}</button>}
      </div>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${tab === t.key ? "border-blue-600 text-blue-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t.label}{t.count !== undefined && t.count > 0 && <span className="ml-1 text-gray-400">({t.count})</span>}
          </button>
        ))}
      </div>

      {tab === "plan" && !plan && <div className="flex flex-col items-center gap-4 py-16 border border-dashed border-gray-300 rounded-lg"><p className="text-gray-500 text-sm">No plan yet. Run IDPS to get started.</p></div>}
      {tab === "plan" && plan && <PlanView plan={plan} />}
      {tab === "sources" && <SourcesView sources={sources} />}
      {tab === "evidence" && <EvidenceView evidence={evidence} sources={sources} />}
      {tab === "graph" && (
        <GraphTreeView
          nodes={graphNodes}
          edges={graphEdges}
          sources={sources}
          evidence={evidence}
          selectedNode={selectedNode}
          onSelectNode={(n) => { setSelectedNode(n); setExpandResult(null); setChallengeResult(null); }}
          expandResult={expandResult}
          challengeResult={challengeResult}
          busy={isRunning}
          onExpand={() => { if (!selectedNode) return; void (async () => { setBusy(true); setError(null); try { setExpandResult(await expandNode(id, selectedNode.id)); } catch (e: unknown) { setError(getErrorMessage(e)); } finally { setBusy(false); } })(); }}
          onChallenge={() => { if (!selectedNode) return; void (async () => { setBusy(true); setError(null); try { setChallengeResult(await challengeNode(id, selectedNode.id)); } catch (e: unknown) { setError(getErrorMessage(e)); } finally { setBusy(false); } })(); }}
        />
      )}
      {tab === "review" && <ReviewView review={reviewResult} />}
      {tab === "article" && <ArticleView memories={memories} article={article} sources={sources} evidence={evidence} reviewResult={reviewResult} />}
    </main>
  );
}

function Md({ children, className }: { children: string; className?: string }) {
  if (!children) return null;
  const processed = preprocessMath(children);
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={{
        p: ({node, ...props}: any) => <p className="mb-1 last:mb-0" {...props} />,
        ul: ({node, ...props}: any) => <ul className="list-disc pl-4 mb-1 space-y-0.5" {...props} />,
        ol: ({node, ...props}: any) => <ol className="list-decimal pl-4 mb-1 space-y-0.5" {...props} />,
        li: ({node, ...props}: any) => <li className="text-inherit" {...props} />,
        strong: ({node, ...props}: any) => <strong className="font-semibold" {...props} />,
        code: ({node, className, ...props}: any) => {
          const isInline = !className;
          return isInline
            ? <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono" {...props} />
            : <code className="block bg-gray-900 text-gray-100 p-2 rounded-lg text-xs overflow-x-auto" {...props} />;
        },
        pre: ({node, ...props}: any) => <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg text-xs overflow-x-auto my-2" {...props} />,
        img: ({node, ...props}: any) => <img className="rounded-lg border border-gray-200 my-3 max-w-full" loading="lazy" {...props} />,
        blockquote: ({node, ...props}: any) => <blockquote className="border-l-3 border-blue-300 pl-3 italic text-gray-600 my-2" {...props} />,
        a: ({node, ...props}: any) => <a className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
        h1: ({node, ...props}: any) => <h1 className="text-base font-bold mt-3 mb-1" {...props} />,
        h2: ({node, ...props}: any) => <h2 className="text-sm font-bold mt-2 mb-1" {...props} />,
        h3: ({node, ...props}: any) => <h3 className="text-xs font-bold mt-2 mb-0.5" {...props} />,
      }}>
        {processed}
      </ReactMarkdown>
    </div>
  );
}

function PlanView({ plan }: { plan: IDPSPlan }) {
  return (
    <div className="space-y-5">
      <section>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Problem</h2>
        <p className="text-gray-800 text-sm">{plan.problem_restatement}</p>
      </section>
      <div className="grid grid-cols-2 gap-4">
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Constraints</h2>
          <ul className="list-disc pl-5 space-y-0.5">{plan.constraints.map((c, i) => <li key={i} className="text-sm text-gray-700">{c}</li>)}</ul>
        </section>
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Assumptions</h2>
          <ul className="list-disc pl-5 space-y-0.5">{plan.assumptions.map((a, i) => <li key={i} className="text-sm text-gray-700">{a}</li>)}</ul>
        </section>
      </div>
      <section>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Dimensions</h2>
        <div className="space-y-3">
          {plan.dimensions.map((d, i) => (
            <div key={i} className="border border-gray-200 rounded-lg p-3">
              <h3 className="font-medium text-sm">{d.name}</h3>
              <p className="text-xs text-gray-500 mt-0.5 mb-2">{d.description}</p>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-xs text-gray-400 mb-0.5">Subquestions</p>
                  <ul className="list-disc pl-4 space-y-0.5">{d.subquestions.map((q, j) => <li key={j} className="text-xs text-gray-700">{q}</li>)}</ul>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mb-0.5">Falsification</p>
                  <ul className="list-disc pl-4 space-y-0.5">{d.falsification_tests.map((f, j) => <li key={j} className="text-xs text-gray-700">{f}</li>)}</ul>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Risk Flags</h2>
        <ul className="space-y-0.5">{plan.risk_flags.map((r, i) => <li key={i} className="flex gap-2 text-sm"><span className="text-amber-500 shrink-0">&#9888;</span><span className="text-gray-700">{r}</span></li>)}</ul>
      </section>
    </div>
);
}

function GraphTreeView({ nodes, edges, sources, evidence, selectedNode, onSelectNode, expandResult, challengeResult, busy, onExpand, onChallenge }: { nodes: GraphNode[]; edges: GraphEdge[]; sources: Source[]; evidence: Evidence[]; selectedNode: GraphNode | null; onSelectNode: (n: GraphNode | null) => void; expandResult: ExpandNodeResult | null; challengeResult: ChallengeNodeResult | null; busy: boolean; onExpand: () => void; onChallenge: () => void; }) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const toggleCollapse = (id: string, e: React.MouseEvent) => { e.stopPropagation(); setCollapsed((prev) => ({ ...prev, [id]: !prev[id] })); };
  if (nodes.length === 0) return <div className="text-center py-16 text-gray-400 text-sm">No graph nodes built yet. Click Build Graph.</div>;
  const dimensions = nodes.filter((n) => n.node_type === "dimension");
  const nonDimensions = nodes.filter((n) => n.node_type !== "dimension");
  const dimGroups: Record<string, GraphNode[]> = {};
  dimensions.forEach((d) => { dimGroups[d.id] = []; });
  const orphans: GraphNode[] = [];
  nonDimensions.forEach((n) => {
    const connectedDim = edges.find((e) => (e.source_node_id === n.id && dimGroups[e.target_node_id]) || (e.target_node_id === n.id && dimGroups[e.source_node_id]));
    if (connectedDim) {
      const dimId = dimGroups[connectedDim.source_node_id] ? connectedDim.source_node_id : connectedDim.target_node_id;
      dimGroups[dimId].push(n);
    } else {
      orphans.push(n);
    }
  });
  const srcMap: Record<string, Source> = {};
  sources.forEach((s) => { srcMap[s.id] = s; });
  const selectedEvidence = selectedNode ? evidence.filter((ev) => selectedNode.evidence_ids.includes(ev.id)) : [];
  return (
    <div className="flex gap-4 items-start">
      <div className="flex-1 min-w-0 border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
        <div className="bg-gray-50 border-b border-gray-200 px-4 py-2.5 flex items-center justify-between"><span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Research Tree Outline</span><span className="text-xs text-gray-400">{nodes.length} items</span></div>
        <div className="divide-y divide-gray-100">
          {dimensions.map((d) => {
            const isCollapsed = !!collapsed[d.id];
            const children = dimGroups[d.id] || [];
            const isSel = selectedNode?.id === d.id;
            return (
              <div key={d.id} className="transition-colors">
                <div onClick={() => onSelectNode(d)} className={`group flex items-center px-4 py-3 cursor-pointer hover:bg-slate-50 gap-2.5 ${isSel ? "bg-indigo-50/50" : ""}`}>
                  <button onClick={(e) => toggleCollapse(d.id, e)} className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600 transition">{children.length > 0 ? (isCollapsed ? "▶" : "▼") : "•"}</button>
                  <div className="flex-1 min-w-0"><div className="flex items-center gap-2"><span className="text-xs font-semibold px-2 py-0.5 rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700 uppercase tracking-wider text-[10px]">Dimension</span><h4 className="text-sm font-semibold text-gray-900 truncate">{d.title}</h4></div><p className="text-xs text-gray-500 mt-1 truncate">{d.summary}</p></div>
                  <span className="text-xs font-mono text-gray-400">cf {d.confidence.toFixed(1)}</span>
                </div>
                {!isCollapsed && children.length > 0 && <div className="bg-slate-50/20 border-t border-gray-50 pl-8 pr-4 py-1 space-y-1 relative"><div className="absolute left-[26px] top-0 bottom-0 w-px bg-gray-200" />{children.map((c) => { const isChildSel = selectedNode?.id === c.id; const toneClass = TYPE_COLORS[c.node_type] || "border-slate-200 bg-slate-50 text-slate-700"; return <div key={c.id} onClick={() => onSelectNode(c)} className={`group flex items-start p-3 rounded-xl border cursor-pointer transition ${isChildSel ? "bg-white border-indigo-300 shadow-sm" : "border-transparent hover:border-gray-200 hover:bg-white"}`}><div className="flex-1 min-w-0 pr-3"><div className="flex items-center gap-2 flex-wrap"><span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded-full border uppercase tracking-wider ${toneClass}`}>{c.node_type}</span><h5 className="text-xs font-semibold text-gray-900 truncate">{c.title}</h5></div><Md className="text-xs text-slate-600 mt-1 line-clamp-2">{c.summary}</Md></div><span className="text-xs font-mono text-slate-400 shrink-0 self-start mt-0.5">cf {c.confidence.toFixed(1)}</span></div> })}</div>}
              </div>
            );
          })}
          {orphans.length > 0 && <div className="p-4 bg-gray-50/50"><h5 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Uncategorized Findings</h5><div className="space-y-1">{orphans.map((o) => <div key={o.id} onClick={() => onSelectNode(o)} className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer hover:bg-white transition ${selectedNode?.id === o.id ? "bg-white border-indigo-300 shadow-sm" : "border-gray-200 bg-white/70"}`}><div><span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-gray-100 text-gray-600 border border-gray-200 mr-2">{o.node_type}</span><span className="text-xs font-medium text-gray-800">{o.title}</span></div><span className="text-xs font-mono text-gray-400">cf {o.confidence.toFixed(1)}</span></div>)}</div></div>}
        </div>
      </div>

      {selectedNode && (
        <div className="w-72 shrink-0 sticky top-4 border border-gray-200 rounded-xl p-4 bg-white shadow-sm space-y-4 max-h-[calc(100vh-120px)] overflow-y-auto">
          <div>
            <div className="flex items-center gap-2 mb-1.5"><span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider ${TYPE_COLORS[selectedNode.node_type] || ""}`}>{selectedNode.node_type}</span><span className="text-xs text-gray-400">Confidence {selectedNode.confidence.toFixed(1)}</span></div>
            <h3 className="text-sm font-semibold text-gray-900 leading-snug">{selectedNode.title}</h3>
            <Md className="text-xs text-gray-600 mt-2 leading-relaxed bg-slate-50 rounded-lg p-2.5 border border-slate-100">{selectedNode.summary}</Md>
          </div>
          <div className="flex gap-2"><button onClick={onExpand} disabled={busy} className="flex-1 py-1.5 px-3 bg-blue-50 text-blue-700 text-xs font-semibold rounded-lg hover:bg-blue-100 disabled:opacity-50 transition">Expand</button><button onClick={onChallenge} disabled={busy} className="flex-1 py-1.5 px-3 bg-amber-50 text-amber-700 text-xs font-semibold rounded-lg hover:bg-amber-100 disabled:opacity-50 transition">Challenge</button></div>
          {expandResult && <div className="border-t border-gray-100 pt-3 space-y-2 text-xs"><p className="font-semibold text-slate-700 flex items-center gap-1"><span className="w-1.5 h-1.5 bg-blue-500 rounded-full" /> Expansion Analysis</p>{expandResult.summary && <Md className="text-slate-600 italic bg-blue-50/40 p-2 rounded-lg text-xs">{expandResult.summary}</Md>}{expandResult.subquestions.length > 0 && <div><p className="text-gray-400 font-medium mb-1">Subquestions</p><ul className="list-disc pl-4 space-y-1">{expandResult.subquestions.map((q, i) => <li key={i} className="text-slate-700">{q}</li>)}</ul></div>}</div>}
          {challengeResult && <div className="border-t border-gray-100 pt-3 space-y-2 text-xs"><p className="font-semibold text-amber-700 flex items-center gap-1"><span className="w-1.5 h-1.5 bg-amber-500 rounded-full" /> Challenge Analysis</p>{challengeResult.summary && <Md className="text-slate-600 italic bg-amber-50/40 p-2 rounded-lg text-xs">{challengeResult.summary}</Md>}{challengeResult.counterarguments.length > 0 && <div><p className="text-amber-600 font-medium mb-1">Counterarguments</p><ul className="list-disc pl-4 space-y-1 text-amber-900">{challengeResult.counterarguments.map((c, i) => <li key={i}>{c}</li>)}</ul></div>}</div>}
          {selectedEvidence.length > 0 && <div className="border-t border-gray-100 pt-3 space-y-2 text-xs"><p className="font-semibold text-slate-700">Evidence Trail ({selectedEvidence.length})</p><div className="space-y-2">{selectedEvidence.slice(0, 3).map((ev) => { const src = srcMap[ev.source_id]; return <div key={ev.id} className="p-2 border border-gray-100 rounded bg-slate-50/40 space-y-1"><Md className="text-gray-800 leading-snug text-xs">{ev.claim}</Md>{ev.support_text && <p className="text-gray-400 italic font-light">&ldquo;{ev.support_text.slice(0, 80)}...&rdquo;</p>}{src && <a href={src.url} target="_blank" rel="noopener noreferrer" className="block text-[11px] text-blue-500 hover:underline truncate">{src.title}</a>}</div> })}</div></div>}
          <button onClick={() => onSelectNode(null)} className="w-full py-1 text-center text-xs text-slate-400 hover:text-slate-600 hover:underline border-t border-gray-100 pt-3">Deselect Item</button>
        </div>
      )}
    </div>
  );
}

function ReviewView({ review }: { review: PremiumReviewResult | null }) {
  if (!review) return <div className="text-center py-16 text-gray-400 text-sm">No review yet.</div>
  return <div className="space-y-5"><section><h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">Overall Assessment</h2><p className="text-gray-800 text-sm">{review.overall_assessment}</p></section>{review.critical_issues.length > 0 && <section><h2 className="text-sm font-semibold text-red-600 uppercase tracking-wide mb-2">Critical Issues</h2><ul className="list-disc pl-5 space-y-1">{review.critical_issues.map((i, idx) => <li key={idx} className="text-sm text-gray-700">{i}</li>)}</ul></section>}{review.missing_dimensions.length > 0 && <section><h2 className="text-sm font-semibold text-amber-600 uppercase tracking-wide mb-2">Missing Dimensions</h2><ul className="list-disc pl-5 space-y-1">{review.missing_dimensions.map((d, idx) => <li key={idx} className="text-sm text-gray-700">{d}</li>)}</ul></section>}{review.contradictions_to_resolve.length > 0 && <section><h2 className="text-sm font-semibold text-orange-600 uppercase tracking-wide mb-2">Contradictions</h2><ul className="list-disc pl-5 space-y-1">{review.contradictions_to_resolve.map((c, idx) => <li key={idx} className="text-sm text-gray-700">{c}</li>)}</ul></section>}{review.recommended_node_edits.length > 0 && <section><h2 className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-2">Recommended Edits</h2><div className="space-y-2">{review.recommended_node_edits.map((e: PremiumReviewEdit, idx: number) => <div key={idx} className="border border-gray-200 rounded-lg p-3"><p className="text-sm font-medium">{e.node_title}</p><p className="text-sm text-gray-600">{e.edit}</p></div>)}</div></section>}{review.next_research_actions.length > 0 && <section><h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">Next Steps</h2><ul className="list-disc pl-5 space-y-1">{review.next_research_actions.map((a, idx) => <li key={idx} className="text-sm text-gray-700">{a}</li>)}</ul></section>}</div>
}

function ArticleView({ memories, article, sources, evidence, reviewResult }: { memories: MemoryItem[]; article: Article | null; sources: Source[]; evidence: Evidence[]; reviewResult: PremiumReviewResult | null }) {
  const [openSection, setOpenSection] = useState<string | null>(null);
  const toggle = (s: string) => setOpenSection(openSection === s ? null : s);

  const srcMap: Record<string, Source> = {};
  sources.forEach(s => { srcMap[s.id] = s; });

  if (!article) {
    return <div className="text-center py-16 text-gray-400 text-sm">尚未生成文章。请先运行 "生成文章"。</div>
  }

  return (
    <div className="space-y-6">
      {/* Hero: Integrated Article */}
      <section>
        <div className="border border-gray-200 rounded-xl p-6 bg-white shadow-sm">
          <h2 className="text-lg font-bold text-gray-900 mb-4">{article.title}</h2>
          <Md className="text-sm text-gray-700 leading-7">{article.content}</Md>
          <p className="text-xs text-gray-400 mt-4 pt-4 border-t border-gray-100">
            生成时间：{new Date(article.created_at).toLocaleString("zh-CN")}
          </p>
        </div>
      </section>

      {/* Collapsible Research Trail */}
      <section className="border border-gray-200 rounded-xl bg-white shadow-sm overflow-hidden">
        <h3 className="text-sm font-semibold text-gray-600 px-5 py-3 bg-gray-50 border-b border-gray-200">📚 研究资料与引用来源</h3>

        {/* Memories */}
        <div className="border-b border-gray-100 last:border-b-0">
          <button onClick={() => toggle("memories")} className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50 transition">
            <span className="text-sm font-medium text-gray-700">📝 研究记忆 ({memories.length})</span>
            <span className="text-xs text-gray-400">{openSection === "memories" ? "收起" : "展开"}</span>
          </button>
          {openSection === "memories" && <div className="px-5 pb-4 space-y-2">
            {memories.map(m => <div key={m.id} className="text-xs border border-gray-100 rounded-lg p-2.5 bg-gray-50/50"><span className="font-semibold text-gray-500 mr-2">[{m.stage}]</span><span className="text-gray-600">{m.content.slice(0, 200)}{m.content.length > 200 ? "…" : ""}</span></div>)}
          </div>}
        </div>

        {/* Sources */}
        <div className="border-b border-gray-100 last:border-b-0">
          <button onClick={() => toggle("sources")} className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50 transition">
            <span className="text-sm font-medium text-gray-700">📎 资料来源 ({sources.length})</span>
            <span className="text-xs text-gray-400">{openSection === "sources" ? "收起" : "展开"}</span>
          </button>
          {openSection === "sources" && <div className="px-5 pb-4 space-y-1.5">
            {sources.slice(0, 20).map(s => <div key={s.id} className="text-xs"><a href={s.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{s.title.slice(0, 80)}</a><span className="text-gray-400 ml-2">{s.publisher}</span></div>)}
          </div>}
        </div>

        {/* Evidence */}
        <div className="border-b border-gray-100 last:border-b-0">
          <button onClick={() => toggle("evidence")} className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50 transition">
            <span className="text-sm font-medium text-gray-700">🔍 审查报告{reviewResult ? " (1)" : ""}</span>
            <span className="text-xs text-gray-400">{openSection === "evidence" ? "收起" : "展开"}</span>
          </button>
          {openSection === "evidence" && <div className="px-5 pb-4 space-y-2">
            {evidence.slice(0, 15).map(ev => {
              const s = srcMap[ev.source_id];
              return <div key={ev.id} className="text-xs border border-gray-100 rounded-lg p-2.5 bg-gray-50/50">
                <p className="text-gray-800">{ev.claim}</p>
                <div className="flex gap-2 mt-1.5 flex-wrap items-center">
                  <span className="text-gray-400">置信度 {ev.confidence.toFixed(1)}</span>
                  {s && <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{s.title.slice(0, 40)}</a>}
                </div>
              </div>
            })}
          </div>}
        </div>

        {/* Review */}
        {reviewResult && <div className="border-b border-gray-100 last:border-b-0">
          <button onClick={() => toggle("review")} className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50 transition">
            <span className="text-sm font-medium text-gray-700">🔍 审查报告</span>
            <span className="text-xs text-gray-400">{openSection === "review" ? "收起" : "展开"}</span>
          </button>
          {openSection === "review" && <div className="px-5 pb-4 space-y-2 text-xs">
            {reviewResult.overall_assessment && <div className="p-2.5 bg-purple-50/50 rounded-lg border border-purple-100"><Md className="text-gray-700">{reviewResult.overall_assessment}</Md></div>}
            {reviewResult.critical_issues?.length > 0 && <div className="p-2.5 bg-red-50/50 rounded-lg border border-red-100"><p className="font-semibold text-red-600 mb-1">关键问题</p><ul className="list-disc pl-4 space-y-0.5">{reviewResult.critical_issues.map((i: string, idx: number) => <li key={idx} className="text-red-800">{i}</li>)}</ul></div>}
            {reviewResult.next_research_actions?.length > 0 && <div className="p-2.5 bg-blue-50/50 rounded-lg border border-blue-100"><p className="font-semibold text-blue-600 mb-1">后续行动</p><ul className="list-disc pl-4 space-y-0.5">{reviewResult.next_research_actions.map((a: string, idx: number) => <li key={idx} className="text-blue-800">{a}</li>)}</ul></div>}
          </div>}
        </div>}</section>
    </div>
  );
}

function SourcesView({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return <div className="text-center py-16 text-gray-400 text-sm">暂无资料来源。</div>;
  return <div className="space-y-3">{sources.map((s) => <div key={s.id} className="border border-gray-200 rounded-lg p-3"><h3 className="text-sm font-medium text-blue-700 truncate">{s.title}</h3><p className="text-xs text-gray-500 mt-0.5">{s.publisher}{s.url && <a href={s.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-gray-400 hover:text-blue-600 underline truncate">{s.url}</a>}</p><p className="text-xs text-gray-600 mt-1">{s.extracted_text.slice(0, 300)}</p><div className="flex gap-2 mt-2"><span className={`text-xs px-1.5 py-0.5 rounded ${s.source_type === "primary" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>{s.source_type}</span><span className="text-xs text-gray-400">query: {s.search_query}</span></div></div>)}</div>;
}

function EvidenceView({ evidence, sources }: { evidence: Evidence[]; sources: Source[] }) {
  const srcMap: Record<string, Source> = {};
  sources.forEach((s) => { srcMap[s.id] = s; });
  if (evidence.length === 0) return <div className="text-center py-16 text-gray-400 text-sm">暂无证据。</div>;
  return <div className="space-y-3">{evidence.map((e) => { const src = srcMap[e.source_id]; return <div key={e.id} className="border border-gray-200 rounded-lg p-3"><p className="text-sm font-medium text-gray-900">{e.claim}</p>{e.support_text && <p className="text-xs text-gray-500 mt-1 italic">&ldquo;{e.support_text.slice(0, 200)}&rdquo;</p>}<div className="flex gap-2 mt-2 flex-wrap"><span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">confidence: {e.confidence.toFixed(2)}</span>{e.tags.map((t, i) => <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{t}</span>)}{src && <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-xs px-1.5 py-0.5 rounded bg-gray-50 text-gray-500 hover:text-blue-600 underline">{src.title.slice(0, 40)}</a>}</div></div>; })}</div>;
}
