"use client";

import { useCallback, useEffect, useState } from "react";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { PageHeader, EmptyState } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type {
  AnalysisRecord,
  AnalyticsSnapshot,
  CompetitorAnalysisRecord,
  ContentAnalysisRecord,
  HistoricalAnalytics,
  ReviewReportRecord,
  TrendReportRecord,
} from "@/types";

type HistoricalRecord =
  | ContentAnalysisRecord
  | CompetitorAnalysisRecord
  | TrendReportRecord
  | ReviewReportRecord
  | AnalysisRecord
  | AnalyticsSnapshot;

function recordTitle(record: HistoricalRecord): string {
  if ("video_id" in record && record.video_id) return record.video_id;
  if ("handle" in record && record.handle) return record.handle;
  if ("period" in record && record.period) return record.period;
  if ("content_id" in record && record.content_id) return record.content_id;
  if ("subject_id" in record && record.subject_id) return record.subject_id;
  if ("metric" in record && record.metric) return record.metric;
  return record.id;
}

function recordPayload(record: HistoricalRecord): Record<string, unknown> {
  if ("payload" in record && record.payload) {
    return record.payload as Record<string, unknown>;
  }
  return record as unknown as Record<string, unknown>;
}

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

  const records: HistoricalRecord[] = data ? (data[tab] as HistoricalRecord[]) : [];

  return (
    <>
      <PageHeader
        title="Historical Reports"
        description="All versioned analyses persisted by the Content Analyst."
      />
      <AnalyticsNav />
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
      ) : records.length === 0 ? (
        <EmptyState message="No records in this category yet." />
      ) : (
        <div className="space-y-3">
          {records.map((record) => (
            <Card key={record.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">{recordTitle(record)}</CardTitle>
                  <div className="flex gap-2">
                    {"version" in record && record.version != null ? (
                      <Badge variant="muted">v{record.version}</Badge>
                    ) : null}
                    <Badge variant="muted">
                      {"agent" in record && record.agent ? record.agent : "snapshot"}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <pre className="max-h-48 overflow-auto rounded bg-muted p-3 text-xs">
                  {JSON.stringify(recordPayload(record), null, 2)}
                </pre>
                {"created_at" in record && record.created_at ? (
                  <div className="mt-2 text-xs text-muted-foreground">
                    {new Date(record.created_at).toLocaleString()}
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
