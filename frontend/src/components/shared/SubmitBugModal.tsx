/* ──────────────────────────────────────────────────────────
 * SubmitBugModal – quick-submit dialog triggered from Header
 * ────────────────────────────────────────────────────────── */

import { useState } from "react";
import { useAppStore } from "@/store";
import { useSubmitBug } from "@/services/queries";
import { Modal, Button, Textarea, Input, Select } from "@/components/ui";

export function SubmitBugModal() {
  const open = useAppStore((s) => s.submitModalOpen);
  const close = useAppStore((s) => s.closeSubmitModal);
  const submitMutation = useSubmitBug();

  const [bugReport, setBugReport] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [mode, setMode] = useState("fix_and_pr");

  const handleSubmit = () => {
    if (!bugReport.trim()) return;
    submitMutation.mutate(
      { bug_report: bugReport, repo_path: repoPath || ".", agent_mode: mode },
      {
        onSuccess: () => {
          setBugReport("");
          setRepoPath("");
          close();
        },
      },
    );
  };

  return (
    <Modal open={open} onClose={close} title="Submit Bug Report" wide>
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">Bug Description</label>
          <Textarea
            value={bugReport}
            onChange={(e) => setBugReport(e.target.value)}
            placeholder="Describe the bug. Include error messages, steps to reproduce, and expected behavior…"
            rows={5}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-400">Repository Path</label>
            <Input
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              placeholder="/path/to/repo (default: .)"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-400">Agent Mode</label>
            <Select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="fix_and_pr">Fix Bug & Create PR</option>
              <option value="create_ticket">Create Jira Ticket</option>
              <option value="report_only">Generate Report Only</option>
            </Select>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!bugReport.trim() || submitMutation.isPending}>
            {submitMutation.isPending ? "Submitting…" : "Submit"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
