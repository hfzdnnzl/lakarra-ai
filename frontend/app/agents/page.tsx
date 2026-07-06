"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Zap } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { AgentInfo } from "@/types";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [invoked, setInvoked] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setAgents(await api.agents());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const invoke = async (name: string) => {
    setBusy(name);
    try {
      const res = (await api.invokeAgent(name)) as { status: string };
      setInvoked((prev) => ({ ...prev, [name]: res.status }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Agent Status"
        description="Every agent is independent and communicates via structured JSON."
      />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {agents.length === 0 && !error ? (
        <EmptyState message="Loading agents…" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {agents.map((agent) => (
            <Card key={agent.name}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{agent.role}</CardTitle>
                  <Badge variant={invoked[agent.name] ? "success" : "muted"}>
                    {invoked[agent.name] ? `last: ${invoked[agent.name]}` : "idle"}
                  </Badge>
                </div>
                <CardDescription>{agent.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <code className="text-xs text-muted-foreground">{agent.name}</code>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => invoke(agent.name)}
                    disabled={busy === agent.name}
                  >
                    {busy === agent.name ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Zap className="h-3.5 w-3.5" />
                    )}
                    Invoke
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
