/* ──────────────────────────────────────────────────────────
 * Agent Flow Explorer – React Flow graph visualization
 * ────────────────────────────────────────────────────────── */

import { useCallback, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeTypes,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { AgentNode } from "./AgentNode";
import { NodeDetailPanel } from "./NodeDetailPanel";
import type { AgentNodeData, AgentStatus } from "@/types";

type AgentNodeRecord = AgentNodeData & Record<string, unknown>;

/* ── Node type registration ── */
const nodeTypes: NodeTypes = {
  agentNode: AgentNode,
};

/* ── Default flow layout ── */
function buildNodes(activePhase: AgentStatus): Node<AgentNodeRecord>[] {
  const phases: { id: AgentStatus; label: string; x: number; y: number }[] = [
    { id: "intake",        label: "Intake Context",         x: 400, y: 0 },
    { id: "hypothesizing", label: "Hypothesis Generation",  x: 400, y: 120 },
    { id: "reproducing",   label: "Reproduction Attempt",   x: 400, y: 240 },
    { id: "analyzing",     label: "Reproduction Analysis",  x: 400, y: 360 },
    { id: "root_cause",    label: "Root Cause Analysis",    x: 400, y: 480 },
    { id: "patching",      label: "Patch Generation",       x: 400, y: 600 },
    { id: "validating",    label: "Validation",             x: 400, y: 720 },
    { id: "complete",      label: "Completion",             x: 400, y: 840 },
    { id: "failed",        label: "Aborted",                x: 700, y: 480 },
  ];

  const COMPLETE_ORDER = [
    "intake", "hypothesizing", "reproducing", "analyzing",
    "root_cause", "patching", "validating", "complete",
  ];
  const activeIdx = COMPLETE_ORDER.indexOf(activePhase);

  return phases.map(({ id, label, x, y }) => {
    const idx = COMPLETE_ORDER.indexOf(id);
    const completed = idx >= 0 && idx < activeIdx;
    const active = id === activePhase;

    return {
      id,
      type: "agentNode",
      position: { x, y },
      data: {
        label,
        phase: id,
        active,
        completed,
      },
    };
  });
}

function buildEdges(): Edge[] {
  const edges: Edge[] = [
    { id: "e1", source: "intake",        target: "hypothesizing" },
    { id: "e2", source: "hypothesizing", target: "reproducing" },
    { id: "e3", source: "reproducing",   target: "analyzing" },
    { id: "e4", source: "analyzing",     target: "root_cause",    label: "reproduced" },
    { id: "e5", source: "root_cause",    target: "patching" },
    { id: "e6", source: "patching",      target: "validating" },
    { id: "e7", source: "validating",    target: "complete",      label: "validated" },
    // Retry loops
    { id: "e8", source: "analyzing",     target: "hypothesizing", label: "retry",    animated: true, style: { stroke: "#f59e0b" } },
    { id: "e9", source: "validating",    target: "hypothesizing", label: "retry",    animated: true, style: { stroke: "#f59e0b" } },
    // Failure paths
    { id: "e10", source: "analyzing",    target: "failed",        label: "max attempts", style: { stroke: "#ef4444" } },
    { id: "e11", source: "validating",   target: "failed",        label: "max attempts", style: { stroke: "#ef4444" } },
  ];

  return edges.map((e) => ({
    ...e,
    style: e.style ?? { stroke: "#3f3f46" },
    labelStyle: { fill: "#71717a", fontSize: 10 },
    labelBgStyle: { fill: "#18181b", fillOpacity: 0.8 },
    labelBgPadding: [4, 2] as [number, number],
  }));
}

/* ── Page component ── */

export default function FlowExplorerPage() {
  const [activePhase] = useState<AgentStatus>("analyzing");
  const [selectedNode, setSelectedNode] = useState<AgentNodeData | null>(null);

  const [nodes, , onNodesChange] = useNodesState(buildNodes(activePhase));
  const [edges, , onEdgesChange] = useEdgesState(buildEdges());

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node.data as unknown as AgentNodeData);
  }, []);

  return (
    <div className="flex h-full gap-4">
      <div className="flex-1 overflow-hidden rounded-xl border border-zinc-800">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.3}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#27272a" gap={20} size={1} />
          <Controls
            showInteractive={false}
            className="rounded-lg border border-zinc-800 bg-zinc-900"
          />
          <MiniMap
            nodeColor={(n) => {
              const d = n.data as unknown as AgentNodeData;
              if (d.active) return "#3b82f6";
              if (d.completed) return "#22c55e";
              return "#3f3f46";
            }}
            maskColor="rgba(0,0,0,0.6)"
            className="rounded-lg border border-zinc-800"
          />
        </ReactFlow>
      </div>

      {/* Detail panel on the right */}
      {selectedNode && (
        <NodeDetailPanel
          data={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
