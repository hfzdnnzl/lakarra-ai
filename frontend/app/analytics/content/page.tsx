"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Loader2, Play } from "lucide-react";

import { useAnalyticsAccount } from "@/components/analytics/AnalyticsShell";
import { PageHeader } from "@/components/page-header";
import { VideoAnalyticsCard } from "@/components/VideoAnalyticsCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ContentAnalyticsPage } from "@/types";

export default function ContentAnalyticsPage() {
  const { configured } = useAnalyticsAccount();
  const [page, setPage] = useState<ContentAnalyticsPage | null>(null);
  const [videoAnalysisProvider, setVideoAnalysisProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<string | null>(null);
  const [expandAll, setExpandAll] = useState(true);

  useEffect(() => {
    void api.health().then((health) => {
      setVideoAnalysisProvider(String(health.video_analysis_provider ?? "unknown"));
    });
  }, []);

  const load = useCallback(async () => {
    if (!configured) {
      setPage(null);
      return;
    }
    try {
      const contentPage = await api.analyticsContent();
      setPage(contentPage);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [configured]);

  useEffect(() => {
    void load();
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

  const sortedVideos = useMemo(() => {
    if (!page) return [];
    return [...page.videos].sort((a, b) => {
      if (a.metrics.required_complete === b.metrics.required_complete) {
        return a.title.localeCompare(b.title);
      }
      return a.metrics.required_complete ? 1 : -1;
    });
  }, [page]);

  const ready = page?.readiness.ready ?? false;

  if (!configured) {
    return (
      <>
        <PageHeader
          title="Content Analytics"
          description="Confirm TikTok Studio metrics, upload each video file, then run AI analysis."
        />
        <p className="text-muted-foreground">
          Connect your TikTok account above to manage video metrics.
        </p>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Content Analytics"
        description="Enter TikTok Studio metrics per video, upload the posted video for full visual analysis, then run AI analysis."
        action={
          <Button onClick={analyzeAll} disabled={busy || !ready} size="sm">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            Analyze New Videos
          </Button>
        }
      />

      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {videoAnalysisProvider === "mock" ? (
        <div className="mb-6 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Visual analysis is running in demo mode (placeholder results). Set{" "}
          <code className="rounded bg-amber-100 px-1">GEMINI_API_KEY</code> and{" "}
          <code className="rounded bg-amber-100 px-1">VIDEO_ANALYSIS_PROVIDER=gemini</code>{" "}
          in the backend, then re-analyze uploaded videos for real on-screen text and scene
          breakdown.
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
                  : `Complete required metrics (views, likes, comments, shares, saves) for all videos. ${page.readiness.complete_videos}/${page.readiness.total_videos} complete.`}
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
              <p className="text-muted-foreground">
                Optional metrics (watch time as hh:mm:ss, completion rate as %) are available
                for every video.
              </p>
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

          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Videos</h2>
            {sortedVideos.length > 0 ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setExpandAll((v) => !v)}
              >
                {expandAll ? (
                  <>
                    <ChevronUp className="mr-1.5 h-4 w-4" />
                    Collapse all
                  </>
                ) : (
                  <>
                    <ChevronDown className="mr-1.5 h-4 w-4" />
                    Expand all
                  </>
                )}
              </Button>
            ) : null}
          </div>

          {sortedVideos.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No videos to track yet. Mark content as Posted in the Content library, or wait
              for TikTok video list to load when the data provider is available.
            </p>
          ) : (
            <div className="space-y-4">
              {sortedVideos.map((video) => (
                <VideoAnalyticsCard
                  key={video.video_id}
                  video={video}
                  requiredLabels={page.required_field_labels}
                  optionalLabels={page.optional_field_labels}
                  onUpdated={load}
                  expandAll={expandAll}
                />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
