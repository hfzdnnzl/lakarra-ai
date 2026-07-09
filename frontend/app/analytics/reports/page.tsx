"use client";

import { useCallback, useEffect, useState } from "react";

import { PageHeader, EmptyState } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { HistoricalAnalytics } from "@/types";

export default function HistoricalReportsPage() {
  const [data, setData] = useState<HistoricalAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<keyof HistoricalAnalytics>("content_analyses");

  const load = useCallback(async () => {
    try {
      setData(await api.analyticsHistorical());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tabs: { key: keyof HistoricalAnalytics; label: string }[] = [
    { key: "content_analyses", label: "Video Analyses" },
    { key: "competitor_analyses", label: "Competitor" },
    { key: "trend_reports", label: "Trends" },
    { key: "review_reports", label: "Reviews" },
    { key: "pattern_analyses", label: "Patterns" },
    { key: "metrics_snapshots", label: "Metrics" },
  ];

  const records = data ? data[tab] : [];

  return (
    <>
      <PageHeader
        title="Historical Reports"
        description="All versioned analyses persisted by the Content Analyst."
      />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="mb-6 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {t.label}
            {data ? ` (${(data[t.key] as unknown[]).length})` : ""}
          </button>
        ))}
      </div>

      {!data ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (records as unknown[]).length === 0 ? (
        <EmptyState message="No records in this category yet." />
      ) : (
        <div className="space-y-3">
          {(records as Array<Record<string, unknown>>).map((r) => (
            <Card key={String(r.id)}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">
                    {String(r.video_id ?? r.handle ?? r.period ?? r.content_id ?? r.subject_id ?? r.metric ?? r.id)}
                  </CardTitle>
                  <div className="flex gap-2">
                    {"version" in r ? <Badge variant="muted">v{String(r.version)}</Badge> : null}
                    <Badge variant="muted">{String(r.agent ?? "snapshot")}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="max-h-48 overflow-auto rounded bg-muted p-3 text-xs">
                  {JSON.stringify(r.payload ?? r, null, 2)}
                </pre>
                {"created_at" in r ? (
                  <div className="mt-2 text-xs text-muted-foreground">
                    {new Date(String(r.created_at)).toLocaleString()}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
