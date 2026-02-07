/* ──────────────────────────────────────────────────────────
 * Configuration page – repository, agent, integration settings
 * ────────────────────────────────────────────────────────── */

import { useState, useEffect } from "react";
import {
  FolderGit2,
  Bot,
  Plug,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import {
  Card,
  Button,
  Input,
  Select,
  LoadingState,
  ErrorState,
} from "@/components/ui";
import { useConfig, useUpdateConfig, useValidateRepo } from "@/services/queries";
import type { AppConfig } from "@/types";

export default function ConfigPage() {
  const { data: config, isLoading, isError, error } = useConfig();
  const updateMutation = useUpdateConfig();
  const validateMutation = useValidateRepo();

  const [form, setForm] = useState<AppConfig | null>(null);

  useEffect(() => {
    if (config) setForm(config);
  }, [config]);

  if (isLoading) return <LoadingState message="Loading configuration…" />;
  if (isError) return <ErrorState message={error.message} />;
  if (!form) return null;

  const update = <K extends keyof AppConfig>(
    section: K,
    key: string,
    value: unknown,
  ) => {
    setForm((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        [section]: { ...prev[section], [key]: value },
      };
    });
  };

  const handleSave = () => {
    if (form) updateMutation.mutate(form);
  };

  const handleValidateRepo = () => {
    validateMutation.mutate(form.repository.local_path);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-zinc-100">Configuration</h1>
        <Button onClick={handleSave} disabled={updateMutation.isPending}>
          {updateMutation.isPending ? "Saving…" : "Save Changes"}
        </Button>
      </div>

      {updateMutation.isSuccess && (
        <div className="animate-slide-in rounded-lg bg-green-500/10 border border-green-500/20 px-4 py-2 text-sm text-green-400">
          Configuration saved successfully.
        </div>
      )}

      {/* ── Repository Settings ── */}
      <Card>
        <SectionHeader icon={FolderGit2} title="Repository Settings" color="text-blue-400" />
        <div className="mt-4 space-y-4">
          <Field label="Local Repository Path">
            <div className="flex gap-2">
              <Input
                value={form.repository.local_path}
                onChange={(e) => update("repository", "local_path", e.target.value)}
                placeholder="/home/user/projects/my-repo"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={handleValidateRepo}
                disabled={validateMutation.isPending}
              >
                {validateMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  "Validate"
                )}
              </Button>
            </div>
            {validateMutation.isSuccess && (
              <div className="mt-1 flex items-center gap-1 text-xs">
                {validateMutation.data.valid ? (
                  <>
                    <CheckCircle2 className="h-3 w-3 text-green-400" />
                    <span className="text-green-400">{validateMutation.data.message}</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-3 w-3 text-red-400" />
                    <span className="text-red-400">{validateMutation.data.message}</span>
                  </>
                )}
              </div>
            )}
          </Field>

          <Field label="Branch">
            <Input
              value={form.repository.branch}
              onChange={(e) => update("repository", "branch", e.target.value)}
              placeholder="main"
            />
          </Field>
        </div>
      </Card>

      {/* ── Agent Settings ── */}
      <Card>
        <SectionHeader icon={Bot} title="Agent Settings" color="text-purple-400" />
        <div className="mt-4 space-y-4">
          <Field label="Operation Mode">
            <Select
              value={form.agent.mode}
              onChange={(e) => update("agent", "mode", e.target.value)}
            >
              <option value="fix_and_pr">Fix Bug & Create PR</option>
              <option value="create_ticket">Create Jira Ticket</option>
              <option value="report_only">Generate Report Only</option>
            </Select>
          </Field>

          <Field label="LLM Model">
            <Input
              value={form.agent.model}
              onChange={(e) => update("agent", "model", e.target.value)}
              placeholder="gpt-4o"
            />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Max Retries">
              <Input
                type="number"
                min={1}
                max={20}
                value={form.agent.max_retries}
                onChange={(e) => update("agent", "max_retries", parseInt(e.target.value))}
              />
            </Field>

            <Field label="Patch Aggressiveness">
              <Select
                value={form.agent.patch_aggressiveness}
                onChange={(e) => update("agent", "patch_aggressiveness", e.target.value)}
              >
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </Select>
            </Field>
          </div>

          <Field label="Test Execution">
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input
                type="checkbox"
                checked={form.agent.allow_test_execution}
                onChange={(e) => update("agent", "allow_test_execution", e.target.checked)}
                className="rounded border-zinc-600 bg-zinc-800 text-blue-500 focus:ring-blue-500/40"
              />
              Allow agent to execute tests in the target repository
            </label>
          </Field>
        </div>
      </Card>

      {/* ── Integration Settings ── */}
      <Card>
        <SectionHeader icon={Plug} title="Integrations" color="text-cyan-400" />
        <div className="mt-4 space-y-4">
          <Field label="GitHub Token">
            <Input
              type="password"
              value={form.integrations.github_token}
              onChange={(e) => update("integrations", "github_token", e.target.value)}
              placeholder="ghp_xxxxxxxxxxxx"
            />
          </Field>

          <Field label="Jira API Token">
            <Input
              type="password"
              value={form.integrations.jira_token}
              onChange={(e) => update("integrations", "jira_token", e.target.value)}
              placeholder="ATATT3xxxxxxxxxxxx"
            />
          </Field>

          <Field label="Slack Webhook URL (optional)">
            <Input
              value={form.integrations.slack_webhook}
              onChange={(e) => update("integrations", "slack_webhook", e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
            />
          </Field>
        </div>
      </Card>
    </div>
  );
}

/* ── Helpers ── */

function SectionHeader({
  icon: Icon,
  title,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className={`h-4 w-4 ${color}`} />
      <h2 className="text-sm font-semibold text-zinc-200">{title}</h2>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-zinc-400">{label}</label>
      {children}
    </div>
  );
}
