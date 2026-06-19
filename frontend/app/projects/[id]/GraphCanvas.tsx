"use client";

import { useState, useRef, useCallback } from "react";
import type { GraphNode, GraphEdge } from "@/lib/types";

const NODE_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  dimension:  { fill: "rgba(99,102,241,0.06)", stroke: "#818cf8", text: "#a5b4fc" },
  claim:      { fill: "rgba(34,197,94,0.06)", stroke: "#4ade80", text: "#86efac" },
  question:   { fill: "rgba(234,179,8,0.06)", stroke: "#facc15", text: "#fde047" },
  gap:        { fill: "rgba(249,115,22,0.06)", stroke: "#fb923c", text: "#fdba74" },
  contradiction: { fill: "rgba(239,68,68,0.06)", stroke: "#f87171", text: "#fca5a5" },
};
const DEFAULT_COLOR = { fill: "rgba(255,255,255,0.02)", stroke: "rgba(148,163,184,0.18)", text: "#cbd5e1" };

const RELATION_COLORS: Record<string, string> = {
  supports: "#22c55e", contradicts: "#ef4444", expands: "#818cf8",
  depends_on: "#eab308", similar_to: "#9ca3af",
};

interface LayeredNode extends GraphNode {
  _x: number; _y: number;
}

const NODE_W = 185, NODE_H = 48;

function hierarchicalLayout(nodes: GraphNode[], edges: GraphEdge[], canvasW: number): LayeredNode[] {
  const result: LayeredNode[] = [];

  // Separate dimensions from other nodes
  const dims = nodes.filter(n => n.node_type === "dimension");
  const others = nodes.filter(n => n.node_type !== "dimension");

  // Build adjacency: for each non-dim node, find which dims it connects to
  const nodeToDims = new Map<string, string[]>();
  for (const n of others) {
    const dimIds: string[] = [];
    for (const e of edges) {
      if (e.source_node_id === n.id && dims.some(d => d.id === e.target_node_id)) dimIds.push(e.target_node_id);
      if (e.target_node_id === n.id && dims.some(d => d.id === e.source_node_id)) dimIds.push(e.source_node_id);
    }
    nodeToDims.set(n.id, Array.from(new Set(dimIds)));
  }

  // Assign each non-dim node to the first connected dim, or last resort to a default bucket
  const dimBuckets = new Map<string, LayeredNode[]>();
  for (const d of dims) dimBuckets.set(d.id, []);
  const orphanBucket: LayeredNode[] = [];

  for (const n of others) {
    const ln: LayeredNode = { ...n, _x: 0, _y: 0 };
    const parentDims = nodeToDims.get(n.id) || [];
    if (parentDims.length > 0) {
      dimBuckets.get(parentDims[0])!.push(ln);
    } else {
      orphanBucket.push(ln);
    }
  }

  // Layout dimensions across top
  const paddingX = 40;
  const dimSpacing = Math.min((canvasW - paddingX * 2) / Math.max(dims.length, 1), 280);
  const dimY = 50;

  dims.forEach((d, i) => {
    const x = paddingX + i * dimSpacing + dimSpacing / 2;
    result.push({ ...d, _x: x, _y: dimY });
  });

  // Layout children under each dimension
  const globalChildY = dimY + 100;

  for (let i = 0; i < dims.length; i++) {
    const bucket = dimBuckets.get(dims[i].id) || [];
    const colX = paddingX + i * dimSpacing + dimSpacing / 2;

    if (bucket.length === 0) {
      // Place a "no evidence" gap node
      result.push({
        ...dims[i], id: dims[i].id + "-gap", title: "No findings",
        summary: "No evidence assigned to this dimension.", node_type: "gap",
        confidence: 0.1, source_ids: [], evidence_ids: [], parent_node_id: dims[i].id,
        _x: colX, _y: globalChildY,
      });
      continue;
    }

    for (let j = 0; j < bucket.length; j++) {
      bucket[j]._x = colX;
      bucket[j]._y = globalChildY + j * (NODE_H + 14);
    }
    result.push(...bucket);
  }

  // Orphan nodes: place at the bottom in a row
  if (orphanBucket.length > 0) {
    const orphanY = globalChildY + 200;
    const orphanSpacing = Math.min((canvasW - paddingX * 2) / Math.max(orphanBucket.length, 1), 250);
    orphanBucket.forEach((n, i) => {
      n._x = paddingX + i * orphanSpacing + orphanSpacing / 2;
      n._y = orphanY;
    });
    result.push(...orphanBucket);
  }

  return result;
}

