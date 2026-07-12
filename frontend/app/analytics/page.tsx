"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";

import { useAnalyticsAccount } from "@/components/analytics/AnalyticsShell";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AccountOverview } from "@/types";

export default function AnalyticsOverviewPage() {
  const { configured, refresh: refreshAccount } = useAnalyticsAccount();
  const [overview, setOverview] = useState<AccountOverview | null>(null);
  const [metricsReady, setMetricsReady] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [trendPage, setTrendPage] = useState(1);
  const TRENDS_PER_PAGE = 5;

  // Reset trend page when overview changes (different account / refresh)
  useEffect(() => {
    setTrendPage(1);
  }, [overview]);

  const sortedTrends = useMemo(() => {
    if (!overview) return [];
    return [...overview.performance_trends].sort((a, b) =>
      b.publish_date.localeCompare(a.publish_date),
    );
  }, [overview]);

  const trendTotalPages = Math.max(1, Math.ceil(sortedTrends.length / TRENDS_PER_PAGE));
  const trendStart = (trendPage - 1) * TRENDS_PER_PAGE;
  const trendEnd = trendStart + TRENDS_PER_PAGE;
  const paginatedTrends = sortedTrends.slice(trendStart, trendEnd);

  const load = useCallback(async () => {
    if (!configured) {
      setOverview(null);
      setMetricsReady(null);
      return;
    }
    try {
      const ov = await api.analyticsOverview();
      setOverview(ov);
      const readiness = await api.analyticsMetricsReadiness().catch(() => null);
      setMetricsReady(readiness?.ready ?? null);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [configured]);

  useEffect(() => {
    void load();
  }, [load]);

  const runAccountAnalysis = async () => {
    setBusy(true);
    try {
      await api.analyzeAccount();
      await load();
      await refreshAccount();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Marketing intelligence from the Content Analyst agent."
        action={
          configured ? (
            <Button
              onClick={runAccountAnalysis}
              disabled={busy || metricsReady === false}
              size="sm"
            >
              {busy ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Analyze Account
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {!configured ? (
        <p className="text-muted-foreground">
          Connect your TikTok account above to see performance data and run analyses.
        </p>
      ) : metricsReady === false ? (
        <div className="mb-6 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Complete required video metrics in{" "}
          <Link href="/analytics/content" className="underline">
            Content Analytics
          </Link>{" "}
          before running account analysis.
        </div>
      ) : null}

      {!configured ? null : !overview ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (
        <>
          {overview.live_data_error ? (
            <div className="mb-6 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {overview.total_videos > 0
                ? `Live TikTok data may be limited: ${overview.live_data_error} Showing available videos below — enter Studio metrics in `
                : `${overview.live_data_error} Mark content as Posted in the Content library, then open `}
              <Link href="/analytics/content" className="underline">
                Content Analytics
              </Link>
              {overview.total_videos > 0 ? "." : " to track metrics."}
            </div>
          ) : null}

          <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Account Health
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">
                  {(overview.account_health_score * 100).toFixed(0)}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Videos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">{overview.total_videos}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">
                  {overview.total_views.toLocaleString()}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Avg Engagement
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">
                  {(overview.avg_engagement_rate * 100).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recent Videos</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {overview.recent_videos.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No videos yet.</p>
                ) : (
                  overview.recent_videos.map((v) => (
                    <div key={v.video_id} className="flex items-start justify-between gap-3 text-sm">
                      <div className="min-w-0">
                        <div className="line-clamp-2 font-medium leading-snug">{v.title}</div>
                        <div className="text-muted-foreground">
                          {v.category} · {v.publish_date}
                        </div>
                      </div>
                      <div className="shrink-0 text-muted-foreground">
                        {v.views.toLocaleString()} views
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Best Performers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {overview.best_performers.map((v) => (
                  <div key={v.video_id} className="flex items-start justify-between gap-3 text-sm">
                    <div className="line-clamp-2 min-w-0 font-medium leading-snug">{v.title}</div>
                    <div className="shrink-0 text-muted-foreground">
                      {v.views.toLocaleString()} views
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Worst Performers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {overview.worst_performers.map((v) => (
                  <div key={v.video_id} className="flex items-start justify-between gap-3 text-sm">
                    <div className="line-clamp-2 min-w-0 font-medium leading-snug">{v.title}</div>
                    <div className="shrink-0 text-muted-foreground">
                      {v.views.toLocaleString()} views
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Performance Trends</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {paginatedTrends.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No trends yet.</p>
                ) : (
                  <>
                    {paginatedTrends.map((t) => (
                      <div key={t.video_id} className="space-y-1">
                        <div className="line-clamp-1 text-sm font-medium">
                          {t.title ?? t.publish_date}
                        </div>
                        <div className="flex items-center gap-3 text-sm">
                          <div className="w-20 shrink-0 text-muted-foreground">{t.publish_date}</div>
                          <div className="h-2 flex-1 rounded bg-muted">
                            <div
                              className="h-2 rounded bg-primary"
                              style={{
                                width: `${Math.min(100, (t.views / Math.max(...sortedTrends.map((x) => x.views), 1)) * 100)}%`,
                              }}
                            />
                          </div>
                          <div className="w-16 text-right text-muted-foreground">
                            {t.views >= 1000 ? `${(t.views / 1000).toFixed(1)}k` : t.views}
                          </div>
                        </div>
                      </div>
                    ))}
                    {trendTotalPages > 1 ? (
                      <div className="flex items-center justify-between pt-2 text-sm">
                        <span className="text-muted-foreground">
                          {trendStart + 1}–{Math.min(trendEnd, sortedTrends.length)} of {sortedTrends.length}
                        </span>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-40"
                            disabled={trendPage <= 1}
                            onClick={() => setTrendPage((p) => Math.max(1, p - 1))}
                          >
                            <ChevronLeft className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-40"
                            disabled={trendPage >= trendTotalPages}
                            onClick={() => setTrendPage((p) => Math.min(trendTotalPages, p + 1))}
                          >
                            <ChevronRight className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="mt-6 text-sm text-muted-foreground">
            Explore{" "}
            <Link href="/analytics/content" className="text-primary underline">
              Content Analytics
            </Link>
            ,{" "}
            <Link href="/analytics/competitors" className="text-primary underline">
              Competitors
            </Link>
            , or the{" "}
            <Link href="/analytics/review-queue" className="text-primary underline">
              Review Queue
            </Link>
            .
          </div>
        </>
      )}
    </>
  );
}
