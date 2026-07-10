"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, TrendingUp } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { TrendReportRecord } from "@/types";

export default function TrendReportsPage() {
  const [reports, setReports] = useState<TrendReportRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.analyticsTrends();
      setReports(data.reports);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async () => {
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
          <Button onClick={generate} disabled={busy} size="sm">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <TrendingUp className="mr-2 h-4 w-4" />}
            Generate Report
          </Button>
        }
      />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
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
