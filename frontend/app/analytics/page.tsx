"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AccountOverview } from "@/types";

export default function AnalyticsOverviewPage() {
  const [overview, setOverview] = useState<AccountOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setOverview(await api.analyticsOverview());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runAccountAnalysis = async () => {
    setBusy(true);
    try {
      await api.analyzeAccount();
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
        title="Analytics"
        description="Marketing intelligence from the Content Analyst agent."
        action={
          <Button onClick={runAccountAnalysis} disabled={busy} size="sm">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Analyze Account
          </Button>
        }
      />
      <AnalyticsNav />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {!overview ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (
        <>
          <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Account Health</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">
                  {(overview.account_health_score * 100).toFixed(0)}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Videos</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">{overview.total_videos}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Views</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">{overview.total_views.toLocaleString()}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Avg Engagement</CardTitle>
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
                {overview.recent_videos.map((v) => (
                  <div key={v.video_id} className="flex items-center justify-between text-sm">
                    <div>
                      <div className="font-medium">{v.title}</div>
                      <div className="text-muted-foreground">{v.category} · {v.publish_date}</div>
                    </div>
                    <div className="text-muted-foreground">{v.views.toLocaleString()} views</div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Best Performers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {overview.best_performers.map((v) => (
                  <div key={v.video_id} className="flex items-center justify-between text-sm">
                    <div className="font-medium">{v.title}</div>
                    <div className="text-muted-foreground">{v.views.toLocaleString()} views</div>
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
                  <div key={v.video_id} className="flex items-center justify-between text-sm">
                    <div className="font-medium">{v.title}</div>
                    <div className="text-muted-foreground">{v.views.toLocaleString()} views</div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Performance Trends</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {overview.performance_trends.map((t) => (
                  <div key={t.video_id} className="flex items-center gap-3 text-sm">
                    <div className="w-20 shrink-0 text-muted-foreground">{t.publish_date}</div>
                    <div className="h-2 flex-1 rounded bg-muted">
                      <div
                        className="h-2 rounded bg-primary"
                        style={{
                          width: `${Math.min(100, (t.views / Math.max(...overview.performance_trends.map((x) => x.views), 1)) * 100)}%`,
                        }}
                      />
                    </div>
                    <div className="w-16 text-right text-muted-foreground">
                      {(t.views / 1000).toFixed(0)}k
                    </div>
                  </div>
                ))}
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
