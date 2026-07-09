"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, TrendingUp } from "lucide-react";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { MetricsReadiness, TrendReportRecord } from "@/types";

export default function TrendReportsPage() {
  const [reports, setReports] = useState<TrendReportRecord[]>([]);
  const [readiness, setReadiness] = useState<MetricsReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [trends, metricsReadiness] = await Promise.all([
        api.analyticsTrends(),
        api.analyticsMetricsReadiness().catch(() => null),
      ]);
      setReports(trends.reports);
      setReadiness(metricsReadiness);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const ready = readiness?.ready ?? false;

  const generate = async () => {
    if (!ready) {
      setError(
        "Complete required metrics for all videos in Content Analytics before generating a trend report.",
      );
      return;
    }
    setBusy(true);
    try {
      await api.generateTrendReport("30d");
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Trend Reports"
        description="Historical pattern recognition and strategic recommendations."
        action={
          <Button onClick={generate} disabled={busy || !ready} size="sm">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <TrendingUp className="mr-2 h-4 w-4" />}
            Generate Report
          </Button>
        }
      />
      <AnalyticsNav />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {readiness && !ready ? (
        <Card className="mb-6 border-amber-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Metrics required</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Complete required video metrics in{" "}
            <Link href="/analytics/content" className="text-primary underline">
              Content Analytics
            </Link>{" "}
            ({readiness.complete_videos}/{readiness.total_videos} videos ready) before
            generating trend reports.
          </CardContent>
        </Card>
      ) : null}

      {reports.length === 0 ? (
        <p className="text-muted-foreground">
          No trend reports yet. Click &quot;Generate Report&quot; to analyze historical patterns.
        </p>
      ) : (
        <div className="space-y-4">
          {reports.map((r) => {
            const p = r.payload as {
              summary?: string;
              account_health_score?: number;
              growth_trend?: string;
              patterns?: {
                best_performing_categories?: string[];
                best_posting_days?: string[];
                strongest_hooks?: string[];
                common_failure_patterns?: string[];
              };
              recommendations?: {
                content_categories?: string[];
                experiments?: string[];
                strategy_gaps?: string[];
              };
            };
            return (
              <Card key={r.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">Period: {r.period}</CardTitle>
                    <Badge variant="muted">v{r.version}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <p>{p.summary}</p>
                  <div className="flex flex-wrap gap-4">
                    <span>
                      Health:{" "}
                      {p.account_health_score
                        ? `${(p.account_health_score * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                    <span>Growth: {p.growth_trend ?? "—"}</span>
                  </div>
                  {p.patterns ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <div className="mb-1 font-medium">Best Categories</div>
                        <div className="flex flex-wrap gap-1">
                          {p.patterns.best_performing_categories?.map((c) => (
                            <Badge key={c} variant="muted">{c}</Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="mb-1 font-medium">Best Posting Days</div>
                        <div className="text-muted-foreground">
                          {p.patterns.best_posting_days?.join(", ")}
                        </div>
                      </div>
                      <div>
                        <div className="mb-1 font-medium">Strongest Hooks</div>
                        <ul className="list-inside list-disc text-muted-foreground">
                          {p.patterns.strongest_hooks?.map((h) => <li key={h}>{h}</li>)}
                        </ul>
                      </div>
                      <div>
                        <div className="mb-1 font-medium">Failure Patterns</div>
                        <ul className="list-inside list-disc text-muted-foreground">
                          {p.patterns.common_failure_patterns?.map((f) => <li key={f}>{f}</li>)}
                        </ul>
                      </div>
                    </div>
                  ) : null}
                  {p.recommendations?.experiments?.length ? (
                    <div>
                      <div className="mb-1 font-medium">Suggested Experiments</div>
                      <ul className="list-inside list-disc text-muted-foreground">
                        {p.recommendations.experiments.map((e) => <li key={e}>{e}</li>)}
                      </ul>
                    </div>
                  ) : null}
                  <div className="text-xs text-muted-foreground">
                    {new Date(r.created_at).toLocaleString()}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