export default function GraphCanvas({
  nodes, edges, selectedNodeId, onSelectNodeId,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onSelectNodeId: (id: string | null) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(1);
  const panStart = useRef({ x: 0, y: 0 });
  const offsetRef = useRef({ x: 0, y: 0 });
  const scaleRef = useRef(1);

  const canvasW = Math.max(1400, nodes.length * 100);
  const canvasH = Math.max(900, nodes.length * 25);

  const layoutNodes = hierarchicalLayout(nodes, edges, canvasW);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const ns = Math.max(0.3, Math.min(2.5, scaleRef.current - e.deltaY * 0.001));
    scaleRef.current = ns;
    setScale(ns);
  }, []);

  const handleBgMouseDown = useCallback((e: React.MouseEvent) => {
    if ((e.target as Element).closest(".graph-node")) return;
    panStart.current = { x: e.clientX - offsetRef.current.x, y: e.clientY - offsetRef.current.y };
    const onMove = (ev: MouseEvent) => {
      offsetRef.current = { x: ev.clientX - panStart.current.x, y: ev.clientY - panStart.current.y };
      setPanOffset({ ...offsetRef.current });
    };
    const onUp = () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, []);

  const handleNodeMouseDown = useCallback((nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const node = layoutNodes.find(n => n.id === nodeId);
    if (!node) return;
    const startX = e.clientX, startY = e.clientY;
    const origX = node._x, origY = node._y;
    const onMove = (ev: MouseEvent) => {
      const dx = (ev.clientX - startX) / scaleRef.current;
      const dy = (ev.clientY - startY) / scaleRef.current;
      node._x = origX + dx;
      node._y = origY + dy;
      // Rerender to reflect
      setPanOffset(prev => ({ ...prev })); // force re-render
    };
    const onUp = () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [layoutNodes]);

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${canvasW} ${canvasH}`}
      className="w-full select-none bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.18),_transparent_24%),linear-gradient(180deg,_#020617_0%,_#0f172a_100%)]"
      style={{ height: 760, overflow: "auto" }}
      onWheel={handleWheel}
      onMouseDown={handleBgMouseDown}
    >
      <defs>
        {Object.entries(RELATION_COLORS).map(([rel, color]) => (
          <marker key={rel} id={`arrow-${rel}`} viewBox="0 0 10 10" refX={9} refY={5}
            markerWidth={5} markerHeight={5} orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
          </marker>
        ))}
      </defs>

      <g transform={`translate(${panOffset.x},${panOffset.y}) scale(${scale})`}>
        <rect x={0} y={0} width={canvasW} height={canvasH} fill="rgba(15,23,42,0.82)" />
        {Array.from({ length: Math.ceil(canvasW / 120) }).map((_, index) => (
          <line
            key={`grid-v-${index}`}
            x1={index * 120}
            y1={0}
            x2={index * 120}
            y2={canvasH}
            stroke="rgba(148,163,184,0.08)"
            strokeWidth={1}
          />
        ))}
        {Array.from({ length: Math.ceil(canvasH / 120) }).map((_, index) => (
          <line
            key={`grid-h-${index}`}
            x1={0}
            y1={index * 120}
            x2={canvasW}
            y2={index * 120}
            stroke="rgba(148,163,184,0.08)"
            strokeWidth={1}
          />
        ))}

        {/* Edges */}
        {edges.map(e => {
          const src = layoutNodes.find(n => n.id === e.source_node_id);
          const tgt = layoutNodes.find(n => n.id === e.target_node_id);
          if (!src || !tgt) return null;
          const color = RELATION_COLORS[e.relation] || "#d1d5db";
          const sel = selectedNodeId === e.source_node_id || selectedNodeId === e.target_node_id;
          // Simple straight line for tree layout
          const x1 = src._x, y1 = src._y;
          const x2 = tgt._x, y2 = tgt._y;

          return (
            <g key={e.id}>
              <line x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={color} strokeWidth={sel ? 2.5 : 1.5}
                strokeOpacity={sel ? 0.95 : 0.42}
                strokeDasharray={e.relation === "contradicts" ? "6,3" : undefined}
                markerEnd={`url(#arrow-${e.relation})`} />
            </g>
          );
        })}

        {/* Dimension group backgrounds */}
        {layoutNodes.filter(n => n.node_type === "dimension").map(dim => {
          const children = layoutNodes.filter(n =>
            n.node_type !== "dimension" &&
            Math.abs(n._x - dim._x) < 120 &&
            n._y > dim._y
          );
          if (children.length === 0) return null;
          const minY = Math.min(...children.map(c => c._y));
          const maxY = Math.max(...children.map(c => c._y));
          return (
            <rect key={`bg-${dim.id}`}
              x={dim._x - 120} y={minY - 30}
              width={240} height={maxY - minY + NODE_H + 50}
              rx={18} fill="rgba(255,255,255,0.02)" stroke="rgba(148,163,184,0.18)" strokeWidth={1}
              strokeDasharray="4,2" />
          );
        })}

        {/* Nodes */}
        {layoutNodes.map(n => {
          const colors = NODE_COLORS[n.node_type] || DEFAULT_COLOR;
          const sel = selectedNodeId === n.id;
          const dim = n.node_type === "dimension";
          const x = n._x - NODE_W / 2, y = n._y - NODE_H / 2;

          return (
            <g key={n.id} className="graph-node"
              onMouseDown={(e) => handleNodeMouseDown(n.id, e)}
              onClick={(e) => { e.stopPropagation(); onSelectNodeId(sel ? null : n.id); }}
              style={{ cursor: "pointer" }}>
              {/* Shadow */}
              <rect x={x + 2} y={y + 3} width={NODE_W} height={NODE_H} rx={7}
                fill={dim ? "rgba(99,102,241,0.16)" : "rgba(15,23,42,0.35)"} />
              {/* Body */}
              <rect x={x} y={y} width={NODE_W} height={NODE_H} rx={7}
                fill={sel ? colors.fill : "rgba(255,255,255,0.96)"}
                stroke={sel ? colors.stroke : `${colors.stroke}70`}
                strokeWidth={dim ? 2 : sel ? 2 : 1.2} />
              {/* Type indicator bar on left */}
              <rect x={x} y={y} width={4} height={NODE_H} rx={2}
                fill={colors.stroke} opacity={0.6} />
              {/* Title */}
              <text x={x + NODE_W / 2} y={n._y + 2} textAnchor="middle"
                fill="#0f172a" fontSize={dim ? 13 : 11.5} fontWeight={dim ? 700 : 600}>
                {n.title.length > (dim ? 20 : 24) ? n.title.slice(0, dim ? 19 : 22) + "…" : n.title}
              </text>
              {/* Sub-label: type + confidence */}
              {!dim && (
                <text x={x + NODE_W / 2} y={n._y + 16} textAnchor="middle"
                  fill={colors.text} fontSize={9.5} fontWeight={400}>
                  {n.node_type} · cf {n.confidence.toFixed(1)}
                </text>
              )}
            </g>
          );
        })}
      </g>

      {/* Legend */}
      <g transform={`translate(${canvasW - 140}, 14)`}>
        <rect x={-6} y={-4} width={135} height={Object.keys(NODE_COLORS).length * 15 + 10} rx={10} fill="rgba(15,23,42,0.78)" stroke="rgba(148,163,184,0.28)" />
        {Object.entries(NODE_COLORS).map(([type, colors], i) => (
          <g key={type} transform={`translate(0, ${i * 15 + 6})`}>
            <rect width={10} height={10} rx={2} fill={colors.fill} stroke={colors.stroke} strokeWidth={1} />
            <text x={15} y={9} fill="#cbd5e1" fontSize={9}>{type}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}
