"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Play } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { WorkflowDefinition, WorkflowRun } from "@/types";

export default function WorkflowsPage() {
  const [defs, setDefs] = useState<WorkflowDefinition[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [d, h] = await Promise.all([api.workflows(), api.workflowHistory()]);
      setDefs(d);
      setRuns(h.slice().reverse());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (name: string) => {
    setBusy(name);
    try {
      await api.runWorkflow(name, `ui-${Date.now()}`);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Workflow History"
        description="Configurable LangGraph workflows and their run history."
      />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <h2 className="mb-3 text-lg font-semibold">Available Workflows</h2>
      <div className="mb-8 grid gap-4 md:grid-cols-2">
        {defs.map((d) => (
          <Card key={d.name}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{d.name}</CardTitle>
                {d.requires_approval ? <Badge variant="warning">approval</Badge> : null}
              </div>
              <CardDescription>{d.description}</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <div className="text-xs text-muted-foreground">{d.steps.join(" → ")}</div>
              <Button size="sm" variant="outline" onClick={() => run(d.name)} disabled={busy === d.name}>
                {busy === d.name ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Play className="h-3.5 w-3.5" />
                )}
                Run
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <h2 className="mb-3 text-lg font-semibold">Run History</h2>
      {runs.length === 0 ? (
        <EmptyState message="No workflow runs yet." />
      ) : (
        <div className="space-y-3">
          {runs.map((r) => (
            <Card key={r.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <div className="font-medium">{r.workflow}</div>
                  <div className="text-sm text-muted-foreground">
                    {r.steps.map((s) => s.agent).join(" → ") || "—"}
                  </div>
                </div>
                <Badge variant={r.status === "completed" ? "success" : "warning"}>
                  {r.status}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
