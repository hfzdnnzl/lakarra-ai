"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Loader2, Play, RefreshCw } from "lucide-react";

import { useAnalyticsAccount } from "@/components/analytics/AnalyticsShell";
import { PageHeader } from "@/components/page-header";
import { VideoAnalyticsCard } from "@/components/VideoAnalyticsCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { ContentAnalyticsPage } from "@/types";

type SortKey = "publish_date" | "views" | "likes";

const SORT_OPTIONS: { label: string; sort_by: SortKey; sort_order: "asc" | "desc" }[] = [
  { label: "Latest", sort_by: "publish_date", sort_order: "desc" },
  { label: "Oldest", sort_by: "publish_date", sort_order: "asc" },
  { label: "Most Views", sort_by: "views", sort_order: "desc" },
  { label: "Least Views", sort_by: "views", sort_order: "asc" },
  { label: "Most Likes", sort_by: "likes", sort_order: "desc" },
  { label: "Least Likes", sort_by: "likes", sort_order: "asc" },
];

export default function ContentAnalyticsPage() {
  const { configured } = useAnalyticsAccount();
  const [page, setPage] = useState<ContentAnalyticsPage | null>(null);
  const [visualAnalysisProvider, setVisualAnalysisProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<string | null>(null);
  const [expandAll, setExpandAll] = useState(false);

  // Sort / pagination state
  const [sortBy, setSortBy] = useState<SortKey>("publish_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const perPage = 10;

  useEffect(() => {
    void api.health().then((health) => {
      setVisualAnalysisProvider(
        String(health.visual_analysis_provider ?? health.video_analysis_provider ?? "unknown"),
      );
    });
  }, []);

  const load = useCallback(async () => {
    if (!configured) {
      setPage(null);
      return;
    }
    setLoading(true);
    try {
      const contentPage = await api.analyticsContent({
        sort_by: sortBy,
        sort_order: sortOrder,
        page: currentPage,
        per_page: perPage,
      });
      setPage(contentPage);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [configured, sortBy, sortOrder, currentPage]);

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

  const refreshFromTikTok = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const freshPage = await api.analyticsContentRefresh({
        sort_by: sortBy,
        sort_order: sortOrder,
        page: currentPage,
        per_page: perPage,
      });
      setPage(freshPage);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  };

  const handleSortChange = (value: string) => {
    const opt = SORT_OPTIONS.find((o) => o.label === value);
    if (!opt) return;
    setSortBy(opt.sort_by);
    setSortOrder(opt.sort_order);
    setCurrentPage(1); // reset to first page on sort change
  };

  const pagination = page?.pagination;
  const totalPages = pagination?.total_pages ?? 1;
  const videos = page?.videos ?? [];
  const ready = page?.readiness.ready ?? false;

  if (!configured) {
    return (
      <>
        <PageHeader
          title="Content Analytics"
          description="Enter TikTok Studio metrics per post, upload media for full visual analysis, then run AI analysis."
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
        description="Enter TikTok Studio metrics per post, upload the posted media for full visual analysis, then run AI analysis."
        action={
          <div className="flex items-center gap-2">
            <Button onClick={refreshFromTikTok} disabled={refreshing} size="sm" variant="outline">
              {refreshing ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-1.5 h-4 w-4" />
              )}
              Refresh from TikTok
            </Button>
            <Button onClick={analyzeAll} disabled={busy || !ready} size="sm">
              {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Analyze New Videos
            </Button>
          </div>
        }
      />

      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {visualAnalysisProvider === "mock" ? (
        <div className="mb-6 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Visual analysis is running in demo mode (placeholder results). Set{" "}
          <code className="rounded bg-amber-100 px-1">GEMINI_API_KEY</code> and{" "}
          <code className="rounded bg-amber-100 px-1">VISUAL_ANALYSIS_PROVIDER=gemini</code>{" "}
          in the backend, then re-analyze uploaded posts for real visual breakdown.
        </div>
      ) : null}
      {analyzeResult ? (
        <div className="mb-6 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {analyzeResult}
        </div>
      ) : null}

      {!page ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          <span>Loading analytics data…</span>
        </div>
      ) : (
        <>
          {loading ? (
            <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Refreshing data…</span>
            </div>
          ) : null}

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
            <h2 className="text-lg font-semibold">Posts</h2>
            <div className="flex items-center gap-2">
              <select
                className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                value={SORT_OPTIONS.find((o) => o.sort_by === sortBy && o.sort_order === sortOrder)?.label ?? "Latest"}
                onChange={(e) => handleSortChange(e.target.value)}
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.label} value={opt.label}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {videos.length > 0 ? (
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
          </div>

          {videos.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No posts to track yet. Mark content as Posted in the Content library, or wait
              for TikTok content list to load when the data provider is available.
            </p>
          ) : (
            <>
              <div className="space-y-4">
                {videos.map((video) => (
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

              {/* Pagination */}
              {pagination && totalPages > 1 ? (
                <div className="mt-6 flex items-center justify-center gap-4 text-sm">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    Previous
                  </Button>
                  <span className="text-muted-foreground">
                    Page {pagination.page} of {totalPages}
                    <span className="ml-1.5">({pagination.total} total)</span>
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Next
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </>
      )}
    </>
  );
}
