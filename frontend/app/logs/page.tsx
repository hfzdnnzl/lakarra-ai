"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { LogEntry } from "@/types";

const variant: Record<string, "muted" | "warning" | "destructive"> = {
  info: "muted",
  warning: "warning",
  error: "destructive",
};

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .logs()
      .then(setLogs)
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <>
      <PageHeader title="Logs" description="System and agent activity logs." />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {logs.length === 0 && !error ? (
        <EmptyState message="No logs recorded yet." />
      ) : (
        <Card>
          <CardContent className="divide-y divide-border p-0">
            {logs.map((l) => (
              <div key={l.id} className="flex items-center gap-3 px-4 py-3 text-sm">
                <Badge variant={variant[l.level] ?? "muted"}>{l.level}</Badge>
                <span className="text-muted-foreground">{l.source}</span>
                <span>{l.message}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </>
  );
}
