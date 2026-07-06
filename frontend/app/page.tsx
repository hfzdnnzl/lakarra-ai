"use client";

import { useCallback, useEffect, useState } from "react";
import { Play, Loader2 } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { WorkflowRun } from "@/types";

interface Stats {
  agents: number;
  tasks: number;
  reports: number;
  approvals: number;
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [agents, tasks, reports, approvals, history] = await Promise.all([
        api.agents(),
        api.tasks(),
        api.reports(),
        api.approvals(),
        api.workflowHistory(),
      ]);
      setStats({
        agents: agents.length,
        tasks: tasks.length,
        reports: reports.length,
        approvals: approvals.filter((a) => a.status === "pending").length,
      });
      setRuns(history.slice().reverse());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const runMorning = async () => {
    setRunning(true);
    setLastResult(null);
    try {
      const state = (await api.runWorkflow("daily_priorities", `daily-${Date.now()}`)) as {
        status: string;
        steps: { agent: string }[];
      };
      setLastResult(
        `Ran daily_priorities → ${state.status} (${state.steps.length} agents executed)`,
      );
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const cards = [
    { label: "Agents", value: stats?.agents ?? "–" },
    { label: "Tasks", value: stats?.tasks ?? "–" },
    { label: "Reports", value: stats?.reports ?? "–" },
    { label: "Pending Approvals", value: stats?.approvals ?? "–" },
  ];

  return (
    <>
      <PageHeader
        title="Overview"
        description="Business health at a glance. Kick off the morning routine to see agents collaborate."
        action={
          <Button onClick={runMorning} disabled={running}>
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run Morning Priorities
          </Button>
        }
      />

      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not reach the API at <code>{api.base}</code>: {error}
        </div>
      ) : null}

      {lastResult ? (
        <div className="mb-6 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {lastResult}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {c.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold">{c.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <h2 className="mb-3 mt-8 text-lg font-semibold">Recent Workflow Runs</h2>
      {runs.length === 0 ? (
        <EmptyState message="No workflow runs yet. Click “Run Morning Priorities” to start one." />
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <Card key={run.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <div className="font-medium">{run.workflow}</div>
                  <div className="text-sm text-muted-foreground">
                    {run.steps.map((s) => s.agent).join(" → ") || "—"}
                  </div>
                </div>
                <Badge variant={run.status === "completed" ? "success" : "warning"}>
                  {run.status}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
