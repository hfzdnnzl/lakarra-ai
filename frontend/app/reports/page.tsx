"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { Report } from "@/types";

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .reports()
      .then(setReports)
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <>
      <PageHeader title="Reports" description="Structured reports produced by agents." />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {reports.length === 0 && !error ? (
        <EmptyState message="No reports yet. Invoke an agent or run a workflow." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {reports.map((r) => (
            <Card key={r.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{r.title}</CardTitle>
                  <Badge variant="muted">{r.agent}</Badge>
                </div>
                <CardDescription>{r.summary}</CardDescription>
              </CardHeader>
              <CardContent>
                <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
                  {JSON.stringify(r.payload, null, 2)}
                </pre>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
