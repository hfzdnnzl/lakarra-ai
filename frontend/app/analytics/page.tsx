"use client";

import { useCallback, useEffect, useState } from "react";
import { Link2, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { AccountOverview, AccountSettings } from "@/types";

export default function AnalyticsOverviewPage() {
  const [overview, setOverview] = useState<AccountOverview | null>(null);
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [metricsReady, setMetricsReady] = useState<boolean | null>(null);
  const [handleInput, setHandleInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [ov, st, readiness] = await Promise.all([
        api.analyticsOverview(),
        api.analyticsAccountSettings(),
        api.analyticsMetricsReadiness().catch(() => null),
      ]);
      setOverview(ov);
      setSettings(st);
      setHandleInput(st.tiktok_handle ?? "");
      setMetricsReady(readiness?.ready ?? null);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const saveAccount = async () => {
    const trimmed = handleInput.trim().replace(/^@/, "");
    if (!trimmed) {
      setError("Enter your TikTok @handle.");
      return;
    }
    setSaving(true);
    try {
      const st = await api.updateAnalyticsAccount(trimmed);
      setSettings(st);
      setHandleInput(st.tiktok_handle ?? trimmed);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const runAccountAnalysis = async () => {
    if (!settings?.configured) {
      setError("Connect your TikTok account before running analysis.");
      return;
    }
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

  const configured = settings?.configured ?? overview?.account_configured ?? false;

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Marketing intelligence from the Content Analyst agent."
        action={
          <Button onClick={runAccountAnalysis} disabled={busy || !configured || metricsReady === false} size="sm">
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

      <Card className="mb-8 border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4" />
            Connect Your TikTok Account
          </CardTitle>
          <CardDescription>
            Enter the @handle for the TikTok account you want analyzed (without the @).
            The Content Analyst fetches real public video and performance data from TikTok.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="tiktok-handle">TikTok handle</Label>
              <div className="flex">
                <span className="inline-flex items-center rounded-l-md border border-r-0 border-input bg-muted px-3 text-sm text-muted-foreground">
                  @
                </span>
                <Input
                  id="tiktok-handle"
                  value={handleInput}
                  onChange={(e) => setHandleInput(e.target.value)}
                  placeholder="yourbrand"
                  className="rounded-l-none"
                />
              </div>
            </div>
            <Button onClick={saveAccount} disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Save Account
            </Button>
          </div>
          {configured && metricsReady === false ? (
            <p className="mt-3 text-sm text-amber-700">
              Complete required video metrics in{" "}
              <Link href="/analytics/content" className="underline">
                Content Analytics
              </Link>{" "}
              before running account analysis.
            </p>
          ) : null}
          {configured && settings?.tiktok_handle ? (
            <p className="mt-3 text-sm text-emerald-700">
              Connected: @{settings.tiktok_handle}
              {settings.source === "environment" ? " (from environment variable)" : ""}
            </p>
          ) : (
            <p className="mt-3 text-sm text-amber-700">
              No account connected yet. Analysis is disabled until you save your handle.
            </p>
          )}
        </CardContent>
      </Card>

      {!configured ? (
        <p className="text-muted-foreground">
          Connect your TikTok account above to see performance data and run analyses.
        </p>
      ) : !overview ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (
        <>
          {overview.tiktok_handle ? (
            <p className="mb-4 text-sm text-muted-foreground">
              Showing data for @{overview.tiktok_handle}
            </p>
          ) : null}
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
