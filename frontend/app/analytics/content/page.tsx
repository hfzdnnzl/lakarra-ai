"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Play } from "lucide-react";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { PageHeader } from "@/components/page-header";
import { VideoAnalyticsCard } from "@/components/VideoAnalyticsCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ContentAnalyticsPage } from "@/types";

export default function ContentAnalyticsPage() {
  const [page, setPage] = useState<ContentAnalyticsPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setPage(await api.analyticsContent());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const analyzeAll = async () => {
    if (!page?.readiness.ready) {
      setError("Complete required metrics for all videos before running bulk analysis.");
      return;
    }
    setBusy(true);
    setAnalyzeResult(null);
    try {
      const result = await api.analyzeAllVideos();
      setAnalyzeResult(
        `Analyzed ${result.analyzed.length} video(s), skipped ${result.skipped_video_ids.length} already analyzed.`,
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const ready = page?.readiness.ready ?? false;

  return (
    <>
      <PageHeader
        title="Content Analytics"
        description="Confirm TikTok Studio metrics, then run AI analysis on your videos."
        action={
          <Button onClick={analyzeAll} disabled={busy || !ready} size="sm">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            Analyze New Videos
          </Button>
        }
      />
      <AnalyticsNav />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {analyzeResult ? (
        <div className="mb-6 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {analyzeResult}
        </div>
      ) : null}

      {!page ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : (
        <>
          <Card className={`mb-8 ${ready ? "border-emerald-200" : "border-amber-200"}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Metrics readiness</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                {ready
                  ? "All videos have required metrics. Account-level analytics and bulk analysis are enabled."
                  : `Complete required metrics (views, likes, comments, shares, saves) for all videos before account analytics. ${page.readiness.complete_videos}/${page.readiness.total_videos} complete.`}
              </p>
              {!ready && page.readiness.incomplete_videos.length > 0 ? (
                <ul className="list-inside list-disc text-muted-foreground">
                  {page.readiness.incomplete_videos.slice(0, 5).map((v) => (
                    <li key={v.video_id}>
                      {v.title} — missing: {v.missing_required.join(", ")}
                    </li>
                  ))}
                </ul>
              ) : null}
              {page.readiness.optional_recommended_for.length > 0 ? (
                <p className="text-muted-foreground">
                  Tip: add optional metrics for your best and worst performers — total watch
                  time as hh:mm:ss (e.g. 1:23:45) and completion rate as a percentage.
                </p>
              ) : null}
            </CardContent>
          </Card>

          {ready ? (
            <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">Account Health</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold">
                    {(page.overview.account_health_score * 100).toFixed(0)}%
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">Total Videos</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold">{page.overview.total_videos}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">Total Views</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold">
                    {page.overview.total_views.toLocaleString()}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">Analyzed</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold">
                    {page.videos.filter((v) => v.is_analyzed).length}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : null}

          <h2 className="mb-4 text-lg font-semibold">Videos</h2>
          {page.videos.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No videos to track yet. Mark content as Posted in the Content library, or wait
              for TikTok video list to load when the data provider is available.
            </p>
          ) : (
          <div className="space-y-4">
            {page.videos.map((video) => (
              <VideoAnalyticsCard
                key={video.video_id}
                video={video}
                requiredLabels={page.required_field_labels}
                optionalLabels={page.optional_field_labels}
                onUpdated={load}
              />
            ))}
          </div>
          )}
        </>
      )}
    </>
  );
}
