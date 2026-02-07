/* ──────────────────────────────────────────────────────────
 * Shared TypeScript types for the BugFixer frontend
 * ────────────────────────────────────────────────────────── */

// ── Agent State (mirrors Python AgentState) ──

export interface AgentState {
  bug_report: string;
  repo_path: string;
  context: Record<string, unknown>;
  suspected_files: string[];
  suspected_tests: string[];
  failing_tests: string[];
  repro_command: string;
  error_output: string;
  hypothesis: string;
  root_cause: string;
  patch: string;
  patch_files: string[];
  status: AgentStatus;
  repro_confirmed: boolean;
  fix_validated: boolean;
  attempt_count: number;
  max_attempts: number;
  logs: string[];
  pr_summary: string;
  pr_title: string;
}

export type AgentStatus =
  | "intake"
  | "hypothesizing"
  | "reproducing"
  | "analyzing"
  | "root_cause"
  | "patching"
  | "validating"
  | "complete"
  | "failed"
  | "pending";

// ── Bug Request ──

export interface BugRequest {
  id: string;
  bug_report: string;
  repo_path: string;
  status: AgentStatus;
  agent_mode: AgentMode;
  created_at: string;
  updated_at: string;
  agent_state: AgentState | null;
  messages: ConversationMessage[];
}

export type AgentMode =
  | "fix_and_pr"
  | "create_ticket"
  | "report_only";

// ── Conversation ──

export interface ConversationMessage {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  timestamp: string;
  phase?: AgentStatus;
}

// ── Dashboard ──

export interface DashboardMetrics {
  active_runs: number;
  total_requests: number;
  success_count: number;
  failure_count: number;
  avg_repro_time_seconds: number;
  prs_created: number;
  tickets_created: number;
}

export interface RecentRequest {
  id: string;
  bug_report: string;
  status: AgentStatus;
  repo_path: string;
  created_at: string;
}

// ── Configuration ──

export interface AppConfig {
  repository: RepositoryConfig;
  agent: AgentConfig;
  integrations: IntegrationConfig;
}

export interface RepositoryConfig {
  local_path: string;
  branch: string;
  validated: boolean;
}

export interface AgentConfig {
  mode: AgentMode;
  max_retries: number;
  patch_aggressiveness: "conservative" | "moderate" | "aggressive";
  allow_test_execution: boolean;
  model: string;
}

export interface IntegrationConfig {
  github_token: string;
  jira_token: string;
  slack_webhook: string;
}

// ── Agent Flow (for React Flow visualization) ──

export interface AgentNodeData {
  label: string;
  phase: AgentStatus;
  active: boolean;
  completed: boolean;
  prompt?: string;
  tools_invoked?: string[];
  state_changes?: Record<string, unknown>;
  duration_ms?: number;
}

export interface FlowTransition {
  from: AgentStatus;
  to: AgentStatus;
  timestamp: string;
  is_retry: boolean;
}

// ── Logs & Telemetry ──

export interface LogEntry {
  id: string;
  timestamp: string;
  phase: AgentStatus;
  message: string;
  level: "info" | "warn" | "error" | "debug";
}

export interface ToolInvocation {
  id: string;
  tool_name: string;
  input_summary: string;
  output_summary: string;
  duration_ms: number;
  timestamp: string;
}

export interface LLMUsage {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_calls: number;
  total_cost_usd: number;
}

// ── Ticket (from BuggyDemo) ──

export interface BugTicket {
  id: string;
  title: string;
  description: string;
  module: string;
  severity: string;
  reporter: string;
  steps: string;
  submitted_at: string;
  status: "pending" | "running" | "complete" | "failed";
  run_id: string | null;
}

// ── WebSocket Events ──

export type WSEvent =
  | { type: "state_update"; request_id: string; state: Partial<AgentState> }
  | { type: "log"; request_id: string; entry: LogEntry }
  | { type: "phase_change"; request_id: string; phase: AgentStatus }
  | { type: "run_complete"; request_id: string; status: AgentStatus }
  | { type: "metrics_update"; metrics: DashboardMetrics }
  | { type: "ticket_created"; ticket: BugTicket }
  | { type: "ticket_updated"; ticket: BugTicket };
